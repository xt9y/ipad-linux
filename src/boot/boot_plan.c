#include "boot_plan.h"

#define TWO_MIB (2ull * 1024ull * 1024ull)

static int aligned(uint64_t value, uint64_t alignment)
{
    return alignment && (value & (alignment - 1)) == 0;
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

    uint64_t base = plan->kernel_addr - plan->image.text_offset;
    if (base > plan->kernel_addr || !aligned(base, TWO_MIB))
        return 0;

    /* Linux arm64 Images must be little-endian for our current loader. */
    if (plan->image.flags & 1u)
        return 0;

    return 1;
}
