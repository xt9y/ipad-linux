.section .text, "ax"

.global aarch64_current_el
.type aarch64_current_el, %function
aarch64_current_el:
    mrs x0, CurrentEL
    lsr x0, x0, #2
    ret
.size aarch64_current_el, . - aarch64_current_el

.global aarch64_daif
.type aarch64_daif, %function
aarch64_daif:
    mrs x0, DAIF
    ret
.size aarch64_daif, . - aarch64_daif

.global aarch64_sctlr_el1
.type aarch64_sctlr_el1, %function
aarch64_sctlr_el1:
    mrs x0, SCTLR_EL1
    ret
.size aarch64_sctlr_el1, . - aarch64_sctlr_el1

.global aarch64_el1_mmu_enabled
.type aarch64_el1_mmu_enabled, %function
aarch64_el1_mmu_enabled:
    mrs x0, SCTLR_EL1
    and x0, x0, #1
    ret
.size aarch64_el1_mmu_enabled, . - aarch64_el1_mmu_enabled

.global aarch64_mmu_enabled
.type aarch64_mmu_enabled, %function
aarch64_mmu_enabled:
    mrs x1, CurrentEL
    lsr x1, x1, #2

    cmp x1, #2
    b.eq 1f
    cmp x1, #1
    b.eq 2f

    /* Fail closed outside the Linux-supported entry ELs. */
    mov x0, #1
    ret

1:
    mrs x0, SCTLR_EL2
    and x0, x0, #1
    ret

2:
    mrs x0, SCTLR_EL1
    and x0, x0, #1
    ret
.size aarch64_mmu_enabled, . - aarch64_mmu_enabled

.global aarch64_clean_dcache_range
.type aarch64_clean_dcache_range, %function
aarch64_clean_dcache_range:
    /* x0 = start physical/identity-mapped address, x1 = byte size */
    cbz x1, 4f

    add x5, x0, x1
    mrs x2, CTR_EL0
    ubfx x2, x2, #16, #4       /* DminLine, log2(words) */
    mov x3, #4
    lsl x3, x3, x2             /* cache line size in bytes */
    sub x4, x3, #1
    bic x0, x0, x4

3:
    dc cvac, x0
    add x0, x0, x3
    cmp x0, x5
    b.lo 3b
    dsb sy
4:
    ret
.size aarch64_clean_dcache_range, . - aarch64_clean_dcache_range

.global aarch64_invalidate_icache_range
.type aarch64_invalidate_icache_range, %function
aarch64_invalidate_icache_range:
    /* x0 = start physical/identity-mapped address, x1 = byte size */
    cbz x1, 6f

    add x5, x0, x1
    mrs x2, CTR_EL0
    and x2, x2, #0xf           /* IminLine, log2(words) */
    mov x3, #4
    lsl x3, x3, x2             /* cache line size in bytes */
    sub x4, x3, #1
    bic x0, x0, x4

5:
    ic ivau, x0
    add x0, x0, x3
    cmp x0, x5
    b.lo 5b
    dsb sy
    isb
6:
    ret
.size aarch64_invalidate_icache_range, . - aarch64_invalidate_icache_range

.global aarch64_mask_interrupts
.type aarch64_mask_interrupts, %function
aarch64_mask_interrupts:
    msr daifset, #0xf
    isb
    ret
.size aarch64_mask_interrupts, . - aarch64_mask_interrupts
