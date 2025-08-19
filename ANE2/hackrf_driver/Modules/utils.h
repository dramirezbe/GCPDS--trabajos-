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

#include "psd-estimators.h"

#define TO_MHZ(x) ((x) / 1000000.0)

typedef struct 
{
    char Samples_folder_path[1024];
    char JSON_folder_path[1024];
    char cs8_file_path[1024];
}PathStruct_t;

typedef struct {
    PathStruct_t paths;
    int bw;
    float freq;
}ParamsCapture_t;


complex double* load_cs8(const char* filename, size_t* num_samples);

void fill_path_struct(PathStruct_t* paths);

void capture_sample(ParamsCapture_t* params);

#endif // UTILS_H