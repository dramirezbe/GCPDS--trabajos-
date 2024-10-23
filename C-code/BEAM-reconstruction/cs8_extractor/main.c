#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
# include "cs8_data.h"


int main(int argc, char *argv[]) {
    const char *file_path = "C:\\Samples-Hack-RF\\88108.cs8"; // Default file path
    if (argc > 1) {
        file_path = argv[1]; // Allow file path to be passed as an argument
    }
    
    size_t file_size;
    uint8_t *raw_data = load_raw_data(file_path, &file_size);
    if (!raw_data) {
        return 1;  // Exit if file cannot be loaded
    }

    size_t num_samples = file_size / 2;
    int8_t *I = NULL, *Q = NULL;

    separate_iq(raw_data, num_samples, &I, &Q);
    if (!I || !Q) {
        free(raw_data);
        return 1;  // Exit if memory allocation for I/Q fails
    }

    printf("File loaded successfully. File size: %zu bytes\n", file_size);
    printf("I/Q data separated successfully. Number of samples: %zu\n", num_samples);

    // Print the first 10 samples as a test
    for (int i = 0; i < 10; i++) {
        printf("Sample %d: I = %d, Q = %d\n", i, I[i], Q[i]);
    }

    printf("Waiting user..........");
    getchar();

    // Free allocated memory
    free(raw_data);
    free(I);
    free(Q);

    return ;
}