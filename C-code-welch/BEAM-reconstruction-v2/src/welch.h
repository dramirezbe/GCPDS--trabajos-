#ifndef WELCH_H
#define WELCH_H

#include <stddef.h>   // Para size_t
#include <complex.h>  // Para el tipo double complex

#define PI 3.14159265358979323846

// Generadores de ventanas
void generate_hamming_window(double* window, int segment_length);

void welch_psd_complex(complex double* signal, size_t N_signal, double fs, 
                       int segment_length, double overlap, double* f_out, double* P_welch_out);

#endif // WELCH_H
