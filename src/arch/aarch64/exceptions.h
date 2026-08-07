#pragma once

#include <stdint.h>

struct aarch64_exception_snapshot {
    uint64_t valid;
    uint64_t vector;
    uint64_t current_el;
    uint64_t esr;
    uint64_t elr;
    uint64_t far;
    uint64_t spsr;
};

extern volatile struct aarch64_exception_snapshot aarch64_last_exception;

void exception_vectors_install_current(void);
void aarch64_exception_record(uint64_t vector, uint64_t current_el,
                              uint64_t esr, uint64_t elr,
                              uint64_t far, uint64_t spsr);
