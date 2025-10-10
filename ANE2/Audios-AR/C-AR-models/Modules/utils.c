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
    char cwd[2048];

    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        // Handle the error if getcwd fails
        fprintf(stderr, "Error: Failed to get current working directory: %s\n", strerror(errno));
        exit(1); // Exit because paths are critical
    }

    // Create samples_path and check for truncation
    int len_samples = snprintf(paths.samples_path, sizeof(paths.samples_path), "%s/Samples", cwd);
    if (len_samples < 0 || (size_t)len_samples >= sizeof(paths.samples_path)) {
        fprintf(stderr, "Error: Potential path truncation for samples_path. Increase buffer size.\n");
        exit(1);
    }

    // Create json_path and check for truncation
    int len_json = snprintf(paths.json_path, sizeof(paths.json_path), "%s/JSON", cwd);
    if (len_json < 0 || (size_t)len_json >= sizeof(paths.json_path)) {
        fprintf(stderr, "Error: Potential path truncation for json_path. Increase buffer size.\n");
        exit(1);
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
    int len_path = snprintf(outfile_path, sizeof(outfile_path), "%s/0.cs8", paths->samples_path);
    if (len_path < 0 || (size_t)len_path >= sizeof(outfile_path)) {
        fprintf(stderr, "Error: Output file path would be truncated.\n");
        return 1; // Return an error code
    }

    char command[2048];
    int len_cmd = snprintf(command, sizeof(command), "hackrf_transfer -f %f -s %f -b %f -r %s -n %d -l 0 -g 0 -a 0", 
                           params->frequency, params->bw, params->bw, outfile_path, (int)params->bw);
    if (len_cmd < 0 || (size_t)len_cmd >= sizeof(command)) {
        fprintf(stderr, "Error: System command string would be truncated.\n");
        return 1; // Return an error code
    }

    //printf("Capturing Sample [%s]\n", command);

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

    int status = pclose(fp);
    if (status == -1) {
        perror("Error closing command stream");
        return 1;
    } else if (WIFEXITED(status) && WEXITSTATUS(status) != 0) {
        fprintf(stderr, "Error: hackrf_transfer command failed with exit status %d\n", WEXITSTATUS(status));
        return 1;
    }

    //printf("Capture completed\n");
    //printf("Output saved to: %s\n", outfile_path);
    return 0;
}
