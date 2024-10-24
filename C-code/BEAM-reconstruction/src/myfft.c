#include "myfft.h"
#include <stdlib.h>
#include <math.h>

#define PI 3.1415926535897932384

complex_t make_complex(double real, double imag) {
    complex_t z;
    z.real = real;
    z.imag = imag;
    return z;
}

complex_t complex_add(complex_t a, complex_t b) {
    return make_complex(a.real + b.real, a.imag + b.imag);
}

complex_t complex_sub(complex_t a, complex_t b) {
    return make_complex(a.real - b.real, a.imag - b.imag);
}

complex_t complex_mul(complex_t a, complex_t b) {
    return make_complex(a.real * b.real - a.imag * b.imag, a.real * b.imag + a.imag * b.real);
}

complex_t complex_exp(double theta) {
    return make_complex(cos(theta), sin(theta));
}

double complex_real(complex_t z) {
    return z.real;
}

double complex_imag(complex_t z) {
    return z.imag;
}

int int_log2(int N) {
    int k = N, i = 0;
    while(k) {
        k >>= 1;
        i++;
    }
    return i - 1;
}

int check(int n) {
    return n > 0 && (n & (n - 1)) == 0;
}

int reverse(int N, int n) {
    int j, p = 0;
    for(j = 1; j <= int_log2(N); j++) {
        if(n & (1 << (int_log2(N) - j)))
            p |= 1 << (j - 1);
    }
    return p;
}

void ordina(complex_t* f1, int N) {
    complex_t* f2 = (complex_t*)malloc(N * sizeof(complex_t));
    for(int i = 0; i < N; i++)
        f2[i] = f1[reverse(N, i)];
    for(int j = 0; j < N; j++)
        f1[j] = f2[j];
    free(f2);
}

void transform(complex_t* f, int N) {
    ordina(f, N);
    complex_t* W = (complex_t*)malloc(N / 2 * sizeof(complex_t));
    
    for(int i = 0; i < N / 2; i++)
        W[i] = complex_exp(-2.0 * PI * i / N);
    
    int n = 1;
    int a = N / 2;
    for(int j = 0; j < int_log2(N); j++) {
        for(int i = 0; i < N; i++) {
            if(!(i & n)) {
                complex_t temp = f[i];
                complex_t Temp = complex_mul(W[(i * a) % (n * a)], f[i + n]);
                f[i] = complex_add(temp, Temp);
                f[i + n] = complex_sub(temp, Temp);
            }
        }
        n *= 2;
        a = a / 2;
    }
    free(W);
}

void FFT(complex_t* array, int dimension, double sampling_step) {
    transform(array, dimension);
    for(int i = 0; i < dimension; i++) {
        array[i].real *= sampling_step;
        array[i].imag *= sampling_step;
    }
}
