.section .text.boot, "ax"
.global _start
.type _start, %function

_start:
    /* x0 is reserved for an optional struct boot_info pointer. */
    mov x19, x0

    /* Temporary internal stack. All symbol references remain PC-relative. */
    adrp x0, __stack_top
    add  x0, x0, :lo12:__stack_top
    mov  sp, x0

    /*
     * payload.bin contains no bytes for the NOLOAD .bss section. A raw
     * next-stage loader therefore cannot be assumed to have zeroed it for us.
     * Clear it explicitly before any C global state (debug sink, exception
     * snapshot, etc.) can be observed.
     */
    adrp x1, __bss_start
    add  x1, x1, :lo12:__bss_start
    adrp x2, __bss_end
    add  x2, x2, :lo12:__bss_end

1:
    cmp x1, x2
    b.hs 2f
    strb wzr, [x1], #1
    b 1b

2:
    dsb sy
    mov x0, x19
    bl kernel_main

3:
    wfe
    b 3b

.size _start, . - _start
