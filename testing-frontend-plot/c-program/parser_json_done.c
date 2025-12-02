/**
 * @file main.c
 * @brief PSD calculation matching the user's specific dBm reference (-70dBm floor)
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <math.h>
#include <string.h> 
#include <libhackrf/hackrf.h>
#include <inttypes.h>

#include "Modules/psd.h"
#include "Drivers/ring_buffer.h" 
#include "Drivers/sdr_HAL.h"
#include "Drivers/zmqsub.h"

// ----------------------------------------------------------------------
// Configuration
// ----------------------------------------------------------------------

//#define FREQ_HZ TO_MHZ(98) 
//#define SAMPLE_RATE TO_MHZ(20)
//#define LNA_GAIN 0
//#define VGA_GAIN 0
//#define PPM_ERROR 0
//#define AMP_ENABLE false

//#define WINDOW BLACKMAN_TYPE
//#define RBW 50000

// Options: "dBm" (default), "dBuV", "dBmV", "W", "V"
//#define DESIRED_SCALE "dBm" 

hackrf_device* device = NULL;
ring_buffer_t rb;
volatile bool stop_streaming = false;



// ----------------------------------------------------------------------
// Standard Helpers
// ----------------------------------------------------------------------

int rx_callback(hackrf_transfer* transfer) {
    if (stop_streaming) return -1;
    rb_write(&rb, transfer->buffer, transfer->valid_length);
    return 0;
}

// This function still calculates NPERSEG based on RBW to ensure 
// you get the frequency resolution you want, but it doesn't affect amplitude scaling.
int find_params_psd(DesiredCfg_t desired, SDR_cfg_t *hack_cfg, PsdConfig_t *psd_cfg, RB_cfg_t *rb_cfg) {
    double enbw_factor = get_window_enbw_factor(desired.window_type);
    double required_nperseg_val = enbw_factor * (double)desired.sample_rate / (double)desired.rbw;
    int exponent = (int)ceil(log2(required_nperseg_val));
    
    psd_cfg->nperseg = (int)pow(2, exponent);
    psd_cfg->noverlap = psd_cfg->nperseg * desired.overlap;
    psd_cfg->window_type = desired.window_type;
    psd_cfg->sample_rate = desired.sample_rate;

    hack_cfg->sample_rate = desired.sample_rate;
    hack_cfg->center_freq = desired.center_freq;
    hack_cfg->amp_enabled = desired.amp_enabled;
    hack_cfg->lna_gain = desired.lna_gain;
    hack_cfg->vga_gain = desired.vga_gain;
    hack_cfg->ppm_error = desired.ppm_error;

    rb_cfg->total_bytes = (size_t)(desired.sample_rate * 2);
    rb_cfg->rb_size = (int)(rb_cfg->total_bytes * 2);
    return 0;
}

// ----------------------------------------------------------------------
// Main
// ----------------------------------------------------------------------

int main() {

    const char *json_data = 
    "{\n"
    "    \"center_freq_hz\": 98000000,\n"
    "    \"rbw_hz\": 10000,\n"
    "    \"sample_rate_hz\": 20000000.0,\n"
    "    \"span\": 20000000.0,\n"
    "    \"overlap\": 0.5,\n"
    "    \"scale\": \"dBm\",\n"
    "    \"window\": \"hamming\",\n"
    "    \"lna_gain\": 0,\n" // Changed to 10 for demonstration
    "    \"vga_gain\": 0,\n" // Changed to 20 for demonstration
    "    \"antenna_amp\": false\n" // Changed to true for demonstration
    "}";
    
    // 1. Initialize the structure
    DesiredCfg_t desired_config = {0}; // Zero-initialize the structure

    printf("Attempting to parse configuration...\n");

    // 2. Call the parsing function
    int result = parse_psd_config(json_data, &desired_config);

    if (result == 0) {
        printf("✅ Parsing successful! Fetched Configuration:\n");
        printf("--------------------------------------\n");
        printf("Center Frequency: %" PRIu64 " Hz\n", desired_config.center_freq);
        printf("RBW:              %d Hz\n", desired_config.rbw);
        printf("Sample Rate:      %.0f Hz\n", desired_config.sample_rate);
        printf("Span:             %.0f Hz\n", desired_config.span);
        printf("Overlap:          %.2f\n", desired_config.overlap);
        printf("Scale:            %s\n", desired_config.scale ? desired_config.scale : "NULL");
        printf("Window Type ID:   %d (Hamming=0)\n", desired_config.window_type);
        printf("LNA Gain:         %d dB\n", desired_config.lna_gain);
        printf("VGA Gain:         %d dB\n", desired_config.vga_gain);
        printf("Antenna Amp:      %s\n", desired_config.amp_enabled ? "Enabled" : "Disabled");
        printf("--------------------------------------\n");
    } else {
        fprintf(stderr, "❌ Parsing failed!\n");
    }

    
    /**
    DesiredCfg_t desired_psd = {
        .sample_rate = SAMPLE_RATE,
        .center_freq = FREQ_HZ,
        .amp_enabled = AMP_ENABLE,
        .lna_gain = LNA_GAIN,
        .vga_gain = VGA_GAIN,
        .ppm_error = PPM_ERROR,
        .window_type = WINDOW,
        .rbw = RBW, 
        .scale = DESIRED_SCALE
    };*/

    SDR_cfg_t hack_cfg;
    PsdConfig_t psd_cfg;
    RB_cfg_t rb_cfg;

    // Determine configuration
    find_params_psd(desired_config, &hack_cfg, &psd_cfg, &rb_cfg);

    // Init Buffer
    rb_init(&rb, rb_cfg.rb_size);

    if (hackrf_init() != HACKRF_SUCCESS) return -1;
    if (hackrf_open(&device) != HACKRF_SUCCESS) return -1;
    
    printf("Nperseg: %d | Target Unit: %s\n", psd_cfg.nperseg, desired_config.scale);
    
    hackrf_apply_cfg(device, &hack_cfg);

    if (hackrf_start_rx(device, rx_callback, NULL) != HACKRF_SUCCESS) goto cleanup;

    printf("Receiving data...\n");
    while (rb_available(&rb) < rb_cfg.total_bytes) usleep(10000); 
    
    stop_streaming = true;
    hackrf_stop_rx(device);
    
    printf("Processing...\n");

    int8_t* linear_buffer = malloc(rb_cfg.total_bytes);
    if (!linear_buffer) goto cleanup;
    
    rb_read(&rb, linear_buffer, rb_cfg.total_bytes);
    signal_iq_t* sig = load_iq_from_buffer(linear_buffer, rb_cfg.total_bytes);
    
    double* freq = malloc(psd_cfg.nperseg * sizeof(double));
    double* psd = malloc(psd_cfg.nperseg * sizeof(double));

    if (freq && psd) {
        execute_welch_psd(sig, &psd_cfg, freq, psd);
        
        // Apply scaling (This now matches your specific dBm formula)
        scale_psd(psd, psd_cfg.nperseg, desired_config.scale);
        
        FILE *fp = fopen("psd_results.csv", "w");
        if (fp) {
            fprintf(fp, "Frequency_Hz,Value_%s\n", desired_config.scale); 
            for (int i = 0; i < psd_cfg.nperseg; i++) {
                fprintf(fp, "%.2f,%.4f\n", freq[i], psd[i]);
            }
            fclose(fp);
            printf("Saved %s results to psd_results.csv\n", desired_config.scale);
            
            // Print first bin to verify noise floor
            printf("First bin: %.2f Hz, %.2f %s\n", freq[0], psd[0], desired_config.scale);
        }
    }

    if (linear_buffer) free(linear_buffer);
    if (freq) free(freq);
    if (psd) free(psd);
    free_signal_iq(sig);
    free_desired_psd(&desired_config);

cleanup:
    hackrf_stop_rx(device);
    hackrf_close(device);
    hackrf_exit();
    rb_free(&rb);
    return 0;
}