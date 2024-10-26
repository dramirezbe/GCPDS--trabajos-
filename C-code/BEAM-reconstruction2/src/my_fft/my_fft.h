#ifndef MY_FFT_H
#define MY_FFT_H

#include <stdint.h>
#include <stdlib.h>
#include "../my_complex/my_complex.h"

/**
 * @brief Genera un vector de frecuencias.
 * @param freq Puntero al vector de frecuencias.
 * @param N Número de puntos.
 * @param fs Frecuencia de muestreo.
 */
void generate_frequency_vector(double* freq, int N, double fs);

/**
 * @brief Verifica si un número es potencia de 2.
 * @param N Número a verificar.
 * @return 1 si es potencia de 2, 0 en caso contrario.
 */
int is_power_of_two(int N);

/**
 * @brief Calcula la siguiente potencia de 2 de un número dado.
 * @param N Número para el cual se calculará la siguiente potencia de 2.
 * @return La siguiente potencia de 2 mayor o igual a N.
 */
int next_power_of_two(int N);

/**
 * @brief Realiza la Transformada Rápida de Fourier (FFT) o su inversa.
 * @param x Puntero al array de números complejos a transformar.
 * @param N Número de elementos en x, debe ser una potencia de 2.
 * @param forward 1 para FFT directa, 0 para FFT inversa.
 */
void fft(Complex* x, int N, int forward);

#endif // MY_FFT_H
