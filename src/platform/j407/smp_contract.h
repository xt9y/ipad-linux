#pragma once

#include <stddef.h>

#include "boot_info.h"
#include "linux_fdt.h"
#include "memory.h"

struct j407_smp_patch {
    struct linux_fdt_cpu_release entries[IPL_MAX_CPU_RELEASES];
    size_t count;
};

/*
 * Translate loader-provided T8103 MPIDR/release-slot pairs into exact Linux
 * DT node paths. This only describes the handoff; it never starts/stops CPUs
 * or touches Apple CPU/PMGR registers.
 *
 * Release slots must live outside the RAM range advertised as usable to
 * Linux; otherwise the allocator could overwrite the holding-pen target.
 */
int j407_build_smp_patch(const struct boot_info *boot,
                         struct memory_range linux_ram,
                         struct j407_smp_patch *out);
