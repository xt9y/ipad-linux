.section .text.boot, "ax"
.global _start
.type _start, %function

_start:
    /*
     * Execution environment is deliberately unspecified for now.
     * Do not touch MMIO or assume a particular exception level here.
     */

    /* Temporary stack supplied by the linker script. */
    adrp x0, __stack_top
    add  x0, x0, :lo12:__stack_top
    mov  sp, x0

    bl kernel_main

1:
    wfe
    b 1b

.size _start, . - _start
