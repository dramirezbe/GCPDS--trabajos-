#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>


#include "src/BER/BER.h"
#include "src/my_fft/my_fft.h"
#include "src/process_cs8/process_cs8.h"

int main() {

    const char *file_path = "C:\\Samples-Hack-RF\\88108.cs8";
    size_t file_size = 0;
    
    // Separar los datos I y Q
    int8_t *I = NULL;
    int8_t *Q = NULL;



    process_data(file_path, &file_size, 0, &I, &Q); //arroja los vectores I y Q uint_8

    printf("\nProcess data, Done");

    size_t num_samples = file_size / 2;
    int N = next_power_of_two((int)num_samples);

    // Convertir los vectores I y Q en un vector de números complejos
    Complex* signal = convert_to_complex((uint8_t*)I, (uint8_t*)Q, num_samples);

    // Reservar memoria para el vector de frecuencias
    double* freq = (double*)malloc((N / 2) * sizeof(double));
    if (freq == NULL) {
        fprintf(stderr, "Error al reservar memoria para las frecuencias.\n");
        free(signal);
        exit(EXIT_FAILURE);
    }

    double fs = 20000000.0;  // Frecuencia de muestreo (Hz)
    int forward = 1;

    double* freq = (double*)malloc((N / 2) * sizeof(double));  // Sólo mitad de las frecuencias

    // Calcular la FFT
    fft(signal, N, forward);
    printf("\nFFT, Done");




    // Generar el vector de frecuencias
    generate_frequency_vector(freq, N, fs);

    //primeros 20 valores
    // Imprimir los primeros 10 valores de la FFT con sus frecuencias
    printf("Primeros 10 valores de FFT y sus frecuencias:\n");
    for (int i = 0; i < 20 && i < N / 2; i++) {
        printf("Frecuencia: %.2f Hz, FFT: %.2f + %.2fi\n", 
               freq[i], signal[i].real, signal[i].imag);
    }

    printf("Waiting user...\n");
    getchar();


    printf("\nFreq vector, Done");

    // Abrir un archivo para guardar los resultados
    FILE* fp = fopen("fft_output.csv", "w");
    if (fp == NULL) {
        perror("Error al abrir el archivo");
        return 1;
    }

    // Escribir los encabezados
    fprintf(fp, "frecuencia,magnitud\n");

    // Guardar frecuencias y magnitudes en el archivo (sólo la mitad útil del espectro)
    for (int i = 0; i < N / 2; i++) {
        double magnitude = complex_magnitude(signal[i]);
        fprintf(fp, "%f,%f\n", freq[i], magnitude);
    }

    // Cerrar el archivo y liberar memoria
    fclose(fp);
    free(signal);
    free(freq);

    printf("Datos exportados a fft_output.csv\n");

    return 0;
}
