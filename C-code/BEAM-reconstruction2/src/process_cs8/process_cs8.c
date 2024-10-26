#define _GNU_SOURCE

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

int process_data(const char *file_path, size_t *file_size, size_t num_samples, int8_t **I, int8_t **Q) {
    if (!file_path || !file_size || !I || !Q) {
        printf("Error: Parámetros inválidos\n");
        return ERROR_INVALID_PARAMETERS;
    }

    FILE *file = fopen(file_path, "rb");
    if (!file) {
        printf("Error: No se pudo abrir el archivo %s\n", file_path);
        return ERROR_OPEN_FILE;
    }

    fseek(file, 0, SEEK_END);
    *file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    if (*file_size == 0) {
        printf("Error: El archivo está vacío.\n");
        fclose(file);
        return ERROR_EMPTY_FILE;
    }

    uint8_t *raw_data = (uint8_t *)malloc(*file_size);
    if (!raw_data) {
        printf("Error: No se pudo asignar memoria para los datos brutos\n");
        fclose(file);
        return ERROR_MEMORY_ALLOCATION;
    }

    size_t read_size = fread(raw_data, sizeof(uint8_t), *file_size, file);
    if (read_size != *file_size) {
        printf("Error: Lectura incompleta. Se esperaban %zu bytes pero se leyeron %zu\n", *file_size, read_size);
        free(raw_data);
        fclose(file);
        return ERROR_INCOMPLETE_READ;
    }

    fclose(file);

    *I = (int8_t *)malloc(num_samples * sizeof(int8_t));
    *Q = (int8_t *)malloc(num_samples * sizeof(int8_t));
    if (!*I || !*Q) {
        printf("Error: No se pudo asignar memoria para I o Q\n");
        free(raw_data);
        if (*I) free(*I);
        if (*Q) free(*Q);
        return ERROR_MEMORY_ALLOCATION;
    }

    // Separar los vectores I y Q
    for (size_t i = 0; i < num_samples; i++) {
        if (2 * i + 1 >= *file_size) {
            printf("Error: Índice fuera de los límites de los datos\n");
            free(raw_data);
            free(*I);
            free(*Q);
            return ERROR_INCOMPLETE_READ;
        }
        (*I)[i] = (int8_t)raw_data[2 * i];       // Componente I
        (*Q)[i] = (int8_t)raw_data[2 * i + 1];   // Componente Q
    }

    // Liberar la memoria de raw_data
    free(raw_data);

    return SUCCESS;
}
