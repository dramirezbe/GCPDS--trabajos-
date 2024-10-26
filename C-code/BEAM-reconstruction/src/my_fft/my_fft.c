// fft.c
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include "my_fft.h"


// Multiplicación de números complejos
Complex complex_mult(Complex a, Complex b) {
    Complex result;
    result.real = a.real * b.real - a.imag * b.imag;
    result.imag = a.real * b.imag + a.imag * b.real;
    return result;
}

// Suma de números complejos
Complex complex_add(Complex a, Complex b) {
    Complex result;
    result.real = a.real + b.real;
    result.imag = a.imag + b.imag;
    return result;
}

// Resta de números complejos
Complex complex_sub(Complex a, Complex b) {
    Complex result;
    result.real = a.real - b.real;
    result.imag = a.imag - b.imag;
    return result;
}

Complex* convert_to_complex(const uint8_t* I, const uint8_t* Q, size_t N) {
    // Reservar memoria para el vector de complejos
    Complex* complex_vector = (Complex*)malloc(N * sizeof(Complex));
    if (complex_vector == NULL) {
        fprintf(stderr, "Error al reservar memoria para el vector complejo.\n");
        exit(EXIT_FAILURE);
    }

    // Llenar el vector con los valores de I y Q
    for (size_t i = 0; i < N; i++) {
        complex_vector[i].real = (double)I[i];
        complex_vector[i].imag = (double)Q[i];
    }

    return complex_vector;
}


// Generar un vector de frecuencias
void generate_frequency_vector(double* freq, int N, double fs) {
    for (int i = 0; i < N / 2; i++) {
        freq[i] = i * (fs / N);
    }
}

// Calcular la magnitud del número complejo
double complex_magnitude(Complex c) {
    return sqrt(c.real * c.real + c.imag * c.imag);
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

// FFT con relleno de ceros
void fft(Complex* x, int N, int forward) {
    if (N <= 1) return;

    // Dividir en pares e impares
    Complex even[N / 2];
    Complex odd[N / 2];
    for (int i = 0; i < N / 2; i++) {
        even[i] = x[i * 2];
        odd[i] = x[i * 2 + 1];
    }

    // Llamadas recursivas
    fft(even, N / 2, forward);
    fft(odd, N / 2, forward);

    // Calcular los factores
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
}
