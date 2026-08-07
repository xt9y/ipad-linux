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

int main(int argc, char **argv)
{
    uint8_t blob[2048];
    struct fdt_builder b;
    size_t size = 0;

    assert(fdt_begin(&b, blob, sizeof(blob)));
    assert(fdt_begin_node(&b, ""));
    assert(fdt_prop_string(&b, "compatible", "apple,j407"));
    assert(fdt_prop_u32(&b, "#address-cells", 2));
    assert(fdt_prop_u32(&b, "#size-cells", 2));

    assert(fdt_begin_node(&b, "memory@800000000"));
    assert(fdt_prop_string(&b, "device_type", "memory"));
    assert(fdt_prop_u64_pair(&b, "reg", 0x800000000ull, 0x40000000ull));
    assert(fdt_end_node(&b));

    assert(fdt_end_node(&b));
    assert(fdt_finish(&b, &size));

    assert(size > 64);
    assert(read_be32(blob) == FDT_MAGIC);
    assert(read_be32(blob + 4) == size);

    size_t checked_size = 0;
    assert(fdt_check_header(blob, size, &checked_size));
    assert(checked_size == size);

    if (argc > 1) {
        FILE *f = fopen(argv[1], "wb");
        assert(f);
        assert(fwrite(blob, 1, size, f) == size);
        assert(fclose(f) == 0);
    }

    puts("FDT tests passed");
    return 0;
}
