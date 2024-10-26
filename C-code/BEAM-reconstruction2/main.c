#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "src/BER/BER.h"
#include "src/my_fft/my_fft.h"
#include "src/process_cs8/process_cs8.h"

int main() {

    const char *file_path = "C:\\Samples-Hack-RF\\88108.cs8";
    size_t file_size = 0;
    
    // Inicializar los punteros para datos I y Q
    int8_t *I = NULL;
    int8_t *Q = NULL;

    // Llamar a process_data para separar los datos I y Q
    process_data(file_path, &file_size, 0, &I, &Q);
    if (file_size == 0 || !I || !Q) {
        fprintf(stderr, "Error: Fallo en el procesamiento de datos I/Q.\n");
        free(I);
        free(Q);
        return EXIT_FAILURE;
    }
    printf("\nProceso de datos completo.\n");

    // Definir número de muestras y calcular la siguiente potencia de 2
    size_t num_samples = file_size / 2;
    int N = next_power_of_two((int)num_samples);

    // Convertir los vectores I y Q en un vector de números complejos
    Complex* signal = convert_to_complex((uint8_t*)I, (uint8_t*)Q, num_samples);
    if (!signal) {
        fprintf(stderr, "Error: Fallo al convertir los datos en complejos.\n");
        free(I);
        free(Q);
        return EXIT_FAILURE;
    }
    printf("\nConversión a señal compleja completada.\n");

    // Liberar los vectores I y Q después de convertirlos
    free(I);
    free(Q);

    double fs = 20000000.0;  // Frecuencia de muestreo (Hz)
    int forward = 1;

    // Reservar memoria para el vector de frecuencias
    double* freq = (double*)malloc((N / 2) * sizeof(double));
    if (freq == NULL) {
        fprintf(stderr, "Error: No se pudo reservar memoria para el vector de frecuencias.\n");
        free(signal);
        return EXIT_FAILURE;
    }

    // Calcular la FFT
    fft(signal, N, forward);
    printf("\nCálculo de FFT completado.\n");

    // Generar el vector de frecuencias
    generate_frequency_vector(freq, N, fs);
    printf("\nGeneración del vector de frecuencias completada.\n");

    // Imprimir los primeros 20 valores de la FFT con sus frecuencias
    printf("Primeros 20 valores de FFT y sus frecuencias:\n");
    for (int i = 0; i < 20 && i < N / 2; i++) {
        printf("Frecuencia: %.2f Hz, FFT: %.2f + %.2fi\n", 
               freq[i], signal[i].real, signal[i].imag);
    }

    printf("Presione Enter para continuar...\n");
    getchar();

    // Liberar memoria asignada
    free(signal);
    free(freq);

    return EXIT_SUCCESS;
}
