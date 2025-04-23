#include <stdio.h>
#include <stdlib.h>
#include <complex.h>

#include "src/cs8_to_iq.h"

int main() {
    size_t num_samples;
    const char* cs8_path = "/home/javastral/Documents/HackF/88108.cs8"; 

    complex float* IQ_data = cargar_cs8(cs8_path, &num_samples);

    for (int i = 0; i < 100; i++) {
        printf("IQ_data[%d] = %f + %fj\n", i, creal(IQ_data[i]), cimag(IQ_data[i]));
    }

    free(IQ_data);

    return EXIT_SUCCESS;
}