/**
 * @file main.c
 * @author David Ramírez
 * @brief This program estimates from scratch the Power Spectral Density (welch, periodogram & wavelet estimatior types).
 *        Then is used as CLI to choose which method use.
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
#define BW TO_MHZ(20000000) // 20 MHz

int main()
{
    // Define the method and configuration
    PsdWindowType_t global_window = HAMMING_TYPE;
    PsdConfig_t psd_config;
    PsdMethodType_t method = PERIODOGRAM_TYPE; // Change as needed


    char test_file_path[1024] = "/home/javastral/GIT/GCPDS--trabajos-/ANE2/hackrf_driver/Samples/output.cs8";
    char psd_output_path[1024] = "/home/javastral/GIT/GCPDS--trabajos-/ANE2/hackrf_driver/Samples/output.csv";

    signal_iq_t* signal_data = load_cs8(test_file_path);
    if (!signal_data) {
        fprintf(stderr, "Failed to load IQ data.\n");
        return 1;
    }
    printf("Successfully loaded %zu samples from %s\n", signal_data->n_signal, test_file_path);

    // --- PPSD CONFIG init ---
    psd_config.method_type = method;
    psd_config.sample_rate = BW;
    psd_config.nfft = NFFT_REQUEST;
    
    // Specific config
    switch(method) {
        case WELCH_TYPE:
            psd_config.nperseg = NPERSEG;
            psd_config.noverlap = (int)(NPERSEG * OVERLAP);
            psd_config.window_type = global_window;
            break;
        case PERIODOGRAM_TYPE:
            psd_config.window_type = RECTANGULAR_TYPE; 
            break;
        case WAVELET_TYPE:
            // Not implemented
            break;
        default:
            fprintf(stderr, "Error in PSD method selection, unsupported method.\n");
            return 1;
    }

    // Assign memory to nfft
    int actual_nfft = (method == WELCH_TYPE) ? psd_config.nfft : psd_config.nfft;
    
    // Assign memory for psd output arrays
    double *f = malloc(actual_nfft * sizeof(double));
    double *psd = malloc(actual_nfft * sizeof(double));
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
   
    for (int i = 0; i < actual_nfft; i++) {
        fprintf(csv, "%.10g,%.10g\n", f[i], psd[i]);
    }
    fclose(csv);
    printf("PSD saved to %s\n", psd_output_path);

    
    free(f);
    free(psd);

    return 0;
}