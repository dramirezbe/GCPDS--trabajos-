#ifndef BER_H
#define BER_H

#include <math.h>

/**
 * @brief Aproxima la función complementaria del error, erfc(x), usando integración numérica.
 * @param x Valor de entrada.
 * @param num_steps Número de pasos en la integración.
 * @return Aproximación de erfc(x), o -1 en caso de error.
 */
double erfc_manual(double x, int num_steps);

/**
 * @brief Calcula la función Q, que es la cola de una distribución normal estándar.
 * @param x Valor de entrada.
 * @return Valor de Q(x), o -1 en caso de error.
 */
double Q(double x);

/**
 * @brief Calcula la tasa de error de bit (BER) para una modulación 64-QAM en función del SNR.
 * @param SNR Relación señal/ruido.
 * @return Tasa de error de bit aproximada (BER), o -1 en caso de error.
 */
double calculate_BER_from_snr(double SNR);

#endif // BER_H
