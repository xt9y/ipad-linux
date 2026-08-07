#include "adt.h"

static uint32_t read_u32le(const uint8_t *p)
{
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static size_t align4(size_t value)
{
    return (value + 3u) & ~3u;
}

static int string_equal_32(const char *wanted, const uint8_t *name)
{
    size_t i = 0;

    for (; i < 32 && wanted[i]; ++i) {
        if ((uint8_t)wanted[i] != name[i])
            return 0;
    }

    if (wanted[i] != '\0')
        return 0;

    return i == 32 || name[i] == 0;
}

static int parse_node(const uint8_t *base, size_t size, size_t offset, size_t *next)
{
    if (offset > size || size - offset < 8)
        return 0;

    uint32_t property_count = read_u32le(base + offset);
    uint32_t child_count = read_u32le(base + offset + 4);
    size_t cursor = offset + 8;

    for (uint32_t i = 0; i < property_count; ++i) {
        if (cursor > size || size - cursor < 36)
            return 0;

        uint32_t encoded_size = read_u32le(base + cursor + 32);
        uint32_t value_size = encoded_size & 0x7fffffffu;
        cursor += 36;

        if (cursor > size || value_size > size - cursor)
            return 0;

        cursor += value_size;
        cursor = align4(cursor);
        if (cursor > size)
            return 0;
    }

    for (uint32_t i = 0; i < child_count; ++i) {
        if (!parse_node(base, size, cursor, &cursor))
            return 0;
    }

    *next = cursor;
    return 1;
}

int adt_validate(struct adt_view adt)
{
    size_t next = 0;

    if (!adt.data || adt.size < 8)
        return 0;

    return parse_node(adt.data, adt.size, 0, &next) && next <= adt.size;
}

int adt_root_property(struct adt_view adt, const char *name, struct adt_property_view *out)
{
    if (!adt.data || !name || !out || adt.size < 8)
        return 0;

    uint32_t property_count = read_u32le(adt.data);
    size_t cursor = 8;

    for (uint32_t i = 0; i < property_count; ++i) {
        if (cursor > adt.size || adt.size - cursor < 36)
            return 0;

        const uint8_t *prop_name = adt.data + cursor;
        uint32_t encoded_size = read_u32le(adt.data + cursor + 32);
        uint32_t value_size = encoded_size & 0x7fffffffu;
        cursor += 36;

        if (cursor > adt.size || value_size > adt.size - cursor)
            return 0;

        if (string_equal_32(name, prop_name)) {
            size_t n = 0;
            for (; n < 32 && prop_name[n]; ++n)
                out->name[n] = (char)prop_name[n];
            out->name[n] = '\0';
            out->value = adt.data + cursor;
            out->size = value_size;
            return 1;
        }

        cursor = align4(cursor + value_size);
    }

    return 0;
}
