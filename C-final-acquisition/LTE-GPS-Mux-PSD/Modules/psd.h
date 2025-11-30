/**
 * @file Modules/psd.h
 */

#ifndef PSD_H
#define PSD_H

#include "datatypes.h"
#include <stdint.h>

signal_iq_t* load_iq_from_buffer(const int8_t* buffer, size_t buffer_size);
void free_signal_iq(signal_iq_t* signal);
void execute_welch_psd(signal_iq_t* signal_data, const PsdConfig_t* config, double* f_out, double* p_out);

#endif