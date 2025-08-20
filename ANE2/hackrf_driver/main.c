/**
 * @file main.c
 * @author David Ramírez
 * @brief This program estimates from scratch the Power Spectral Density (welch, periodogram & wavelet estimatior types).
 *        It uses the HackRF device to capture IQ samples.
 */
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <math.h>
#include "Modules/utils.h"
#include "Modules/psd-estimators.h"

#define NPERSEG 4096
#define NFFT_REQUEST 4096
#define OVERLAP 0.5
#define BW TO_MHZ(20) // 20 MHz

#define FREQ TO_MHZ(98) // 98 MHz

int err_capture;

int main()
{
    // Define the method and configuration
    Paths_t paths = get_paths();

    char test_file_path[2048];
    char psd_output_path[2048];

    snprintf(test_file_path, sizeof(test_file_path), "%s/0.cs8", paths.samples_path);
    snprintf(psd_output_path, sizeof(psd_output_path), "%s/output.csv", paths.samples_path);

    BackendParams_t params = {
        .bw = BW,
        .frequency = FREQ,
        .mode = INSTANTANEOUS_TYPE
    };

    err_capture = instantaneous_capture(&params, &paths);
    if (err_capture) {
        fprintf(stderr, "Instantaneous capture failed\n");
        return 1;
    }

    signal_iq_t* signal_data = load_cs8(test_file_path);
    if (!signal_data) {
        fprintf(stderr, "Failed to load IQ data.\n");
        return 1;
    }
    printf("Successfully loaded %zu samples from %s\n", signal_data->n_signal, test_file_path);

    PsdWindowType_t global_window = HAMMING_TYPE;
    PsdMethodType_t method = PERIODOGRAM_TYPE; // Change as needed

    PsdConfig_t psd_config = {
        .method_type = method,
        .sample_rate = params.bw,
        .nfft = NFFT_REQUEST,
        .nperseg = NPERSEG,
        .noverlap = (int)(NPERSEG * OVERLAP),
        .window_type = method == WELCH_TYPE ? global_window : RECTANGULAR_TYPE
    };

    //Resize nfft to power of 2
    if (method == PERIODOGRAM_TYPE) {
        if ((NFFT_REQUEST > 0) && ((NFFT_REQUEST & (NFFT_REQUEST - 1)) != 0)) {
            psd_config.nfft = 1 << (int)ceil(log2(NFFT_REQUEST));
        }
    }

    
    
    // Assign memory for psd output arrays
    double *f = malloc(psd_config.nfft * sizeof(double));
    double *psd = malloc(psd_config.nfft * sizeof(double));
    if (!f || !psd) {
        fprintf(stderr, "Memory allocation failed for PSD arrays.\n");
        free(f);
        free(psd);
        free(signal_data->signal_iq);
        free(signal_data);
        return 1;
    }

    // Call the unified function to compute the PSD
    execute_psd(signal_data, &psd_config, f, psd);

    // Free memory
    free(signal_data->signal_iq);
    free(signal_data);

    // Guardar los resultados en el CSV
    FILE *csv = fopen(psd_output_path, "w");
    if (!csv) {
        perror("Failed to open output CSV file");
        free(f);
        free(psd);
        return 1;
    }
    fprintf(csv, "Frequency_Hz,PSD\n");

    for (int i = 0; i < psd_config.nfft; i++) {
        fprintf(csv, "%.10g,%.10g\n", f[i], psd[i]);
    }
    fclose(csv);
    printf("PSD saved to %s\n", psd_output_path);

    
    free(f);
    free(psd);

    return 0;
}