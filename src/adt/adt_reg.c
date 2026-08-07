#include "adt.h"

#define ADT_MAX_DEPTH 16

static uint64_t read_u64le(const uint8_t *p)
{
    return (uint64_t)p[0] |
           ((uint64_t)p[1] << 8) |
           ((uint64_t)p[2] << 16) |
           ((uint64_t)p[3] << 24) |
           ((uint64_t)p[4] << 32) |
           ((uint64_t)p[5] << 40) |
           ((uint64_t)p[6] << 48) |
           ((uint64_t)p[7] << 56);
}

static int translate_ranges(struct adt_node_view bus, uint64_t *addr)
{
    struct adt_property_view ranges;

    if (!adt_node_property(bus, "ranges", &ranges))
        return 1; /* no ranges means identity */

    if (ranges.size == 0)
        return 1;

    /* T8103 arm-io uses <u64 child, u64 parent, u64 size> entries. */
    if (ranges.size % 24u)
        return 0;

    for (uint32_t off = 0; off < ranges.size; off += 24) {
        uint64_t child = read_u64le(ranges.value + off);
        uint64_t parent = read_u64le(ranges.value + off + 8);
        uint64_t size = read_u64le(ranges.value + off + 16);

        if (*addr >= child && *addr - child < size) {
            *addr = parent + (*addr - child);
            return 1;
        }
    }

    return 0;
}

int adt_path_reg64(struct adt_view adt, const char *path, unsigned index,
                   uint64_t *phys_addr, uint64_t *reg_size)
{
    struct adt_node_view chain[ADT_MAX_DEPTH];
    unsigned depth = 0;
    const char *p = path;

    if (!path || !phys_addr || !reg_size || !adt_root(adt, &chain[0]))
        return 0;

    while (*p == '/') ++p;

    while (*p) {
        char component[33];
        size_t len = 0;

        if (depth + 1 >= ADT_MAX_DEPTH)
            return 0;

        while (*p && *p != '/') {
            if (len >= 32)
                return 0;
            component[len++] = *p++;
        }
        component[len] = '\0';
        while (*p == '/') ++p;

        if (!adt_find_child(chain[depth], component, &chain[depth + 1]))
            return 0;
        depth++;
    }

    if (depth == 0)
        return 0;

    struct adt_property_view reg;
    if (!adt_node_property(chain[depth], "reg", &reg))
        return 0;

    if (reg.size % 16u || index >= reg.size / 16u)
        return 0;

    uint64_t addr = read_u64le(reg.value + index * 16u);
    uint64_t size = read_u64le(reg.value + index * 16u + 8u);

    /* Translate from the target's parent bus up toward the root. */
    for (unsigned level = depth; level > 0; --level) {
        if (!translate_ranges(chain[level - 1], &addr))
            return 0;
    }

    *phys_addr = addr;
    *reg_size = size;
    return 1;
}
