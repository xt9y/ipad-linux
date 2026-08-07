#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "adt.h"

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

static size_t put_prop(uint8_t *buf, size_t off, const char *name, const void *value, uint32_t size)
{
    memset(buf + off, 0, 32);
    strncpy((char *)(buf + off), name, 31);
    put_u32le(buf + off + 32, size);
    off += 36;
    memcpy(buf + off, value, size);
    off += size;
    return (off + 3u) & ~3u;
}

int main(void)
{
    uint8_t blob[1024] = {0};
    uint8_t ranges[24] = {0};
    uint8_t reg[16] = {0};
    size_t off = 0;

    put_u64le(ranges + 0, 0x000000000ull);
    put_u64le(ranges + 8, 0x200000000ull);
    put_u64le(ranges + 16, 0x100000000ull);

    put_u64le(reg + 0, 0x35200000ull);
    put_u64le(reg + 8, 0x4000ull);

    /* root */
    put_u32le(blob + off, 1); off += 4;
    put_u32le(blob + off, 1); off += 4;
    off = put_prop(blob, off, "name", "device-tree", 12);

    /* arm-io */
    put_u32le(blob + off, 2); off += 4;
    put_u32le(blob + off, 1); off += 4;
    off = put_prop(blob, off, "name", "arm-io", 7);
    off = put_prop(blob, off, "ranges", ranges, sizeof(ranges));

    /* uart0 */
    put_u32le(blob + off, 2); off += 4;
    put_u32le(blob + off, 0); off += 4;
    off = put_prop(blob, off, "name", "uart0", 6);
    off = put_prop(blob, off, "reg", reg, sizeof(reg));

    struct adt_view adt = { .data = blob, .size = off };
    assert(adt_validate(adt));

    uint64_t addr = 0;
    uint64_t size = 0;
    assert(adt_path_reg64(adt, "/arm-io/uart0", 0, &addr, &size));
    assert(addr == 0x235200000ull);
    assert(size == 0x4000ull);

    puts("ADT reg translation tests passed");
    return 0;
}
