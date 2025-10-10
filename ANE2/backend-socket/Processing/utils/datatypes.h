/**
 * @file datatypes.h
 * @brief Contains all shared data structures and type definitions for the application.
 */

#ifndef DATATYPES_H
#define DATATYPES_H

// Enum defining the different types of services the module can handle.
typedef enum {
    ACQUISITION_SERVICE,
    DEMODULATION_SERVICE,
    SYSTEM_STATUS_SERVICE,
    SYSTEM_SUBSCRIBE_SERVICE,
    UNKNOWN_SERVICE
} ServiceType_t;

// Structure to hold the parameters for a data acquisition request.
typedef struct {
    char *initial_frequency_hz;
    char *final_frequency_hz;
    char *resolution_bandwidth_hz;
    char *task_duration_s;
} AcquisitionRequest_t;

// --- MODIFIED STRUCTURE ---
// Structure to hold the results of a data acquisition.
typedef struct {
    int num_psd_values;                 // The number of elements in the array below
    double *power_spectral_density;     // Pointer to a dynamically allocated array of PSD values
    double initial_frequency_hz;
    double final_frequency_hz;
} AcquisitionResult_t;

#endif // DATATYPES_H