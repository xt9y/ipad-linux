.section .text.boot, "ax"
.global _start
.type _start, %function

_start:
    /* x0 is reserved for an optional struct boot_info pointer. */
    mov x19, x0

    /* Temporary internal stack. The image load address is still provisional. */
    adrp x0, __stack_top
    add  x0, x0, :lo12:__stack_top
    mov  sp, x0

    mov x0, x19
    bl kernel_main

1:
    wfe
    b 1b

.size _start, . - _start
