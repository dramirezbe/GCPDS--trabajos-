#ifndef TDT_H
#define TDT_H

#define MAX_CITIES 33
#define MAX_CHANNELS 38
#define MAX_CITY_NAME 50

// Estructura para almacenar la información de un canal
typedef struct {
    int canal_num;
    float frecuencia;
    char modulacion[MAX_CITIES][10];  // Modulación para cada ciudad
} Canal;

// Estructura para almacenar toda la información
typedef struct {
    char ciudades[MAX_CITIES][MAX_CITY_NAME];
    int num_ciudades;
    Canal canales[MAX_CHANNELS];
    int num_canales;
} DatosTDT;

// Función para cargar los datos del archivo CSV
int cargar_csv_mod(const char *filename, DatosTDT *datos);

// Función para obtener la frecuencia y modulación para una ciudad y un canal dados
int obtener_frecuencia_y_modulacion(const DatosTDT *datos, const char *ciudad, int canal, float *frecuencia, char *modulacion);

#endif
