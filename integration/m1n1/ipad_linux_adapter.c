/* SPDX-License-Identifier: MIT */

#include "adt.h"
#include "malloc.h"
#include "memory.h"
#include "smp.h"
#include "soc.h"
#include "types.h"
#include "utils.h"
#include "xnuboot.h"

#include "../../src/boot/m1n1_handoff.h"

#define J407_BOARD_ID 0x10u

static int j407_mpidr_known(u64 mpidr)
{
    switch (mpidr) {
        case 0x00000:
        case 0x00001:
        case 0x00002:
        case 0x00003:
        case 0x10100:
        case 0x10101:
        case 0x10102:
        case 0x10103:
            return 1;
        default:
            return 0;
    }
}

/*
 * Collect the SMP state that upstream m1n1 already establishes for Linux.
 *
 * J407 has eight CPUs and m1n1 indexes the T8103 CPU table by cpu-id. The
 * Stage-2 J407 contract validates the MPIDR set again, so any unexpected ADT
 * layout fails closed instead of silently patching the wrong Linux CPU node.
 */
int ipad_linux_m1n1_collect_j407_smp(struct m1n1_handoff_input *input)
{
    if (!input || chip_id != T8103 || board_id != J407_BOARD_ID)
        return 0;

    smp_start_secondaries();

    for (int cpu = 0; cpu < (int)IPL_MAX_CPU_RELEASES; ++cpu) {
        u64 mpidr = smp_get_mpidr(cpu);
        u64 release_addr = smp_get_release_addr(cpu);

        if (!j407_mpidr_known(mpidr) || !release_addr)
            return 0;

        input->cpus[cpu].mpidr = mpidr;
        input->cpus[cpu].release_addr = release_addr;
    }

    input->cpu_count = IPL_MAX_CPU_RELEASES;

    /* Match m1n1 kboot: Linux releases secondaries with writes + SEV. */
    smp_set_wfe_mode(true);
    return 1;
}

/*
 * Fill the parts of the handoff which are authoritative in m1n1 itself.
 *
 * startup.c converts Apple's virtual boot_args.devtree pointer into the
 * physical global `adt`, and cur_boot_args.phys_base/mem_size are the exact
 * usable range m1n1's own kboot exposes to Linux.
 *
 * `mmu_enabled` describes the state at next_stage entry, not the state while
 * this function is running. m1n1_main() always executes mmu_shutdown() before
 * calling next_stage.entry. The ipad-linux payload verifies SCTLR again after
 * entry, so a future upstream behavior change still fails closed.
 */
int ipad_linux_m1n1_seed_environment(struct m1n1_handoff_input *input)
{
    if (!input || chip_id != T8103 || board_id != J407_BOARD_ID ||
        !cur_boot_args.phys_base || !cur_boot_args.mem_size ||
        !adt || !cur_boot_args.devtree_size)
        return 0;

    input->memory_base = cur_boot_args.phys_base;
    input->memory_size = cur_boot_args.mem_size;
    input->adt_addr = (u64)adt;
    input->adt_size = cur_boot_args.devtree_size;
    input->current_el = mrs(CurrentEL) >> 2;
    input->mmu_enabled = 0;

    /*
     * m1n1_main() performs the same shutdown path before every next_stage:
     * NVMe, exception state, USB, display/framebuffer and MMU are shut down.
     */
    input->platform_quiesced = 1;
    return input->current_el == 1 || input->current_el == 2;
}

/*
 * Finalize the J407 handoff and schedule the relocatable ipad-linux payload as
 * m1n1's next stage. The caller supplies already-loaded Linux artifacts and a
 * writable DTB in `input`; this function supplies live platform/SMP state.
 *
 * The boot_info allocation intentionally uses m1n1's own allocator. Upstream
 * kboot uses memalign() for its final FDT and passes that same pointer through
 * mmu_shutdown() into Linux, so we use the identical lifetime/address model.
 */
int ipad_linux_m1n1_schedule(struct m1n1_handoff_input *input)
{
    if (!input || !input->payload_addr || !input->payload_size ||
        !input->linux_image_addr || !input->linux_image_size ||
        !input->dtb_addr || !input->dtb_size)
        return 0;

    if (!ipad_linux_m1n1_seed_environment(input) ||
        !ipad_linux_m1n1_collect_j407_smp(input))
        return 0;

    input->dtb_mutable = 1;

    struct boot_info *boot = memalign(16, sizeof(*boot));
    if (!boot || !m1n1_handoff_build(input, boot)) {
        if (boot)
            free(boot);
        return 0;
    }

    /* Make freshly populated next-stage data/code visible before MMU shutdown. */
    dc_cvac_range(boot, sizeof(*boot));
    dc_cvau_range((void *)input->payload_addr, input->payload_size);
    ic_ivau_range((void *)input->payload_addr, input->payload_size);
    sysop("dsb sy");
    sysop("isb");

    next_stage.entry = (generic_func *)input->payload_addr;
    next_stage.args[0] = (u64)boot;
    next_stage.args[1] = 0;
    next_stage.args[2] = 0;
    next_stage.args[3] = 0;
    next_stage.args[4] = 0;
    next_stage.restore_logo = false;

    return 1;
}
