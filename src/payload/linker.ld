ENTRY(_start)

/*
 * Link at zero so the flat binary can be loaded at an arbitrary physical
 * address. All references inside the payload must remain PC-relative and CI
 * rejects linked AArch64 relocations.
 */
IMAGE_BASE = 0;
STACK_SIZE = 64K;

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

    . = ALIGN(16);
    __stack_bottom = .;
    . += STACK_SIZE;
    __stack_top = .;
    __image_end = .;

    /DISCARD/ : {
        *(.comment*)
        *(.note*)
        *(.eh_frame*)
        *(.got*)
        *(.plt*)
    }
}
