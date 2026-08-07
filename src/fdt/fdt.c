#include "fdt.h"

#define FDT_BEGIN_NODE 0x1u
#define FDT_END_NODE   0x2u
#define FDT_PROP       0x3u
#define FDT_NOP        0x4u
#define FDT_END        0x9u
#define FDT_MAX_DEPTH  64

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

static uint32_t read_be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) |
           ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) |
           (uint32_t)p[3];
}

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

static int bounded_cstr_len(const uint8_t *s, size_t available, size_t *out_len)
{
    if (!s || !out_len)
        return 0;

    for (size_t i = 0; i < available; ++i) {
        if (s[i] == 0) {
            *out_len = i;
            return 1;
        }
    }

    return 0;
}

static int text_equals_bytes(const char *text, const uint8_t *bytes, size_t bytes_len)
{
    if (!text || !bytes)
        return 0;

    size_t i = 0;
    while (text[i] && i < bytes_len) {
        if ((uint8_t)text[i] != bytes[i])
            return 0;
        ++i;
    }

    return i == bytes_len && text[i] == '\0';
}

static int path_component_count(const char *path, size_t *out_count)
{
    if (!path || !out_count || path[0] != '/')
        return 0;

    size_t count = 0;
    size_t i = 1;

    while (path[i]) {
        while (path[i] == '/')
            ++i;
        if (!path[i])
            break;

        ++count;
        while (path[i] && path[i] != '/')
            ++i;
    }

    *out_count = count;
    return 1;
}

static int path_component_equals(const char *path, size_t wanted_index,
                                 const uint8_t *name, size_t name_len)
{
    size_t index = 0;
    size_t i = 1;

    while (path[i]) {
        while (path[i] == '/')
            ++i;
        if (!path[i])
            break;

        size_t start = i;
        while (path[i] && path[i] != '/')
            ++i;

        if (index == wanted_index) {
            size_t len = i - start;
            if (len != name_len)
                return 0;
            for (size_t n = 0; n < len; ++n) {
                if ((uint8_t)path[start + n] != name[n])
                    return 0;
            }
            return 1;
        }

        ++index;
    }

    return 0;
}

int fdt_check_header(const void *data, size_t available, size_t *total_size)
{
    const uint8_t *p = (const uint8_t *)data;

    if (!p || available < sizeof(struct fdt_header))
        return 0;

    if (read_be32(p) != FDT_MAGIC)
        return 0;

    uint32_t total = read_be32(p + 4);
    uint32_t struct_off = read_be32(p + 8);
    uint32_t strings_off = read_be32(p + 12);
    uint32_t reserve_off = read_be32(p + 16);
    uint32_t version = read_be32(p + 20);
    uint32_t strings_size = read_be32(p + 32);
    uint32_t struct_size = read_be32(p + 36);

    if (total < sizeof(struct fdt_header) || total > available)
        return 0;
    if (version < 16 || version > 17)
        return 0;
    if (reserve_off < sizeof(struct fdt_header) || reserve_off > total ||
        total - reserve_off < 16)
        return 0;
    if (struct_off > total || struct_size > total - struct_off)
        return 0;
    if (strings_off > total || strings_size > total - strings_off)
        return 0;

    if (total_size)
        *total_size = total;
    return 1;
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
    b->struct_off = sizeof(struct fdt_header) + 16;
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

int fdt_prop_u64(struct fdt_builder *b, const char *name, uint64_t value)
{
    uint64_t x = be64(value);
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

int fdt_setprop_inplace(void *dtb, size_t available,
                        const char *path, const char *property,
                        const void *data, uint32_t size)
{
    uint8_t *blob = (uint8_t *)dtb;
    size_t total = 0;
    size_t component_count = 0;

    if (!blob || !property || (!data && size) ||
        !path_component_count(path, &component_count) ||
        !fdt_check_header(blob, available, &total))
        return 0;

    uint32_t struct_off = read_be32(blob + 8);
    uint32_t strings_off = read_be32(blob + 12);
    uint32_t strings_size = read_be32(blob + 32);
    uint32_t struct_size = read_be32(blob + 36);

    if ((size_t)struct_off + struct_size > total ||
        (size_t)strings_off + strings_size > total)
        return 0;

    uint8_t *structure = blob + struct_off;
    uint8_t *strings = blob + strings_off;
    size_t cursor = 0;
    int depth = -1;
    uint8_t prefix_matches[FDT_MAX_DEPTH] = {0};

    while (cursor + 4 <= struct_size) {
        uint32_t token = read_be32(structure + cursor);
        cursor += 4;

        if (token == FDT_BEGIN_NODE) {
            if (++depth >= FDT_MAX_DEPTH)
                return 0;

            size_t name_len = 0;
            if (!bounded_cstr_len(structure + cursor, struct_size - cursor, &name_len))
                return 0;

            size_t encoded = align4(name_len + 1);
            if (encoded > struct_size - cursor)
                return 0;

            if (depth == 0) {
                prefix_matches[0] = name_len == 0;
            } else {
                prefix_matches[depth] = prefix_matches[depth - 1] &&
                    (size_t)depth <= component_count &&
                    path_component_equals(path, (size_t)depth - 1,
                                          structure + cursor, name_len);
            }

            cursor += encoded;
            continue;
        }

        if (token == FDT_END_NODE) {
            if (depth < 0)
                return 0;
            prefix_matches[depth] = 0;
            --depth;
            continue;
        }

        if (token == FDT_PROP) {
            if (cursor + 8 > struct_size)
                return 0;

            uint32_t prop_size = read_be32(structure + cursor);
            uint32_t name_off = read_be32(structure + cursor + 4);
            cursor += 8;

            size_t padded = align4(prop_size);
            if (padded > struct_size - cursor || name_off >= strings_size)
                return 0;

            size_t prop_name_len = 0;
            if (!bounded_cstr_len(strings + name_off,
                                  strings_size - name_off,
                                  &prop_name_len))
                return 0;

            if (depth >= 0 && (size_t)depth == component_count &&
                prefix_matches[depth] &&
                text_equals_bytes(property, strings + name_off, prop_name_len)) {
                if (prop_size != size)
                    return 0;

                const uint8_t *src = (const uint8_t *)data;
                for (uint32_t i = 0; i < size; ++i)
                    structure[cursor + i] = src[i];
                return 1;
            }

            cursor += padded;
            continue;
        }

        if (token == FDT_NOP)
            continue;

        if (token == FDT_END)
            return 0;

        return 0;
    }

    return 0;
}

int fdt_setprop_u64_inplace(void *dtb, size_t available,
                            const char *path, const char *property,
                            uint64_t value)
{
    uint64_t encoded = be64(value);
    return fdt_setprop_inplace(dtb, available, path, property,
                               &encoded, sizeof(encoded));
}

int fdt_setprop_u64_pair_inplace(void *dtb, size_t available,
                                 const char *path, const char *property,
                                 uint64_t a, uint64_t b)
{
    uint64_t encoded[2] = { be64(a), be64(b) };
    return fdt_setprop_inplace(dtb, available, path, property,
                               encoded, sizeof(encoded));
}
