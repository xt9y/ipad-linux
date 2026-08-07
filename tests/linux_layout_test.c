#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "linux_layout.h"

static struct linux_layout_request request(void)
{
    struct linux_layout_request r = {
        .ram = {
            .base = 0x800000000ull,
            .size = 0x100000000ull,
        },
        .image = {
            .text_offset = 0x80000ull,
            .image_size = 0x01000000ull,
            .flags = 0,
        },
        .kernel_buffer_size = 0x01000000ull,
        .dtb_size = 0x20000ull,
        .initrd_size = 0x02000000ull,
    };
    return r;
}

int main(void)
{
    struct linux_artifact_layout layout;
    struct linux_layout_request r = request();

    assert(linux_layout_plan(&r, &layout));
    assert(layout.kernel_addr == 0x800080000ull);
    assert(layout.kernel_effective_size == 0x01000000ull);
    assert(layout.initrd_addr == 0x801080000ull);
    assert(layout.dtb_addr == 0x803080000ull);

    r = request();
    r.initrd_size = 0;
    assert(linux_layout_plan(&r, &layout));
    assert(layout.initrd_addr == 0);
    assert(layout.dtb_addr == 0x801080000ull);

    /* An unaligned usable-RAM base moves the 2 MiB kernel base upward. */
    r = request();
    r.ram.base = 0x800010000ull;
    r.ram.size = 0x0fff00000ull;
    assert(linux_layout_plan(&r, &layout));
    assert(layout.kernel_addr == 0x800280000ull);

    r = request();
    r.dtb_size = 0x200001ull;
    assert(!linux_layout_plan(&r, &layout));

    r = request();
    r.ram.size = 0x1000000ull;
    assert(!linux_layout_plan(&r, &layout));

    /* Current planner rejects an Image that claims more bytes than loaded. */
    r = request();
    r.image.image_size = r.kernel_buffer_size + 1;
    assert(!linux_layout_plan(&r, &layout));

    /* Big-endian Images are rejected by the shared boot-plan validator. */
    r = request();
    r.image.flags = 1;
    assert(!linux_layout_plan(&r, &layout));

    puts("Linux layout tests passed");
    return 0;
}
