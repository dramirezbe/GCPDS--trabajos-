#include <stdio.h>
# include <stdlib.h>
#include "process_cs8.h"


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

    printf("Waiting user...");
    getchar();

    free(I);
    free(Q);

    return 0;
}
