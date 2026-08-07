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
    uint8_t ranges[48] = {0};
    uint8_t uart_reg[16] = {0};
    uint8_t ans_regs[64] = {0};
    uint8_t usb_reg[16] = {0};
    uint8_t dart_usb_reg[32] = {0};
    size_t off = 0;

    /*
     * These are the two J407 arm-io ranges relevant to this test:
     *
     *   0x000000000 -> 0x200000000, size 0x100000000
     *   0x380000000 -> 0x380000000, size 0x180000000
     *
     * Low SoC registers therefore use the +0x200000000 translation, while
     * USB/ATC addresses in the 0x38... aperture are identity-mapped.
     */
    put_u64le(ranges + 0,  0x000000000ull);
    put_u64le(ranges + 8,  0x200000000ull);
    put_u64le(ranges + 16, 0x100000000ull);
    put_u64le(ranges + 24, 0x380000000ull);
    put_u64le(ranges + 32, 0x380000000ull);
    put_u64le(ranges + 40, 0x180000000ull);

    put_u64le(uart_reg + 0, 0x35200000ull);
    put_u64le(uart_reg + 8, 0x4000ull);

    /* First four real J407 ANS tuples; discovery intentionally selects #3. */
    put_u64le(ans_regs + 0,  0x77400000ull);
    put_u64le(ans_regs + 8,  0x6c000ull);
    put_u64le(ans_regs + 16, 0x77050000ull);
    put_u64le(ans_regs + 24, 0x4000ull);
    put_u64le(ans_regs + 32, 0);
    put_u64le(ans_regs + 40, 0);
    put_u64le(ans_regs + 48, 0x7bcc0000ull);
    put_u64le(ans_regs + 56, 0x60000ull);

    /* J407 usb-drd0 primary Apple window. Mainline splits a subset of it. */
    put_u64le(usb_reg + 0, 0x382280000ull);
    put_u64le(usb_reg + 8, 0x11800ull);

    /* J407 dart-usb0 has exactly these two 16 KiB register windows. */
    put_u64le(dart_usb_reg + 0, 0x382f00000ull);
    put_u64le(dart_usb_reg + 8, 0x4000ull);
    put_u64le(dart_usb_reg + 16, 0x382f80000ull);
    put_u64le(dart_usb_reg + 24, 0x4000ull);

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

    /* Low child address uses the first +0x200000000 range. */
    assert(hw.uart0_base == 0x235200000ull);
    assert(hw.uart0_size == 0x4000ull);

    /* Real ANS tuple #3 also lives in the low translated aperture. */
    assert(hw.nvme_base == 0x27bcc0000ull);
    assert(hw.nvme_size == 0x60000ull);

    /* USB lives in J407's identity-mapped 0x38... arm-io aperture. */
    assert(hw.usb_drd0_base == 0x382280000ull);
    assert(hw.usb_drd0_size == 0x11800ull);
    assert(hw.dart_usb0_base == 0x382f00000ull);
    assert(hw.dart_usb0_size == 0x4000ull);

    assert(hw.aic_base == 0);
    assert(hw.dcp_base == 0);

    puts("J407 discovery tests passed");
    return 0;
}
