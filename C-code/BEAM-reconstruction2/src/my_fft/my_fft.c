#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include "my_fft.h"
#include "../my_complex/my_complex.h"

#define PI 3.14159265358979323846


// Generar vector de frecuencias
void generate_frequency_vector(double* freq, int N, double fs) {
    if (!freq || N <= 0 || fs <= 0) {
        fprintf(stderr, "Error: Parámetros inválidos para generar el vector de frecuencias.\n");
        return;
    }
    for (int i = 0; i < N / 2; i++) {
        freq[i] = i * (fs / N);
    }
}

// Verificar si un número es potencia de 2
int is_power_of_two(int N) {
    return (N > 0) && ((N & (N - 1)) == 0);
}

// Calcular la siguiente potencia de 2
int next_power_of_two(int N) {
    int p = 1;
    while (p < N) {
        p *= 2;
    }
    return p;
}

// Implementación de FFT
void fft(Complex* x, int N, int forward) {
    if (N <= 1) return;

    if (!is_power_of_two(N)) {
        fprintf(stderr, "Error: El tamaño N debe ser una potencia de 2 para la FFT.\n");
        return;
    }

    Complex* even = (Complex*)malloc(N / 2 * sizeof(Complex));
    Complex* odd = (Complex*)malloc(N / 2 * sizeof(Complex));

    if (!even || !odd) {
        fprintf(stderr, "Error: No se pudo asignar memoria para el cálculo de FFT.\n");
        free(even);
        free(odd);
        return;
    }

    for (int i = 0; i < N / 2; i++) {
        even[i] = x[i * 2];
        odd[i] = x[i * 2 + 1];
    }

    fft(even, N / 2, forward);
    fft(odd, N / 2, forward);

    for (int k = 0; k < N / 2; k++) {
        double theta = (2 * PI * k / N) * (forward ? -1 : 1);
        Complex t = {cos(theta), sin(theta)};
        Complex twiddle = complex_mult(t, odd[k]);

        x[k] = complex_add(even[k], twiddle);
        x[k + N / 2] = complex_sub(even[k], twiddle);

        if (!forward) {
            x[k].real /= 2;
            x[k].imag /= 2;
            x[k + N / 2].real /= 2;
            x[k + N / 2].imag /= 2;
        }
    }

    free(even);
    free(odd);
}
