.section .text, "ax"
.global linux_enter
.type linux_enter, %function

linux_enter:
    /* x0 = kernel entry, x1 = physical DTB address */
    mov x4, x0
    mov x0, x1
    mov x1, xzr
    mov x2, xzr
    mov x3, xzr
    br  x4

.size linux_enter, . - linux_enter
