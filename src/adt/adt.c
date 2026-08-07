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

static int bytes_equal_cstr(const uint8_t *value, uint32_t size, const char *wanted)
{
    uint32_t i = 0;

    if (!wanted)
        return 0;

    for (; wanted[i]; ++i) {
        if (i >= size || value[i] != (uint8_t)wanted[i])
            return 0;
    }

    return i < size && value[i] == 0;
}

static int node_layout(struct adt_node_view node,
                       uint32_t *property_count,
                       uint32_t *child_count,
                       size_t *children_offset)
{
    struct adt_view adt = node.tree;
    size_t offset = node.offset;

    if (!adt.data || offset > adt.size || adt.size - offset < 8)
        return 0;

    uint32_t props = read_u32le(adt.data + offset);
    uint32_t children = read_u32le(adt.data + offset + 4);
    size_t cursor = offset + 8;

    for (uint32_t i = 0; i < props; ++i) {
        if (cursor > adt.size || adt.size - cursor < 36)
            return 0;

        uint32_t encoded_size = read_u32le(adt.data + cursor + 32);
        uint32_t value_size = encoded_size & 0x7fffffffu;
        cursor += 36;

        if (cursor > adt.size || value_size > adt.size - cursor)
            return 0;

        cursor = align4(cursor + value_size);
        if (cursor > adt.size)
            return 0;
    }

    if (property_count)
        *property_count = props;
    if (child_count)
        *child_count = children;
    if (children_offset)
        *children_offset = cursor;

    return 1;
}

static int parse_node(const uint8_t *base, size_t size, size_t offset, size_t *next)
{
    struct adt_node_view node = {
        .tree = {.data = base, .size = size},
        .offset = offset,
    };
    uint32_t child_count = 0;
    size_t cursor = 0;

    if (!node_layout(node, 0, &child_count, &cursor))
        return 0;

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

int adt_root(struct adt_view adt, struct adt_node_view *out)
{
    if (!out || !adt.data || adt.size < 8)
        return 0;

    out->tree = adt;
    out->offset = 0;
    return 1;
}

int adt_node_property(struct adt_node_view node, const char *name, struct adt_property_view *out)
{
    struct adt_view adt = node.tree;
    size_t cursor = node.offset;

    if (!name || !out || !adt.data || cursor > adt.size || adt.size - cursor < 8)
        return 0;

    uint32_t property_count = read_u32le(adt.data + cursor);
    cursor += 8;

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

int adt_find_child(struct adt_node_view parent, const char *name, struct adt_node_view *out)
{
    uint32_t child_count = 0;
    size_t cursor = 0;

    if (!name || !out || !node_layout(parent, 0, &child_count, &cursor))
        return 0;

    for (uint32_t i = 0; i < child_count; ++i) {
        struct adt_node_view child = {
            .tree = parent.tree,
            .offset = cursor,
        };
        struct adt_property_view prop;
        size_t next = 0;

        if (adt_node_property(child, "name", &prop) &&
            bytes_equal_cstr(prop.value, prop.size, name)) {
            *out = child;
            return 1;
        }

        if (!parse_node(parent.tree.data, parent.tree.size, cursor, &next))
            return 0;
        cursor = next;
    }

    return 0;
}

int adt_find_node(struct adt_view adt, const char *path, struct adt_node_view *out)
{
    struct adt_node_view current;

    if (!path || !out || !adt_root(adt, &current))
        return 0;

    while (*path == '/')
        ++path;

    if (*path == '\0') {
        *out = current;
        return 1;
    }

    while (*path) {
        char component[33];
        size_t len = 0;

        while (*path && *path != '/') {
            if (len >= 32)
                return 0;
            component[len++] = *path++;
        }
        component[len] = '\0';

        while (*path == '/')
            ++path;

        if (!adt_find_child(current, component, &current))
            return 0;
    }

    *out = current;
    return 1;
}

int adt_root_property(struct adt_view adt, const char *name, struct adt_property_view *out)
{
    struct adt_node_view root;

    return adt_root(adt, &root) && adt_node_property(root, name, out);
}
