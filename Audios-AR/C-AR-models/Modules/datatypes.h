/**
 * @file datatypes.h
 * @author David Ramírez
 * @brief Data types used in the project.
 */

#ifndef DATATYPES_H
#define DATATYPES_H

#include <complex.h>
#include <stddef.h>
#include <math.h>

//-----------------------
//IQ STRUCTS
//-----------------------

typedef struct {
    complex double* signal_iq;
    size_t n_signal;
}signal_iq_t;

//-----------------------
//PSD STRUCTS
//-----------------------

typedef enum {
    WELCH_TYPE,
    PERIODOGRAM_TYPE,
    WAVELET_TYPE
}PsdMethodType_t;

typedef enum {
    HAMMING_TYPE,
    HANN_TYPE,
    RECTANGULAR_TYPE,
    BLACKMAN_TYPE,
    FLAT_TOP_TYPE,
    KAISER_TYPE,
    TUKEY_TYPE,
    BARTLETT_TYPE
}PsdWindowType_t;

typedef struct {
    PsdMethodType_t method_type;
    PsdWindowType_t window_type;
    double sample_rate;
    int nperseg;
    int noverlap;
    int nfft;
}PsdConfig_t;

//-----------------------  
//BACKEND PARAMS STRUCT
//-----------------------

typedef enum {
    INSTANTANEOUS_TYPE,
    SWEEP_TYPE
}HackRFCaptureMode_t;

typedef struct {
    double bw;
    double frequency;
    HackRFCaptureMode_t mode;
} BackendParams_t;

typedef struct {
    char json_path[2048];
    char samples_path[2048];
} Paths_t;

#endif // DATATYPES_H