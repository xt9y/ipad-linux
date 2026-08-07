#pragma once

#include <stddef.h>
#include <stdint.h>

#define ARM64_IMAGE_MAGIC 0x644d5241u

struct linux_image_info {
    uint64_t text_offset;
    uint64_t image_size;
    uint64_t flags;
};

int linux_image_parse(const void *image, size_t size, struct linux_image_info *out);
