#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "fdt.h"

static uint32_t read_be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) |
           ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) |
           (uint32_t)p[3];
}

static int contains_bytes(const uint8_t *data, size_t size,
                          const uint8_t *needle, size_t needle_size)
{
    if (!needle_size || needle_size > size)
        return 0;

    for (size_t i = 0; i <= size - needle_size; ++i) {
        size_t n = 0;
        while (n < needle_size && data[i + n] == needle[n])
            ++n;
        if (n == needle_size)
            return 1;
    }

    return 0;
}

int main(int argc, char **argv)
{
    uint8_t blob[4096];
    struct fdt_builder b;
    size_t size = 0;

    assert(fdt_begin(&b, blob, sizeof(blob)));
    assert(fdt_begin_node(&b, ""));
    assert(fdt_prop_string(&b, "compatible", "apple,j407"));
    assert(fdt_prop_u32(&b, "#address-cells", 2));
    assert(fdt_prop_u32(&b, "#size-cells", 2));

    assert(fdt_begin_node(&b, "chosen"));
    assert(fdt_prop_u64(&b, "linux,initrd-start", 0));
    assert(fdt_prop_u64(&b, "linux,initrd-end", 0));
    assert(fdt_end_node(&b));

    assert(fdt_begin_node(&b, "memory@800000000"));
    assert(fdt_prop_string(&b, "device_type", "memory"));
    assert(fdt_prop_u64_pair(&b, "reg", 0, 0));
    assert(fdt_end_node(&b));

    assert(fdt_end_node(&b));
    assert(fdt_finish(&b, &size));

    assert(size > 64);
    assert(read_be32(blob) == FDT_MAGIC);
    assert(read_be32(blob + 4) == size);

    size_t checked_size = 0;
    assert(fdt_check_header(blob, size, &checked_size));
    assert(checked_size == size);

    assert(fdt_setprop_u64_pair_inplace(blob, size,
                                        "/memory@800000000", "reg",
                                        0x800000000ull, 0x40000000ull));
    assert(fdt_setprop_u64_inplace(blob, size,
                                   "/chosen", "linux,initrd-start",
                                   0x802000000ull));
    assert(fdt_setprop_u64_inplace(blob, size,
                                   "/chosen", "linux,initrd-end",
                                   0x802800000ull));

    assert(!fdt_setprop_u64_inplace(blob, size,
                                    "/chosen", "does-not-exist", 1));

    uint32_t wrong_size = 0;
    assert(!fdt_setprop_inplace(blob, size,
                                "/chosen", "linux,initrd-start",
                                &wrong_size, sizeof(wrong_size)));

    const uint8_t memory_reg[] = {
        0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00,
    };
    const uint8_t initrd_start[] = {
        0x00, 0x00, 0x00, 0x08, 0x02, 0x00, 0x00, 0x00,
    };
    const uint8_t initrd_end[] = {
        0x00, 0x00, 0x00, 0x08, 0x02, 0x80, 0x00, 0x00,
    };

    assert(contains_bytes(blob, size, memory_reg, sizeof(memory_reg)));
    assert(contains_bytes(blob, size, initrd_start, sizeof(initrd_start)));
    assert(contains_bytes(blob, size, initrd_end, sizeof(initrd_end)));

    if (argc > 1) {
        FILE *f = fopen(argv[1], "wb");
        assert(f);
        assert(fwrite(blob, 1, size, f) == size);
        assert(fclose(f) == 0);
    }

    puts("FDT tests passed");
    return 0;
}
