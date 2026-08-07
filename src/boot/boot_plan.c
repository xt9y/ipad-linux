#include "boot_plan.h"

#define TWO_MIB (2ull * 1024ull * 1024ull)
#define ONE_GIB (1024ull * 1024ull * 1024ull)
#define THIRTY_TWO_GIB (32ull * ONE_GIB)
#define PHYS_48BIT_LIMIT (1ull << 48)

static int aligned(uint64_t value, uint64_t alignment)
{
    return alignment && (alignment & (alignment - 1)) == 0 &&
           (value & (alignment - 1)) == 0;
}

static int ranges_overlap(uint64_t a, uint64_t a_size,
                          uint64_t b, uint64_t b_size)
{
    return a < b + b_size && b < a + a_size;
}

static int initrd_window_valid(uint64_t kernel_addr, uint64_t kernel_size,
                               uint64_t initrd_addr, uint64_t initrd_size)
{
    uint64_t kernel_end = kernel_addr + kernel_size;
    uint64_t initrd_end = initrd_addr + initrd_size;
    uint64_t first = kernel_addr < initrd_addr ? kernel_addr : initrd_addr;
    uint64_t last = kernel_end > initrd_end ? kernel_end : initrd_end;
    uint64_t window_base = first & ~(ONE_GIB - 1);

    return last >= window_base && last - window_base <= THIRTY_TWO_GIB;
}

int linux_boot_plan_validate(const struct linux_boot_plan *plan)
{
    if (!plan || !memory_range_valid(plan->ram))
        return 0;

    if (plan->current_el != 1 && plan->current_el != 2)
        return 0;

    if (plan->mmu_enabled)
        return 0;

    if (!plan->kernel_addr || !plan->dtb_addr || !plan->dtb_size)
        return 0;

    if (plan->dtb_size > TWO_MIB || !aligned(plan->dtb_addr, 8))
        return 0;

    if (!memory_range_contains(plan->ram, plan->dtb_addr, plan->dtb_size))
        return 0;

    uint64_t effective_size = plan->image.image_size;
    if (effective_size == 0)
        effective_size = plan->kernel_buffer_size;

    if (effective_size == 0 || effective_size > plan->kernel_buffer_size)
        return 0;

    if (!memory_range_contains(plan->ram, plan->kernel_addr, effective_size))
        return 0;

    if (plan->image.text_offset > plan->kernel_addr)
        return 0;

    uint64_t base = plan->kernel_addr - plan->image.text_offset;
    if (!aligned(base, TWO_MIB))
        return 0;

    /* Linux arm64 Images must be little-endian for our current loader. */
    if (plan->image.flags & 1u)
        return 0;

    /* Bit 3 requests placement fully within the 48-bit PA range. */
    if (plan->image.flags & (1ull << 3)) {
        if (plan->kernel_addr >= PHYS_48BIT_LIMIT ||
            effective_size > PHYS_48BIT_LIMIT - plan->kernel_addr)
            return 0;
    }

    /* Loaded artifacts must not overwrite one another. */
    if (ranges_overlap(plan->kernel_addr, effective_size,
                       plan->dtb_addr, plan->dtb_size))
        return 0;

    if ((plan->initrd_addr == 0) != (plan->initrd_size == 0))
        return 0;

    if (plan->initrd_size) {
        if (!memory_range_contains(plan->ram, plan->initrd_addr, plan->initrd_size))
            return 0;

        if (ranges_overlap(plan->kernel_addr, effective_size,
                           plan->initrd_addr, plan->initrd_size) ||
            ranges_overlap(plan->dtb_addr, plan->dtb_size,
                           plan->initrd_addr, plan->initrd_size))
            return 0;

        if (!initrd_window_valid(plan->kernel_addr, effective_size,
                                 plan->initrd_addr, plan->initrd_size))
            return 0;
    }

    return 1;
}
