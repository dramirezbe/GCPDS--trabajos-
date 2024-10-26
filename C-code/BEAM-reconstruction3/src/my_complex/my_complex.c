#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
# include "my_complex.h"

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

// Convertir datos I/Q a números complejos
Complex* convert_to_complex(const uint8_t* I, const uint8_t* Q, size_t N) {
    if (!I || !Q) {
        fprintf(stderr, "Error: Punteros de entrada nulos.\n");
        return NULL;
    }

    Complex* complex_vector = (Complex*)malloc(N * sizeof(Complex));
    if (!complex_vector) {
        fprintf(stderr, "Error al reservar memoria para el vector complejo.\n");
        return NULL;
    }

    for (size_t i = 0; i < N; i++) {
        complex_vector[i].real = (double)I[i];
        complex_vector[i].imag = (double)Q[i];
    }

    return complex_vector;
}

// Calcular la magnitud de un número complejo
double complex_magnitude(Complex c) {
    return sqrt(c.real * c.real + c.imag * c.imag);
}
