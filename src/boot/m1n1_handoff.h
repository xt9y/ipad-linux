#pragma once

#include <stdint.h>

#include "boot_info.h"

struct m1n1_handoff_input {
    uint64_t memory_base;
    uint64_t memory_size;

    uint64_t adt_addr;
    uint64_t adt_size;

    uint64_t payload_addr;
    uint64_t payload_size;

    uint64_t current_el;
    int mmu_enabled;

    uint64_t debug_write_addr;
    uint64_t debug_ctx;

    uint64_t linux_image_addr;
    uint64_t linux_image_size;
    uint64_t dtb_addr;
    uint64_t dtb_size;
    uint64_t initrd_addr;
    uint64_t initrd_size;

    int platform_quiesced;
    int dtb_mutable;

    uint32_t cpu_count;
    struct boot_cpu_release cpus[IPL_MAX_CPU_RELEASES];
};

/*
 * Build the versioned ipad-linux entry ABI from information an m1n1-style
 * stage-1 already owns. This function performs consistency checks only; it
 * does not start CPUs, quiesce devices, change EL/MMU state or branch away.
 */
int m1n1_handoff_build(const struct m1n1_handoff_input *input,
                       struct boot_info *out);
