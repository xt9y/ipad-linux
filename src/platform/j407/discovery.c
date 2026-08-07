#include "discovery.h"

static int resolve(struct adt_view adt, const char *path, uint64_t *base, uint64_t *size)
{
    if (!adt_path_reg64(adt, path, 0, base, size)) {
        *base = 0;
        *size = 0;
        return 0;
    }
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

    return found;
}
