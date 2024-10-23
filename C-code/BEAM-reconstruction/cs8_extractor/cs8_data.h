#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

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



void separate_iq(const uint8_t *raw_data, size_t num_samples, int8_t **I, int8_t **Q) {
    *I = (int8_t *)malloc(num_samples * sizeof(int8_t));
    *Q = (int8_t *)malloc(num_samples * sizeof(int8_t));

    if (!(*I) || !(*Q)) {
        printf("Error: Unable to allocate memory for I and Q vectors\n");
        if (*I) free(*I);
        if (*Q) free(*Q);
        *I = *Q = NULL;  // Avoid dangling pointers
        return;
    }

    for (size_t i = 0; i < num_samples; i++) {
        (*I)[i] = (int8_t)raw_data[2 * i];
        (*Q)[i] = (int8_t)raw_data[2 * i + 1];
    }
}
