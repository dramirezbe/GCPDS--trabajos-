#ifndef PROCESS_CS8
#define PROCESS_CS8

#include <stdint.h>
#include <complex.h>
#include <stddef.h>

// Declaración de la función para cargar datos IQ desde un archivo binario
complex double* cargar_cs8(const char* filename, size_t* num_samples);

#endif  // PROCESS_CS8