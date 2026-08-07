#include <stdint.h>

#include "platform.h"

__attribute__((noreturn))
void kernel_main(void)
{
    platform_early_init();

    const struct platform_info *platform = platform_get_info();
    volatile uint64_t heartbeat = ((uint64_t)platform->cpid << 32) | platform->bdid;

    for (;;) {
        heartbeat++;
        __asm__ volatile("yield");
    }
}
