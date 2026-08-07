#include <stdint.h>

#include "adt.h"
#include "boot_info.h"
#include "boot_plan.h"
#include "debug.h"
#include "discovery.h"
#include "fdt.h"
#include "linux_handoff.h"
#include "linux_image.h"
#include "memory.h"
#include "platform.h"
#include "system.h"
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

static int try_linux_handoff(const struct boot_info *boot, struct memory_range ram)
{
    const uint64_t need = BOOT_INFO_HAS_LINUX_IMAGE |
                          BOOT_INFO_HAS_DTB |
                          BOOT_INFO_PLATFORM_QUIESCED;

    if ((boot->flags & need) != need)
        return 0;

    if (boot->flags & BOOT_INFO_MMU_ENABLED)
        return 0;

    if (!memory_range_contains(ram, boot->linux_image_addr, 64) ||
        !memory_range_contains(ram, boot->dtb_addr, boot->dtb_size))
        return 0;

    struct linux_image_info image;
    if (!linux_image_parse((const void *)(uintptr_t)boot->linux_image_addr,
                           (size_t)boot->linux_image_size, &image))
        return 0;

    size_t dtb_total = 0;
    if (!fdt_check_header((const void *)(uintptr_t)boot->dtb_addr,
                          (size_t)boot->dtb_size, &dtb_total))
        return 0;

    struct linux_boot_plan plan = {
        .ram = ram,
        .kernel_addr = boot->linux_image_addr,
        .kernel_buffer_size = boot->linux_image_size,
        .dtb_addr = boot->dtb_addr,
        .dtb_size = dtb_total,
        .current_el = boot->current_el,
        .mmu_enabled = 0,
        .image = image,
    };

    if (!linux_boot_plan_validate(&plan))
        return 0;

    debug_puts("ipad-linux: Linux handoff contract valid\n");
    debug_puts("ipad-linux: entering Linux\n");

    aarch64_mask_interrupts();
    linux_enter(boot->linux_image_addr, boot->dtb_addr);
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

        if (memory_range_valid(ram)) {
            debug_puts("ipad-linux: RAM contract valid\n");
            try_linux_handoff(boot, ram);
        }
    }

    for (;;) {
        heartbeat++;
        __asm__ volatile("yield");
    }
}
