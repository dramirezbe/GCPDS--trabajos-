#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <libhackrf/hackrf.h>

#define SAMPLE_RATE 2000000 // 2 Msps
#define TOTAL_BYTES (SAMPLE_RATE * 2) // 1 sec of I+Q samples (8-bit each)

hackrf_device* device = NULL;
int8_t* main_buffer = NULL;
int bytes_collected = 0;
int finished = 0;

// Callback function called by libhackrf when data is ready
int rx_callback(hackrf_transfer* transfer) {
    if (finished) return 0;

    for (int i = 0; i < transfer->valid_length; i++) {
        if (bytes_collected < TOTAL_BYTES) {
            main_buffer[bytes_collected++] = transfer->buffer[i];
        } else {
            finished = 1;
            return -1; // Stop transfer immediately
        }
    }
    return 0;
}

int main() {
    // Allocate memory for exactly 1 second of samples
    main_buffer = (int8_t*)malloc(TOTAL_BYTES);

    hackrf_init();
    hackrf_open(&device);

    // Basic Setup
    hackrf_set_sample_rate(device, SAMPLE_RATE);
    hackrf_set_freq(device, 915000000); // 915 MHz
    hackrf_set_lna_gain(device, 16);
    hackrf_set_vga_gain(device, 20);

    // Start Rx
    hackrf_start_rx(device, rx_callback, NULL);

    // Wait until buffer is full
    while (!finished) {
        usleep(1000);
    }

    hackrf_stop_rx(device);
    hackrf_close(device);
    hackrf_exit();

    // Print first 10 I,Q pairs (Interleaved: I, Q, I, Q...)
    printf("First 10 Samples (I, Q):\n");
    for (int i = 0; i < 20; i += 2) {
        printf("%d: I=%d, Q=%d\n", (i/2)+1, main_buffer[i], main_buffer[i+1]);
    }

    free(main_buffer);
    return 0;
}