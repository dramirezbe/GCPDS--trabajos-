#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "csv_to_tdt_mod.h"

#define MAX_LINE 1024

// Función para dividir una línea en tokens
void split_line(char *line, char *tokens[], int *count, const char *delimiter) {
    char *token = strtok(line, delimiter);
    *count = 0;
    while (token != NULL && *count < MAX_CITIES + 2) {  // +2 para Canal y Frecuencia
        tokens[*count] = token;
        (*count)++;
        token = strtok(NULL, delimiter);
    }
}

// Función para cargar los datos del CSV
int cargar_csv_mod(const char *filename, DatosTDT *datos) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        printf("Error al abrir el archivo %s\n", filename);
        return 0;
    }

    char line[MAX_LINE];
    char *tokens[MAX_CITIES + 2];
    int count;

    // Leer la primera línea (encabezados)
    if (fgets(line, sizeof(line), file)) {
        line[strcspn(line, "\n")] = 0;  // Eliminar el salto de línea
        split_line(line, tokens, &count, ",");
        
        // Guardar nombres de ciudades
        datos->num_ciudades = count - 2;  // -2 por Canal y Frecuencia
        for (int i = 2; i < count; i++) {
            strncpy(datos->ciudades[i-2], tokens[i], MAX_CITY_NAME-1);
        }
    }

    // Leer datos de canales
    datos->num_canales = 0;
    while (fgets(line, sizeof(line), file) && datos->num_canales < MAX_CHANNELS) {
        line[strcspn(line, "\n")] = 0;
        split_line(line, tokens, &count, ",");
        
        // Extraer número de canal (eliminar "Canal ")
        datos->canales[datos->num_canales].canal_num = atoi(tokens[0] + 6);
        datos->canales[datos->num_canales].frecuencia = atof(tokens[1]);
        
        // Guardar modulaciones
        for (int i = 2; i < count; i++) {
            strncpy(datos->canales[datos->num_canales].modulacion[i-2], tokens[i], 9);
        }
        
        datos->num_canales++;
    }

    fclose(file);
    return 1;
}

// Función para obtener la frecuencia y modulación para una ciudad y un canal dados
int obtener_frecuencia_y_modulacion(const DatosTDT *datos, const char *ciudad, int canal, float *frecuencia, char *modulacion) {
    // Buscar la ciudad
    int ciudad_idx = -1;
    for (int i = 0; i < datos->num_ciudades; i++) {
        if (strcmp(datos->ciudades[i], ciudad) == 0) {
            ciudad_idx = i;
            break;
        }
    }
    if (ciudad_idx == -1) {
        return 0;  // Ciudad no encontrada
    }

    // Buscar el canal
    int canal_idx = -1;
    for (int i = 0; i < datos->num_canales; i++) {
        if (datos->canales[i].canal_num == canal) {
            canal_idx = i;
            break;
        }
    }
    if (canal_idx == -1) {
        return 0;  // Canal no válido
    }

    // Obtener frecuencia y modulación
    *frecuencia = datos->canales[canal_idx].frecuencia;
    strncpy(modulacion, datos->canales[canal_idx].modulacion[ciudad_idx], 9);

    return 1;  // Éxito
}
