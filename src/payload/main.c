#include <stdint.h>

#include "adt.h"
#include "boot_info.h"
#include "memory.h"
#include "platform.h"

__attribute__((noreturn))
void kernel_main(const struct boot_info *boot)
{
    platform_early_init();

    const struct platform_info *platform = platform_get_info();
    volatile uint64_t heartbeat = ((uint64_t)platform->cpid << 32) | platform->bdid;

    if (boot_info_valid(boot)) {
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
