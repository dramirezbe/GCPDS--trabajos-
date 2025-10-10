/**
 * @file ar-model.c
 * @author David Ramírez Betancourth
 * @brief Autoregressive model functions and macros
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>     // For memset
#include <unistd.h>     // For getcwd
#include "datatypes.h"  // Your header file with all the structs
#include "utils.h"      // Your header file for utility functions

/**
 * @brief Normalizes an I/Q signal to the range [-1, 1] in-place.
 *
 * It finds the maximum absolute value among all real and imaginary components
 * and scales the signal by that value.
 *
 * @param signal A pointer to the signal_iq_t struct to be normalized.
 */
static void normalize_iq_signal(signal_iq_t *signal) {
    if (signal == NULL || signal->signal_iq == NULL || signal->n_signal == 0) {
        return;
    }

    double max_abs = 0.0;
    for (size_t i = 0; i < signal->n_signal; ++i) {
        double real_part = creal(signal->signal_iq[i]);
        double imag_part = cimag(signal->signal_iq[i]);
        if (fabs(real_part) > max_abs) max_abs = fabs(real_part);
        if (fabs(imag_part) > max_abs) max_abs = fabs(imag_part);
    }

    if (max_abs > 0.0) {
        for (size_t i = 0; i < signal->n_signal; ++i) {
            signal->signal_iq[i] /= max_abs;
        }
    }
}

/**
 * @brief Safely frees the memory used by the temporary signal buffer.
 *
 * This function iterates through an array of signal_iq_t pointers, freeing
 * the inner complex array and the struct itself for each valid entry. Finally,
 * it frees the main buffer pointer.
 *
 * @param buffer The array of signal_iq_t pointers.
 * @param num_signals The number of elements allocated in the buffer.
 */
static void free_signal_buffer(signal_iq_t** buffer, int num_signals) {
    if (!buffer) return;
    for (int i = 0; i < num_signals; i++) {
        if (buffer[i]) {
            free(buffer[i]->signal_iq); // Free the complex double array
            free(buffer[i]);            // Free the struct itself
        }
    }
    free(buffer); // Free the array of pointers
}

