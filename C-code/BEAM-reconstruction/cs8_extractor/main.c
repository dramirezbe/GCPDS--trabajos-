#include <stdio.h>
#include <complex.h>
#include "cs8_full.h"

int main() {
    size_t num_samples;
    float _Complex *complex_vector = process_raw_data("C:\\Samples-Hack-RF\\88108.cs8", &num_samples);

    if (!complex_vector) {
        return 1;  // Error handling if loading fails
    }

    for (size_t i = 0; i < num_samples; i++) {
        printf("Sample %zu: %.2f + %.2fj\n", i, crealf(complex_vector[i]), cimagf(complex_vector[i]));
    }

    free(complex_vector);
    return 0;
}
