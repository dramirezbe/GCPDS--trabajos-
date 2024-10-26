
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include "process_cs8.h"
#include "../my_complex/my_complex.h"

// Definir constantes de error
#define SUCCESS 0
#define ERROR_OPEN_FILE -1
#define ERROR_EMPTY_FILE -2
#define ERROR_MEMORY_ALLOCATION -3
#define ERROR_INCOMPLETE_READ -4
#define ERROR_INVALID_PARAMETERS -5

Complex* process_data(const char *file_path, size_t *file_size, size_t num_samples) {
    if (!file_path || !file_size) {
        printf("Error: Parámetros inválidos\n");
        return NULL;
    }

    FILE *file = fopen(file_path, "rb");
    if (!file) {
        printf("Error: No se pudo abrir el archivo %s\n", file_path);
        return NULL;
    }
    printf("Archivo abierto...\n");

    fseek(file, 0, SEEK_END);
    *file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    if (*file_size == 0) {
        printf("Error: El archivo está vacío.\n");
        fclose(file);
        return NULL;
    }

    uint8_t *raw_data = (uint8_t *)malloc(*file_size);
    if (!raw_data) {
        printf("Error: No se pudo asignar memoria para los datos brutos\n");
        fclose(file);
        return NULL;
    }

    size_t read_size = fread(raw_data, sizeof(uint8_t), *file_size, file);
    if (read_size != *file_size) {
        printf("Error: Lectura incompleta. Se esperaban %zu bytes pero se leyeron %zu\n", *file_size, read_size);
        free(raw_data);
        fclose(file);
        return NULL;
    }

    fclose(file);

    uint8_t *I = (uint8_t *)malloc(num_samples * sizeof(uint8_t));
    uint8_t *Q = (uint8_t *)malloc(num_samples * sizeof(uint8_t));

    if (!I || !Q) {
        printf("Error: No se pudo asignar memoria para I o Q\n");
        free(raw_data);
        if (I) free(I);
        if (Q) free(Q);
        return NULL;
    }

    // Separar los vectores I y Q
    for (size_t i = 0; i < num_samples; i++) {
        if (2 * i + 1 >= *file_size) {
            printf("Error: Índice fuera de los límites de los datos\n");
            free(raw_data);
            free(I);
            free(Q);
            return NULL;
        }
        I[i] = (int8_t)raw_data[2 * i];       // Componente I
        Q[i] = (int8_t)raw_data[2 * i + 1];   // Componente Q
    }

    for (int i = 0; i < 10; i++) {
        printf("I[%d] = %d, Q[%d] = %d\n", i, I[i], i, Q[i]);
    }

    // Convertir a complejo
    Complex* signal = convert_to_complex((uint8_t*)I, (uint8_t*)Q, num_samples);

    // Liberar la memoria de raw_data y de los vectores I y Q
    free(raw_data);
    free(I);
    free(Q);

    return signal;
}
