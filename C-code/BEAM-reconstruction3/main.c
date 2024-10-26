#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "src/process_cs8/process_cs8.h"
#include "src/my_complex/my_complex.h"


int main() {

    const char *file_path = "C:\\Samples-Hack-RF\\88108.cs8";
    size_t file_size = 0;

    // Definir número de muestras y calcular la siguiente potencia de 2
    size_t num_samples = file_size / 2;
    

    Complex *signal = process_data(file_path, &file_size, num_samples);
    printf("process data, Done");

    if (signal == NULL) {
        printf("Error al procesar los datos\n");
        return -1;
    }

    for (size_t i = 0; i < num_samples; i++) {
        printf("Sample %zu: I=%f, Q=%f\n", i, signal[i].real, signal[i].imag);
    }

    


    // Liberar la memoria de `signal`
    free(signal);

    return 0;
}