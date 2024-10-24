#ifndef MY_FUNCTIONS
#define MY_FUNCTIONS

#include <stdint.h>
#include <stddef.h>

void process_data(const char *file_path, size_t *file_size, size_t num_samples, int8_t **I, int8_t **Q);

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

#endif // MY_FUNCTIONS