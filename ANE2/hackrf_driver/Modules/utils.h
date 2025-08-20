/**
 * @file utils.h
 * @author David Ramírez Betancourth
 * @brief Utility functions and macros
 */

#ifndef UTILS_H
#define UTILS_H

#include <complex.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#include "datatypes.h"

#define TO_MHZ(x) ((x) / 1000000.0)

// La función ahora devuelve un puntero a la nueva estructura.
signal_iq_t* load_cs8(const char* filename);

//to implement

//void get_capture(ParamsCapture_t* params);

#endif // UTILS_H