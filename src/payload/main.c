#include <stdint.h>

#include "adt.h"
#include "boot_info.h"
#include "debug.h"
#include "memory.h"
#include "platform.h"

static void loader_debug_write(const char *data, size_t size, void *ctx)
{
    const struct boot_info *boot = (const struct boot_info *)ctx;
    boot_debug_write_fn fn = (boot_debug_write_fn)(uintptr_t)boot->debug_write_addr;

    if (fn)
        fn(data, (uint64_t)size, (void *)(uintptr_t)boot->debug_ctx);
}

__attribute__((noreturn))
void kernel_main(const struct boot_info *boot)
{
    platform_early_init();

    const struct platform_info *platform = platform_get_info();
    volatile uint64_t heartbeat = ((uint64_t)platform->cpid << 32) | platform->bdid;

    if (boot_info_valid(boot)) {
        if ((boot->flags & BOOT_INFO_HAS_DEBUG_WRITE) && boot->debug_write_addr) {
            struct debug_sink sink = {
                .write = loader_debug_write,
                .ctx = (void *)boot,
            };
            debug_set_sink(sink);
            debug_puts("ipad-linux: entered payload\n");
        }

        struct memory_range ram = {
            .base = boot->memory_base,
            .size = boot->memory_size,
        };

        if (memory_range_valid(ram)) {
            heartbeat ^= boot->memory_size;
            debug_puts("ipad-linux: RAM contract valid\n");
        }

        if ((boot->flags & BOOT_INFO_HAS_ADT) && boot->adt_addr && boot->adt_size) {
            struct adt_view adt = {
                .data = (const uint8_t *)(uintptr_t)boot->adt_addr,
                .size = (size_t)boot->adt_size,
            };

            if (adt_validate(adt)) {
                debug_puts("ipad-linux: ADT valid\n");

                struct adt_node_view arm_io;
                if (adt_find_node(adt, "/arm-io", &arm_io))
                    debug_puts("ipad-linux: found /arm-io\n");

                struct adt_property_view model;
                if (adt_root_property(adt, "model", &model))
                    heartbeat ^= model.size;
            }
        }
    }

    for (;;) {
        heartbeat++;
        __asm__ volatile("yield");
    }
}
