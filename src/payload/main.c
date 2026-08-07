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
#include "quiesce.h"
#include "system.h"
#include "uart.h"

#define DAIF_ALL_MASKED 0x3c0ull

static void loader_debug_write(const char *data, size_t size, void *ctx)
{
    const struct boot_info *boot = (const struct boot_info *)ctx;
    boot_debug_write_fn fn = (boot_debug_write_fn)(uintptr_t)boot->debug_write_addr;

    if (fn)
        fn(data, (uint64_t)size, (void *)(uintptr_t)boot->debug_ctx);
}

static int runtime_cpu_contract_valid(const struct boot_info *boot)
{
    uint64_t runtime_el = aarch64_current_el();
    int runtime_mmu = aarch64_mmu_enabled();
    int reported_mmu = (boot->flags & BOOT_INFO_MMU_ENABLED) != 0;

    if (runtime_el != 1 && runtime_el != 2) {
        debug_puts("ipad-linux: unsupported runtime exception level\n");
        return 0;
    }

    if (runtime_el != boot->current_el) {
        debug_puts("ipad-linux: loader/runtime EL mismatch\n");
        return 0;
    }

    if (runtime_mmu != reported_mmu) {
        debug_puts("ipad-linux: loader/runtime MMU mismatch\n");
        return 0;
    }

    if (runtime_mmu) {
        debug_puts("ipad-linux: Linux entry requires MMU off\n");
        return 0;
    }

    return 1;
}

static int execution_can_touch_physical_mmio(void)
{
    uint64_t runtime_el = aarch64_current_el();
    return (runtime_el == 1 || runtime_el == 2) && !aarch64_mmu_enabled();
}

static int try_linux_handoff(const struct boot_info *boot, struct memory_range ram)
{
    const uint64_t need = BOOT_INFO_HAS_LINUX_IMAGE |
                          BOOT_INFO_HAS_DTB |
                          BOOT_INFO_PLATFORM_QUIESCED;

    if ((boot->flags & need) != need)
        return 0;

    if (!runtime_cpu_contract_valid(boot))
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
        .initrd_addr = (boot->flags & BOOT_INFO_HAS_INITRD) ? boot->initrd_addr : 0,
        .initrd_size = (boot->flags & BOOT_INFO_HAS_INITRD) ? boot->initrd_size : 0,
        .current_el = aarch64_current_el(),
        .mmu_enabled = aarch64_mmu_enabled(),
        .image = image,
    };

    if (!linux_boot_plan_validate(&plan))
        return 0;

    uint64_t kernel_cache_size = image.image_size ? image.image_size : boot->linux_image_size;

    /*
     * Linux requires the loaded Image to be clean to the Point of Coherency
     * and free of stale instruction-cache entries. The DTB/initrd are data,
     * so they only need the data-cache clean here.
     */
    aarch64_clean_dcache_range(boot->linux_image_addr, kernel_cache_size);
    aarch64_clean_dcache_range(boot->dtb_addr, (uint64_t)dtb_total);
    if (plan.initrd_size)
        aarch64_clean_dcache_range(plan.initrd_addr, plan.initrd_size);
    aarch64_invalidate_icache_range(boot->linux_image_addr, kernel_cache_size);

    debug_puts("ipad-linux: Linux handoff contract valid\n");
    debug_puts("ipad-linux: kernel/DTB caches synchronized\n");
    debug_puts("ipad-linux: entering Linux\n");

    aarch64_mask_interrupts();
    if ((aarch64_daif() & DAIF_ALL_MASKED) != DAIF_ALL_MASKED) {
        debug_puts("ipad-linux: failed to mask DAIF\n");
        return 0;
    }

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
                int physical_mmio = execution_can_touch_physical_mmio();

                if (!loader_debug && physical_mmio)
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

                if (physical_mmio && j407_disable_watchdogs(adt))
                    debug_puts("ipad-linux: watchdogs disabled\n");

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
