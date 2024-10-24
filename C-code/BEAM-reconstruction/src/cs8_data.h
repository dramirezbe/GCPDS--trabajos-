#ifndef CS8_DATA_PROCESSING_H
#define CS8_DATA_PROCESSING_H

#include <stdint.h>
#include <stddef.h>

// Función para cargar los datos crudos desde un archivo
uint8_t* load_raw_data(const char *file_path, size_t *file_size);

// Función para separar los vectores I y Q
void separate_iq(const uint8_t *raw_data, size_t num_samples, int8_t **I, int8_t **Q);

#endif // CS8_DATA_PROCESSING_H