#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "boot_info.h"
#include "m1n1_handoff.h"

static struct m1n1_handoff_input valid_input(void)
{
    struct m1n1_handoff_input in;
    memset(&in, 0, sizeof(in));

    in.memory_base = 0x800000000ull;
    in.memory_size = 0x40000000ull;
    in.adt_addr = 0x900000000ull;
    in.adt_size = 0x20000ull;
    in.payload_addr = 0x900100000ull;
    in.payload_size = 0x100000ull;
    in.current_el = 2;
    in.linux_image_addr = 0x800080000ull;
    in.linux_image_size = 0x2000000ull;
    in.dtb_addr = 0x820000000ull;
    in.dtb_size = 0x20000ull;
    in.initrd_addr = 0x821000000ull;
    in.initrd_size = 0x1000000ull;
    in.platform_quiesced = 1;
    in.dtb_mutable = 1;
    in.cpu_count = IPL_MAX_CPU_RELEASES;

    static const uint64_t mpidrs[IPL_MAX_CPU_RELEASES] = {
        0x00000ull, 0x00001ull, 0x00002ull, 0x00003ull,
        0x10100ull, 0x10101ull, 0x10102ull, 0x10103ull,
    };

    for (uint32_t i = 0; i < IPL_MAX_CPU_RELEASES; ++i) {
        in.cpus[i].mpidr = mpidrs[i];
        in.cpus[i].release_addr = 0x900200000ull + (uint64_t)i * 0x40ull;
    }

    return in;
}

int main(void)
{
    struct boot_info out;
    struct m1n1_handoff_input in = valid_input();

    assert(m1n1_handoff_build(&in, &out));
    assert(boot_info_valid(&out));
    assert(out.version == IPL_BOOT_INFO_VERSION);
    assert(out.flags & BOOT_INFO_HAS_ADT);
    assert(out.flags & BOOT_INFO_HAS_LINUX_IMAGE);
    assert(out.flags & BOOT_INFO_HAS_DTB);
    assert(out.flags & BOOT_INFO_HAS_INITRD);
    assert(out.flags & BOOT_INFO_PLATFORM_QUIESCED);
    assert(out.flags & BOOT_INFO_DTB_MUTABLE);
    assert(out.flags & BOOT_INFO_HAS_CPU_RELEASES);
    assert(out.cpu_release_count == IPL_MAX_CPU_RELEASES);

    in = valid_input();
    in.current_el = 0;
    assert(!m1n1_handoff_build(&in, &out));

    in = valid_input();
    in.dtb_size = 0;
    assert(!m1n1_handoff_build(&in, &out));

    in = valid_input();
    in.cpu_count = IPL_MAX_CPU_RELEASES + 1;
    assert(!m1n1_handoff_build(&in, &out));

    in = valid_input();
    in.cpus[7].release_addr = 0;
    assert(!m1n1_handoff_build(&in, &out));

    in = valid_input();
    in.debug_ctx = 1;
    assert(!m1n1_handoff_build(&in, &out));

    puts("m1n1 handoff builder tests passed");
    return 0;
}
