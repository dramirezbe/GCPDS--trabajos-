#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <fftw3.h>
#include <math.h>

#include "src/welch.h"
#include "src/cs8_to_iq.h"

int main() {
    size_t num_samples;
    const char* cs8_path = "/home/javastral/Desktop/HackF/88108.cs8"; 


    // Cargar datos IQ desde el archivo .cs8
    complex double* IQ_data = cargar_cs8(cs8_path, &num_samples);

    size_t segment_size = 1024;
    double fs = 20000000.0;
    double overlap = 0.5;

    double psd_out[segment_size];
    double f_out[segment_size];

    // Calcular la PSD usando el método de Welch
    welch_psd_complex(IQ_data, num_samples, fs, segment_size, overlap, f_out, psd_out);

    // Guardar los resultados en un archivo CSV
    FILE* file = fopen("psd_output.csv", "w");
    fprintf(file, "Frecuencia,PSD\n");

    for (size_t i = 0; i < segment_size; i++) {
        fprintf(file, "%f,%f\n", f_out[i], psd_out[i]);
    }
    fclose(file);


    // Liberar memoria
    free(IQ_data);

    return EXIT_SUCCESS;
}