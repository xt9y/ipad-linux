#pragma once

#include <stddef.h>
#include <stdint.h>

#define FDT_MAGIC 0xd00dfeedu

struct fdt_builder {
    uint8_t *buffer;
    size_t capacity;
    size_t struct_off;
    size_t strings_off;
    size_t struct_size;
    size_t strings_size;
    int depth;
};

int fdt_begin(struct fdt_builder *b, void *buffer, size_t capacity);
int fdt_begin_node(struct fdt_builder *b, const char *name);
int fdt_end_node(struct fdt_builder *b);
int fdt_prop(struct fdt_builder *b, const char *name, const void *data, uint32_t size);
int fdt_prop_u32(struct fdt_builder *b, const char *name, uint32_t value);
int fdt_prop_u64_pair(struct fdt_builder *b, const char *name, uint64_t a, uint64_t c);
int fdt_prop_string(struct fdt_builder *b, const char *name, const char *value);
int fdt_finish(struct fdt_builder *b, size_t *out_size);
