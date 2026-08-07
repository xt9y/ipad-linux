#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "adt.h"
#include "adt_clock.h"
#include "adt_function.h"

struct reg_query {
    const char *label;
    const char *path;
    unsigned index;
};

static const struct reg_query queries[] = {
    { "uart0",         "/arm-io/uart0",         0 },
    { "aic",           "/arm-io/aic",           0 },
    { "pmgr",          "/arm-io/pmgr",          0 },
    { "gpio",          "/arm-io/gpio",          0 },
    { "wdt",           "/arm-io/wdt",           0 },
    { "ans-nvme",      "/arm-io/ans",           3 },
    { "sart-ans",      "/arm-io/sart-ans",      0 },
    { "usb-drd0",      "/arm-io/usb-drd0",      0 },
    { "dart-usb0",     "/arm-io/dart-usb0",     0 },
    { "apcie",         "/arm-io/apcie",         0 },
    { "dart-apcie0",   "/arm-io/dart-apcie0",   0 },
    { "spi4",          "/arm-io/spi4",          0 },
    { "dcp",           "/arm-io/dcp",           0 },
    { "dart-dcp",      "/arm-io/dart-dcp",      0 },
    { "dart-disp0",    "/arm-io/dart-disp0",    0 },
    { "dcpext",        "/arm-io/dcpext",        0 },
    { "dart-dcpext",   "/arm-io/dart-dcpext",   0 },
    { "dart-dispext0", "/arm-io/dart-dispext0", 0 },
};

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

static void print_root_string(struct adt_view adt, const char *name)
{
    struct adt_property_view prop;

    printf("%-18s: ", name);
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

static void print_ascii_u64_property(struct adt_view adt,
                                     const char *path,
                                     const char *name)
{
    struct adt_node_view node;
    struct adt_property_view prop;

    printf("%-18s: ", name);
    if (!adt_find_node(adt, path, &node) ||
        !adt_node_property(node, name, &prop) || prop.size < 8) {
        puts("<missing>");
        return;
    }

    uint64_t raw = read_u64le(prop.value);
    uint8_t bytes[8];
    for (unsigned i = 0; i < 8; ++i)
        bytes[i] = (uint8_t)(raw >> (i * 8));

    putchar('"');
    for (unsigned i = 0; i < 8 && bytes[i]; ++i)
        putchar(bytes[i] >= 32 && bytes[i] < 127 ? bytes[i] : '.');
    printf("\" (0x%016" PRIx64 ")\n", raw);
}

static void print_function_property(struct adt_view adt,
                                    const char *path,
                                    const char *name)
{
    struct adt_function_view fn;

    printf("%-18s: ", name);
    if (!adt_path_function(adt, path, name, &fn)) {
        puts("<missing>");
        return;
    }

    printf("phandle=%" PRIu32 " function='%c%c%c%c'",
           fn.phandle,
           (char)(fn.function >> 24),
           (char)(fn.function >> 16),
           (char)(fn.function >> 8),
           (char)fn.function);

    for (uint32_t i = 0; i < fn.arg_count; ++i) {
        uint32_t arg = 0;
        if (adt_function_arg_u32(&fn, i, &arg))
            printf(" arg%" PRIu32 "=%" PRIu32 "(0x%08" PRIx32 ")", i, arg, arg);
    }
    putchar('\n');
}

static void print_string_property(struct adt_view adt,
                                  const char *path,
                                  const char *name)
{
    struct adt_node_view node;
    struct adt_property_view prop;

    printf("%-18s: ", name);
    if (!adt_find_node(adt, path, &node) ||
        !adt_node_property(node, name, &prop) || !prop.size) {
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

static void print_boot_clock(struct adt_view adt,
                             const char *label,
                             const char *path,
                             unsigned clock_index)
{
    uint32_t clock_id = 0;
    uint32_t frequency_hz = 0;

    printf("%-18s: ", label);
    if (!adt_path_boot_clock(adt, path, clock_index,
                             &clock_id, &frequency_hz)) {
        puts("<not resolved>");
        return;
    }

    printf("clock-id=%" PRIu32 " table-index=%" PRIu32
           " frequency=%" PRIu32 " Hz",
           clock_id, clock_id - 256u, frequency_hz);
    if (!frequency_hz)
        printf(" (runtime/template value unavailable)");
    putchar('\n');
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

    puts("\nJ407 PCIe/radio identity:");
    print_ascii_u64_property(adt, "/arm-io/wlan", "module-instance");
    print_function_property(adt, "/arm-io/apcie/pci-bridge0", "function-perst");

    puts("\nJ407 multitouch identity:");
    print_string_property(adt, "/arm-io/spi4/multi-touch", "bootloader-type");
    print_boot_clock(adt, "spi4 boot clock", "/arm-io/spi4", 0);
    print_function_property(adt, "/arm-io/spi4/multi-touch", "function-enable_cs");
    print_function_property(adt, "/arm-io/spi4/multi-touch", "function-reset");
    print_function_property(adt, "/arm-io/spi4/multi-touch", "function-set_int_config");

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
