#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

int main() 
{
    // Ruta del archivo .cs8
    const char *file_path = "C:\\Samples-Hack-RF\\88108.cs8";

    // Abrir el archivo en modo binario
    FILE *file = fopen(file_path, "rb");
    if (!file) {
        perror("Error al abrir el archivo");
        return 1;
    }

    // Obtener el tamaño del archivo
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    // Asignar memoria para los datos en bruto
    uint8_t *raw_data = (uint8_t *)malloc(file_size * sizeof(uint8_t));
    if (!raw_data) {
        perror("Error al asignar memoria");
        fclose(file);
        return 1;
    }

    // Leer los datos del archivo
    size_t read_size = fread(raw_data, sizeof(uint8_t), file_size, file);
    if (read_size != file_size) {
        perror("Error al leer el archivo");
        free(raw_data);
        fclose(file);
        return 1;
    }

    // Separar I y Q (asumiendo que están intercalados)
    size_t num_samples = file_size / 2;
    int8_t *I = (int8_t *)malloc(num_samples * sizeof(int8_t));
    int8_t *Q = (int8_t *)malloc(num_samples * sizeof(int8_t));
    
    if (!I || !Q) {
        perror("Error al asignar memoria para I/Q");
        free(raw_data);
        fclose(file);
        return 1;
    }

    // Llenar los vectores I y Q
    for (size_t i = 0; i < num_samples; i++) {
        I[i] = (int8_t)raw_data[2 * i];      // Datos I en las posiciones pares
        Q[i] = (int8_t)raw_data[2 * i + 1];  // Datos Q en las posiciones impares
    }

    // Aquí puedes procesar I y Q como desees

    // Liberar memoria y cerrar el archivo
    free(raw_data);
    free(I);
    free(Q);
    fclose(file);

    return 0;
}

