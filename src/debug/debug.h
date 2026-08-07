#pragma once

#include <stddef.h>
#include <stdint.h>

struct debug_sink {
    void (*write)(const char *data, size_t size, void *ctx);
    void *ctx;
};

void debug_set_sink(struct debug_sink sink);
void debug_write(const char *data, size_t size);
void debug_puts(const char *text);
void debug_puthex64(uint64_t value);
