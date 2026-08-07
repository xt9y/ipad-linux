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
    info.size = sizeof(info);

    info.cpu_release_count = IPL_MAX_CPU_RELEASES + 1;
    assert(!boot_info_valid(&info));
    info.cpu_release_count = IPL_MAX_CPU_RELEASES;
    assert(boot_info_valid(&info));

    assert(offsetof(struct boot_info, flags) == 16);
    assert(offsetof(struct boot_info, memory_base) == 24);
    assert(offsetof(struct boot_info, adt_addr) == 40);
    assert(offsetof(struct boot_info, current_el) == 72);
    assert(offsetof(struct boot_info, debug_write_addr) == 80);
    assert(offsetof(struct boot_info, debug_ctx) == 88);
    assert(offsetof(struct boot_info, linux_image_addr) == 96);
    assert(offsetof(struct boot_info, dtb_addr) == 112);
    assert(offsetof(struct boot_info, initrd_addr) == 128);
    assert(offsetof(struct boot_info, cpu_release_count) == 144);
    assert(offsetof(struct boot_info, cpu_releases) == 152);
    assert(sizeof(struct boot_cpu_release) == 16);
    assert(sizeof(struct boot_info) == 312);

    puts("boot_info tests passed");
    return 0;
}
