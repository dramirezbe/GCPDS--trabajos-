/**
 * @file main.c
 * @author David Ramírez
 * @brief This program estimates from scratch the Power Spectral Density (welch, periodogram & wavelet estimatior types).
 *        Then is used as CLI to choose which method use.
 */
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <math.h> // Necesario para la corrección de NFFT
#include "Modules/utils.h"
#include "Modules/psd-estimators.h"

#define FS 20000000
#define NPERSEG 4096
#define NFFT_REQUEST 4096
#define OVERLAP 0.5
PsdWindowType_t global_window = HAMMING_TYPE; // Renombrado para claridad

int main(int argc, char *argv[])
{
    PsdMethodType_t method;

    if (argc < 2) {
        fprintf(stderr, "Usage: %s <method>\n", argv[0]);
        return 1;
    }
    else {
        if(strcmp(argv[1], "welch") == 0) {
            method = WELCH_TYPE;
        }
        else if(strcmp(argv[1], "periodogram") == 0) {
            method = PERIODOGRAM_TYPE;
        }
        else if(strcmp(argv[1], "wavelet") == 0) {
            method = WAVELET_TYPE;
        }
        else {
            fprintf(stderr, "Unknown method: %s. Use 'welch', 'periodogram' or 'wavelet'.\n", argv[1]);
            return 1;
        }
    }

    char comp_path[1024];
    getcwd(comp_path, sizeof(comp_path));

    char exchange_folder_path[1024];
    char test_file_path[1024];
    char psd_output_path[1024];

    snprintf(exchange_folder_path, sizeof(exchange_folder_path), "%s/%s", comp_path, "exchange");
    snprintf(test_file_path, sizeof(test_file_path), "%s/%s", exchange_folder_path, "test_file.cs8");
    snprintf(psd_output_path, sizeof(psd_output_path), "%s/%s", exchange_folder_path, "psd_output_C.csv");

    size_t N_signal_IQ = 0;
    complex double *signal_iq = load_cs8(test_file_path, &N_signal_IQ);
    if (!signal_iq) {
        fprintf(stderr, "Failed to load IQ data.\n");
        return 1;
    }
    printf("Successfully loaded %zu samples from %s\n", N_signal_IQ, test_file_path);

    PsdConfig_t psd_config;
    int actual_nfft = NFFT_REQUEST; // Por defecto

    switch(method) {
        case WELCH_TYPE:
            psd_config = (PsdConfig_t){
                .sample_rate = FS,
                .nperseg = NPERSEG,
                .nfft = NFFT_REQUEST,
                .noverlap = (int)(NPERSEG * OVERLAP),
                .window_type = global_window
            };
            actual_nfft = NFFT_REQUEST;
            break;

        case PERIODOGRAM_TYPE:
            psd_config = (PsdConfig_t){
                .sample_rate = FS,
                .nfft = NFFT_REQUEST,
                .window_type = RECTANGULAR_TYPE 
            };
           
            if ((NFFT_REQUEST > 0) && ((NFFT_REQUEST & (NFFT_REQUEST - 1)) != 0)) {
                actual_nfft = 1 << (int)ceil(log2(NFFT_REQUEST));
            } else {
                actual_nfft = NFFT_REQUEST;
            }
            break;

        case WAVELET_TYPE:
            printf("Wavelet method not implemented.\n");
            free(signal_iq);
            return 0; // Salir limpiamente

        default:
            fprintf(stderr, "Error in method type struct, PANICKING...\n");
            free(signal_iq);
            return 1;
    }

    printf("Allocating output arrays for FFT length of %d\n", actual_nfft);
    double *f = malloc(actual_nfft * sizeof(double));
    double *psd = malloc(actual_nfft * sizeof(double));
    if (!f || !psd) {
        fprintf(stderr, "Memory allocation failed for PSD arrays.\n");
        free(signal_iq);
        free(f);
        free(psd);
        return 1;
    }

    
    switch (method) {
        case WELCH_TYPE:
            execute_welch_psd(signal_iq, N_signal_IQ, &psd_config, f, psd);
            break;
        case PERIODOGRAM_TYPE:
            
            psd_config.nfft = actual_nfft; 
            execute_periodogram_psd(signal_iq, N_signal_IQ, &psd_config, f, psd);
            break;
        default:
            break;
    }

    // Guardar los resultados en el CSV
    FILE *csv = fopen(psd_output_path, "w");
    if (!csv) {
        perror("Failed to open output CSV file");
        free(signal_iq);
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

    // Limpieza
    free(signal_iq);
    free(f);
    free(psd);

    return 0;
}
