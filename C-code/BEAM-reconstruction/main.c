#include <stdio.h>
# include <stdlib.h>
#include "my_functions.h"


int main() {

    const char *file_path = "C:\\Samples-Hack-RF\\88108.cs8";
    size_t file_size = 0;

    
    // Separar los datos I y Q
    int8_t *I = NULL;
    int8_t *Q = NULL;

    process_data(file_path, &file_size, 0, &I, &Q);

    size_t num_samples = file_size / 2;

    // Mostrar las primeras 10 muestras de I y Q
    printf("Primeras 10 muestras de I y Q:\n");
    for (size_t i = 0; i < 10 && i < num_samples; i++) {
        printf("Muestra %zu: I = %d, Q = %d\n", i, I[i], Q[i]);
    }


    // Especifica la dimensión del array (debe ser potencia de 2)
    int n = file_size; // Por ejemplo, 8 elementos (potencia de 2)
    
    // Especifica el paso de muestreo
    double d = 10; // Ejemplo de paso de muestreo
    
    // Inicialización del array con valores de ejemplo (parte real e imaginaria)
    // Especifica la dimensión del array (debe ser potencia de 2)


    // Crear el array de complejos usando los vectores I y Q
    complex_t *vec = (complex_t *)malloc(n * sizeof(complex_t));

    for (size_t i = 0; i < n; i++) {
        vec[i] = make_complex((double)I[i], (double)Q[i]);
    }
    
    // Ejecuta la FFT
    FFT(vec, n, d);

    for(int j = 0; j < n; j++) {
        if(complex_imag(vec[j]) < 0)
            printf("%.2f - %.2fi\n", complex_real(vec[j]), -complex_imag(vec[j]));
        else
            printf("%.2f + %.2fi\n", complex_real(vec[j]), complex_imag(vec[j]));
    }

    printf("Waiting user...");
    getchar();

    free(I);
    free(Q);

    return 0;
}