float* create_and_process_signal_matrix(
    int num_signals,
    BackendParams_t *capture_params,
    Paths_t *paths,
    size_t* out_signal_len
) {
    if (num_signals <= 0 || out_signal_len == NULL || capture_params == NULL || paths == NULL) {
        fprintf(stderr, "Error: Invalid arguments provided to create_and_process_signal_matrix.\n");
        return NULL;
    }

    // Step 1: Allocate a temporary buffer to hold pointers to each signal struct.
    signal_iq_t** signal_buffer = malloc(num_signals * sizeof(signal_iq_t*));
    if (!signal_buffer) {
        perror("Error: Failed to allocate temporary signal buffer");
        return NULL;
    }

    char test_file_path[2048];
    int len_path = snprintf(test_file_path, sizeof(test_file_path), "%s/0.cs8", paths->samples_path);
    if (len_path < 0 || (size_t)len_path >= sizeof(test_file_path)) {
        fprintf(stderr, "Error: Test file path would be truncated.\n");
        free(signal_buffer); // Clean up allocated memory
        return NULL;
    }

    // Step 2: Main loop to capture, load, normalize, and store signals temporarily.
    for (int i = 0; i < num_signals; i++) {
        // Capture the signal using the provided function.
        if (instantaneous_capture(capture_params, paths) != 0) {
            fprintf(stderr, "Error: Instantaneous capture failed for signal %d\n", i + 1);
            free_signal_buffer(signal_buffer, i); // Clean up what's been allocated.
            return NULL;
        }

        // Load the signal from the file.
        signal_buffer[i] = load_cs8(test_file_path);
        if (!signal_buffer[i]) {
            fprintf(stderr, "Error: Failed to load IQ data for signal %d.\n", i + 1);
            free_signal_buffer(signal_buffer, i);
            return NULL;
        }
        
        printf("------------[%d/%d] IQ signal acquired--------------\n", i + 1, num_signals);

        // Normalize the loaded signal in-place.
        normalize_iq_signal(signal_buffer[i]);

        
        // Delete the temporary file.
        if (remove(test_file_path) != 0) {
            perror("Warning: Could not delete temporary file");
        }
        
    }

    // Step 3: Find the maximum signal length to determine the final matrix dimension.
    size_t max_len = 0;
    for (int i = 0; i < num_signals; i++) {
        if (signal_buffer[i]->n_signal > max_len) {
            max_len = signal_buffer[i]->n_signal;
        }
    }
    *out_signal_len = max_len;
    

    // Step 4: Allocate the final contiguous float matrix.
    size_t matrix_size_bytes = (size_t)num_signals * 2 * max_len * sizeof(float);
    float* final_matrix = malloc(matrix_size_bytes);
    if (!final_matrix) {
        perror("Error: Failed to allocate final float matrix");
        free_signal_buffer(signal_buffer, num_signals);
        return NULL;
    }
    // Initialize with zeros. This handles zero-padding automatically.
    memset(final_matrix, 0, matrix_size_bytes);

    // Step 5: Populate the final matrix from the temporary buffer.
    for (int i = 0; i < num_signals; i++) {
        signal_iq_t* current_signal = signal_buffer[i];
        size_t current_len = current_signal->n_signal;
        
        // The block for signal 'i' starts at i * (2 * max_len)
        // I data is in the first half of the block, Q data is in the second.
        size_t base_idx_I = (size_t)i * 2 * max_len;
        size_t base_idx_Q = base_idx_I + max_len;

        for (size_t j = 0; j < current_len; j++) {
            final_matrix[base_idx_I + j] = (float)creal(current_signal->signal_iq[j]);
            final_matrix[base_idx_Q + j] = (float)cimag(current_signal->signal_iq[j]);
        }
    }

    printf("Matrix created. Maximum signal length is %zu.\n", max_len);

    // Step 6: Clean up the intermediate buffer.
    free_signal_buffer(signal_buffer, num_signals);

    return final_matrix;
}

/**
 * @brief Solves the Yule-Walker equations using the Levinson-Durbin algorithm.
 *
 * This is an efficient way to find the AR coefficients from the autocorrelation sequence.
 *
 * @param r An array containing the autocorrelation sequence R(0), R(1), ..., R(p).
 * @param order The order of the AR model (p).
 * @param a_out A pre-allocated array where the AR coefficients a_1, ..., a_p will be stored.
 */
static void levinson_durbin(const double* r, int order, double* a_out) {
    double* a = (double*)calloc(order + 1, sizeof(double));
    double* e = (double*)malloc((order + 1) * sizeof(double));
    double* k = (double*)malloc((order + 1) * sizeof(double));

    if (!a || !e || !k) {
        perror("Failed to allocate memory for Levinson-Durbin");
        free(a); free(e); free(k);
        return;
    }

    e[0] = r[0];

    for (int i = 1; i <= order; i++) {
        double sum = 0.0;
        for (int j = 1; j < i; j++) {
            sum += a[j] * r[i - j];
        }
        k[i] = (r[i] - sum) / e[i - 1];

        a[i] = k[i];
        for (int j = 1; j < i; j++) {
            a[j] = a[j] - k[i] * a[i - j];
        }
        e[i] = (1 - k[i] * k[i]) * e[i - 1];
    }

    // Copy results to output array (a_out is 1-indexed in AR model theory)
    for (int i = 0; i < order; i++) {
        a_out[i] = a[i + 1];
    }

    free(a);
    free(e);
    free(k);
}

/**
 * @brief Calculates the AR model coefficients for a complex signal.
 *
 * @param signal The input complex signal.
 * @param len The length of the signal.
 * @param order The desired order of the AR model.
 * @param coeffs_out A pre-allocated array to store the resulting coefficients.
 */
