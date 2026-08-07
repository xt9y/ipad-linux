#include "linux_layout.h"

#include <stdint.h>

#include "boot_plan.h"

#define TWO_MIB (2ull * 1024ull * 1024ull)
#define SIXTY_FOUR_KIB (64ull * 1024ull)
#define DTB_MAX_SIZE (2ull * 1024ull * 1024ull)

static int align_up_checked(uint64_t value, uint64_t alignment, uint64_t *out)
{
    if (!out || !alignment || (alignment & (alignment - 1)) != 0)
        return 0;

    uint64_t add = alignment - 1;
    if (value > UINT64_MAX - add)
        return 0;

    *out = (value + add) & ~add;
    return 1;
}

static int add_checked(uint64_t a, uint64_t b, uint64_t *out)
{
    if (!out || a > UINT64_MAX - b)
        return 0;
    *out = a + b;
    return 1;
}

int linux_layout_plan(const struct linux_layout_request *request,
                      struct linux_artifact_layout *out)
{
    uint64_t kernel_base;
    uint64_t kernel_addr;
    uint64_t kernel_effective_size;
    uint64_t cursor;
    uint64_t initrd_addr = 0;
    uint64_t dtb_addr;

    if (!request || !out || !memory_range_valid(request->ram) ||
        !request->kernel_buffer_size || !request->dtb_size ||
        request->dtb_size > DTB_MAX_SIZE)
        return 0;

    kernel_effective_size = request->image.image_size;
    if (!kernel_effective_size)
        kernel_effective_size = request->kernel_buffer_size;

    if (!kernel_effective_size ||
        kernel_effective_size > request->kernel_buffer_size)
        return 0;

    if (!align_up_checked(request->ram.base, TWO_MIB, &kernel_base) ||
        !add_checked(kernel_base, request->image.text_offset, &kernel_addr) ||
        !memory_range_contains(request->ram, kernel_addr, kernel_effective_size) ||
        !add_checked(kernel_addr, kernel_effective_size, &cursor))
        return 0;

    if (request->initrd_size) {
        if (!align_up_checked(cursor, SIXTY_FOUR_KIB, &initrd_addr) ||
            !memory_range_contains(request->ram, initrd_addr, request->initrd_size) ||
            !add_checked(initrd_addr, request->initrd_size, &cursor))
            return 0;
    }

    if (!align_up_checked(cursor, 8, &dtb_addr) ||
        !memory_range_contains(request->ram, dtb_addr, request->dtb_size))
        return 0;

    struct linux_boot_plan check = {
        .ram = request->ram,
        .kernel_addr = kernel_addr,
        .kernel_buffer_size = request->kernel_buffer_size,
        .dtb_addr = dtb_addr,
        .dtb_size = request->dtb_size,
        .initrd_addr = initrd_addr,
        .initrd_size = request->initrd_size,
        .current_el = 2,
        .mmu_enabled = 0,
        .image = request->image,
    };

    if (!linux_boot_plan_validate(&check))
        return 0;

    out->kernel_addr = kernel_addr;
    out->kernel_effective_size = kernel_effective_size;
    out->dtb_addr = dtb_addr;
    out->initrd_addr = initrd_addr;
    return 1;
}
