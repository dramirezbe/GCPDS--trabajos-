#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <fftw3.h>
#include <math.h>
#include <string.h>

#include "welch.h"

#define PI 3.14159265358979323846

/**
 * @brief Genera una ventana de Hamming.
 * 
 * Esta función genera una ventana de Hamming de longitud `segment_length` y
 * almacena los valores en el arreglo `window`.
 *
 * @param window Un puntero al arreglo donde se almacenarán los valores de la ventana de Hamming.
 * @param segment_length La longitud del segmento para la ventana de Hamming.
 */
void generate_hamming_window(double* window, int segment_length) {
    for (int n = 0; n < segment_length; n++) {
        window[n] = 0.54 - 0.46 * cos((2.0 * PI * n) / (segment_length - 1));
    }
}

/**
 * @brief Calcula la Densidad Espectral de Potencia (PSD) de Welch para señales complejas.
 * 
 * Esta función aplica el método de Welch para calcular la PSD de una señal compleja de entrada.
 * Divide la señal en segmentos superpuestos, aplica una ventana de Hamming a cada segmento,
 * realiza la Transformada de Fourier en cada segmento, y promedia las potencias espectrales.
 *
 * @param signal Puntero a la señal de entrada de tipo `complex double`.
 * @param N_signal Tamaño de la señal de entrada.
 * @param fs Frecuencia de muestreo de la señal de entrada.
 * @param segment_length Longitud de cada segmento en el que se divide la señal.
 * @param overlap Factor de solapamiento entre segmentos (0 a 1).
 * @param f_out Puntero al arreglo donde se almacenarán las frecuencias de salida.
 * @param P_welch_out Puntero al arreglo donde se almacenarán los valores calculados de la PSD.
 * 
 * @note Es necesario liberar la memoria reservada para la FFT usando `fftw_destroy_plan` y `fftw_free`.
 *
 * @example
 * @code
 * size_t N_signal = 1024;
 * complex double signal[N_signal];
 * double fs = 1000.0;
 * int segment_length = 256;
 * double overlap = 0.5;
 * double f_out[segment_length];
 * double P_welch_out[segment_length];
 * welch_psd_complex(signal, N_signal, fs, segment_length, overlap, f_out, P_welch_out);
 * @endcode
 */
void welch_psd_complex(complex double* signal, size_t N_signal, double fs, 
                       int segment_length, double overlap, double* f_out, double* P_welch_out) {
    int step = (int)(segment_length * (1.0 - overlap));
    int K = ((N_signal - segment_length) / step) + 1;
    size_t psd_size = segment_length;

    // Inicializar ventana
    double window[segment_length];
    generate_hamming_window(window, segment_length);

    // Calcular normalización de la ventana
    double U = 0.0;
    for (int i = 0; i < segment_length; i++) {
        U += window[i] * window[i];
    }
    U /= segment_length;

    // Reservar memoria para segmentos y resultados FFT
    complex double* segment = fftw_alloc_complex(segment_length);
    complex double* X_k = fftw_alloc_complex(segment_length);
    fftw_plan plan = fftw_plan_dft_1d(segment_length, segment, X_k, FFTW_FORWARD, FFTW_ESTIMATE);

    // Inicializar PSD
    memset(P_welch_out, 0, psd_size * sizeof(double));

    // Procesar cada segmento
    for (int k = 0; k < K; k++) {
        int start = k * step;

        // Aplicar ventana al segmento
        for (int i = 0; i < segment_length; i++) {
            segment[i] = signal[start + i] * window[i];
        }

        // Ejecutar FFT en el segmento
        fftw_execute(plan);

        // Acumular la potencia espectral
        for (size_t i = 0; i < psd_size; i++) {
            double abs_X_k = cabs(X_k[i]);
            P_welch_out[i] += (abs_X_k * abs_X_k) / (fs * U);
        }
    }

    // Promediar sobre los segmentos
    for (size_t i = 0; i < psd_size; i++) {
        P_welch_out[i] /= K;
    }

    // Generar frecuencias asociadas
    double val = fs / segment_length;
    for (size_t i = 0; i < psd_size; i++) {
        f_out[i] = -fs / 2 + i * val;
    }

    printf("Finish");

    // Liberar memoria
    fftw_destroy_plan(plan);
    fftw_free(segment);
    fftw_free(X_k);
}
