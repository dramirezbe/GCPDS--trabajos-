#define _GNU_SOURCE

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include "my_functions.h"

#define PI 3.1415926535897932384

void process_data(const char *file_path, size_t *file_size, size_t num_samples, int8_t **I, int8_t **Q) {
    FILE *file = fopen(file_path, "rb");
    if (!file) {
        printf("Error: Unable to open file %s\n", file_path);
        return;
    }

    fseek(file, 0, SEEK_END);
    *file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    if (*file_size == 0) {
        printf("Error: File is empty.\n");
        fclose(file);
        return;
    }

    uint8_t *raw_data = (uint8_t *)malloc(*file_size);
    if (!raw_data) {
        printf("Error: Unable to allocate memory for raw data\n");
        fclose(file);
        return;
    }

    size_t read_size = fread(raw_data, sizeof(uint8_t), *file_size, file);
    if (read_size != *file_size) {
        printf("Error: Incomplete read. Expected %zu bytes but got %zu\n", *file_size, read_size);
        free(raw_data);
        fclose(file);
        return;
    }

    fclose(file);

    *I = (int8_t *)malloc(num_samples * sizeof(int8_t));
    *Q = (int8_t *)malloc(num_samples * sizeof(int8_t));
    if (!*I || !*Q) {
        printf("Error: Unable to allocate memory for I or Q\n");
        free(raw_data);
        if (*I) free(*I);
        if (*Q) free(*Q);
        return;
    }

    // Separar los vectores I y Q
    for (size_t i = 0; i < num_samples; i++) {
        (*I)[i] = (int8_t)raw_data[2 * i];       // Componente I
        (*Q)[i] = (int8_t)raw_data[2 * i + 1];   // Componente Q
    }

    // Liberar la memoria de raw_data
    free(raw_data);
}


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
    // Verificar si N es una potencia de 2
    if (!check(dimension)) {
        // Encontrar la siguiente potencia de 2 más cercana
        int new_dimension = pow(2, int_log2(dimension) + 1);
        
        // Crear un nuevo array con la nueva dimensión
        complex_t* padded_array = (complex_t*)malloc(new_dimension * sizeof(complex_t));
        
        // Copiar los elementos existentes del array original
        for (int i = 0; i < dimension; i++) {
            padded_array[i] = array[i];
        }
        
        // Rellenar el resto con ceros
        for (int i = dimension; i < new_dimension; i++) {
            padded_array[i] = make_complex(0.0, 0.0);
        }
        
        // Reemplazar el array original con el nuevo array
        array = padded_array;
        dimension = new_dimension;
    }
    
    // Continuar con la transformada
    transform(array, dimension);
    
    // Escalar los resultados por el paso de muestreo
    for (int i = 0; i < dimension; i++) {
        array[i].real *= sampling_step;
        array[i].imag *= sampling_step;
    }
}
