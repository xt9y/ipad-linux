#pragma once

#include <stdint.h>

uint64_t aarch64_current_el(void);
uint64_t aarch64_daif(void);
uint64_t aarch64_sctlr_el1(void);
int aarch64_el1_mmu_enabled(void);
void aarch64_mask_interrupts(void);
