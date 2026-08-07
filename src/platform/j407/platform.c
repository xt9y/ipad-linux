#include "platform.h"

static const struct platform_info info = {
    .product_type = IPAD_PRODUCT_TYPE,
    .board_config = IPAD_BOARD_CONFIG,
    .model_number = IPAD_MODEL_NUMBER,
    .soc_name = IPAD_SOC_NAME,
    .cpid = IPAD_CPID,
    .bdid = IPAD_BDID,
};

const struct platform_info *platform_get_info(void)
{
    return &info;
}

void platform_early_init(void)
{
    /*
     * Intentionally empty until we have a verified execution environment.
     * No MMIO writes belong here until addresses and required power/clock
     * state have been confirmed for J407AP from trustworthy sources or
     * measurements on the device.
     */
}
