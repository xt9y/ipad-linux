#pragma once

#include "adt.h"

/* Safe subset of J407 handoff preparation verified against m1n1. */
int j407_disable_watchdogs(struct adt_view adt);
