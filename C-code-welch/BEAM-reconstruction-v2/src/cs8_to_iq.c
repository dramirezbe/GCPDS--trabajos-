#include "cs8_to_iq.h"
#include <stdio.h>
#include <stdlib.h>

// Función para cargar datos IQ desde un archivo binario con formato CS8
complex double* cargar_cs8(const char* filename, size_t* num_samples) {
    // Abrir el archivo en modo binario
    FILE* file = fopen(filename, "rb");
    if (!file) {
        perror("No se pudo abrir el archivo");
        return NULL;
    }

    // Determinar el tamaño del archivo
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    rewind(file);

    // Cada muestra tiene dos valores de 8 bits (I y Q)
    *num_samples = file_size / 2;

    // Reservar memoria para los datos binarios y los complejos
    int8_t* raw_data = (int8_t*)malloc(file_size);
    complex double* IQ_data = (complex double*)malloc(*num_samples * sizeof(complex double));

    if (!raw_data || !IQ_data) {
        perror("No se pudo reservar memoria");
        free(raw_data);
        free(IQ_data);
        fclose(file);
        return NULL;
    }

    // Leer todo el archivo de una sola vez
    if (fread(raw_data, 1, (size_t)file_size, file) != (size_t)file_size) {

        perror("Error leyendo el archivo completo");
        free(raw_data);
        free(IQ_data);
        fclose(file);
        return NULL;
    }

    // Convertir los datos binarios en números complejos
    for (size_t i = 0; i < *num_samples; i++) {
        IQ_data[i] = raw_data[2 * i] + raw_data[2 * i + 1] * I;
    }

    // Liberar la memoria de los datos binarios y cerrar el archivo
    free(raw_data);
    fclose(file);

    return IQ_data;
}