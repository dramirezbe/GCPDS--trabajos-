/**
 * @file Modules/psd.c
 */

#include "psd.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <fftw3.h>
#include <alloca.h>
#include <complex.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

signal_iq_t* load_iq_from_buffer(const int8_t* buffer, size_t buffer_size) {
    size_t n_samples = buffer_size / 2;
    signal_iq_t* signal_data = (signal_iq_t*)malloc(sizeof(signal_iq_t));
    
    signal_data->n_signal = n_samples;
    signal_data->signal_iq = (double complex*)malloc(n_samples * sizeof(double complex));

    for (size_t i = 0; i < n_samples; i++) {
        signal_data->signal_iq[i] = (double)buffer[2 * i] + (double)buffer[2 * i + 1] * I;
    }

    return signal_data;
}

void free_signal_iq(signal_iq_t* signal) {
    if (signal) {
        if (signal->signal_iq) free(signal->signal_iq);
        free(signal);
    }
}

static void generate_window(PsdWindowType_t window_type, double* window_buffer, int window_length) {
    for (int n = 0; n < window_length; n++) {
        switch (window_type) {
            case HANN_TYPE:
                window_buffer[n] = 0.5 * (1 - cos((2.0 * M_PI * n) / (window_length - 1)));
                break;
            case RECTANGULAR_TYPE:
                window_buffer[n] = 1.0;
                break;
            case BLACKMAN_TYPE:
                window_buffer[n] = 0.42 - 0.5 * cos((2.0 * M_PI * n) / (window_length - 1)) + 0.08 * cos((4.0 * M_PI * n) / (window_length - 1));
                break;
            case HAMMING_TYPE:
            default:
                window_buffer[n] = 0.54 - 0.46 * cos((2.0 * M_PI * n) / (window_length - 1));
                break;
        }
    }
}

static void fftshift(double* data, int n) {
    int half = n / 2;
    double* temp = (double*)alloca(half * sizeof(double));
    memcpy(temp, data, half * sizeof(double));
    memcpy(data, &data[half], (n - half) * sizeof(double));
    memcpy(&data[n - half], temp, half * sizeof(double));
}

void execute_welch_psd(signal_iq_t* signal_data, const PsdConfig_t* config, double* f_out, double* p_out) {
    double complex* signal = signal_data->signal_iq;
    size_t n_signal = signal_data->n_signal;
    int nperseg = config->nperseg;
    int noverlap = config->noverlap;
    double fs = config->sample_rate;
    
    int nfft = nperseg;
    int step = nperseg - noverlap;
    int k_segments = (n_signal - noverlap) / step;

    double* window = (double*)malloc(nperseg * sizeof(double));
    generate_window(config->window_type, window, nperseg);

    double u_norm = 0.0;
    for (int i = 0; i < nperseg; i++) u_norm += window[i] * window[i];
    u_norm /= nperseg;

    double complex* fft_in = fftw_alloc_complex(nfft);
    double complex* fft_out = fftw_alloc_complex(nfft);
    fftw_plan plan = fftw_plan_dft_1d(nfft, fft_in, fft_out, FFTW_FORWARD, FFTW_ESTIMATE);

    memset(p_out, 0, nfft * sizeof(double));

    for (int k = 0; k < k_segments; k++) {
        int start = k * step;
        
        for (int i = 0; i < nperseg; i++) {
            fft_in[i] = signal[start + i] * window[i];
        }

        fftw_execute(plan);

        for (int i = 0; i < nfft; i++) {
            double mag = cabs(fft_out[i]);
            p_out[i] += (mag * mag);
        }
    }

    double scale = 1.0 / (fs * u_norm * k_segments * nperseg);
    for (int i = 0; i < nfft; i++) p_out[i] *= scale;

    fftshift(p_out, nfft);

    // --- DC SPIKE REMOVAL ---
    // Flatten center 7 bins (indices -3 to +3 relative to DC)
    // Replace them with the average of the neighbors at -4 and +4
    int c = nfft / 2; 
    if (nfft > 8) {
        double neighbor_mean = (p_out[c - 4] + p_out[c + 4]) / 2.0;
        for (int i = -3; i <= 3; i++) {
            p_out[c + i] = neighbor_mean;
        }
    }

    double df = fs / nfft;
    for (int i = 0; i < nfft; i++) {
        f_out[i] = -fs / 2.0 + i * df;
    }

    free(window);
    fftw_destroy_plan(plan);
    fftw_free(fft_in);
    fftw_free(fft_out);
}