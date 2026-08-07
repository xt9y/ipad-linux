#include "debug.h"

static struct debug_sink current_sink;

void debug_set_sink(struct debug_sink sink)
{
    current_sink = sink;
}

void debug_write(const char *data, size_t size)
{
    if (current_sink.write && data && size)
        current_sink.write(data, size, current_sink.ctx);
}

void debug_puts(const char *text)
{
    size_t len = 0;

    if (!text)
        return;

    while (text[len])
        ++len;

    debug_write(text, len);
}

void debug_puthex64(uint64_t value)
{
    static const char digits[] = "0123456789abcdef";
    char text[18];

    text[0] = '0';
    text[1] = 'x';

    for (unsigned i = 0; i < 16; ++i) {
        unsigned shift = (15u - i) * 4u;
        text[2 + i] = digits[(value >> shift) & 0xfu];
    }

    debug_write(text, sizeof(text));
}
