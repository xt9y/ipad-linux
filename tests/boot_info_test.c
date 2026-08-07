#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "boot_info.h"

int main(void)
{
    struct boot_info info;
    memset(&info, 0, sizeof(info));

    assert(!boot_info_valid(&info));

    info.magic = IPL_BOOT_INFO_MAGIC;
    info.version = IPL_BOOT_INFO_VERSION;
    info.size = sizeof(info);
    assert(boot_info_valid(&info));

    info.version++;
    assert(!boot_info_valid(&info));
    info.version = IPL_BOOT_INFO_VERSION;

    info.size = sizeof(info) - 1;
    assert(!boot_info_valid(&info));

    assert(offsetof(struct boot_info, flags) == 16);
    assert(offsetof(struct boot_info, memory_base) == 24);
    assert(offsetof(struct boot_info, adt_addr) == 40);
    assert(offsetof(struct boot_info, current_el) == 72);
    assert(offsetof(struct boot_info, debug_write_addr) == 80);
    assert(offsetof(struct boot_info, debug_ctx) == 88);

    puts("boot_info tests passed");
    return 0;
}
