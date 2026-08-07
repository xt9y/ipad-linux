#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "adt.h"

struct reg_query {
    const char *label;
    const char *path;
    unsigned index;
};

static const struct reg_query queries[] = {
    { "uart0",        "/arm-io/uart0",        0 },
    { "aic",          "/arm-io/aic",          0 },
    { "pmgr",         "/arm-io/pmgr",         0 },
    { "gpio",         "/arm-io/gpio",         0 },
    { "wdt",          "/arm-io/wdt",          0 },
    { "ans-nvme",     "/arm-io/ans",          3 },
    { "sart-ans",     "/arm-io/sart-ans",     0 },
    { "usb-drd0",     "/arm-io/usb-drd0",     0 },
    { "dart-usb0",    "/arm-io/dart-usb0",    0 },
    { "dcp",          "/arm-io/dcp",          0 },
    { "dart-dcp",     "/arm-io/dart-dcp",     0 },
    { "dart-disp0",   "/arm-io/dart-disp0",   0 },
    { "dcpext",       "/arm-io/dcpext",       0 },
    { "dart-dcpext",  "/arm-io/dart-dcpext",  0 },
    { "dart-dispext0", "/arm-io/dart-dispext0", 0 },
};

static void print_root_string(struct adt_view adt, const char *name)
{
    struct adt_property_view prop;

    printf("%-14s: ", name);
    if (!adt_root_property(adt, name, &prop) || !prop.size) {
        puts("<missing>");
        return;
    }

    putchar('"');
    for (uint32_t i = 0; i < prop.size && prop.value[i]; ++i) {
        unsigned char c = prop.value[i];
        putchar(c >= 32 && c < 127 ? c : '.');
    }
    puts("\"");
}

static int read_file(const char *path, uint8_t **out_data, size_t *out_size)
{
    FILE *f = fopen(path, "rb");
    long length;
    uint8_t *data;

    if (!f)
        return 0;

    if (fseek(f, 0, SEEK_END) != 0 || (length = ftell(f)) <= 0 ||
        fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        return 0;
    }

    data = malloc((size_t)length);
    if (!data) {
        fclose(f);
        return 0;
    }

    if (fread(data, 1, (size_t)length, f) != (size_t)length) {
        free(data);
        fclose(f);
        return 0;
    }

    fclose(f);
    *out_data = data;
    *out_size = (size_t)length;
    return 1;
}

int main(int argc, char **argv)
{
    uint8_t *data = 0;
    size_t size = 0;

    if (argc != 2) {
        fprintf(stderr, "usage: %s adt.bin\n", argv[0]);
        return 2;
    }

    if (!read_file(argv[1], &data, &size)) {
        fprintf(stderr, "adt-inspect: could not read %s\n", argv[1]);
        return 1;
    }

    struct adt_view adt = { .data = data, .size = size };
    if (!adt_validate(adt)) {
        fprintf(stderr, "adt-inspect: invalid/truncated Apple Device Tree\n");
        free(data);
        return 1;
    }

    printf("Apple Device Tree: %zu bytes\n", size);
    print_root_string(adt, "model");
    print_root_string(adt, "target-type");
    print_root_string(adt, "compatible");

    puts("\nTranslated register regions:");
    for (size_t i = 0; i < sizeof(queries) / sizeof(queries[0]); ++i) {
        uint64_t addr = 0;
        uint64_t reg_size = 0;

        if (adt_path_reg64(adt, queries[i].path, queries[i].index,
                           &addr, &reg_size)) {
            printf("  %-14s  phys=0x%016" PRIx64 " size=0x%" PRIx64
                   "  %s[%u]\n",
                   queries[i].label, addr, reg_size,
                   queries[i].path, queries[i].index);
        } else {
            printf("  %-14s  <not resolved>  %s[%u]\n",
                   queries[i].label, queries[i].path, queries[i].index);
        }
    }

    free(data);
    return 0;
}
