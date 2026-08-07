#include "linux_image.h"

static uint32_t read_u32le(const uint8_t *p)
{
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static uint64_t read_u64le(const uint8_t *p)
{
    return (uint64_t)read_u32le(p) | ((uint64_t)read_u32le(p + 4) << 32);
}

int linux_image_parse(const void *image, size_t size, struct linux_image_info *out)
{
    const uint8_t *p = (const uint8_t *)image;

    if (!p || !out || size < 64)
        return 0;

    if (read_u32le(p + 56) != ARM64_IMAGE_MAGIC)
        return 0;

    out->text_offset = read_u64le(p + 8);
    out->image_size = read_u64le(p + 16);
    out->flags = read_u64le(p + 24);

    if (out->image_size == 0)
        out->text_offset = 0x80000;

    return 1;
}
