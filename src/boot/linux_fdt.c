#include "linux_fdt.h"

#include "fdt.h"

int linux_fdt_patch_runtime(void *dtb, size_t available,
                            const struct linux_fdt_runtime *runtime)
{
    size_t total = 0;

    if (!dtb || !runtime || !runtime->memory_path ||
        !memory_range_valid(runtime->ram) ||
        !fdt_check_header(dtb, available, &total))
        return 0;

    if ((runtime->initrd_addr == 0) != (runtime->initrd_size == 0))
        return 0;

    if (runtime->initrd_size &&
        !memory_range_contains(runtime->ram,
                               runtime->initrd_addr,
                               runtime->initrd_size))
        return 0;

    uint64_t initrd_end = 0;
    if (runtime->initrd_size) {
        initrd_end = runtime->initrd_addr + runtime->initrd_size;
        if (initrd_end < runtime->initrd_addr)
            return 0;
    }

    if (!fdt_setprop_u64_pair_inplace(dtb, total,
                                      runtime->memory_path, "reg",
                                      runtime->ram.base,
                                      runtime->ram.size))
        return 0;

    /*
     * Mutable templates always carry these placeholders. Patch them even
     * without an initrd so a reused DTB can never retain stale addresses.
     */
    if (!fdt_setprop_u64_inplace(dtb, total,
                                 "/chosen", "linux,initrd-start",
                                 runtime->initrd_addr))
        return 0;

    if (!fdt_setprop_u64_inplace(dtb, total,
                                 "/chosen", "linux,initrd-end",
                                 initrd_end))
        return 0;

    return 1;
}

int linux_fdt_patch_cpu_releases(void *dtb, size_t available,
                                 const struct linux_fdt_cpu_release *cpus,
                                 size_t cpu_count)
{
    size_t total = 0;

    if (!dtb || (!cpus && cpu_count) ||
        !fdt_check_header(dtb, available, &total))
        return 0;

    for (size_t i = 0; i < cpu_count; ++i) {
        if (!cpus[i].cpu_path || !cpus[i].release_addr)
            return 0;

        if (!fdt_setprop_u64_inplace(dtb, total,
                                     cpus[i].cpu_path,
                                     "cpu-release-addr",
                                     cpus[i].release_addr))
            return 0;
    }

    return 1;
}
