#include "discovery.h"

#include "adt_function.h"

static int resolve_index(struct adt_view adt, const char *path, unsigned index,
                         uint64_t *base, uint64_t *size)
{
    if (!adt_path_reg64(adt, path, index, base, size)) {
        *base = 0;
        *size = 0;
        return 0;
    }
    return 1;
}

static int resolve(struct adt_view adt, const char *path, uint64_t *base, uint64_t *size)
{
    return resolve_index(adt, path, 0, base, size);
}

static int property_string_equals(struct adt_view adt, const char *path,
                                  const char *property, const char *wanted)
{
    struct adt_node_view node;
    struct adt_property_view value;
    size_t i = 0;

    if (!adt_find_node(adt, path, &node) ||
        !adt_node_property(node, property, &value) ||
        !value.value || !value.size || !wanted)
        return 0;

    while (i < value.size && wanted[i]) {
        if (value.value[i] != (uint8_t)wanted[i])
            return 0;
        ++i;
    }

    return i < value.size && wanted[i] == '\0' && value.value[i] == 0;
}

static int touch_gpio(struct adt_view adt, const char *property,
                      uint32_t expected_function, unsigned arg,
                      uint32_t *out)
{
    struct adt_function_view function;

    if (!out ||
        !adt_path_function(adt, "/arm-io/spi4/multi-touch", property, &function) ||
        function.function != expected_function ||
        !adt_function_arg_u32(&function, arg, out))
        return 0;

    return 1;
}

int j407_discover(struct adt_view adt, struct j407_discovery *out)
{
    int found = 0;

    if (!out)
        return 0;

    *out = (struct j407_discovery){0};

    found += resolve(adt, "/arm-io/uart0", &out->uart0_base, &out->uart0_size);
    found += resolve(adt, "/arm-io/aic", &out->aic_base, &out->aic_size);
    found += resolve(adt, "/arm-io/pmgr", &out->pmgr_base, &out->pmgr_size);
    found += resolve(adt, "/arm-io/gpio", &out->gpio_base, &out->gpio_size);
    found += resolve(adt, "/arm-io/wdt", &out->wdt_base, &out->wdt_size);

    /* m1n1's T8103 NVMe driver selects ANS reg tuple 3. */
    found += resolve_index(adt, "/arm-io/ans", 3,
                           &out->nvme_base, &out->nvme_size);
    found += resolve(adt, "/arm-io/sart-ans",
                     &out->sart_ans_base, &out->sart_ans_size);

    found += resolve(adt, "/arm-io/usb-drd0",
                     &out->usb_drd0_base, &out->usb_drd0_size);
    found += resolve(adt, "/arm-io/dart-usb0",
                     &out->dart_usb0_base, &out->dart_usb0_size);

    found += resolve(adt, "/arm-io/dcp", &out->dcp_base, &out->dcp_size);
    found += resolve(adt, "/arm-io/dart-dcp",
                     &out->dart_dcp_base, &out->dart_dcp_size);
    found += resolve(adt, "/arm-io/dart-disp0",
                     &out->dart_disp0_base, &out->dart_disp0_size);

    found += resolve(adt, "/arm-io/dcpext", &out->dcpext_base, &out->dcpext_size);
    found += resolve(adt, "/arm-io/dart-dcpext",
                     &out->dart_dcpext_base, &out->dart_dcpext_size);
    found += resolve(adt, "/arm-io/dart-dispext0",
                     &out->dart_dispext0_base, &out->dart_dispext0_size);

    out->touch_hbpp = property_string_equals(adt,
                                             "/arm-io/spi4/multi-touch",
                                             "bootloader-type", "HBPP");

    touch_gpio(adt, "function-enable_cs", ADT_FUNC_GPIO, 0,
               &out->touch_cs_gpio);
    touch_gpio(adt, "function-reset", ADT_FUNC_GPIO, 0,
               &out->touch_reset_gpio);
    touch_gpio(adt, "function-config_interrupts", ADT_FUNC_GPIO_CONFIG, 0,
               &out->touch_irq_gpio);

    struct adt_function_view display_sync;
    if (adt_path_function(adt, "/arm-io/spi4/multi-touch",
                          "function-set_display_sync", &display_sync) &&
        display_sync.function == ADT_FUNC_GPIO) {
        adt_function_arg_u32(&display_sync, 0, &out->touch_display_sync0_gpio);
        adt_function_arg_u32(&display_sync, 2, &out->touch_display_sync1_gpio);
    }

    return found;
}
