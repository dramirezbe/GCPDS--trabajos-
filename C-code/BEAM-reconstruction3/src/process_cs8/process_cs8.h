#ifndef PROCESS_CS8_H
#define PROCESS_CS8_H

#include <stdint.h>
#include <stdlib.h>
#include <stddef.h>
#include "../my_complex/my_complex.h"

// Definición de códigos de error
#define SUCCESS 0
#define ERROR_OPEN_FILE -1
#define ERROR_EMPTY_FILE -2
#define ERROR_MEMORY_ALLOCATION -3
#define ERROR_INCOMPLETE_READ -4
#define ERROR_INVALID_PARAMETERS -5

/**
 * @brief Procesa los datos de un archivo binario conteniendo muestras I/Q en formato CS8.
 *
 * @param file_path Ruta al archivo binario a leer.
 * @param file_size Puntero a una variable donde se almacenará el tamaño del archivo en bytes.
 * @param num_samples Número de muestras I/Q a extraer.
 * @param I Puntero al array donde se almacenarán las muestras I.
 * @param Q Puntero al array donde se almacenarán las muestras Q.
 * @return Código de error: SUCCESS (0) en caso de éxito o un valor negativo en caso de error.
 */
Complex* process_data(const char *file_path, size_t *file_size, size_t num_samples);


#endif // PROCESS_CS8_H