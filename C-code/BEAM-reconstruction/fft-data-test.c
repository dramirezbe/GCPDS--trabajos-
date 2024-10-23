#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <fftw3.h>

// Function to load raw data from file and return its pointer along with the file size.
uint8_t* load_raw_data(const char *file_path, size_t *file_size) {
    FILE *file = fopen(file_path, "rb");
    fseek(file, 0, SEEK_END);
    *file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    uint8_t *raw_data = (uint8_t *)malloc(*file_size * sizeof(uint8_t));
    fread(raw_data, sizeof(uint8_t), *file_size, file);
    fclose(file);
    return raw_data;
}

// Function to separate I and Q data from the raw data.
void separate_iq(const uint8_t *raw_data, size_t num_samples, int8_t **I, int8_t **Q) {
    *I = (int8_t *)malloc(num_samples * sizeof(int8_t));
    *Q = (int8_t *)malloc(num_samples * sizeof(int8_t));

    for (size_t i = 0; i < num_samples; i++) {
        (*I)[i] = (int8_t)raw_data[2 * i];      // Even index -> I
        (*Q)[i] = (int8_t)raw_data[2 * i + 1];  // Odd index -> Q
    }
}

// Function to perform FFT on I and Q data
void compute_fft(int8_t *I, int8_t *Q, size_t num_samples, fftw_complex **result) {
    // Create complex array
    *result = (fftw_complex*) fftw_malloc(num_samples * sizeof(fftw_complex));

    // Combine I and Q into the complex array
    for (size_t i = 0; i < num_samples; i++) {
        (*result)[i][0] = (double)I[i]; // Real part (I)
        (*result)[i][1] = (double)Q[i]; // Imaginary part (Q)
    }

    // Create FFT plan
    fftw_plan plan = fftw_plan_dft_1d(num_samples, *result, *result, FFTW_FORWARD, FFTW_ESTIMATE);

    // Execute FFT
    fftw_execute(plan);

    // Output results (for demonstration, printing first 10 FFT results)
    for (size_t i = 0; i < 10; i++) {
        printf("FFT Sample %zu: Real = %f, Imaginary = %f\n", i, (*result)[i][0], (*result)[i][1]);
    }

    // Cleanup FFT plan
    fftw_destroy_plan(plan);
}

int main(int argc, char *argv[]) {
    const char *file_path = "C:\\Samples-Hack-RF\\88108.cs8"; // Default file path
    if (argc > 1) {
        file_path = argv[1]; // Allow file path to be passed as an argument
    }
    
    size_t file_size;
    uint8_t *raw_data = load_raw_data(file_path, &file_size);

    size_t num_samples = file_size / 2;
    int8_t *I = NULL, *Q = NULL;

    separate_iq(raw_data, num_samples, &I, &Q);
    printf("File loaded successfully. File size: %zu bytes\n", file_size);
    printf("I/Q data separated successfully. Number of samples: %zu\n", num_samples);

    // Compute FFT of I and Q
    fftw_complex *fft_result = NULL;
    compute_fft(I, Q, num_samples, &fft_result);

    // Wait for user to press ENTER or any key.
    printf("Press ENTER or any key to continue and free memory...");
    getchar();  // Pause the program

    // Free allocated memory
    free(raw_data);
    free(I);
    free(Q);
    fftw_free(fft_result); // Free the FFT result array

    return 0;
}
