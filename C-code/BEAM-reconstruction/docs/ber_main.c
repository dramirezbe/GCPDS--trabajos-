#include <stdio.h>
# include <math.h>
#include "ber.h"

int main() {
    double SNR_dB = -30.0;  // SNR en decibelios
    double SNR = pow(10.0, SNR_dB / 10.0);  // Convertir de dB a valor lineal

    // Calcular BER
    double ber = calculate_BER_from_snr(SNR);

    // Imprimir resultado
    printf("BER: %.6e\n", ber);

    return 0;
}
