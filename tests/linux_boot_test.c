#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "boot_plan.h"
#include "linux_image.h"

static void put_u32le(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 0);
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static void put_u64le(uint8_t *p, uint64_t v)
{
    put_u32le(p, (uint32_t)v);
    put_u32le(p + 4, (uint32_t)(v >> 32));
}

int main(void)
{
    uint8_t image[64] = {0};
    put_u64le(image + 8, 0x80000);
    put_u64le(image + 16, 0x1000000);
    put_u64le(image + 24, 0);
    put_u32le(image + 56, ARM64_IMAGE_MAGIC);

    struct linux_image_info info;
    assert(linux_image_parse(image, sizeof(image), &info));
    assert(info.text_offset == 0x80000);
    assert(info.image_size == 0x1000000);

    struct linux_boot_plan plan = {
        .ram = { .base = 0x800000000ull, .size = 0x40000000ull },
        .kernel_addr = 0x800080000ull,
        .kernel_buffer_size = 0x1000000ull,
        .dtb_addr = 0x801200000ull,
        .dtb_size = 0x10000,
        .current_el = 2,
        .mmu_enabled = 0,
        .image = info,
    };

    assert(linux_boot_plan_validate(&plan));

    plan.mmu_enabled = 1;
    assert(!linux_boot_plan_validate(&plan));
    plan.mmu_enabled = 0;

    plan.current_el = 0;
    assert(!linux_boot_plan_validate(&plan));

    puts("linux boot tests passed");
    return 0;
}
