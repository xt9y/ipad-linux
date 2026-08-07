#include <stdint.h>

#include "adt.h"
#include "boot_info.h"
#include "debug.h"
#include "discovery.h"
#include "memory.h"
#include "platform.h"
#include "uart.h"

static void loader_debug_write(const char *data, size_t size, void *ctx)
{
    const struct boot_info *boot = (const struct boot_info *)ctx;
    boot_debug_write_fn fn = (boot_debug_write_fn)(uintptr_t)boot->debug_write_addr;

    if (fn)
        fn(data, (uint64_t)size, (void *)(uintptr_t)boot->debug_ctx);
}

static int execution_can_touch_physical_mmio(const struct boot_info *boot)
{
    return boot->current_el >= 1 && boot->current_el <= 2 &&
           !(boot->flags & BOOT_INFO_MMU_ENABLED);
}

__attribute__((noreturn))
void kernel_main(const struct boot_info *boot)
{
    platform_early_init();

    const struct platform_info *platform = platform_get_info();
    volatile uint64_t heartbeat = ((uint64_t)platform->cpid << 32) | platform->bdid;

    if (boot_info_valid(boot)) {
        int loader_debug = (boot->flags & BOOT_INFO_HAS_DEBUG_WRITE) && boot->debug_write_addr;
        if (loader_debug) {
            struct debug_sink sink = {
                .write = loader_debug_write,
                .ctx = (void *)boot,
            };
            debug_set_sink(sink);
        }

        struct memory_range ram = {
            .base = boot->memory_base,
            .size = boot->memory_size,
        };

        if (memory_range_valid(ram))
            heartbeat ^= boot->memory_size;

        if ((boot->flags & BOOT_INFO_HAS_ADT) && boot->adt_addr && boot->adt_size) {
            struct adt_view adt = {
                .data = (const uint8_t *)(uintptr_t)boot->adt_addr,
                .size = (size_t)boot->adt_size,
            };

            if (adt_validate(adt)) {
                /*
                 * iBoot marks J407 uart0 as the boot console. If the future
                 * entry mechanism gives us physical-address execution with
                 * the MMU off and no better debug callback, reuse that
                 * already-configured console rather than programming clocks.
                 */
                if (!loader_debug && execution_can_touch_physical_mmio(boot))
                    debug_uart_from_adt(adt, 0);

                debug_puts("ipad-linux: entered J407 payload\n");
                debug_puts("ipad-linux: ADT valid\n");

                struct j407_discovery hw;
                int discovered = j407_discover(adt, &hw);
                if (discovered > 0) {
                    heartbeat ^= hw.uart0_base;
                    heartbeat ^= hw.aic_base;
                    debug_puts("ipad-linux: J407 hardware discovery complete\n");
                }

                struct adt_property_view model;
                if (adt_root_property(adt, "model", &model))
                    heartbeat ^= model.size;
            }
        }

        if (memory_range_valid(ram))
            debug_puts("ipad-linux: RAM contract valid\n");
    }

    for (;;) {
        heartbeat++;
        __asm__ volatile("yield");
    }
}
