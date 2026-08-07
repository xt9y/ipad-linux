#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "boot_info.h"
#include "smp_contract.h"

static void fill_valid(struct boot_info *boot)
{
    static const uint64_t mpidrs[IPL_MAX_CPU_RELEASES] = {
        0x00000ull, 0x00001ull, 0x00002ull, 0x00003ull,
        0x10100ull, 0x10101ull, 0x10102ull, 0x10103ull,
    };

    memset(boot, 0, sizeof(*boot));
    boot->flags = BOOT_INFO_HAS_CPU_RELEASES;
    boot->cpu_release_count = IPL_MAX_CPU_RELEASES;

    for (uint32_t i = 0; i < IPL_MAX_CPU_RELEASES; ++i) {
        boot->cpu_releases[i].mpidr = mpidrs[i];
        boot->cpu_releases[i].release_addr = 0x900000000ull + (uint64_t)i * 0x40ull;
    }
}

int main(void)
{
    struct boot_info boot;
    struct j407_smp_patch patch;

    fill_valid(&boot);
    assert(j407_build_smp_patch(&boot, &patch));
    assert(patch.count == IPL_MAX_CPU_RELEASES);
    assert(patch.entries[0].release_addr == 0x900000000ull);
    assert(patch.entries[4].release_addr == 0x900000100ull);

    fill_valid(&boot);
    boot.cpu_release_count = IPL_MAX_CPU_RELEASES - 1;
    assert(!j407_build_smp_patch(&boot, &patch));

    fill_valid(&boot);
    boot.cpu_releases[7].mpidr = 0xdeadbeefull;
    assert(!j407_build_smp_patch(&boot, &patch));

    fill_valid(&boot);
    boot.cpu_releases[7].mpidr = boot.cpu_releases[6].mpidr;
    assert(!j407_build_smp_patch(&boot, &patch));

    fill_valid(&boot);
    boot.cpu_releases[7].release_addr = boot.cpu_releases[6].release_addr;
    assert(!j407_build_smp_patch(&boot, &patch));

    fill_valid(&boot);
    boot.cpu_releases[7].release_addr |= 4ull;
    assert(!j407_build_smp_patch(&boot, &patch));

    fill_valid(&boot);
    boot.flags = 0;
    assert(!j407_build_smp_patch(&boot, &patch));

    puts("J407 SMP contract tests passed");
    return 0;
}