static void calculate_ar_coefficients(complex double* signal, size_t len, int order, double* coeffs_out) {
    if (order >= len) return;

    double* r = (double*)calloc(order + 1, sizeof(double));
    if (!r) {
        perror("Failed to allocate for autocorrelation");
        return;
    }

    // Calculate autocorrelation sequence (real part only for simplicity)
    for (int lag = 0; lag <= order; lag++) {
        double sum_r = 0.0;
        for (size_t n = lag; n < len; n++) {
            // R(k) = E[x(n) * conj(x(n-k))]
            sum_r += creal(signal[n] * conj(signal[n - lag]));
        }
        r[lag] = sum_r / (len - lag);
    }

    // Solve for AR coefficients using Levinson-Durbin
    levinson_durbin(r, order, coeffs_out);

    free(r);
}

complex double* reconstruct_signal_from_ar_model(
    const float* signal_matrix,
    int num_signals,
    size_t max_len,
    int order
) {
    if (!signal_matrix || num_signals <= 0 || max_len <= order) {
        fprintf(stderr, "Error: Invalid arguments for AR model reconstruction.\n");
        return NULL;
    }

    // 1. Allocate memory for averaged coefficients and temporary buffers
    double* avg_coeffs = (double*)calloc(order, sizeof(double));
    double* temp_coeffs = (double*)malloc(order * sizeof(double));
    complex double* temp_signal = (complex double*)malloc(max_len * sizeof(complex double));

    if (!avg_coeffs || !temp_coeffs || !temp_signal) {
        perror("Error: Failed to allocate memory for AR processing");
        free(avg_coeffs); free(temp_coeffs); free(temp_signal);
        return NULL;
    }

    printf("Calculating and averaging AR coefficients for %d signals...\n", num_signals);

    // 2. Loop through each signal to calculate and accumulate its AR coefficients
    for (int i = 0; i < num_signals; i++) {
        // Reconstruct the complex signal from the float matrix
        size_t base_idx_I = (size_t)i * 2 * max_len;
        size_t base_idx_Q = base_idx_I + max_len;
        for (size_t j = 0; j < max_len; j++) {
            temp_signal[j] = signal_matrix[base_idx_I + j] + I * signal_matrix[base_idx_Q + j];
        }

        // Calculate the AR coefficients for this specific signal
        calculate_ar_coefficients(temp_signal, max_len, order, temp_coeffs);

        // Add them to the running average
        for (int k = 0; k < order; k++) {
            avg_coeffs[k] += temp_coeffs[k];
        }
    }

    // Finalize the average by dividing by the number of signals
    for (int k = 0; k < order; k++) {
        avg_coeffs[k] /= num_signals;
    }
    printf("Averaged AR coefficients computed.\n");

    // 3. Allocate and synthesize the new signal
    complex double* reconstructed_signal = (complex double*)malloc(max_len * sizeof(complex double));
    if (!reconstructed_signal) {
        perror("Error: Failed to allocate memory for the reconstructed signal");
        free(avg_coeffs); free(temp_coeffs); free(temp_signal);
        return NULL;
    }
    
    printf("Synthesizing new signal from averaged model...\n");

    // Seed the first 'order' values of the signal with small random noise to start the process
    for (int i = 0; i < order; i++) {
        reconstructed_signal[i] = ((rand() / (double)RAND_MAX) - 0.5) * 0.01 + 
                                  I * (((rand() / (double)RAND_MAX) - 0.5) * 0.01);
    }
    
    // Generate the rest of the signal using the averaged AR coefficients
    for (size_t i = order; i < max_len; i++) {
        complex double next_sample = 0.0;
        for (int k = 0; k < order; k++) {
            // AR model formula: x[n] = sum(a_k * x[n-k])
            next_sample += avg_coeffs[k] * reconstructed_signal[i - (k + 1)];
        }
        reconstructed_signal[i] = next_sample;
    }

    printf("Reconstruction complete.\n");

    // 4. Cleanup and return
    free(avg_coeffs);
    free(temp_coeffs);
    free(temp_signal);

    return reconstructed_signal;
}