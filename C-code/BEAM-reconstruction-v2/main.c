#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <fftw3.h>
#include <math.h>

#include "src/welch.h"
#include "src/cs8_to_iq.h"

#define FS 2000000.0         // Frecuencia de muestreo
#define SEGMENT_SIZE 1024   // Tamaño del segmento
#define OVERLAP 0.5         // Solapamiento de segmentos

int main() {

    size_t num_samples;
    const char* cs8_path = "/home/javastral/Documents/HackF/88108.cs8"; 

    complex double* IQ_data = cargar_cs8(cs8_path, &num_samples);

    for (int i = 0; i < 10; i++) {
        printf("IQ_data[%d] = %f + %fj\n", i, creal(IQ_data[i]), cimag(IQ_data[i]));
    }
    
    // Calculate the Welch PSD
    double* f_out = malloc(SEGMENT_SIZE * sizeof(double));
    double* psd_out = malloc(SEGMENT_SIZE * sizeof(double));

    welch_psd_complex(IQ_data, num_samples, FS, SEGMENT_SIZE, OVERLAP, f_out, psd_out);

    
    printf("Primeros valores de la PSD:\n");
    for (size_t i = 0; i < 10 && i < SEGMENT_SIZE; i++) {
        printf("Frecuencia: %f Hz, PSD: %f dB\n", f_out[i], 10 * log10(psd_out[i]));
    }


    FILE* file = fopen("psd_output.csv", "w");
    if (file == NULL) {
        perror("Error al abrir el archivo CSV");
        free(psd_out);
        free(f_out);
        free(IQ_data);
        return EXIT_FAILURE;
    }

    fprintf(file, "Frecuencia,PSD\n");
    for (size_t i = -SEGMENT_SIZE; i < SEGMENT_SIZE-1; i++) {
        fprintf(file, "%f,%f\n", f_out[i], psd_out[i]);
    }
    fclose(file);

    printf("PSD guardada en 'psd_output.csv'\n");

    free(psd_out);
    free(f_out);
    free(IQ_data);

    return EXIT_SUCCESS;
}

