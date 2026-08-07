.section .text.vectors, "ax"
.align 11
.global exception_vectors
exception_vectors:
    .rept 16
        b exception_default
        .space 124
    .endr

.global exception_default
exception_default:
1:
    wfe
    b 1b

.global exception_vectors_install_el1
.type exception_vectors_install_el1, %function
exception_vectors_install_el1:
    adrp x0, exception_vectors
    add  x0, x0, :lo12:exception_vectors
    msr  vbar_el1, x0
    isb
    ret
.size exception_vectors_install_el1, . - exception_vectors_install_el1
