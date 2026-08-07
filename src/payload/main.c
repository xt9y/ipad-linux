#include <stdint.h>

__attribute__((noreturn))
void kernel_main(void)
{
    volatile uint64_t heartbeat = 0;

    for (;;) {
        heartbeat++;
        __asm__ volatile("yield");
    }
}
