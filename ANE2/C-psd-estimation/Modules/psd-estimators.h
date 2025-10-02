/**
 * @file psd-estimators.h
 * @author David Ramírez Betancourth
 */
#ifndef PSD_ESTIMATORS_H
#define PSD_ESTIMATORS_H

#include <complex.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <fftw3.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif


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
    PsdWindowType_t window_type;
    double sample_rate;
    double center_freq;
    double bandwidth;
    double nperseg;
    double noverlap;
    double nfft;   
}PsdConfig_t;

void generate_window(PsdWindowType_t window_type, double* window_buffer, int window_length);

void execute_welch_psd(complex double* signal, size_t n_signal, const PsdConfig_t* config, double* f_out, double* p_out);
void execute_periodogram_psd(complex double* signal, size_t n_signal, const PsdConfig_t* config, double* f_out, double* p_out);
void execute_wavelet_psd(complex double* signal, size_t n_signal, const PsdConfig_t* config, double* f_out, double* p_out);

#endif //PSD_ESTIMATORS_H