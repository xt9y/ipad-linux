#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "adt_function.h"

static void put_u32le(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

int main(void)
{
    /* Real J407 function-reset shape: phandle 40, GPIO, gpio 180, flags. */
    uint8_t reset_blob[16];
    put_u32le(reset_blob + 0, 40);
    put_u32le(reset_blob + 4, ADT_FUNC_GPIO);
    put_u32le(reset_blob + 8, 180);
    put_u32le(reset_blob + 12, 0x00010001u);

    struct adt_property_view prop = {
        .value = reset_blob,
        .size = sizeof(reset_blob),
    };
    struct adt_function_view fn;
    uint32_t arg = 0;

    assert(adt_decode_function(prop, &fn));
    assert(fn.phandle == 40);
    assert(fn.function == ADT_FUNC_GPIO);
    assert(fn.arg_count == 2);
    assert(adt_function_arg_u32(&fn, 0, &arg));
    assert(arg == 180);
    assert(adt_function_arg_u32(&fn, 1, &arg));
    assert(arg == 0x00010001u);
    assert(!adt_function_arg_u32(&fn, 2, &arg));

    /* Real J407 interrupt-config shape has three u32 arguments. */
    uint8_t irq_blob[20];
    put_u32le(irq_blob + 0, 67);
    put_u32le(irq_blob + 4, ADT_FUNC_GPIO_CONFIG);
    put_u32le(irq_blob + 8, 20);
    put_u32le(irq_blob + 12, 0x06000001u);
    put_u32le(irq_blob + 16, 0x04000001u);

    prop.value = irq_blob;
    prop.size = sizeof(irq_blob);
    assert(adt_decode_function(prop, &fn));
    assert(fn.phandle == 67);
    assert(fn.function == ADT_FUNC_GPIO_CONFIG);
    assert(fn.arg_count == 3);
    assert(adt_function_arg_u32(&fn, 0, &arg));
    assert(arg == 20);

    prop.size = 7;
    assert(!adt_decode_function(prop, &fn));
    prop.size = 13;
    assert(!adt_decode_function(prop, &fn));

    puts("ADT function tests passed");
    return 0;
}
