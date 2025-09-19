/**
 * @file utils.h
 * @author David Ramírez
 * @brief Utility functions and macros.
 */

#ifndef UTILS_H
#define UTILS_H

#include <complex.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#define TO_MHZ(x) ((x) / 1000000.0)

complex double* load_cs8(const char* filename, size_t* num_samples);

#endif // UTILS_H