#pragma once

#include <stdint.h>

#define IPL_BOOT_INFO_MAGIC 0x495041444C4E5831ULL /* "IPADLNX1" */
#define IPL_BOOT_INFO_VERSION 1u

enum boot_info_flags {
    BOOT_INFO_HAS_ADT = 1u << 0,
    BOOT_INFO_MMU_ENABLED = 1u << 1,
};

struct boot_info {
    uint64_t magic;
    uint32_t version;
    uint32_t size;

    uint64_t flags;

    uint64_t memory_base;
    uint64_t memory_size;

    uint64_t adt_addr;
    uint64_t adt_size;

    uint64_t image_base;
    uint64_t image_size;

    uint64_t current_el;
    uint64_t reserved[7];
};

static inline int boot_info_valid(const struct boot_info *info)
{
    return info &&
           info->magic == IPL_BOOT_INFO_MAGIC &&
           info->version == IPL_BOOT_INFO_VERSION &&
           info->size >= sizeof(struct boot_info);
}
