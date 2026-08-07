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
    uint8_t blob[512] = {0};
    size_t off = 0;

    /* root: properties { name="device-tree" }, one child */
    put_u32le(blob + off, 1); off += 4;
    put_u32le(blob + off, 1); off += 4;
    off = put_prop(blob, off, "name", "device-tree", 12);

    /* child: arm-io */
    put_u32le(blob + off, 2); off += 4;
    put_u32le(blob + off, 0); off += 4;
    off = put_prop(blob, off, "name", "arm-io", 7);
    off = put_prop(blob, off, "compatible", "apple,t8103", 12);

    struct adt_view adt = {
        .data = blob,
        .size = off,
    };

    assert(adt_validate(adt));

    struct adt_node_view node;
    assert(adt_find_node(adt, "/arm-io", &node));

    struct adt_property_view prop;
    assert(adt_node_property(node, "compatible", &prop));
    assert(prop.size == 12);
    assert(memcmp(prop.value, "apple,t8103", 12) == 0);

    assert(!adt_find_node(adt, "/does-not-exist", &node));

    puts("ADT tests passed");
    return 0;
}
