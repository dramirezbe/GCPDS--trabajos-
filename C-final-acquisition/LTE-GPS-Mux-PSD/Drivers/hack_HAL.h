#ifndef HACK_HAL_H
#define HACK_HAL_H

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <libhackrf/hackrf.h>

typedef struct {
    int fc;
    int fs;
    bool amplifier_on;
    int lna_gain;
    int vga_gain;
}hack_cfg_t;

#endif

