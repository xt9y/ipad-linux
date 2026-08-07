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

.global aarch64_mask_interrupts
.type aarch64_mask_interrupts, %function
aarch64_mask_interrupts:
    msr daifset, #0xf
    isb
    ret
.size aarch64_mask_interrupts, . - aarch64_mask_interrupts
