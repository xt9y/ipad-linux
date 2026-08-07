#include "memory.h"

int memory_range_valid(struct memory_range range)
{
    return range.size != 0 && range.base + range.size >= range.base;
}

int memory_range_contains(struct memory_range range, uint64_t addr, uint64_t size)
{
    if (!memory_range_valid(range))
        return 0;

    if (size > range.size)
        return 0;

    if (addr < range.base)
        return 0;

    return addr - range.base <= range.size - size;
}

uint64_t memory_align_up(uint64_t value, uint64_t alignment)
{
    if (alignment == 0 || (alignment & (alignment - 1)) != 0)
        return value;

    return (value + alignment - 1) & ~(alignment - 1);
}
