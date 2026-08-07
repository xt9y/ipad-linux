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
