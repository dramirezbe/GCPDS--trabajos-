/**
 * @file bacn_RF.h
 * @brief Definiciones y prototipos para el manejo del dispositivo HackRF.
 * 
 * Este archivo contiene la estructura de configuración y la función
 * principal para la adquisición de datos IQ con HackRF, soportando
 * tanto capturas instantáneas como barridos de frecuencia.
 */

#ifndef BACN_RF_H
#define BACN_RF_H

#include <libhackrf/hackrf.h>
#include <stdint.h>

/**
 * @def FD_BUFFER_SIZE
 * @brief Tamaño del búfer de escritura a disco para mejorar el rendimiento.
 */
#define FD_BUFFER_SIZE (128 * 1024)

/**
 * @enum capture_mode_t
 * @brief Modos de operación para la captura de muestras.
 */
typedef enum {
	MODE_INSTANT, /**< Captura en una única frecuencia central. */
	MODE_SWEEP    /**< Realiza un barrido entre una frecuencia inicial y final. */
} capture_mode_t;

/**
 * @struct hackrf_config_t
 * @brief Estructura para contener los parámetros de configuración de la captura.
 */
typedef struct {
	capture_mode_t mode;             /**< Modo de operación: INSTANT o SWEEP. */

	// --- Parámetros comunes para ambos modos ---
	uint32_t sample_rate_hz;         /**< Tasa de muestreo en Hz. */
	uint32_t lna_gain;               /**< Ganancia LNA (IF) en dB. Rango: 0-40, en pasos de 8. */
	uint32_t vga_gain;               /**< Ganancia VGA (Baseband) en dB. Rango: 0-62, en pasos de 2. */
	uint64_t num_samples_per_step;   /**< Número de muestras (pares IQ) a capturar por cada paso. */
	const char* output_path;         /**< Directorio donde se guardarán los archivos de captura. */

	// --- Parámetros para MODE_INSTANT ---
	uint64_t center_freq_hz;         /**< Frecuencia central en Hz para la captura instantánea. */

	// --- Parámetros para MODE_SWEEP ---
	uint64_t start_freq_hz;          /**< Frecuencia de inicio del barrido en Hz. */
	uint64_t end_freq_hz;            /**< Frecuencia final del barrido en Hz. */

} hackrf_config_t;

/**
 * @brief Configura y ejecuta la adquisición de muestras con HackRF según la configuración.
 * 
 * @param config Puntero a la estructura de configuración que define la captura.
 * @return int Devuelve 0 en caso de éxito, o -1 en caso de error.
 */
int capture_samples(const hackrf_config_t* config);

#endif // BACN_RF_H