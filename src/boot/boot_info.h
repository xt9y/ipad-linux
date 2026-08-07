#pragma once

#include <stdint.h>

#define IPL_BOOT_INFO_MAGIC 0x495041444C4E5831ULL /* "IPADLNX1" */
#define IPL_BOOT_INFO_VERSION 4u
#define IPL_MAX_CPU_RELEASES 8u

enum boot_info_flags {
    BOOT_INFO_HAS_ADT = 1u << 0,
    BOOT_INFO_MMU_ENABLED = 1u << 1,
    BOOT_INFO_HAS_DEBUG_WRITE = 1u << 2,
    BOOT_INFO_HAS_LINUX_IMAGE = 1u << 3,
    BOOT_INFO_HAS_DTB = 1u << 4,
    BOOT_INFO_HAS_INITRD = 1u << 5,
    BOOT_INFO_PLATFORM_QUIESCED = 1u << 6,
    /* DTB is writable and contains the fixed-size runtime placeholders. */
    BOOT_INFO_DTB_MUTABLE = 1u << 7,
    /* cpu_releases[] contains loader-owned spin-table release slots. */
    BOOT_INFO_HAS_CPU_RELEASES = 1u << 8,
};

/* Optional loader-provided debug callback ABI. */
typedef void (*boot_debug_write_fn)(const char *data, uint64_t size, void *ctx);

struct boot_cpu_release {
    /* Linux/DT MPIDR value with non-affinity/reserved bits already cleared. */
    uint64_t mpidr;
    /* Physical address of the loader's 64-bit spin-table target slot. */
    uint64_t release_addr;
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

    /* Address/size of this ipad-linux payload, if known. */
    uint64_t image_base;
    uint64_t image_size;

    uint64_t current_el;

    uint64_t debug_write_addr;
    uint64_t debug_ctx;

    /* Optional preloaded Linux artifacts supplied by the entry loader. */
    uint64_t linux_image_addr;
    uint64_t linux_image_size;
    uint64_t dtb_addr;
    uint64_t dtb_size;
    uint64_t initrd_addr;
    uint64_t initrd_size;

    uint32_t cpu_release_count;
    uint32_t cpu_release_reserved;
    struct boot_cpu_release cpu_releases[IPL_MAX_CPU_RELEASES];

    uint64_t reserved[4];
};

static inline int boot_info_valid(const struct boot_info *info)
{
    return info &&
           info->magic == IPL_BOOT_INFO_MAGIC &&
           info->version == IPL_BOOT_INFO_VERSION &&
           info->size >= sizeof(struct boot_info) &&
           info->cpu_release_count <= IPL_MAX_CPU_RELEASES;
}
