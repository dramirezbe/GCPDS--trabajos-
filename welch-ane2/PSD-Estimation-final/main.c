/**
 * @file main.c
 * @author David Ramírez
 * @brief This program estimates from scratch the Power Spectral Density (welch, periodogram & wavelet estimatior types).
 *        Then is used as CLI to choose which method use.
 */

#include <stdio.h>
#include <unistd.h>
#include "Modules/utils.h"
#include "Modules/psd-estimators.h"

#define FS 20000000
#define NPERSEG 4096
#define NFFT NPERSEG
#define OVERLAP 0.5
const PsdWindowType_t window = HAMMING_TYPE;

#define CENT_FREQ TO_MHZ(98)
#define BW TO_MHZ(20)
#define INF_FREQ CENT_FREQ - BW
#define SUP_FREQ CENT_FREQ + BW

int main(int argc, char *argv[])
{
    (void)argc; // Unused
    (void)argv; // Unused

    char comp_path[1024];
    getcwd(comp_path, sizeof(comp_path));

    char exchange_folder_path[1024];
    char test_file_path[1024];
    char psd_output_path[1024];

    snprintf(exchange_folder_path, sizeof(exchange_folder_path), "%s/%s", comp_path, "exchange");
    snprintf(test_file_path, sizeof(test_file_path), "%s/%s", exchange_folder_path, "test_file.cs8");
    snprintf(psd_output_path, sizeof(psd_output_path), "%s/%s", exchange_folder_path, "psd_output_C.csv");

    // 2. Load the complex signal from the file
    size_t N_signal_IQ = 0;
    complex double *signal_iq = load_cs8(test_file_path, &N_signal_IQ);
    if (!signal_iq) {
        fprintf(stderr, "Failed to load IQ data.\n");
        return 1;
    }
    printf("Successfully loaded %zu samples from %s\n", N_signal_IQ, test_file_path);

    // 3. Prepare Welch config
    PsdConfig_t welch_config = {
        .sample_rate = FS,
        .nperseg = NPERSEG,
        .nfft = NFFT,
        .noverlap = (int)(NPERSEG * OVERLAP),
        .window_type = window
    };

    // 4. Allocate output arrays
    double *f = malloc(NFFT * sizeof(double));
    double *psd = malloc(NFFT * sizeof(double));
    if (!f || !psd) {
        fprintf(stderr, "Memory allocation failed for PSD arrays.\n");
        free(signal_iq);
        free(f);
        free(psd);
        return 1;
    }

    // 5. Compute PSD using Welch estimator
    execute_welch_psd(signal_iq, N_signal_IQ, &welch_config, f, psd);

    // 6. Save PSD to CSV in "exchange" directory
    FILE *csv = fopen(psd_output_path, "w");
    if (!csv) {
        perror("Failed to open output CSV file");
        free(signal_iq);
        free(f);
        free(psd);
        return 1;
    }
    fprintf(csv, "Frequency_Hz,PSD\n");
    for (int i = 0; i < NFFT; i++) {
        fprintf(csv, "%.10g,%.10g\n", f[i], psd[i]);
    }
    fclose(csv);
    printf("PSD saved to %s\n", psd_output_path);

    // 7. Cleanup
    free(signal_iq);
    free(f);
    free(psd);

    return 0;
}
