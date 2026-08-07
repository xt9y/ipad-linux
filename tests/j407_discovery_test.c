#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "adt.h"
#include "discovery.h"

static void put_u32le(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 0);
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static void put_u64le(uint8_t *p, uint64_t v)
{
    put_u32le(p, (uint32_t)v);
    put_u32le(p + 4, (uint32_t)(v >> 32));
}

static size_t put_prop(uint8_t *buf, size_t off, const char *name,
                       const void *value, uint32_t size)
{
    memset(buf + off, 0, 32);
    strncpy((char *)(buf + off), name, 31);
    put_u32le(buf + off + 32, size);
    off += 36;
    memcpy(buf + off, value, size);
    off += size;
    return (off + 3u) & ~3u;
}

static size_t put_leaf(uint8_t *blob, size_t off, const char *name,
                       const uint8_t *reg, uint32_t reg_size)
{
    put_u32le(blob + off, 2); off += 4;
    put_u32le(blob + off, 0); off += 4;
    off = put_prop(blob, off, "name", name, (uint32_t)strlen(name) + 1);
    off = put_prop(blob, off, "reg", reg, reg_size);
    return off;
}

int main(void)
{
    uint8_t blob[4096] = {0};
    uint8_t ranges[24] = {0};
    uint8_t uart_reg[16] = {0};
    uint8_t ans_regs[64] = {0};
    uint8_t usb_reg[16] = {0};
    uint8_t dart_usb_reg[16] = {0};
    size_t off = 0;

    put_u64le(ranges + 0, 0x000000000ull);
    put_u64le(ranges + 8, 0x200000000ull);
    put_u64le(ranges + 16, 0x100000000ull);

    put_u64le(uart_reg + 0, 0x35200000ull);
    put_u64le(uart_reg + 8, 0x4000ull);

    for (unsigned i = 0; i < 4; ++i) {
        put_u64le(ans_regs + i * 16, 0x70000000ull + (uint64_t)i * 0x100000ull);
        put_u64le(ans_regs + i * 16 + 8, 0x40000ull);
    }

    put_u64le(usb_reg + 0, 0x82280000ull);
    put_u64le(usb_reg + 8, 0xcd00ull);

    put_u64le(dart_usb_reg + 0, 0x82f00000ull);
    put_u64le(dart_usb_reg + 8, 0x4000ull);

    /* root */
    put_u32le(blob + off, 1); off += 4;
    put_u32le(blob + off, 1); off += 4;
    off = put_prop(blob, off, "name", "device-tree", 12);

    /* arm-io */
    put_u32le(blob + off, 2); off += 4;
    put_u32le(blob + off, 4); off += 4;
    off = put_prop(blob, off, "name", "arm-io", 7);
    off = put_prop(blob, off, "ranges", ranges, sizeof(ranges));

    off = put_leaf(blob, off, "uart0", uart_reg, sizeof(uart_reg));
    off = put_leaf(blob, off, "ans", ans_regs, sizeof(ans_regs));
    off = put_leaf(blob, off, "usb-drd0", usb_reg, sizeof(usb_reg));
    off = put_leaf(blob, off, "dart-usb0", dart_usb_reg, sizeof(dart_usb_reg));

    struct adt_view adt = { .data = blob, .size = off };
    assert(adt_validate(adt));

    struct j407_discovery hw;
    int found = j407_discover(adt, &hw);

    assert(found == 4);
    assert(hw.uart0_base == 0x235200000ull);
    assert(hw.uart0_size == 0x4000ull);

    /* ANS tuple 3: child 0x70300000 translated through arm-io. */
    assert(hw.nvme_base == 0x270300000ull);
    assert(hw.nvme_size == 0x40000ull);

    assert(hw.usb_drd0_base == 0x282280000ull);
    assert(hw.usb_drd0_size == 0xcd00ull);
    assert(hw.dart_usb0_base == 0x282f00000ull);
    assert(hw.dart_usb0_size == 0x4000ull);

    assert(hw.aic_base == 0);
    assert(hw.dcp_base == 0);

    puts("J407 discovery tests passed");
    return 0;
}
