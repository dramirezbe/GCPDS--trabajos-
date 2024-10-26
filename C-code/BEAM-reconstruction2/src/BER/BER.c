#include <stdio.h>
#include <math.h>
#include "BER.h"

#define PI 3.1415926535897932384

// Definir la función que se va a integrar, que es e^(-t^2)
static double integrand(double t) {
    return exp(-t * t);
}

// Aproximación de la función complementaria del error (erfc) usando integración numérica
double erfc_manual(double x, int num_steps) {
    if (num_steps <= 0) {
        fprintf(stderr, "Error: El número de pasos debe ser positivo.\n");
        return -1.0;
    }

    double step_size = 10.0 / num_steps;
    double integral_approx = 0.0;

    // Aplicar la regla del trapecio para aproximar la integral
    for (int i = 0; i < num_steps; i++) {
        double t1 = x + i * step_size;
        double t2 = x + (i + 1) * step_size;
        integral_approx += 0.5 * (integrand(t1) + integrand(t2)) * step_size;
    }

    // Multiplicar por la constante (2 / sqrt(pi)) para obtener erfc(x)
    return (2.0 / sqrt(PI)) * integral_approx;
}

// Función Q basada en erfc_manual
double Q(double x) {
    if (x < 0) {
        fprintf(stderr, "Error: x debe ser no negativo para calcular Q(x).\n");
        return -1.0;
    }
    return 0.5 * erfc_manual(x / sqrt(2.0), 10000);
}

// Función para calcular la Tasa de Error de Bit (BER) en una modulación 64-QAM en función del SNR
double calculate_BER_from_snr(double SNR) {
    const int M = 64;
    if (SNR < 0) {
        fprintf(stderr, "Error: SNR debe ser no negativo.\n");
        return -1.0;
    }

    double factor = (3.0 * log2(M) / (M - 1.0)) * SNR;
    return (4.0 / log2(M)) * (1.0 - 1.0 / sqrt(M)) * Q(sqrt(factor));
}
