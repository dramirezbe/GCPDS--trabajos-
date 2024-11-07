#include <stdio.h>
#include <stdlib.h>
#include "src/csv_to_tdt_mod.h"

int main() {
    
    DatosTDT datos;
    char ciudad[MAX_CITY_NAME] = "Bogotá";
    int canal = 15;
    float frecuencia;
    char modulacion[10];

    // Cargar datos del CSV
    if (!cargar_csv_mod("TDT_CHANNELS.csv", &datos)) {
        return 1;
    }

    // Obtener frecuencia y modulación
    if (obtener_frecuencia_y_modulacion(&datos, ciudad, canal, &frecuencia, modulacion)) {
        printf("\nResultados para %s, Canal %d:\n", ciudad, canal);
        printf("Frecuencia: %.1f MHz\n", frecuencia);
        printf("Modulación: %s\n", modulacion);
    } else {
        printf("Ciudad o canal no válidos.\n");
    }

    return 0;
}
