ENTRY(_start)

/*
 * Placeholder link address for build-time validation only.
 * This is NOT a discovered or claimed iPad physical address.
 */
VMLINUX_BASE = 0x80000000;
STACK_SIZE = 64K;

SECTIONS
{
    . = VMLINUX_BASE;

    .text : ALIGN(16) {
        KEEP(*(.text.boot))
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

    /DISCARD/ : {
        *(.comment*)
        *(.note*)
        *(.eh_frame*)
    }
}
