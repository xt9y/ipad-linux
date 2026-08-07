#include "smp_contract.h"

#include <stdint.h>

struct cpu_path_map {
    uint64_t mpidr;
    const char *path;
};

static const struct cpu_path_map cpu_paths[IPL_MAX_CPU_RELEASES] = {
    { 0x00000ull, "/cpus/cpu@0" },
    { 0x00001ull, "/cpus/cpu@1" },
    { 0x00002ull, "/cpus/cpu@2" },
    { 0x00003ull, "/cpus/cpu@3" },
    { 0x10100ull, "/cpus/cpu@10100" },
    { 0x10101ull, "/cpus/cpu@10101" },
    { 0x10102ull, "/cpus/cpu@10102" },
    { 0x10103ull, "/cpus/cpu@10103" },
};

static const char *cpu_path_for_mpidr(uint64_t mpidr)
{
    for (size_t i = 0; i < IPL_MAX_CPU_RELEASES; ++i) {
        if (cpu_paths[i].mpidr == mpidr)
            return cpu_paths[i].path;
    }

    return 0;
}

int j407_build_smp_patch(const struct boot_info *boot,
                         struct j407_smp_patch *out)
{
    if (!boot || !out || !(boot->flags & BOOT_INFO_HAS_CPU_RELEASES))
        return 0;

    /* J407/T8103 has four Icestorm + four Firestorm CPUs. */
    if (boot->cpu_release_count != IPL_MAX_CPU_RELEASES)
        return 0;

    out->count = 0;

    for (uint32_t i = 0; i < boot->cpu_release_count; ++i) {
        const struct boot_cpu_release *source = &boot->cpu_releases[i];
        const char *path = cpu_path_for_mpidr(source->mpidr);

        if (!path || !source->release_addr || (source->release_addr & 7ull))
            return 0;

        for (uint32_t j = 0; j < i; ++j) {
            if (boot->cpu_releases[j].mpidr == source->mpidr ||
                boot->cpu_releases[j].release_addr == source->release_addr)
                return 0;
        }

        out->entries[out->count].cpu_path = path;
        out->entries[out->count].release_addr = source->release_addr;
        out->count++;
    }

    return out->count == IPL_MAX_CPU_RELEASES;
}
