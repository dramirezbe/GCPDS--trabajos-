/**
 * @file utils.c
 * @author David Ramírez Betancourth
 */

#include "utils.h"

signal_iq_t* load_cs8(const char* filename) {
    FILE* file = fopen(filename, "rb");
    if (!file) {
        perror("Error: No se pudo abrir el archivo de datos CS8");
        return NULL;
    }

    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    rewind(file);

    if (file_size % 2 != 0) {
        fprintf(stderr, "Error: Tamaño del archivo inválido. Debe ser múltiplo de 2.\n");
        fclose(file);
        return NULL;
    }

    
    signal_iq_t* signal_data = (signal_iq_t*)malloc(sizeof(signal_iq_t));
    if (!signal_data) {
        perror("Error: No se pudo reservar memoria para la estructura signal_iq_t");
        fclose(file);
        return NULL;
    }

    signal_data->n_signal = file_size / 2;
    int8_t* raw_data = (int8_t*)malloc(file_size);
    signal_data->signal_iq = (complex double*)malloc(signal_data->n_signal * sizeof(complex double));

    if (!raw_data || !signal_data->signal_iq) {
        perror("Error: No se pudo reservar memoria para los datos IQ");
        free(raw_data);
        free(signal_data->signal_iq);
        free(signal_data);
        fclose(file);
        return NULL;
    }

    if (fread(raw_data, 1, (size_t)file_size, file) != (size_t)file_size) {
        perror("Error: Lectura incompleta del archivo");
        free(raw_data);
        free(signal_data->signal_iq);
        free(signal_data);
        fclose(file);
        return NULL;
    }

    for (size_t i = 0; i < signal_data->n_signal; i++) {
        signal_data->signal_iq[i] = raw_data[2 * i] + raw_data[2 * i + 1] * I;
    }

    free(raw_data);
    fclose(file);

    return signal_data;
}

Paths_t get_paths(void) {
    Paths_t paths;
    // Get the current working directory
    char cwd[2048];
    if (getcwd(cwd, sizeof(cwd)) != NULL) {
        snprintf(paths.samples_path, sizeof(paths.samples_path), "%s/Samples", cwd);
        snprintf(paths.json_path, sizeof(paths.json_path), "%s/JSON", cwd);
    }

    printf("Sample path: %s\n", paths.samples_path);
    printf("JSON path: %s\n", paths.json_path);
    return paths;
}

int instantaneous_capture(BackendParams_t* params, Paths_t* paths) {
    // Get params
    double bw = params->bw;
    double frequency = params->frequency;

    char* samples_path = paths->samples_path;

    char outfile_path[2048];
    snprintf(outfile_path, sizeof(outfile_path), "%s/0.cs8", samples_path);

    char command[2048];
    snprintf(command, sizeof(command), "hackrf_transfer -f %f -s %f -b %f -r %s -n %d -l 0 -g 0 -a 0", frequency, bw, bw, outfile_path, (int)bw);

    printf("Capturing Sample [%s]\n", command);

    FILE *fp;
    char buffer[2048];

    // Execute command and capture output
    fp = popen(command, "r");
    if (fp == NULL) {
        perror("Error executing command");
        return 1;
    }

    while (fgets(buffer, sizeof(buffer), fp) != NULL) {
        printf("%s", buffer);
    }

    pclose(fp);

    printf("Capture completed\n");
    printf("Output saved to: %s\n", outfile_path);
    return 0;

}
