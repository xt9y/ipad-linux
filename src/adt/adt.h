#pragma once

#include <stddef.h>
#include <stdint.h>

struct adt_view {
    const uint8_t *data;
    size_t size;
};

struct adt_property_view {
    char name[33];
    const uint8_t *value;
    uint32_t size;
};

int adt_validate(struct adt_view adt);
int adt_root_property(struct adt_view adt, const char *name, struct adt_property_view *out);
