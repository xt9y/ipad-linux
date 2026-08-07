#pragma once

#include <stdint.h>

#include "adt.h"

int debug_uart_from_adt(struct adt_view adt, uint64_t *resolved_base);
void debug_uart_use_base(uint64_t base);
