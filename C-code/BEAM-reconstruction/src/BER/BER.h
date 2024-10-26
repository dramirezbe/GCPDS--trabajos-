#ifndef BER_CALCULATOR_H
#define BER_CALCULATOR_H

// Función que calcula la aproximación manual de la función complementaria del error (erfc)
double erfc_manual(double x, int num_steps);

// Función Q que usa erfc_manual
double Q(double x);

// Función para calcular la Tasa de Error de Bit (BER) en 64-QAM en función del SNR
double calculate_BER_from_snr(double SNR);

#endif // BER_CALCULATOR_H