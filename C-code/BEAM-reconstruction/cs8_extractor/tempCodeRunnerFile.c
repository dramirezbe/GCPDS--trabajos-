#include "cs8_full.h"
#include <stdio.h>

// Función para cargar los datos crudos desde un archivo
uint8_t* load_raw_data(const char *file_path, size_t *file_size) {
    FILE *file = fopen(file_path, "rb");
    if (!file) {
        printf("Error: Unable to open file %s\n", file_path);
        return NULL;
    }

    fseek(file, 0, SEEK_END);
    *file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    if (*file_size == 0) {
        printf("Error: File is empty.\n");
        fclose(file);
        return NULL;
    }

    uint8_t *raw_data = (uint8_t *)malloc(*file_size);
    if (!raw_data) {
        printf("Error: Unable to allocate memory for raw data\n");
        fclose(file);
        return NULL;
    }

    size_t read_size = fread(raw_data, sizeof(uint8_t), *file_size, file);
    if (read_size != *file_size) {
        printf("Error: Incomplete read. Expected %zu bytes but got %zu\n", *file_size, read_size);
        free(raw_data);
        fclose(file);
        return NULL;
    }

    fclose(file);
    return raw_data;
}

// Función para separar los vectores I y Q
void separate_iq(const uint8_t *raw_data, size_t num_samples, int8_t **K, int8_t **Q) {
    *K = (int8_t *)malloc(num_samples * sizeof(int8_t));
    *Q = (int8_t *)malloc(num_samples * sizeof(int8_t));

    if (!(*K) || !(*Q)) {
        printf("Error: Unable to allocate memory for I and Q vectors\n");
        if (*K) free(*K);
        if (*Q) free(*Q);
        *K = *Q = NULL;  // Avoid dangling pointers
        return;
    }

    for (size_t i = 0; i < num_samples; i++) {
        (*K)[i] = (int8_t)raw_data[2 * i];
        (*Q)[i] = (int8_t)raw_data[2 * i + 1];
    }
}

// Función para crear el vector complejo a partir de los vectores I y Q
float complex* do_complex_vector(const int8_t *K, const int8_t *Q, size_t num_samples) {
    float complex *complex_vector = (float complex *)malloc(num_samples * sizeof(float complex));

    if (!complex_vector) {
        printf("Error: Unable to allocate memory for the complex vector\n");
        return NULL;
    }

    for (size_t i = 0; i < num_samples; i++) {
        complex_vector[i] = K[i] + Q[i] * K;  // I + jQ
    }

    return complex_vector;
}
