#include "exceptions.h"

#include "debug.h"

volatile struct aarch64_exception_snapshot aarch64_last_exception;

static void print_field(const char *name, uint64_t value)
{
    debug_puts(name);
    debug_puthex64(value);
    debug_puts("\n");
}

void aarch64_exception_record(uint64_t vector, uint64_t current_el,
                              uint64_t esr, uint64_t elr,
                              uint64_t far, uint64_t spsr)
{
    aarch64_last_exception.vector = vector;
    aarch64_last_exception.current_el = current_el;
    aarch64_last_exception.esr = esr;
    aarch64_last_exception.elr = elr;
    aarch64_last_exception.far = far;
    aarch64_last_exception.spsr = spsr;
    aarch64_last_exception.valid = 1;

    debug_puts("\nipad-linux: AArch64 exception\n");
    print_field("  vector=", vector);
    print_field("  EL=", current_el);
    print_field("  ESR=", esr);
    print_field("  ELR=", elr);
    print_field("  FAR=", far);
    print_field("  SPSR=", spsr);
}
