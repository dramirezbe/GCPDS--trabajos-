/**
 * @file bacn_RF.c
 * @brief Implementación de captura de datos IQ con HackRF (modos INSTANT y SWEEP).
 */

#include <libhackrf/hackrf.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>
#include <signal.h>
#include <math.h> // Para ceil()
#include "bacn_RF.h"

// Variables estáticas globales para el estado de la captura
static volatile bool do_exit = false;
static FILE* file = NULL;
static size_t bytes_to_xfer = 0;
static hackrf_device* device = NULL;

// Prototipo de la función interna
static int perform_single_capture(const hackrf_config_t* config, uint64_t current_center_freq, const char* filename);

void stop_main_loop(void) {
	do_exit = true;
	kill(getpid(), SIGALRM);
}

int rx_callback(hackrf_transfer* transfer) {
	if (file == NULL) return -1;

	size_t bytes_to_write = transfer->valid_length;
	if (bytes_to_xfer > 0) {
		if (bytes_to_write > bytes_to_xfer) {
			bytes_to_write = bytes_to_xfer;
		}
		bytes_to_xfer -= bytes_to_write;
	}

	if (fwrite(transfer->buffer, 1, bytes_to_write, file) != bytes_to_write) {
		fprintf(stderr, "Error escribiendo en el archivo.\n");
		stop_main_loop();
		return -1;
	}

	if (bytes_to_xfer == 0) {
		stop_main_loop();
	}
	return 0;
}

void sigint_callback_handler(int signum) {
	fprintf(stderr, "\nSeñal %d recibida. Saliendo...\n", signum);
	do_exit = true;
	kill(getpid(), SIGALRM);
}

void sigalrm_callback_handler() { }


int capture_samples(const hackrf_config_t* config) {
	int result = 0;

	// Inicializar libhackrf una sola vez
	result = hackrf_init();
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr, "hackrf_init() falló: %s (%d)\n", hackrf_error_name(result), result);
		return -1;
	}
	
	// Configurar manejadores de señales
	signal(SIGINT, &sigint_callback_handler);
	signal(SIGTERM, &sigint_callback_handler);
	signal(SIGALRM, &sigalrm_callback_handler);

	switch (config->mode) {
		case MODE_INSTANT: {
			fprintf(stderr, "--- MODO CAPTURA INSTANTÁNEA ---\n");
			char filename[256];
			snprintf(filename, sizeof(filename), "%s/0", config->output_path);
			result = perform_single_capture(config, config->center_freq_hz, filename);
			break;
		}
		case MODE_SWEEP: {
			fprintf(stderr, "--- MODO BARRIDO DE FRECUENCIA ---\n");
			if (config->end_freq_hz <= config->start_freq_hz) {
				fprintf(stderr, "Error: La frecuencia final debe ser mayor que la inicial.\n");
				result = -1;
				break;
			}

			uint64_t total_bw = config->end_freq_hz - config->start_freq_hz;
			int num_steps = (int)ceil((double)total_bw / config->sample_rate_hz);
            if (num_steps == 0) num_steps = 1;

			fprintf(stderr, "Rango: %.2f a %.2f MHz\n", (double)config->start_freq_hz / 1e6, (double)config->end_freq_hz / 1e6);
            fprintf(stderr, "Tasa de muestreo: %.2f Msps\n", (double)config->sample_rate_hz / 1e6);
			fprintf(stderr, "Se realizarán %d capturas.\n", num_steps);

			for (int i = 0; i < num_steps; i++) {
				// Detener el barrido si el usuario lo solicita
				if (do_exit) {
					fprintf(stderr, "Barrido interrumpido por el usuario.\n");
					break;
				}
				
				uint64_t current_center_freq = config->start_freq_hz + (config->sample_rate_hz / 2) + (i * config->sample_rate_hz);
				
				// Asegurarse de no exceder la frecuencia final
				if (current_center_freq > config->end_freq_hz) {
					current_center_freq = config->end_freq_hz - (config->sample_rate_hz / 2);
				}

				char filename[256];
				snprintf(filename, sizeof(filename), "%s/%d", config->output_path, i);

				fprintf(stderr, "\n[Paso %d/%d] Capturando en %.2f MHz...\n", i + 1, num_steps, (double)current_center_freq / 1e6);
				result = perform_single_capture(config, current_center_freq, filename);

				if (result != 0) {
					fprintf(stderr, "Error en el paso %d. Abortando barrido.\n", i + 1);
					break;
				}
			}
			break;
		}
		default:
			fprintf(stderr, "Error: Modo de captura no reconocido.\n");
			result = -1;
			break;
	}

	// Liberar recursos de libhackrf al final
	hackrf_exit();
	fprintf(stderr, "Proceso finalizado.\n");
	return result;
}

/**
 * @brief Realiza una única captura en una frecuencia específica.
 */
static int perform_single_capture(const hackrf_config_t* config, uint64_t current_center_freq, const char* filename) {
	int result = 0;
	do_exit = false;
	bytes_to_xfer = config->num_samples_per_step * 2;

	file = fopen(filename, "wb");
	if (file == NULL) {
		fprintf(stderr, "Error: No se pudo abrir el archivo de salida: %s\n", filename);
		return -1;
	}
	setvbuf(file, NULL, _IOFBF, FD_BUFFER_SIZE);

	result = hackrf_open(&device);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr, "hackrf_open() falló: %s (%d)\n", hackrf_error_name(result), result);
		fclose(file);
		return -1;
	}

	// Configurar parámetros del dispositivo
	uint32_t bw = hackrf_compute_baseband_filter_bw_round_down_lt(config->sample_rate_hz);
	result = hackrf_set_freq(device, current_center_freq);
	result |= hackrf_set_sample_rate(device, config->sample_rate_hz);
	result |= hackrf_set_baseband_filter_bandwidth(device, bw);
	result |= hackrf_set_vga_gain(device, config->vga_gain);
	result |= hackrf_set_lna_gain(device, config->lna_gain);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr, "Error configurando los parámetros del HackRF.\n");
		goto cleanup;
	}

	result = hackrf_start_rx(device, rx_callback, NULL);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr, "hackrf_start_rx() falló: %s (%d)\n", hackrf_error_name(result), result);
		goto cleanup;
	}
	
	while (!do_exit) {
		pause(); // Esperar eficientemente por una señal
	}

cleanup:
	if (device != NULL) {
		hackrf_stop_rx(device);
		hackrf_close(device);
		device = NULL;
	}
	if (file != NULL) {
		fclose(file);
		file = NULL;
	}
	return (result == HACKRF_SUCCESS) ? 0 : -1;
}