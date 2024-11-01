#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <fftw3.h>
#include <math.h>

#include "src/welch.h"
#include "src/cs8_to_iq.h"

#define FS 20000000.0         // Frecuencia de muestreo
#define SEGMENT_SIZE 1024    // Tamaño del segmento
#define OVERLAP 0.5          // Solapamiento de segmentos

int main() {
    size_t num_samples;
    const char* cs8_path = "/home/javastral/Desktop/HackF/88108.cs8"; 

    // Cargar datos IQ desde el archivo .cs8
    complex double* IQ_data = cargar_cs8(cs8_path, &num_samples);
    if (IQ_data == NULL) {
        fprintf(stderr, "Error al cargar los datos IQ desde el archivo .cs8\n");
        return EXIT_FAILURE;
    }

    // Mostrar los primeros valores de IQ_data
    for (int i = 0; i < 10; i++) {
        printf("IQ_data[%d] = %f + %fj\n", i, creal(IQ_data[i]), cimag(IQ_data[i]));
    }

    // Preparar variables para almacenar la salida de PSD y frecuencias
    size_t psd_size = SEGMENT_SIZE;
    double* psd_out = (double*) malloc(psd_size * sizeof(double));
    double* f_out = (double*) malloc(psd_size * sizeof(double));
    if (psd_out == NULL || f_out == NULL) {
        fprintf(stderr, "Error al asignar memoria para PSD o frecuencias\n");
        free(IQ_data);
        return EXIT_FAILURE;
    }

    // Calcular la PSD usando el método de Welch
    welch_psd_complex(IQ_data, num_samples, FS, SEGMENT_SIZE, OVERLAP, f_out, psd_out);

    // Mostrar los primeros valores de la PSD calculada
    printf("Primeros valores de la PSD:\n");
    for (size_t i = 0; i < 10 && i < psd_size; i++) {
        printf("Frecuencia: %f Hz, PSD: %f dB\n", f_out[i], psd_out[i]);
    }

    // Guardar los resultados en un archivo CSV
    FILE* file = fopen("psd_output.csv", "w");
    if (file == NULL) {
        perror("Error al abrir el archivo CSV");
        free(psd_out);
        free(f_out);
        free(IQ_data);
        return EXIT_FAILURE;
    }

    fprintf(file, "Frecuencia,PSD\n");
    for (size_t i = 0; i < psd_size; i++) {
        fprintf(file, "%f,%f\n", f_out[i], psd_out[i]);
    }
    fclose(file);

    printf("PSD guardada en 'psd_output.csv'\n");

    // Liberar memoria
    free(psd_out);
    free(f_out);
    free(IQ_data);

    return EXIT_SUCCESS;
}

