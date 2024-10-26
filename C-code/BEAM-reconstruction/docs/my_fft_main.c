// main.c
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "my_fft.h"

int main() {
    int original_N = 1024;   // Tamaño más grande para apreciarlo mejor en el gráfico
    int N = next_power_of_two(original_N);
    double fs = 1000.0;  // Frecuencia de muestreo (Hz)

    // Reservar memoria para la señal y las frecuencias
    Complex* signal = (Complex*)malloc(N * sizeof(Complex));
    double* freq = (double*)malloc((N / 2) * sizeof(double));  // Sólo mitad de las frecuencias

    // Generar señal sintética: suma de dos senos de 50 Hz y 120 Hz
    for (int i = 0; i < original_N; i++) {
        signal[i].real = sin(2 * PI * 50 * i / fs) + 0.5 * sin(2 * PI * 120 * i / fs);
        signal[i].imag = 0.0;
    }
    for (int i = original_N; i < N; i++) {
        signal[i].real = 0.0;
        signal[i].imag = 0.0;
    }

    // Calcular la FFT
    fft(signal, N, 1);

    // Generar el vector de frecuencias
    generate_frequency_vector(freq, N, fs);

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
