#include "m1n1_handoff.h"

#include <stddef.h>
#include <stdint.h>

static void zero_bytes(void *ptr, size_t size)
{
    uint8_t *p = (uint8_t *)ptr;
    for (size_t i = 0; i < size; ++i)
        p[i] = 0;
}

static int pair_valid(uint64_t addr, uint64_t size)
{
    return (addr == 0 && size == 0) ||
           (addr != 0 && size != 0 && addr + size >= addr);
}

int m1n1_handoff_build(const struct m1n1_handoff_input *input,
                       struct boot_info *out)
{
    if (!input || !out)
        return 0;

    if (!input->memory_size || input->memory_base + input->memory_size < input->memory_base)
        return 0;

    if (input->current_el != 1 && input->current_el != 2)
        return 0;

    if (!pair_valid(input->adt_addr, input->adt_size) ||
        !pair_valid(input->payload_addr, input->payload_size) ||
        !pair_valid(input->linux_image_addr, input->linux_image_size) ||
        !pair_valid(input->dtb_addr, input->dtb_size) ||
        !pair_valid(input->initrd_addr, input->initrd_size))
        return 0;

    if (input->debug_ctx && !input->debug_write_addr)
        return 0;

    if (input->dtb_mutable && !input->dtb_addr)
        return 0;

    if (input->cpu_count > IPL_MAX_CPU_RELEASES)
        return 0;

    zero_bytes(out, sizeof(*out));

    out->magic = IPL_BOOT_INFO_MAGIC;
    out->version = IPL_BOOT_INFO_VERSION;
    out->size = sizeof(*out);

    out->memory_base = input->memory_base;
    out->memory_size = input->memory_size;

    out->adt_addr = input->adt_addr;
    out->adt_size = input->adt_size;
    if (input->adt_addr)
        out->flags |= BOOT_INFO_HAS_ADT;

    out->image_base = input->payload_addr;
    out->image_size = input->payload_size;
    out->current_el = input->current_el;
    if (input->mmu_enabled)
        out->flags |= BOOT_INFO_MMU_ENABLED;

    out->debug_write_addr = input->debug_write_addr;
    out->debug_ctx = input->debug_ctx;
    if (input->debug_write_addr)
        out->flags |= BOOT_INFO_HAS_DEBUG_WRITE;

    out->linux_image_addr = input->linux_image_addr;
    out->linux_image_size = input->linux_image_size;
    if (input->linux_image_addr)
        out->flags |= BOOT_INFO_HAS_LINUX_IMAGE;

    out->dtb_addr = input->dtb_addr;
    out->dtb_size = input->dtb_size;
    if (input->dtb_addr)
        out->flags |= BOOT_INFO_HAS_DTB;

    out->initrd_addr = input->initrd_addr;
    out->initrd_size = input->initrd_size;
    if (input->initrd_addr)
        out->flags |= BOOT_INFO_HAS_INITRD;

    if (input->platform_quiesced)
        out->flags |= BOOT_INFO_PLATFORM_QUIESCED;
    if (input->dtb_mutable)
        out->flags |= BOOT_INFO_DTB_MUTABLE;

    out->cpu_release_count = input->cpu_count;
    for (uint32_t i = 0; i < input->cpu_count; ++i) {
        if (!input->cpus[i].release_addr)
            return 0;
        out->cpu_releases[i] = input->cpus[i];
    }
    if (input->cpu_count)
        out->flags |= BOOT_INFO_HAS_CPU_RELEASES;

    return boot_info_valid(out);
}
