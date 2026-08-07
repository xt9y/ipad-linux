#pragma once

#include <stddef.h>
#include <stdint.h>

struct adt_view {
    const uint8_t *data;
    size_t size;
};

struct adt_node_view {
    struct adt_view tree;
    size_t offset;
};

struct adt_property_view {
    char name[33];
    const uint8_t *value;
    uint32_t size;
};

int adt_validate(struct adt_view adt);
int adt_root(struct adt_view adt, struct adt_node_view *out);
int adt_node_property(struct adt_node_view node, const char *name, struct adt_property_view *out);
int adt_find_child(struct adt_node_view parent, const char *name, struct adt_node_view *out);
int adt_find_node(struct adt_view adt, const char *path, struct adt_node_view *out);
int adt_root_property(struct adt_view adt, const char *name, struct adt_property_view *out);

/*
 * Resolve a 64-bit Apple ADT reg tuple through ancestor ranges mappings.
 * This currently supports the 2-address-cell/2-size-cell layouts used by
 * T8103 arm-io and fails closed on other encodings.
 */
int adt_path_reg64(struct adt_view adt, const char *path, unsigned index,
                   uint64_t *phys_addr, uint64_t *reg_size);
