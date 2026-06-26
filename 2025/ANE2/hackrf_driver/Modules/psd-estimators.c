/**
 * @file psd-estimators.c
 * @author David Ramírez Betancourth
 */

#include "psd-estimators.h"
#include <alloca.h>

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


static void fftshift(double* data, int n) {
    if (n <= 1) {
        return;
    }
    int half = n / 2;
    int remaining = n - half;

    
    double* temp_buffer = (double*)alloca(half * sizeof(double));
    if (!temp_buffer) {
        fprintf(stderr, "Error: Falló la asignación de memoria en la pila para fftshift.\n");
        return;
    }

    memcpy(temp_buffer, data, half * sizeof(double));

    memcpy(data, &data[half], remaining * sizeof(double));

    memcpy(&data[remaining], temp_buffer, half * sizeof(double));
}


// --- PSD Method Implementations ---

void execute_welch_psd_internal(signal_iq_t* signal_data, const PsdConfig_t* config, double* f_out, double* p_out) {
    // Extract params
    complex double* signal = signal_data->signal_iq;
    size_t n_signal = signal_data->n_signal;
    int nperseg = config->nperseg;
    int nfft = config->nfft;
    int noverlap = config->noverlap;
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

    fftshift(p_out, nfft);
    
    // Generate frequency bins (from –fs/2 to +fs/2)
    double df = fs / nfft;
    for (int i = 0; i < nfft; i++) {
        f_out[i] = -fs / 2.0 + i * df;
    }

    printf("[welch] PSD computation complete.\n");

    // Clean up FFTW resources
    fftw_destroy_plan(plan);
    fftw_free(segment);
    fftw_free(x_k_fft);
}

void execute_periodogram_psd_internal(signal_iq_t* signal_data, const PsdConfig_t* config, double* f_out, double* p_out) {
    // Extract params
    complex double* signal = signal_data->signal_iq;
    size_t n_signal = signal_data->n_signal;
    int nfft_arg = config->nfft;
    double fs = config->sample_rate;
    PsdWindowType_t window_type = config->window_type;

    // Determine segment length
    size_t segment_len = (nfft_arg > 0) ? (size_t)nfft_arg : n_signal;
    if (segment_len > n_signal) {
        segment_len = n_signal;
    }

    // Gen window
    double* window = (double*)malloc(segment_len * sizeof(double));
    if (window == NULL) {
        fprintf(stderr, "Error: Falló la asignación de memoria para la ventana.\n");
        return;
    }
    generate_window(window_type, window, (int)segment_len);

    // Compute FFT length
    int fft_len = 1;
    while (fft_len < segment_len) {
        fft_len <<= 1;
    }
    if (config->nfft > segment_len) {
      fft_len = config->nfft;
    }

    // Allocate FFTW resources
    complex double* fft_input_buffer = fftw_alloc_complex(fft_len);
    complex double* fft_output_buffer = fftw_alloc_complex(fft_len);
    if (!fft_input_buffer || !fft_output_buffer) {
        fprintf(stderr, "Error: Falló la asignación de memoria para los buffers de FFTW.\n");
        free(window);
        fftw_free(fft_input_buffer);
        fftw_free(fft_output_buffer);
        return;
    }

    // Apply window to segment and zero-pad
    for (size_t i = 0; i < segment_len; i++) {
        fft_input_buffer[i] = signal[i] * window[i];
    }
    if (fft_len > segment_len) {
        memset(&fft_input_buffer[segment_len], 0, (fft_len - segment_len) * sizeof(complex double));
    }

    // 4. Execute fftw
    fftw_plan plan = fftw_plan_dft_1d(fft_len, fft_input_buffer, fft_output_buffer, FFTW_FORWARD, FFTW_ESTIMATE);
    fftw_execute(plan);

    // 5. Calculate PSD normalization
    double S2 = 0.0;
    for (size_t i = 0; i < segment_len; i++) {
        S2 += window[i] * window[i];
    }
    if (S2 == 0) S2 = 1.0;

    double scale = 1.0 / (fs * S2);
    for (int i = 0; i < fft_len; i++) {
        p_out[i] = (creal(fft_output_buffer[i]) * creal(fft_output_buffer[i]) +
                    cimag(fft_output_buffer[i]) * cimag(fft_output_buffer[i])) * scale;
    }

    // Center the power spectrum using the utility function
    fftshift(p_out, fft_len);

    // Generate frequency bins
    double df = fs / fft_len;
    for (int i = 0; i < fft_len; i++) {
        f_out[i] = -fs / 2.0 + i * df;
    }

    // Clean up resources
    fftw_destroy_plan(plan);
    fftw_free(fft_input_buffer);
    fftw_free(fft_output_buffer);
    free(window);

    printf("[periodogram] PSD computation complete.\n");
}

// --- Unified Function ---

void execute_psd(signal_iq_t* signal_data, const PsdConfig_t* config, double* f_out, double* p_out) {
    if (signal_data == NULL || signal_data->signal_iq == NULL) {
        fprintf(stderr, "Error: Signal data is NULL.\n");
        return;
    }
    if (config == NULL) {
        fprintf(stderr, "Error: PsdConfig_t struct is NULL.\n");
        return;
    }
    switch (config->method_type) {
        case WELCH_TYPE:
            execute_welch_psd_internal(signal_data, config, f_out, p_out);
            break;
        case PERIODOGRAM_TYPE:
            execute_periodogram_psd_internal(signal_data, config, f_out, p_out);
            break;
        case WAVELET_TYPE:
            printf("Wavelet method not implemented.\n");
            break;
        default:
            fprintf(stderr, "Error: Unknown PSD method type.\n");
            break;
    }
}