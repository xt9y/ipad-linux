#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "adt.h"
#include "adt_clock.h"

static void put_u32le(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 0);
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
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

int main(void)
{
    uint8_t blob[2048] = {0};
    uint8_t frequencies[125 * 4] = {0};
    uint8_t clock_ids[4];
    size_t off = 0;

    /* clock-id 380 -> boot-clock table index 124. */
    put_u32le(frequencies + 124 * 4, 200000000u);
    put_u32le(clock_ids, 380u);

    /* root: one name property, one arm-io child */
    put_u32le(blob + off, 1); off += 4;
    put_u32le(blob + off, 1); off += 4;
    off = put_prop(blob, off, "name", "device-tree", 12);

    /* arm-io: name + boot clock table, one spi4 child */
    put_u32le(blob + off, 2); off += 4;
    put_u32le(blob + off, 1); off += 4;
    off = put_prop(blob, off, "name", "arm-io", 7);
    off = put_prop(blob, off, "clock-frequencies",
                   frequencies, sizeof(frequencies));

    /* spi4: one clock-id, no children */
    put_u32le(blob + off, 2); off += 4;
    put_u32le(blob + off, 0); off += 4;
    off = put_prop(blob, off, "name", "spi4", 5);
    off = put_prop(blob, off, "clock-ids", clock_ids, sizeof(clock_ids));

    struct adt_view adt = { .data = blob, .size = off };
    assert(adt_validate(adt));

    uint32_t clock_id = 0;
    uint32_t hz = 0;
    assert(adt_path_boot_clock(adt, "/arm-io/spi4", 0, &clock_id, &hz));
    assert(clock_id == 380u);
    assert(hz == 200000000u);

    assert(!adt_path_boot_clock(adt, "/arm-io/spi4", 1, &clock_id, &hz));
    assert(!adt_path_boot_clock(adt, "/arm-io/missing", 0, &clock_id, &hz));

    /* Fixed/legacy IDs are intentionally outside this helper's contract. */
    struct adt_node_view spi4;
    struct adt_property_view ids;
    assert(adt_find_node(adt, "/arm-io/spi4", &spi4));
    assert(adt_node_property(spi4, "clock-ids", &ids));
    put_u32le((uint8_t *)ids.value, 42u);
    assert(!adt_path_boot_clock(adt, "/arm-io/spi4", 0, &clock_id, &hz));

    puts("ADT clock tests passed");
    return 0;
}
