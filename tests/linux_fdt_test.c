#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "fdt.h"
#include "linux_fdt.h"

static int build_template(uint8_t *blob, size_t capacity, size_t *out_size)
{
    struct fdt_builder b;

    if (!fdt_begin(&b, blob, capacity) ||
        !fdt_begin_node(&b, "") ||
        !fdt_prop_u32(&b, "#address-cells", 2) ||
        !fdt_prop_u32(&b, "#size-cells", 2) ||
        !fdt_begin_node(&b, "chosen") ||
        !fdt_prop_u64(&b, "linux,initrd-start", 0) ||
        !fdt_prop_u64(&b, "linux,initrd-end", 0) ||
        !fdt_end_node(&b) ||
        !fdt_begin_node(&b, "memory@800000000") ||
        !fdt_prop_string(&b, "device_type", "memory") ||
        !fdt_prop_u64_pair(&b, "reg", 0, 0) ||
        !fdt_end_node(&b) ||
        !fdt_end_node(&b) ||
        !fdt_finish(&b, out_size))
        return 0;

    return 1;
}

int main(void)
{
    uint8_t blob[4096];
    size_t size = 0;

    assert(build_template(blob, sizeof(blob), &size));

    struct linux_fdt_runtime runtime = {
        .memory_path = "/memory@800000000",
        .ram = {
            .base = 0x800000000ull,
            .size = 0x200000000ull,
        },
        .initrd_addr = 0x810000000ull,
        .initrd_size = 0x02000000ull,
    };

    assert(linux_fdt_patch_runtime(blob, size, &runtime));

    /* No initrd is also valid and does not require touching chosen values. */
    assert(build_template(blob, sizeof(blob), &size));
    runtime.initrd_addr = 0;
    runtime.initrd_size = 0;
    assert(linux_fdt_patch_runtime(blob, size, &runtime));

    /* Partial initrd metadata is rejected. */
    assert(build_template(blob, sizeof(blob), &size));
    runtime.initrd_addr = 0x810000000ull;
    runtime.initrd_size = 0;
    assert(!linux_fdt_patch_runtime(blob, size, &runtime));

    /* Initrd must be contained in declared usable RAM. */
    assert(build_template(blob, sizeof(blob), &size));
    runtime.initrd_addr = 0xa00000000ull;
    runtime.initrd_size = 0x1000;
    assert(!linux_fdt_patch_runtime(blob, size, &runtime));

    /* The precompiled DTB must expose the expected memory placeholder. */
    assert(build_template(blob, sizeof(blob), &size));
    runtime.initrd_addr = 0;
    runtime.initrd_size = 0;
    runtime.memory_path = "/memory@deadbeef";
    assert(!linux_fdt_patch_runtime(blob, size, &runtime));

    puts("Linux FDT runtime patch tests passed");
    return 0;
}
