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

int fdt_check_header(const void *data, size_t available, size_t *total_size);
int fdt_begin(struct fdt_builder *b, void *buffer, size_t capacity);
int fdt_begin_node(struct fdt_builder *b, const char *name);
int fdt_end_node(struct fdt_builder *b);
int fdt_prop(struct fdt_builder *b, const char *name, const void *data, uint32_t size);
int fdt_prop_u32(struct fdt_builder *b, const char *name, uint32_t value);
int fdt_prop_u64(struct fdt_builder *b, const char *name, uint64_t value);
int fdt_prop_u64_pair(struct fdt_builder *b, const char *name, uint64_t a, uint64_t c);
int fdt_prop_string(struct fdt_builder *b, const char *name, const char *value);
int fdt_finish(struct fdt_builder *b, size_t *out_size);

/*
 * Replace an existing property's payload without moving structure blocks.
 * The replacement size must exactly match the existing property size.
 */
int fdt_setprop_inplace(void *dtb, size_t available,
                        const char *path, const char *property,
                        const void *data, uint32_t size);
int fdt_setprop_u64_inplace(void *dtb, size_t available,
                            const char *path, const char *property,
                            uint64_t value);
int fdt_setprop_u64_pair_inplace(void *dtb, size_t available,
                                 const char *path, const char *property,
                                 uint64_t a, uint64_t b);
