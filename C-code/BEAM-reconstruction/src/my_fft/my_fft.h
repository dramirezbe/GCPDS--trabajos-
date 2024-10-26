// fft.h
#ifndef FFT_H
#define FFT_H

#include <stdint.h>

#define PI 3.14159265358979323846

// Estructura para números complejos
typedef struct {
    double real;
    double imag;
} Complex;

// Declaración de funciones
Complex complex_mult(Complex a, Complex b);
Complex complex_add(Complex a, Complex b);
Complex complex_sub(Complex a, Complex b);

void generate_frequency_vector(double* freq, int N, double fs);
double complex_magnitude(Complex c);

Complex* convert_to_complex(const uint8_t* I, const uint8_t* Q, size_t N);

int is_power_of_two(int N);
int next_power_of_two(int N);
void fft(Complex* x, int N, int forward);


#endif // FFT_H
