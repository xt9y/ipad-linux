#pragma once

#include <stddef.h>
#include <stdint.h>

#include "adt.h"

#define ADT_FOURCC(a, b, c, d) \
    (((uint32_t)(a) << 24) | ((uint32_t)(b) << 16) | \
     ((uint32_t)(c) << 8) | (uint32_t)(d))

#define ADT_FUNC_GPIO ADT_FOURCC('G', 'P', 'I', 'O')
#define ADT_FUNC_GPIO_CONFIG ADT_FOURCC('G', 'P', 'I', 'c')

struct adt_function_view {
    uint32_t phandle;
    uint32_t function;
    const uint8_t *args;
    uint32_t arg_count;
};

/* Decode m1n1's Apple ADT Function layout: u32 phandle, FourCC, u32 args[]. */
int adt_decode_function(struct adt_property_view property,
                        struct adt_function_view *out);

int adt_function_arg_u32(const struct adt_function_view *function,
                         unsigned index, uint32_t *out);

/* Convenience lookup for a function-* property on an exact ADT path. */
int adt_path_function(struct adt_view adt, const char *path,
                      const char *property,
                      struct adt_function_view *out);
