#pragma once

#include <stdint.h>

#define IPAD_PRODUCT_TYPE "iPad13,16"
#define IPAD_BOARD_CONFIG "J407AP"
#define IPAD_MODEL_NUMBER "A2588"
#define IPAD_SOC_NAME "T8103"
#define IPAD_CPID 0x8103u
#define IPAD_BDID 0x10u

struct platform_info {
    char product_type[16];
    char board_config[16];
    char model_number[16];
    char soc_name[16];
    uint32_t cpid;
    uint32_t bdid;
};

const struct platform_info *platform_get_info(void);
void platform_early_init(void);
