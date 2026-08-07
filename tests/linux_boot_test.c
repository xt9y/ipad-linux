#include <assert.h>
#include <stdint.h>
#include <stdio.h>

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

static struct linux_image_info make_image_info(void)
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
    return info;
}

static struct linux_boot_plan make_plan(struct linux_image_info info)
{
    struct linux_boot_plan plan = {
        .ram = { .base = 0x800000000ull, .size = 0x40000000ull },
        .kernel_addr = 0x800080000ull,
        .kernel_buffer_size = 0x1000000ull,
        .dtb_addr = 0x801200000ull,
        .dtb_size = 0x10000,
        .initrd_addr = 0,
        .initrd_size = 0,
        .current_el = 2,
        .mmu_enabled = 0,
        .image = info,
    };
    return plan;
}

int main(void)
{
    struct linux_image_info info = make_image_info();
    struct linux_boot_plan plan = make_plan(info);

    assert(linux_boot_plan_validate(&plan));

    plan.mmu_enabled = 1;
    assert(!linux_boot_plan_validate(&plan));
    plan.mmu_enabled = 0;

    plan.current_el = 0;
    assert(!linux_boot_plan_validate(&plan));
    plan.current_el = 2;

    plan.dtb_addr = plan.kernel_addr + 0x1000;
    assert(!linux_boot_plan_validate(&plan));
    plan.dtb_addr = 0x801200000ull;

    plan.initrd_addr = 0x802000000ull;
    plan.initrd_size = 0x800000;
    assert(linux_boot_plan_validate(&plan));

    plan.initrd_addr = plan.kernel_addr + 0x200000;
    assert(!linux_boot_plan_validate(&plan));
    plan.initrd_addr = 0x802000000ull;

    plan.initrd_size = 0;
    assert(!linux_boot_plan_validate(&plan));
    plan.initrd_addr = 0;

    plan.image.flags = 1;
    assert(!linux_boot_plan_validate(&plan));
    plan.image.flags = 0;

    /* A physical-placement Image (flags bit 3) must remain below 2^48. */
    plan = make_plan(info);
    plan.ram.base = 1ull << 48;
    plan.ram.size = 0x40000000ull;
    plan.kernel_addr = (1ull << 48) + 0x80000ull;
    plan.dtb_addr = (1ull << 48) + 0x1200000ull;
    plan.image.flags = 1ull << 3;
    assert(!linux_boot_plan_validate(&plan));

    /* initrd and Image must fit one <=32 GiB window with a 1 GiB-aligned base. */
    plan = make_plan(info);
    plan.ram.base = 0;
    plan.ram.size = 0x1000000000ull; /* 64 GiB */
    plan.kernel_addr = 0x80000ull;
    plan.dtb_addr = 0x02000000ull;
    plan.initrd_addr = 0x840000000ull; /* 33 GiB */
    plan.initrd_size = 0x100000ull;
    assert(!linux_boot_plan_validate(&plan));

    puts("linux boot tests passed");
    return 0;
}
