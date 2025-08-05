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


int main(int argc, char *argv[]) {
    (void)argc; // Unused
    (void)argv; // Unused

    char comp_path[1024];
    getcwd(comp_path, sizeof(comp_path));

    const char* output_csv_filename = "psd_output_C.csv";
    const char* test_filename = "test_file.cs8";
    const char test_file_path[1024];

    snprintf(test_file_path, sizeof(test_file_path), "%s/%s", comp_path, test_filename);
    
    // 2. Load the complex signal from the file
    size_t N_signal_IQ = 0;
    complex double* signal_iq = load_cs8(test_file_path, &N_signal_IQ);
    printf("Successfully loaded %zu samples from %s\n", N_signal_IQ,  test_file_path);

    //PsdConfig_t welch_config = {}
    


    
    return 0;
}

