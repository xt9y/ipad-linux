#include "uart.h"

#include <stddef.h>

#include "debug.h"

#define UTRSTAT 0x010u
#define UTXH    0x020u
#define UTRSTAT_TXBE (1u << 1)

static volatile uint8_t *uart_base;

static uint32_t mmio_read32(uint64_t addr)
{
    return *(volatile uint32_t *)(uintptr_t)addr;
}

static void mmio_write32(uint64_t addr, uint32_t value)
{
    *(volatile uint32_t *)(uintptr_t)addr = value;
}

static void uart_sink_write(const char *data, size_t size, void *ctx)
{
    (void)ctx;

    if (!uart_base)
        return;

    uint64_t base = (uint64_t)(uintptr_t)uart_base;
    for (size_t i = 0; i < size; ++i) {
        char c = data[i];
        if (c == '\n') {
            while (!(mmio_read32(base + UTRSTAT) & UTRSTAT_TXBE)) {}
            mmio_write32(base + UTXH, '\r');
        }
        while (!(mmio_read32(base + UTRSTAT) & UTRSTAT_TXBE)) {}
        mmio_write32(base + UTXH, (uint8_t)c);
    }
}

void debug_uart_use_base(uint64_t base)
{
    uart_base = (volatile uint8_t *)(uintptr_t)base;

    struct debug_sink sink = {
        .write = uart_sink_write,
        .ctx = 0,
    };
    debug_set_sink(sink);
}

int debug_uart_from_adt(struct adt_view adt, uint64_t *resolved_base)
{
    uint64_t base = 0;
    uint64_t size = 0;

    if (!adt_path_reg64(adt, "/arm-io/uart0", 0, &base, &size))
        return 0;

    if (size < 0x30)
        return 0;

    if (resolved_base)
        *resolved_base = base;

    debug_uart_use_base(base);
    return 1;
}
