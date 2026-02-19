// main.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>

#include "Drivers/ring_buffer.h"
#include "Drivers/consumer.h"
#include "Modules/fm_logic.h"
#include "Drivers/sdr_HAL.h"

// --- SETTINGS ---
#define SAMPLE_RATE_RF 1920000 
#define FREQ_HZ 105700000 // 105.7 MHz
#define BLOCK_SIZE (256 * 1024)

volatile int keep_running = 1;

// --- DUMMY CSV LOGIC ---
void csv_logic(const uint8_t *data, size_t len, void *ctx) {
    // In real life: Write to file
    // Here: Just print stats periodically
    static int calls = 0;
    if (calls++ % 100 == 0) {
        printf("[CSV Consumer] Processed block of %zu bytes. (First byte: %02x)\n", 
               len, data[0]);
    }
    // Simulate disk I/O time
    usleep(100); 
}

// --- DISPATCHER ---
typedef struct {
    ring_buffer_t *main_rb;
    Consumer_t *c_fm;
    Consumer_t *c_csv;
} DispatcherCtx;

void* dispatcher_thread(void* arg) {
    DispatcherCtx *d = (DispatcherCtx*)arg;
    uint8_t temp[16 * 1024]; // Dispatch 16KB chunks

    while(keep_running) {
        size_t read = rb_read(d->main_rb, temp, sizeof(temp));
        if (read > 0) {
            // Fan-out: Send same data to both consumers
            consumer_push_chunk(d->c_fm, temp, read);
            consumer_push_chunk(d->c_csv, temp, read);
        } else {
            usleep(1000);
        }
    }
    return NULL;
}

// --- HACKRF CALLBACK ---
// Feeds the Main Ring Buffer
int producer_realtime(hackrf_transfer* transfer) {
    ring_buffer_t *rb = (ring_buffer_t*)transfer->rx_ctx;
    rb_write(rb, transfer->buffer, transfer->valid_length);
    return 0;
}

int main() {
    // 1. Init Main Ring Buffer (High capacity for RF data)
    ring_buffer_t main_rb;
    rb_init(&main_rb, 1024 * 1024 * 64); // 64MB Buffer

    // 2. Setup FM Consumer Context (DSP State)
    FMDemodContext fm_ctx;
    fm_context_init(&fm_ctx, SAMPLE_RATE_RF, 48000);

    // 3. Init Consumers
    Consumer_t cons_fm, cons_csv;
    
    // Init FM Consumer: Note we pass &fm_ctx as the user data
    consumer_init(&cons_fm, "FM_Radio", 1024*1024, fm_demod_logic, &fm_ctx);
    
    // Init CSV Consumer: Context can be NULL or a FILE*
    consumer_init(&cons_csv, "CSV_Log", 1024*1024, csv_logic, NULL);

    // 4. Start Consumer Threads
    consumer_start(&cons_fm);
    consumer_start(&cons_csv);

    // 5. Start Dispatcher Thread
    pthread_t th_disp;
    DispatcherCtx d_ctx = { .main_rb = &main_rb, .c_fm = &cons_fm, .c_csv = &cons_csv };
    pthread_create(&th_disp, NULL, dispatcher_thread, &d_ctx);

    // 6. Setup HackRF
    hackrf_init();
    hackrf_device *device = NULL;
    hackrf_open(&device);

    // Configuration Object
    SDR_cfg_t cfg = {
        .sample_rate = 1920000.0, // .0 for double
        .center_freq = 105700000, // 105.7 MHz
        .amp_enabled = false,     // Amp off
        .lna_gain = 32,
        .vga_gain = 28,
        .ppm_error = -14          // Correction value
    };
    hackrf_apply_cfg(device, &cfg);

    // Start SDR (Producer)
    hackrf_start_rx(device, producer_realtime, &main_rb);

    printf("=== SYSTEM RUNNING ===\n");
    printf("1. SDR -> Main RingBuffer\n");
    printf("2. Dispatcher -> FM Consumer (Audio) & CSV Consumer (Log)\n");
    printf("Press ENTER to stop...\n");
    getchar();

    // 7. Cleanup
    keep_running = 0;
    hackrf_stop_rx(device);
    hackrf_close(device);
    hackrf_exit();
    
    pthread_join(th_disp, NULL);
    
    consumer_stop(&cons_fm);
    consumer_stop(&cons_csv);
    
    fm_context_cleanup(&fm_ctx); // Close PortAudio
    rb_free(&main_rb);

    printf("Done.\n");
    return 0;
}