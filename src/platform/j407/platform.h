#pragma once

#include <stdint.h>

#define IPAD_PRODUCT_TYPE "iPad13,16"
#define IPAD_BOARD_CONFIG "J407AP"
#define IPAD_MODEL_NUMBER "A2588"
#define IPAD_SOC_NAME "T8103"
#define IPAD_CPID 0x8103u
#define IPAD_BDID 0x10u

struct platform_info {
    const char *product_type;
    const char *board_config;
    const char *model_number;
    const char *soc_name;
    uint32_t cpid;
    uint32_t bdid;
};

const struct platform_info *platform_get_info(void);
void platform_early_init(void);
