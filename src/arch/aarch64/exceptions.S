.section .text.vectors, "ax"
.align 11
.global exception_vectors
exception_vectors:
    b vector_0
    .space 124
    b vector_1
    .space 124
    b vector_2
    .space 124
    b vector_3
    .space 124
    b vector_4
    .space 124
    b vector_5
    .space 124
    b vector_6
    .space 124
    b vector_7
    .space 124
    b vector_8
    .space 124
    b vector_9
    .space 124
    b vector_10
    .space 124
    b vector_11
    .space 124
    b vector_12
    .space 124
    b vector_13
    .space 124
    b vector_14
    .space 124
    b vector_15
    .space 124

vector_0:  mov x0, #0;  b exception_common
vector_1:  mov x0, #1;  b exception_common
vector_2:  mov x0, #2;  b exception_common
vector_3:  mov x0, #3;  b exception_common
vector_4:  mov x0, #4;  b exception_common
vector_5:  mov x0, #5;  b exception_common
vector_6:  mov x0, #6;  b exception_common
vector_7:  mov x0, #7;  b exception_common
vector_8:  mov x0, #8;  b exception_common
vector_9:  mov x0, #9;  b exception_common
vector_10: mov x0, #10; b exception_common
vector_11: mov x0, #11; b exception_common
vector_12: mov x0, #12; b exception_common
vector_13: mov x0, #13; b exception_common
vector_14: mov x0, #14; b exception_common
vector_15: mov x0, #15; b exception_common

exception_common:
    mrs x1, CurrentEL
    lsr x1, x1, #2

    cmp x1, #2
    b.eq exception_from_el2
    cmp x1, #1
    b.eq exception_from_el1

    mov x2, xzr
    mov x3, xzr
    mov x4, xzr
    mov x5, xzr
    b exception_record

exception_from_el2:
    mrs x2, ESR_EL2
    mrs x3, ELR_EL2
    mrs x4, FAR_EL2
    mrs x5, SPSR_EL2
    b exception_record

exception_from_el1:
    mrs x2, ESR_EL1
    mrs x3, ELR_EL1
    mrs x4, FAR_EL1
    mrs x5, SPSR_EL1

exception_record:
    bl aarch64_exception_record
1:
    wfe
    b 1b

.global exception_vectors_install_current
.type exception_vectors_install_current, %function
exception_vectors_install_current:
    adrp x0, exception_vectors
    add  x0, x0, :lo12:exception_vectors

    mrs x1, CurrentEL
    lsr x1, x1, #2
    cmp x1, #2
    b.eq 2f
    cmp x1, #1
    b.eq 3f
    ret

2:
    msr vbar_el2, x0
    isb
    ret

3:
    msr vbar_el1, x0
    isb
    ret
.size exception_vectors_install_current, . - exception_vectors_install_current
