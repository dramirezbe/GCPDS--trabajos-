#ifndef MYFFT_H
#define MYFFT_H

// Definición explícita de la estructura para un número complejo
typedef struct {
    double real;
    double imag;
} complex_t;

// Funciones auxiliares para números complejos
complex_t make_complex(double real, double imag);
complex_t complex_add(complex_t a, complex_t b);
complex_t complex_sub(complex_t a, complex_t b);
complex_t complex_mul(complex_t a, complex_t b);
complex_t complex_exp(double theta);
double complex_real(complex_t z);
double complex_imag(complex_t z);
int check(int n);
void FFT(complex_t* array, int dimension, double sampling_step);

#endif // MYFFT_H
