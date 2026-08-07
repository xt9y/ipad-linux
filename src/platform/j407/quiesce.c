#include "quiesce.h"

#include <stdint.h>

#define WDT_CTL 0x1cu

static void mmio_write32(uint64_t addr, uint32_t value)
{
    *(volatile uint32_t *)(uintptr_t)addr = value;
}

int j407_disable_watchdogs(struct adt_view adt)
{
    uint64_t primary = 0;
    uint64_t primary_size = 0;

    if (!adt_path_reg64(adt, "/arm-io/wdt", 0, &primary, &primary_size))
        return 0;
    if (primary_size <= WDT_CTL)
        return 0;

    mmio_write32(primary + WDT_CTL, 0);

    /*
     * J407 reports watchdog version 2. m1n1 disables the secondary watchdog
     * through reg[2], which is a single control register.
     */
    uint64_t secondary = 0;
    uint64_t secondary_size = 0;
    if (adt_path_reg64(adt, "/arm-io/wdt", 2, &secondary, &secondary_size) &&
        secondary_size >= sizeof(uint32_t))
        mmio_write32(secondary, 0);

    return 1;
}
