/**
 * @file main.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <math.h>               // Added for log10
#include <libhackrf/hackrf.h>

#include "Modules/psd.h"
#include "Drivers/ring_buffer.h" 
#include "Drivers/sdr_HAL.h"

#define FREQ_HZ TO_MHZ(98) 
#define SAMPLE_RATE TO_MHZ(20)
#define LNA_GAIN 0
#define VGA_GAIN 0
#define PPM_ERROR 0
#define AMP_ENABLE false
#define TOTAL_BYTES (size_t)(SAMPLE_RATE * 2) 
#define RB_SIZE (TOTAL_BYTES * 2)

#define WINDOW HAMMING_TYPE
#define NPERSEG 4096
#define NOVERLAP 2048

hackrf_device* device = NULL;
ring_buffer_t rb;
volatile bool stop_streaming = false;

// Callback: Push to Ring Buffer
int rx_callback(hackrf_transfer* transfer) {
    if (stop_streaming) return -1;
    rb_write(&rb, transfer->buffer, transfer->valid_length);
    return 0;
}

int main() {
    rb_init(&rb, RB_SIZE);

    if (hackrf_init() != HACKRF_SUCCESS) return -1;
    if (hackrf_open(&device) != HACKRF_SUCCESS) return -1;

    SDR_cfg_t hack_cfg = {
        .sample_rate = SAMPLE_RATE,
        .center_freq = FREQ_HZ,
        .amp_enabled = AMP_ENABLE,
        .lna_gain = LNA_GAIN,
        .vga_gain = VGA_GAIN,
        .ppm_error = PPM_ERROR
    };
    hackrf_apply_cfg(device, &hack_cfg);

    // Start Rx
    if (hackrf_start_rx(device, rx_callback, NULL) != HACKRF_SUCCESS) goto cleanup;

    printf("Receiving data...\n");

    while (rb_available(&rb) < TOTAL_BYTES) {
        usleep(10000); 
    }
    
    stop_streaming = true;
    hackrf_stop_rx(device);
    
    printf("Capture complete. Processing PSD...\n");

    int8_t* linear_buffer = malloc(TOTAL_BYTES);
    if (!linear_buffer) goto cleanup;
    
    rb_read(&rb, linear_buffer, TOTAL_BYTES);

    signal_iq_t* sig = load_iq_from_buffer(linear_buffer, TOTAL_BYTES);

    PsdConfig_t psd_cfg = {
        .window_type = WINDOW,
        .sample_rate = (double)SAMPLE_RATE,
        .nperseg = NPERSEG,
        .noverlap = NOVERLAP
    };

    double* freq = malloc(psd_cfg.nperseg * sizeof(double));
    double* psd = malloc(psd_cfg.nperseg * sizeof(double));

    if (freq && psd) {
        execute_welch_psd(sig, &psd_cfg, freq, psd);
        
        // --- Export to CSV with dBm conversion ---
        FILE *fp = fopen("psd_results.csv", "w");
        if (fp) {
            fprintf(fp, "Frequency_Hz,Power_dBm\n");
            
            for (int i = 0; i < psd_cfg.nperseg; i++) {
                // Formula: 10 * log10( (V^2 / R) * 1000 )
                // psd[i] is V^2 (linear power density)
                double power_watts = psd[i] / 50.0;
                double dbm = 10.0 * log10(power_watts * 1000.0);
                
                fprintf(fp, "%.2f,%.4f\n", freq[i], dbm);
            }
            fclose(fp);
            printf("Saved dBm results to psd_results.csv\n");
            printf("First bin: %.2f Hz, %.2f dBm\n", freq[0], 10.0 * log10((psd[0]/50.0)*1000.0));
        } else {
            perror("Failed to open CSV file");
        }
    }

    if (linear_buffer) free(linear_buffer);
    if (freq) free(freq);
    if (psd) free(psd);
    free_signal_iq(sig);

cleanup:
    hackrf_stop_rx(device);
    hackrf_close(device);
    hackrf_exit();
    rb_free(&rb);
    return 0;
}