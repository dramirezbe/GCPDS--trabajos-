/**
 * @file main.c
 * @author David Ramírez
 * @brief This program estimates from scratch the Power Spectral Density (welch, periodogram & wavelet estimatior types).
 *        It uses the HackRF device to capture IQ samples.
 */
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include "Modules/utils.h"
#include "Modules/datatypes.h"
#include "Modules/ar-model.h"

#define BW TO_MHZ(2) // 2 MHz

#define NUM_SIGNALS 10
#define AR_MODEL_ORDER 8

#define FREQ TO_MHZ(98) // 98 MHz

size_t out_signal_len = 0;
int main()
{
    // Define the method and configuration
    Paths_t paths = get_paths();

    BackendParams_t params = {
        .bw = BW,
        .frequency = FREQ,
        .mode = INSTANTANEOUS_TYPE
    };

    float* signal_matrix = create_and_process_signal_matrix(
        NUM_SIGNALS,
        &params,
        &paths,
        &out_signal_len
    );

    if (!signal_matrix) {
        fprintf(stderr, "Error: Failed to create signal matrix.\n");
        return 1;
    }
    printf("Matrix shape is (%d, %zu)\n", NUM_SIGNALS, out_signal_len);

    // Continue with the rest of your processing...

    free(signal_matrix);
    return 0;
}