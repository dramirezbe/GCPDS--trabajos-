#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <complex.h>
#include "cs8_full.h"

float _Complex* process_raw_data(const char *file_path, size_t *num_samples) {
    FILE *file = fopen(file_path, "rb");
    if (!file) {
        printf("Error: Unable to open file %s\n", file_path);
        return NULL;
    }

    fseek(file, 0, SEEK_END);
    size_t file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    if (file_size == 0) {
        printf("Error: File is empty.\n");
        fclose(file);
        return NULL;
    }

    uint8_t *raw_data = (uint8_t *)malloc(file_size);
    if (!raw_data) {
        printf("Error: Unable to allocate memory for raw data\n");
        fclose(file);
        return NULL;
    }

    size_t read_size = fread(raw_data, sizeof(uint8_t), file_size, file);
    fclose(file);
    if (read_size != file_size) {
        printf("Error: Incomplete read. Expected %zu bytes but got %zu\n", file_size, read_size);
        free(raw_data);
        return NULL;
    }

    *num_samples = file_size / 2;
    int8_t *phase = (int8_t *)malloc(*num_samples * sizeof(int8_t));
    int8_t *quadrature = (int8_t *)malloc(*num_samples * sizeof(int8_t));

    if (!phase || !quadrature) {
        printf("Error: Unable to allocate memory for phase and quadrature vectors\n");
        free(raw_data);
        free(phase);
        free(quadrature);
        return NULL;
    }

    for (size_t i = 0; i < *num_samples; i++) {
        phase[i] = (int8_t)raw_data[2 * i];
        quadrature[i] = (int8_t)raw_data[2 * i + 1];
    }
    free(raw_data);

    float _Complex *complex_vector = (float _Complex *)malloc(*num_samples * sizeof(float _Complex));
    if (!complex_vector) {
        printf("Error: Unable to allocate memory for the complex vector\n");
        free(phase);
        free(quadrature);
        return NULL;
    }

    for (size_t i = 0; i < *num_samples; i++) {
        complex_vector[i] = phase[i] + quadrature[i] * _Complex_I;  // I + jQ
    }

    free(phase);
    free(quadrature);

    return complex_vector;
}
