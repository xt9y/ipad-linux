#pragma once

#include <stdint.h>

#include "adt.h"

/*
 * Resolve one device clock-id through /arm-io/clock-frequencies.
 *
 * Modern Apple ADTs use clock IDs >= 256 for the boot-clock table; ID N maps
 * to clock-frequencies[N - 256]. The returned frequency may legitimately be
 * zero in template/static ADTs where iBoot fills the runtime value later.
 *
 * Returns 1 when both the device clock-id and corresponding frequency-table
 * entry exist, otherwise 0. Fixed/legacy clock IDs below 256 are deliberately
 * not guessed here.
 */
int adt_path_boot_clock(struct adt_view adt, const char *path,
                        unsigned clock_index, uint32_t *clock_id,
                        uint32_t *frequency_hz);
