#pragma once

#include <stddef.h>
#include <stdint.h>

#include "memory.h"

struct linux_fdt_runtime {
    /* Exact node path in the precompiled DTB, e.g. /memory@800000000. */
    const char *memory_path;
    struct memory_range ram;

    /* Zero/zero means no initrd. */
    uint64_t initrd_addr;
    uint64_t initrd_size;
};

/*
 * Patch fixed-size placeholders in a writable, precompiled Linux FDT.
 *
 * Required placeholders:
 *   <memory_path>/reg        16 bytes (#address-cells=2, #size-cells=2)
 *
 * When an initrd is present:
 *   /chosen/linux,initrd-start   8 bytes
 *   /chosen/linux,initrd-end     8 bytes
 *
 * The function never grows or relocates the FDT. Failure means the caller
 * must not hand the blob to Linux. A failed call is not transactional: an
 * earlier property may already have been patched.
 */
int linux_fdt_patch_runtime(void *dtb, size_t available,
                            const struct linux_fdt_runtime *runtime);
