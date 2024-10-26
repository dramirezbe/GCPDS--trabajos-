#ifndef PROCESS_CS8
#define PROCESS_CS8

#include <stdint.h>
#include <stddef.h>

void process_data(const char *file_path, size_t *file_size, size_t num_samples, int8_t **I, int8_t **Q);

#endif // PROCESS_CS8
