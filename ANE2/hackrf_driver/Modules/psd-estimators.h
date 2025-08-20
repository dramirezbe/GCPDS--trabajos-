/**
 * @file psd-estimators.h
 * @author David Ramírez Betancourth
 */
#ifndef PSD_ESTIMATORS_H
#define PSD_ESTIMATORS_H

#include <complex.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <fftw3.h>

#include "datatypes.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void generate_window(PsdWindowType_t window_type, double* window_buffer, int window_length);

void execute_psd(signal_iq_t* signal_data, const PsdConfig_t* config, double* f_out, double* p_out);

#endif //PSD_ESTIMATORS_H