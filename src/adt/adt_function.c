#include "adt_function.h"

static uint32_t read_u32le(const uint8_t *p)
{
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

int adt_decode_function(struct adt_property_view property,
                        struct adt_function_view *out)
{
    if (!out || !property.value || property.size < 8 ||
        ((property.size - 8u) & 3u) != 0)
        return 0;

    out->phandle = read_u32le(property.value);
    out->function = read_u32le(property.value + 4);
    out->args = property.value + 8;
    out->arg_count = (property.size - 8u) / 4u;
    return 1;
}

int adt_function_arg_u32(const struct adt_function_view *function,
                         unsigned index, uint32_t *out)
{
    if (!function || !out || !function->args || index >= function->arg_count)
        return 0;

    *out = read_u32le(function->args + (size_t)index * 4u);
    return 1;
}

int adt_path_function(struct adt_view adt, const char *path,
                      const char *property,
                      struct adt_function_view *out)
{
    struct adt_node_view node;
    struct adt_property_view value;

    if (!path || !property || !out ||
        !adt_find_node(adt, path, &node) ||
        !adt_node_property(node, property, &value))
        return 0;

    return adt_decode_function(value, out);
}
