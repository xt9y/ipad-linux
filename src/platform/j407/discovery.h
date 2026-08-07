#pragma once

#include <stdint.h>

#include "adt.h"

struct j407_discovery {
    uint64_t uart0_base;
    uint64_t uart0_size;
    uint64_t aic_base;
    uint64_t aic_size;
    uint64_t pmgr_base;
    uint64_t pmgr_size;
    uint64_t gpio_base;
    uint64_t gpio_size;
    uint64_t wdt_base;
    uint64_t wdt_size;

    /* Apple ANS/NVMe. m1n1 uses reg tuple 3 as the NVMe controller base. */
    uint64_t nvme_base;
    uint64_t nvme_size;
    uint64_t sart_ans_base;
    uint64_t sart_ans_size;

    /* The single J407 USB DRD path and its DART. */
    uint64_t usb_drd0_base;
    uint64_t usb_drd0_size;
    uint64_t dart_usb0_base;
    uint64_t dart_usb0_size;

    /* Internal-display DCP path used by m1n1's M1 display configuration. */
    uint64_t dcp_base;
    uint64_t dcp_size;
    uint64_t dart_dcp_base;
    uint64_t dart_dcp_size;
    uint64_t dart_disp0_base;
    uint64_t dart_disp0_size;

    /* External-display path is present on some J407 ADTs; discovery is optional. */
    uint64_t dcpext_base;
    uint64_t dcpext_size;
    uint64_t dart_dcpext_base;
    uint64_t dart_dcpext_size;
    uint64_t dart_dispext0_base;
    uint64_t dart_dispext0_size;
};

int j407_discover(struct adt_view adt, struct j407_discovery *out);
