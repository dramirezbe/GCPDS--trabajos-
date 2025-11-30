/**
 * @file Modules/datatypes.h
 * @brief Shared types for PSD and Signal processing
 */

#ifndef DATATYPES_H
#define DATATYPES_H

#include <complex.h>
#include <stddef.h>

typedef struct {
    double complex* signal_iq;
    size_t n_signal;
} signal_iq_t;

typedef enum {
    HAMMING_TYPE,
    HANN_TYPE,
    RECTANGULAR_TYPE,
    BLACKMAN_TYPE,
    FLAT_TOP_TYPE,
    KAISER_TYPE,
    TUKEY_TYPE,
    BARTLETT_TYPE
} PsdWindowType_t;

typedef struct {
    PsdWindowType_t window_type;
    double sample_rate;
    int nperseg;
    int noverlap;
} PsdConfig_t;

#endif