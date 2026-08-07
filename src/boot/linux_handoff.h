#pragma once

#include <stdint.h>

/*
 * Final AArch64 Linux kernel entry shim.
 *
 * The caller must already satisfy the Linux arm64 boot protocol: non-secure
 * EL1 or EL2, interrupts masked, MMU off, caches/device DMA handled, and a
 * valid flattened DTB in RAM.
 */
__attribute__((noreturn))
void linux_enter(uint64_t kernel_entry, uint64_t dtb_phys);
