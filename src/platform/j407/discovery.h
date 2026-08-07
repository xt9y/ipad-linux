#pragma once

#include <stdint.h>

#include "adt.h"

struct j407_discovery {
    uint64_t uart0_base;
    uint64_t uart0_size;
    uint64_t aic_base;
    uint64_t aic_size;
    uint64_t pmgr_base;
    uint64_t pmgr_size;
    uint64_t gpio_base;
    uint64_t gpio_size;
    uint64_t wdt_base;
    uint64_t wdt_size;
};

int j407_discover(struct adt_view adt, struct j407_discovery *out);
