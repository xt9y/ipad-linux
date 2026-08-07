#pragma once

#include <stdint.h>

#include "linux_image.h"
#include "memory.h"

struct linux_boot_plan {
    struct memory_range ram;
    uint64_t kernel_addr;
    uint64_t kernel_buffer_size;
    uint64_t dtb_addr;
    uint64_t dtb_size;
    uint64_t initrd_addr;
    uint64_t initrd_size;
    uint64_t current_el;
    int mmu_enabled;
    struct linux_image_info image;
};

int linux_boot_plan_validate(const struct linux_boot_plan *plan);
