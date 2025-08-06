/**
 * @file psd-estimators.c
 * @author David Ramírez Betancourth
 */

#include "psd-estimators.h"

void generate_window(PsdWindowType_t window_type, double* window_buffer, int window_length) {
    switch (window_type) {
        case HANN_TYPE:
            for (int n = 0; n < window_length; n++) {
                window_buffer[n] = 0.5 * (1 - cos((2.0 * M_PI * n) / (window_length - 1)));
            }
            break;
        case RECTANGULAR_TYPE:
            for (int n = 0; n < window_length; n++) {
                window_buffer[n] = 1.0;
            }
            break;
        case BLACKMAN_TYPE:
            for (int n = 0; n < window_length; n++) {
                window_buffer[n] = 0.42 - 0.5 * cos((2.0 * M_PI * n) / (window_length - 1)) + 0.08 * cos((4.0 * M_PI * n) / (window_length - 1));
            }
            break;
        // NOTE: Additional window types like KAISER or TUKEY may require more parameters.
        case HAMMING_TYPE:
        default: // Default to Hamming if type is unknown
            for (int n = 0; n < window_length; n++) {
                window_buffer[n] = 0.54 - 0.46 * cos((2.0 * M_PI * n) / (window_length - 1));
            }
            break;
    }
}

void execute_welch_psd(complex double* signal, size_t n_signal, const PsdConfig_t* config, double* f_out, double* p_out) {
    // Extract parameters from the config struct
    int nperseg = (int)config->nperseg;
    int nfft = (int)config->nfft;
    int noverlap = (int)config->noverlap;
    double fs = config->sample_rate;
    PsdWindowType_t window_type = config->window_type;

    int step = nperseg - noverlap;
    if (step <= 0) {
        fprintf(stderr, "Error: Overlap results in a non-positive step size.\n");
        return;
    }

    int k_segments = (n_signal - noverlap) / step;
    if (k_segments <= 0) {
        fprintf(stderr, "Error: Signal is too short for the given segment and overlap settings.\n");
        return;
    }

    // Allocate and prepare the window
    double window[nperseg];
    generate_window(window_type, window, nperseg);

    // Compute window normalization factor (U)
    double u_norm = 0.0;
    for (int i = 0; i < nperseg; i++) {
        u_norm += window[i] * window[i];
    }
    u_norm /= nperseg;

    // Allocate FFTW resources
    complex double* segment = fftw_alloc_complex(nfft);
    complex double* x_k_fft = fftw_alloc_complex(nfft);
    fftw_plan plan = fftw_plan_dft_1d(nfft, segment, x_k_fft, FFTW_FORWARD, FFTW_ESTIMATE);

    // Initialize PSD accumulator to zeros
    memset(p_out, 0, nfft * sizeof(double));

    // --- Main loop over each segment ---
    for (int k = 0; k < k_segments; k++) {
        int start_index = k * step;

        // Apply window to the current segment and copy to FFT buffer
        for (int i = 0; i < nperseg; i++) {
            segment[i] = signal[start_index + i] * window[i];
        }
        // Zero-pad if nfft > nperseg
        for (int i = nperseg; i < nfft; i++) {
            segment[i] = 0.0;
        }

        // Perform FFT
        fftw_execute(plan);

        // Accumulate the squared magnitude of the FFT results
        for (int i = 0; i < nfft; i++) {
            double mag = cabs(x_k_fft[i]);
            p_out[i] += (mag * mag);
        }
    }

    // Average the PSD and scale by normalization factors
    double scale = 1.0 / (fs * u_norm * k_segments * nperseg);
    for (int i = 0; i < nfft; i++) {
        p_out[i] *= scale;
    }

    // Generate frequency bins (from –fs/2 to +fs/2)
    double df = fs / nfft;
    for (int i = 0; i < nfft; i++) {
        // FFT shift: move the second half of the frequencies to the beginning
        int shifted_index = (i + nfft / 2) % nfft;
        f_out[i] = -fs / 2.0 + i * df;
        
        // The corresponding PSD value needs to be fetched from the shifted position
        // To avoid creating a temporary buffer, we can do the swap in-place, but
        // for clarity, we just re-assign. Note that p_out must be indexed correctly.
        // The power p_out[0] corresponds to 0 Hz. p_out[1] to df, ..., p_out[nfft/2] to fs/2.
        // The negative frequencies are in the upper half of the original FFT output.
    }
    
    // Simple FFT shift for the power output array
    double temp_psd[nfft];
    memcpy(temp_psd, p_out, nfft * sizeof(double));
    for (int i = 0; i < nfft; i++) {
        int shifted_index = (i + nfft/2) % nfft;
        p_out[i] = temp_psd[shifted_index];
    }


    printf("[welch] PSD computation complete.\n");

    // Clean up FFTW resources
    fftw_destroy_plan(plan);
    fftw_free(segment);
    fftw_free(x_k_fft);
}