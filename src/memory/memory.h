#pragma once

#include <stddef.h>
#include <stdint.h>

struct memory_range {
    uint64_t base;
    uint64_t size;
};

int memory_range_valid(struct memory_range range);
int memory_range_contains(struct memory_range range, uint64_t addr, uint64_t size);
uint64_t memory_align_up(uint64_t value, uint64_t alignment);
