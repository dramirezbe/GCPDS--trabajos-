#include <stdio.h>
#include <math.h>
#include "ber.h"

#define PI 3.1415926535897932384

// Definir la función que se va a integrar, que es e^(-t^2)
static double integrand(double t) {
    return exp(-t * t);
}

// Aproximación manual de la función complementaria del error (erfc) usando integración numérica
double erfc_manual(double x, int num_steps) {
    double step_size = 10.0 / num_steps;  // Tamaño del paso
    double integral_approx = 0.0;

    // Aplicar la regla del trapecio
    for (int i = 0; i < num_steps; i++) {
        double t1 = x + i * step_size;
        double t2 = x + (i + 1) * step_size;
        integral_approx += 0.5 * (integrand(t1) + integrand(t2)) * step_size;
    }

    // Multiplicar por la constante (2 / sqrt(pi)) para obtener erfc(x)
    double result = (2.0 / sqrt(PI)) * integral_approx;

    return result;
}

// Función Q basada en erfc_manual
double Q(double x) {
    return 0.5 * erfc_manual(x / sqrt(2.0), 10000);
}

// Función para calcular la Tasa de Error de Bit (BER) en una modulación 64-QAM en función del SNR
double calculate_BER_from_snr(double SNR) {
    int M = 64;  // Número de símbolos en la modulación 64-QAM
    return (4.0 / log2(M)) * (1.0 - 1.0 / sqrt(M)) * Q(sqrt((3.0 * log2(M) / (M - 1.0)) * SNR));
}
