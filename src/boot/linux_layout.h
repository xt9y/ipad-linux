#pragma once

#include <stdint.h>

#include "linux_image.h"
#include "memory.h"

struct linux_layout_request {
    struct memory_range ram;
    struct linux_image_info image;
    uint64_t kernel_buffer_size;
    uint64_t dtb_size;
    uint64_t initrd_size;
};

struct linux_artifact_layout {
    uint64_t kernel_addr;
    uint64_t kernel_effective_size;
    uint64_t dtb_addr;
    uint64_t initrd_addr;
};

/*
 * Choose a conservative physical layout inside the RAM range already deemed
 * usable by the entry loader. The kernel is placed from the lowest suitable
 * 2 MiB base, followed by the optional initrd and then the DTB.
 *
 * No memory is allocated or written here. The result is revalidated through
 * linux_boot_plan_validate() before it is returned.
 */
int linux_layout_plan(const struct linux_layout_request *request,
                      struct linux_artifact_layout *out);
