/* SPDX-License-Identifier: MIT */

#include "smp.h"
#include "types.h"

#include "../../src/boot/m1n1_handoff.h"

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
    if (!input)
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
