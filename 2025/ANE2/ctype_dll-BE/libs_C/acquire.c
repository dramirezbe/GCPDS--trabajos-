#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/**
 * @file acquire.c
 * @brief Generates a dummy signal array with random negative numbers.
 *
 * @param start_freq_hz The starting frequency in Hz.
 * @param end_freq_hz The ending frequency in Hz.
 * @param resolution_hz The number of elements in the signal array.
 * @param antenna_port The antenna port number.
 * @return A pointer to the dynamically allocated signal array of doubles.
 *         The caller is responsible for freeing this memory.
 */

//Compile with: gcc -shared -o acquire.so -fPIC acquire.c

double *acquire_signal(double start_freq_hz, double end_freq_hz, int resolution_hz, int antenna_port) {
    // Allocate memory for the signal array
    double *signal_array = (double *)malloc(resolution_hz * sizeof(double));
    if (signal_array == NULL) {
        fprintf(stderr, "Error: Memory allocation failed.\n");
        return NULL;
    }

    // Seed the random number generator
    srand((unsigned int)time(NULL));

    // Print the received parameters for demonstration
    printf("C function acquire_signal called with:\n");
    printf("  start_freq_hz: %f\n", start_freq_hz);
    printf("  end_freq_hz: %f\n", end_freq_hz);
    printf("  resolution_hz: %d\n", resolution_hz);
    printf("  antenna_port: %d\n", antenna_port);

    // Generate random negative numbers for the signal array
    for (int i = 0; i < resolution_hz; i++) {
        signal_array[i] = -((double)rand() / RAND_MAX) * 100.0; // Random double between -100.0 and 0.0
    }

    return signal_array;
}

/**
 * @brief Frees the memory allocated for the signal array.
 *
 * @param signal_array A pointer to the signal array to be freed.
 */
void free_signal_array(double *signal_array) {
    free(signal_array);
}