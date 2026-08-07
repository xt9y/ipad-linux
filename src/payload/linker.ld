ENTRY(_start)

/*
 * Link at zero so the flat binary can be loaded at an arbitrary physical
 * address. All references inside the payload must remain PC-relative and CI
 * rejects linked AArch64 relocations.
 */
IMAGE_BASE = 0;

SECTIONS
{
    . = IMAGE_BASE;
    __image_start = .;

    .text : ALIGN(2048) {
        KEEP(*(.text.boot))
        KEEP(*(.text.vectors))
        *(.text*)
    }

    .rodata : ALIGN(16) {
        *(.rodata*)
    }

    .data : ALIGN(16) {
        *(.data*)
    }

    .bss (NOLOAD) : ALIGN(16) {
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    }

    /*
     * .stack is deliberately PROGBITS (emitted by start.S), not NOLOAD.
     * This makes the flat payload self-contained: its file footprint reserves
     * the exact 64 KiB stack storage used by _start.
     */
    .stack : ALIGN(16) {
        __stack_bottom = .;
        KEEP(*(.stack))
        __stack_top = .;
    }

    __image_end = .;

    ASSERT((__stack_top - __stack_bottom) == 64K,
           "bootstrap stack must remain exactly 64 KiB");

    /DISCARD/ : {
        *(.comment*)
        *(.note*)
        *(.eh_frame*)
        *(.got*)
        *(.plt*)
    }
}
