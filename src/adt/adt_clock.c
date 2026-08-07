#include "adt_clock.h"

static uint32_t read_u32le(const uint8_t *p)
{
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

int adt_path_boot_clock(struct adt_view adt, const char *path,
                        unsigned clock_index, uint32_t *clock_id,
                        uint32_t *frequency_hz)
{
    struct adt_node_view node;
    struct adt_node_view arm_io;
    struct adt_property_view ids;
    struct adt_property_view frequencies;

    if (!path || !clock_id || !frequency_hz)
        return 0;

    *clock_id = 0;
    *frequency_hz = 0;

    if (!adt_find_node(adt, path, &node) ||
        !adt_node_property(node, "clock-ids", &ids))
        return 0;

    size_t id_offset = (size_t)clock_index * sizeof(uint32_t);
    if (id_offset > ids.size || ids.size - id_offset < sizeof(uint32_t))
        return 0;

    uint32_t id = read_u32le(ids.value + id_offset);
    if (id < 256)
        return 0;

    if (!adt_find_node(adt, "/arm-io", &arm_io) ||
        !adt_node_property(arm_io, "clock-frequencies", &frequencies))
        return 0;

    size_t frequency_index = (size_t)(id - 256u);
    if (frequency_index > SIZE_MAX / sizeof(uint32_t))
        return 0;

    size_t frequency_offset = frequency_index * sizeof(uint32_t);
    if (frequency_offset > frequencies.size ||
        frequencies.size - frequency_offset < sizeof(uint32_t))
        return 0;

    *clock_id = id;
    *frequency_hz = read_u32le(frequencies.value + frequency_offset);
    return 1;
}
