#include "fdt.h"

#define FDT_BEGIN_NODE 0x1u
#define FDT_END_NODE   0x2u
#define FDT_PROP       0x3u
#define FDT_END        0x9u

struct fdt_header {
    uint32_t magic;
    uint32_t totalsize;
    uint32_t off_dt_struct;
    uint32_t off_dt_strings;
    uint32_t off_mem_rsvmap;
    uint32_t version;
    uint32_t last_comp_version;
    uint32_t boot_cpuid_phys;
    uint32_t size_dt_strings;
    uint32_t size_dt_struct;
};

static uint32_t be32(uint32_t v)
{
    return ((v & 0x000000ffu) << 24) |
           ((v & 0x0000ff00u) << 8) |
           ((v & 0x00ff0000u) >> 8) |
           ((v & 0xff000000u) >> 24);
}

static uint64_t be64(uint64_t v)
{
    return ((uint64_t)be32((uint32_t)v) << 32) | be32((uint32_t)(v >> 32));
}

static size_t align4(size_t n)
{
    return (n + 3u) & ~3u;
}

static size_t cstr_len(const char *s)
{
    size_t n = 0;
    while (s && s[n]) ++n;
    return n;
}

static int reserve_struct(struct fdt_builder *b, size_t n, uint8_t **out)
{
    size_t end = b->struct_off + b->struct_size + n;
    if (!b->buffer || end > b->strings_off || end > b->capacity)
        return 0;
    *out = b->buffer + b->struct_off + b->struct_size;
    b->struct_size += n;
    return 1;
}

static int push_u32(struct fdt_builder *b, uint32_t v)
{
    uint8_t *p;
    if (!reserve_struct(b, 4, &p))
        return 0;
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)v;
    return 1;
}

static int string_offset(struct fdt_builder *b, const char *name, uint32_t *out)
{
    size_t len = cstr_len(name) + 1;
    if (!b || !name || !out || b->strings_off + b->strings_size + len > b->capacity)
        return 0;

    *out = (uint32_t)b->strings_size;
    for (size_t i = 0; i < len; ++i)
        b->buffer[b->strings_off + b->strings_size + i] = (uint8_t)name[i];
    b->strings_size += len;
    return 1;
}

int fdt_begin(struct fdt_builder *b, void *buffer, size_t capacity)
{
    if (!b || !buffer || capacity < 256)
        return 0;

    b->buffer = (uint8_t *)buffer;
    b->capacity = capacity;
    b->struct_off = sizeof(struct fdt_header) + 16; /* terminating memreserve pair */
    b->strings_off = capacity / 2;
    if (b->strings_off <= b->struct_off)
        return 0;
    b->struct_size = 0;
    b->strings_size = 0;
    b->depth = 0;

    for (size_t i = 0; i < capacity; ++i)
        b->buffer[i] = 0;

    return 1;
}

int fdt_begin_node(struct fdt_builder *b, const char *name)
{
    if (!b || !name || !push_u32(b, FDT_BEGIN_NODE))
        return 0;

    size_t len = cstr_len(name) + 1;
    size_t padded = align4(len);
    uint8_t *p;
    if (!reserve_struct(b, padded, &p))
        return 0;

    for (size_t i = 0; i < padded; ++i)
        p[i] = i < len ? (uint8_t)name[i] : 0;

    b->depth++;
    return 1;
}

int fdt_end_node(struct fdt_builder *b)
{
    if (!b || b->depth <= 0 || !push_u32(b, FDT_END_NODE))
        return 0;
    b->depth--;
    return 1;
}

int fdt_prop(struct fdt_builder *b, const char *name, const void *data, uint32_t size)
{
    uint32_t nameoff;
    if (!b || !name || (!data && size) || !string_offset(b, name, &nameoff))
        return 0;

    if (!push_u32(b, FDT_PROP) || !push_u32(b, size) || !push_u32(b, nameoff))
        return 0;

    size_t padded = align4(size);
    uint8_t *p;
    if (!reserve_struct(b, padded, &p))
        return 0;

    const uint8_t *src = (const uint8_t *)data;
    for (size_t i = 0; i < padded; ++i)
        p[i] = i < size ? src[i] : 0;

    return 1;
}

int fdt_prop_u32(struct fdt_builder *b, const char *name, uint32_t value)
{
    uint32_t x = be32(value);
    return fdt_prop(b, name, &x, sizeof(x));
}

int fdt_prop_u64_pair(struct fdt_builder *b, const char *name, uint64_t a, uint64_t c)
{
    uint64_t pair[2] = { be64(a), be64(c) };
    return fdt_prop(b, name, pair, sizeof(pair));
}

int fdt_prop_string(struct fdt_builder *b, const char *name, const char *value)
{
    return value && fdt_prop(b, name, value, (uint32_t)(cstr_len(value) + 1));
}

int fdt_finish(struct fdt_builder *b, size_t *out_size)
{
    if (!b || b->depth != 0 || !push_u32(b, FDT_END))
        return 0;

    size_t strings_dst = align4(b->struct_off + b->struct_size);
    if (strings_dst + b->strings_size > b->strings_off ||
        strings_dst + b->strings_size > b->capacity)
        return 0;

    for (size_t i = 0; i < b->strings_size; ++i)
        b->buffer[strings_dst + i] = b->buffer[b->strings_off + i];

    struct fdt_header *h = (struct fdt_header *)b->buffer;
    size_t total = strings_dst + b->strings_size;
    h->magic = be32(FDT_MAGIC);
    h->totalsize = be32((uint32_t)total);
    h->off_dt_struct = be32((uint32_t)b->struct_off);
    h->off_dt_strings = be32((uint32_t)strings_dst);
    h->off_mem_rsvmap = be32((uint32_t)sizeof(struct fdt_header));
    h->version = be32(17);
    h->last_comp_version = be32(16);
    h->boot_cpuid_phys = 0;
    h->size_dt_strings = be32((uint32_t)b->strings_size);
    h->size_dt_struct = be32((uint32_t)b->struct_size);

    if (out_size)
        *out_size = total;
    return 1;
}
