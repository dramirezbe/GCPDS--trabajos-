/**
 * @file main.c
 * @brief Continuous Headless PSD Analyzer
 * Flow: ZMQ_SUB -> HackRF -> Welch -> JSON -> ZMQ_PUB
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <math.h>
#include <string.h> 
#include <libhackrf/hackrf.h>
#include <inttypes.h>
#include <cjson/cJSON.h>

#include "Modules/psd.h"
#include "Drivers/ring_buffer.h" 
#include "Drivers/sdr_HAL.h"
#include "Drivers/zmqsub.h"
#include "Drivers/zmqpub.h"

// ----------------------------------------------------------------------
// Global State & Config
// ----------------------------------------------------------------------

hackrf_device* device = NULL;
ring_buffer_t rb;
zpub_t *publisher = NULL; // The Output Channel

// Flags for thread synchronization
volatile bool stop_streaming = false;
volatile bool config_received = false; 

// Global Configuration Containers
DesiredCfg_t desired_config = {0};
PsdConfig_t psd_cfg = {0};
SDR_cfg_t hack_cfg = {0};
RB_cfg_t rb_cfg = {0};

// ----------------------------------------------------------------------
// Forward Declarations
// ----------------------------------------------------------------------
void print_desired(const DesiredCfg_t *cfg);
int find_params_psd(DesiredCfg_t desired, SDR_cfg_t *hack_cfg, PsdConfig_t *psd_cfg, RB_cfg_t *rb_cfg);
void publish_results(double* freq_array, double* psd_array, int length);

// ----------------------------------------------------------------------
// HackRF Callback
// ----------------------------------------------------------------------

int rx_callback(hackrf_transfer* transfer) {
    if (stop_streaming) return -1;
    rb_write(&rb, transfer->buffer, transfer->valid_length);
    return 0;
}

// ----------------------------------------------------------------------
// Config Logic
// ----------------------------------------------------------------------

int find_params_psd(DesiredCfg_t desired, SDR_cfg_t *hack_cfg, PsdConfig_t *psd_cfg, RB_cfg_t *rb_cfg) {
    double enbw_factor = get_window_enbw_factor(desired.window_type);
    
    // Calculate NPERSEG to hit the desired Resolution Bandwidth (RBW)
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

    // Ring Buffer Sizing
    rb_cfg->total_bytes = (size_t)(desired.sample_rate * 2); // Capture ~1 second for good averaging
    rb_cfg->rb_size = (int)(rb_cfg->total_bytes * 2);
    
    return 0;
}

// ----------------------------------------------------------------------
// Output Serialization (JSON Builder)
// ----------------------------------------------------------------------

void publish_results(double* freq_array, double* psd_array, int length) {
    if (!publisher || !freq_array || !psd_array) return;

    // 1. Create the Root JSON Object
    cJSON *root = cJSON_CreateObject();
    
    // 2. Add Start/End Frequency
    // Assuming freq_array is sorted (which it is from Welch)
    cJSON_AddNumberToObject(root, "start_freq_hz", freq_array[0] + (double)hack_cfg.center_freq);
    cJSON_AddNumberToObject(root, "end_freq_hz", freq_array[length-1] + (double)hack_cfg.center_freq);

    // 3. Add the Pxx Array
    // cJSON_CreateDoubleArray copies the data into the JSON object
    cJSON *pxx_array = cJSON_CreateDoubleArray(psd_array, length);
    cJSON_AddItemToObject(root, "Pxx", pxx_array);

    // 4. Serialize to String
    char *json_string = cJSON_PrintUnformatted(root); // Unformatted = smaller payload, no newlines

    // 5. Send via ZMQ
    // We use a topic name "data" so the Python subscriber can filter for it
    zpub_publish(publisher, "data", json_string);
    
    printf("[ZMQ] Published results (%d bins, %zu bytes)\n", length, strlen(json_string));

    // 6. Cleanup
    free(json_string); // cJSON_Print allocates memory
    cJSON_Delete(root); // This frees the array and children too
}

// ----------------------------------------------------------------------
// ZMQ Callback
// ----------------------------------------------------------------------

void handle_psd_message(const char *payload) {
    printf("\n>>> [ZMQ] Received Command Payload.\n");

    free_desired_psd(&desired_config); 
    memset(&desired_config, 0, sizeof(DesiredCfg_t));

    // Parse incoming JSON using Modules/psd.c parser
    if (parse_psd_config(payload, &desired_config) == 0) {
        find_params_psd(desired_config, &hack_cfg, &psd_cfg, &rb_cfg);
        print_desired(&desired_config);
        config_received = true; 
    } else {
        fprintf(stderr, ">>> [PARSER] Failed to parse JSON configuration.\n");
    }
}

// ----------------------------------------------------------------------
// Main Application
// ----------------------------------------------------------------------

int main() {
    char *input_topic = "acquire";
    int cycle_count = 0;

    // -------------------------------------------------
    // 1. Initialization
    // -------------------------------------------------
    
    // A. Init ZMQ Subscriber (Input)
    zsub_t *sub = zsub_init(input_topic, handle_psd_message);
    if (!sub) {
        fprintf(stderr, "CRITICAL: Failed to init ZMQ Subscriber.\n");
        return 1;
    }
    zsub_start(sub);

    // B. Init ZMQ Publisher (Output)
    publisher = zpub_init();
    if (!publisher) {
        fprintf(stderr, "CRITICAL: Failed to init ZMQ Publisher.\n");
        zsub_close(sub);
        return 1;
    }

    // C. Open Hardware
    if (hackrf_init() != HACKRF_SUCCESS) {
        fprintf(stderr, "CRITICAL: HackRF Library Init Failed.\n");
        return 1;
    }
    
    int status = hackrf_open(&device);
    if (status != HACKRF_SUCCESS) {
        fprintf(stderr, "CRITICAL: No HackRF device found. (Error %d)\n", status);
        return 1;
    }
    printf("[SYSTEM] HackRF Connected. Entering Idle Loop.\n");

    // -------------------------------------------------
    // 2. Infinite Loop
    // -------------------------------------------------
    while (1) {
        
        // --- IDLE STATE ---
        if (!config_received) {
            usleep(10000); // 10ms
            continue;
        }

        // --- START CYCLE ---
        cycle_count++;
        printf("\n=== Acquisition Cycle #%d ===\n", cycle_count);

        rb_init(&rb, rb_cfg.rb_size);
        stop_streaming = false;

        hackrf_apply_cfg(device, &hack_cfg);

        if (hackrf_start_rx(device, rx_callback, NULL) != HACKRF_SUCCESS) {
            fprintf(stderr, "[ERROR] Failed to start RX.\n");
            goto end_of_cycle;
        }

        // Wait for buffer fill with timeout
        int safety_timeout = 500; // 5 seconds
        while ((rb_available(&rb) < rb_cfg.total_bytes) && (safety_timeout > 0)) {
            usleep(10000); 
            safety_timeout--;
        }

        stop_streaming = true;
        hackrf_stop_rx(device);

        if (safety_timeout <= 0) {
            fprintf(stderr, "[ERROR] Timeout waiting for samples.\n");
            goto end_of_cycle;
        }

        // --- DSP & PROCESSING ---
        int8_t* linear_buffer = malloc(rb_cfg.total_bytes);
        if (!linear_buffer) goto end_of_cycle;

        rb_read(&rb, linear_buffer, rb_cfg.total_bytes);
        signal_iq_t* sig = load_iq_from_buffer(linear_buffer, rb_cfg.total_bytes);
        
        double* freq = malloc(psd_cfg.nperseg * sizeof(double));
        double* psd = malloc(psd_cfg.nperseg * sizeof(double));

        if (freq && psd && sig) {
            // 
            execute_welch_psd(sig, &psd_cfg, freq, psd);
            
            // Apply Units (dBm, dBuV, etc)
            scale_psd(psd, psd_cfg.nperseg, desired_config.scale);
            
            // --- PUBLISH TO ZMQ ---
            publish_results(freq, psd, psd_cfg.nperseg);
        }

        // --- MEMORY CLEANUP ---
        if (linear_buffer) free(linear_buffer);
        if (freq) free(freq);
        if (psd) free(psd);
        free_signal_iq(sig);

        end_of_cycle:
        rb_free(&rb);
        config_received = false; // Return to Idle
    }

    // Unreachable cleanup
    hackrf_close(device);
    hackrf_exit();
    zsub_close(sub);
    zpub_close(publisher);
    return 0;
}

void print_desired(const DesiredCfg_t *cfg) {
    printf("  [CFG] Freq: %" PRIu64 " | RBW: %d | Scale: %s\n", 
           cfg->center_freq, cfg->rbw, cfg->scale ? cfg->scale : "dBm");
}