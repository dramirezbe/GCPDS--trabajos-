/**
 * @file ar-model.h
 * @author David Ramírez Betancourth
 * @brief Autoregressive model functions and macros
 */

#ifndef AR_MODEL_H
#define AR_MODEL_H

#include "datatypes.h"

/**
 * @brief Creates and processes a matrix of signals with unknown initial lengths.
 *
 * This function performs the entire pipeline:
 * 1. Captures and loads a specified number of signals into a temporary buffer.
 * 2. Normalizes each signal and deletes the temporary .cs8 file.
 * 3. Finds the maximum length among all loaded signals.
 * 4. Dynamically allocates a single, flat float matrix of the correct size.
 * 5. Populates the matrix with the signal data, applying zero-padding.
 * 6. Cleans up all temporary buffers.
 *
 * @param num_signals The total number of signals to capture and process.
 * @param capture_params A pointer to the backend capture parameters.
 * @param paths A pointer to the paths configuration.
 * @param out_signal_len A pointer to a size_t variable where the final, standardized
 *                       signal length will be stored.
 * @return A pointer to the newly allocated float matrix with shape
 *         (num_signals, 2, max_len). The caller is responsible for freeing this
 *         memory. Returns NULL on failure.
 */
float* create_and_process_signal_matrix(
    int num_signals,
    BackendParams_t *capture_params,
    Paths_t *paths,
    size_t* out_signal_len
);

/**
 * @brief Reconstructs a representative signal from a matrix of signals using an averaged AR model.
 *
 * This function computes the AR coefficients for each signal in the matrix, averages
 * these coefficients, and then synthesizes a new signal of the same length based
 * on the averaged model.
 *
 * @param signal_matrix The input float matrix (I and Q components separated).
 * @param num_signals The number of signals in the matrix (e.g., 10).
 * @param max_len The length of each signal component (e.g., 2000000).
 * @param order The order of the AR model to use (a small number, e.g., 4 to 16, is typical).
 * @return A newly allocated complex double array of length `max_len` representing the reconstructed signal.
 *         The caller is responsible for freeing this memory. Returns NULL on failure.
 */
complex double* reconstruct_signal_from_ar_model(
    const float* signal_matrix,
    int num_signals,
    size_t max_len,
    int order
);


#endif // AR_MODEL_H