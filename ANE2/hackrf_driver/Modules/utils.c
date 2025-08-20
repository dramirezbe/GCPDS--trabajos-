/**
 * @file utils.c
 * @author David Ramírez Betancourth
 */

#include "utils.h"

signal_iq_t* load_cs8(const char* filename) {
    FILE* file = fopen(filename, "rb");
    if (!file) {
        perror("Error: No se pudo abrir el archivo de datos CS8");
        return NULL;
    }

    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    rewind(file);

    if (file_size % 2 != 0) {
        fprintf(stderr, "Error: Tamaño del archivo inválido. Debe ser múltiplo de 2.\n");
        fclose(file);
        return NULL;
    }

    
    signal_iq_t* signal_data = (signal_iq_t*)malloc(sizeof(signal_iq_t));
    if (!signal_data) {
        perror("Error: No se pudo reservar memoria para la estructura signal_iq_t");
        fclose(file);
        return NULL;
    }

    signal_data->n_signal = file_size / 2;
    int8_t* raw_data = (int8_t*)malloc(file_size);
    signal_data->signal_iq = (complex double*)malloc(signal_data->n_signal * sizeof(complex double));

    if (!raw_data || !signal_data->signal_iq) {
        perror("Error: No se pudo reservar memoria para los datos IQ");
        free(raw_data);
        free(signal_data->signal_iq);
        free(signal_data);
        fclose(file);
        return NULL;
    }

    if (fread(raw_data, 1, (size_t)file_size, file) != (size_t)file_size) {
        perror("Error: Lectura incompleta del archivo");
        free(raw_data);
        free(signal_data->signal_iq);
        free(signal_data);
        fclose(file);
        return NULL;
    }

    for (size_t i = 0; i < signal_data->n_signal; i++) {
        signal_data->signal_iq[i] = raw_data[2 * i] + raw_data[2 * i + 1] * I;
    }

    free(raw_data);
    fclose(file);

    return signal_data;
}