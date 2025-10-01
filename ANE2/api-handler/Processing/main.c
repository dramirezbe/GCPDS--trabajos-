/**
 * @file main.c
 * @brief Módulo de procesamiento de señales en C (Versión con envío de datos).
 * @details Este programa se conecta a un socket, espera una petición JSON,
 *          simula el procesamiento de la tarea (con prints) y envía un
 *          nuevo JSON con datos "dummy" como resultado.
 * @author GCPDS
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include "cJSON.h" 

// La ruta para el socket Unix debe coincidir con el script del servidor Python.
#define SOCKET_PATH "/tmp/exchange_processing"
#define BUFFER_SIZE 1024

// --- Definiciones de Tipos ---

typedef enum {
    UNKNOWN_SERVICE = -1,
    DEMODULATION,
    ACQUIRING
} ServiceType_t;

typedef struct {
    ServiceType_t service_type;
    char time_task[50]; // si está vacío, la acción es instantánea
} Petition_t;

// --- Prototipos de Funciones ---

int create_and_connect_socket(const char* socket_path);
void close_connection(int server_fd);
int exist_petition(int server_fd, char* buffer, size_t buffer_size);
int parse_petition(const char* message, Petition_t* petition);
void execute_service_simulation(const Petition_t* petition);
int send_processed_data(int server_fd, const Petition_t* petition);

// --- Aplicación Principal ---
int main() {
    Petition_t petition;
    char buffer[BUFFER_SIZE];

    // 1. Crear el socket y conectarse al servidor
    int server_fd = create_and_connect_socket(SOCKET_PATH);
    if (server_fd == -1) {
        exit(EXIT_FAILURE);
    }
    printf("Conexión exitosa.\n");

    // 2. Bucle de comunicación principal
    while (1) {
        // Esperar y leer la petición del servidor
        if (exist_petition(server_fd, buffer, sizeof(buffer)) <= 0) {
            break; // Salir si no hay mensaje o la conexión se cierra
        }

        // Analizar la petición
        if (parse_petition(buffer, &petition) == 0) {
            // Simular la ejecución del servicio con prints
            execute_service_simulation(&petition);
            
            // Enviar los datos dummy procesados de vuelta al servidor
            if (send_processed_data(server_fd, &petition) != 0) {
                break; // Salir si hay un error al enviar
            }
        } else {
            fprintf(stderr, "La petición no pudo ser procesada debido a un error de formato.\n");
        }
    }

    // 3. Cerrar la conexión
    close_connection(server_fd);

    return 0;
}

/**
 * @brief Simula la ejecución de la acción con prints en la consola.
 * @param petition Puntero a la estructura de la petición con los datos.
 */
void execute_service_simulation(const Petition_t* petition) {
    int is_scheduled = (strlen(petition->time_task) > 0);

    switch (petition->service_type) {
        case DEMODULATION:
            printf(">> SIMULACIÓN: Realizando DEMODULACIÓN.\n");
            if (is_scheduled) printf("   -> Tarea programada para: %s\n", petition->time_task);
            else printf("   -> Tarea de ejecución instantánea.\n");
            break;
        case ACQUIRING:
            printf(">> SIMULACIÓN: Realizando ADQUISICIÓN Y PSD.\n");
            if (is_scheduled) printf("   -> Tarea programada para: %s\n", petition->time_task);
            else printf("   -> Tarea de ejecución instantánea.\n");
            break;
        default:
            printf(">> SIMULACIÓN: Servicio desconocido. No se hace nada.\n");
            break;
    }
}

/**
 * @brief Crea y envía un JSON con datos dummy basados en el servicio solicitado.
 * @param server_fd El descriptor de archivo del socket.
 * @param petition La petición que determina qué tipo de datos generar.
 * @return 0 en caso de éxito, -1 en caso de error.
 */
int send_processed_data(int server_fd, const Petition_t* petition) {
    cJSON* root = cJSON_CreateObject();
    if (root == NULL) {
        fprintf(stderr, "No se pudo crear el objeto cJSON raíz.\n");
        return -1;
    }

    cJSON_AddStringToObject(root, "source", "C_Client_Processed_Data");

    switch (petition->service_type) {
        case DEMODULATION: {
            cJSON_AddStringToObject(root, "dataType", "audio_samples");
            float dummy_samples[] = {0.15, -0.22, 0.51, 0.33, -0.10, -0.45};
            cJSON* data_array = cJSON_CreateFloatArray(dummy_samples, 6);
            cJSON_AddItemToObject(root, "data", data_array);
            break;
        }
        case ACQUIRING: {
            cJSON_AddStringToObject(root, "dataType", "psd_data");
            float freqs[] = {100.0, 200.0, 300.0, 400.0};
            float powers[] = {-85.5, -92.1, -110.7, -89.3};
            
            cJSON* data_obj = cJSON_CreateObject();
            cJSON_AddItemToObject(data_obj, "frequencies_hz", cJSON_CreateFloatArray(freqs, 4));
            cJSON_AddItemToObject(data_obj, "power_dbm", cJSON_CreateFloatArray(powers, 4));
            cJSON_AddItemToObject(root, "data", data_obj);
            break;
        }
        default:
            cJSON_AddStringToObject(root, "status", "error");
            cJSON_AddStringToObject(root, "details", "Servicio desconocido, no se generaron datos.");
            break;
    }

    char* response_string = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);

    if (response_string == NULL) {
        fprintf(stderr, "No se pudo imprimir cJSON a cadena.\n");
        return -1;
    }

    int result = 0;
    if (write(server_fd, response_string, strlen(response_string)) < 0) {
        perror("error de escritura al enviar datos procesados");
        result = -1;
    } else {
        printf("Datos dummy enviados: %s\n", response_string);
    }
    
    free(response_string);
    return result;
}


// --- (Las siguientes funciones no han cambiado) ---

int create_and_connect_socket(const char* socket_path) {
    struct sockaddr_un server_addr;
    int client_fd;
    if ((client_fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
        perror("error de socket");
        return -1;
    }
    memset(&server_addr, 0, sizeof(struct sockaddr_un));
    server_addr.sun_family = AF_UNIX;
    strncpy(server_addr.sun_path, socket_path, sizeof(server_addr.sun_path) - 1);
    printf("Conectando al servidor Python en %s...\n", socket_path);
    if (connect(client_fd, (struct sockaddr*)&server_addr, sizeof(struct sockaddr_un)) == -1) {
        perror("error de conexión, asegúrate de que el servidor esté en ejecución");
        close(client_fd);
        return -1;
    }
    return client_fd;
}

int exist_petition(int server_fd, char* buffer, size_t buffer_size) {
    printf("\nEsperando petición del servidor...\n");
    memset(buffer, 0, buffer_size);
    ssize_t bytes_read = read(server_fd, buffer, buffer_size - 1);
    if (bytes_read < 0) {
        perror("error de lectura");
    } else if (bytes_read == 0) {
        printf("El servidor cerró la conexión.\n");
    }
    return bytes_read;
}

int parse_petition(const char* message, Petition_t* petition) {
    printf("Petición recibida: %s\n", message);
    petition->service_type = UNKNOWN_SERVICE;
    strcpy(petition->time_task, "");
    cJSON* root = cJSON_Parse(message);
    if (root == NULL) {
        fprintf(stderr, "Error: No se pudo analizar el JSON recibido.\n");
        return -1;
    }
    const cJSON* service_item = cJSON_GetObjectItem(root, "service");
    if (!cJSON_IsString(service_item) || (service_item->valuestring == NULL)) {
        fprintf(stderr, "Error: El campo 'service' no existe o no es una cadena.\n");
        cJSON_Delete(root);
        return -1;
    }
    if (strcmp(service_item->valuestring, "demodulation") == 0) {
        petition->service_type = DEMODULATION;
    } else if (strcmp(service_item->valuestring, "acquiring") == 0) {
        petition->service_type = ACQUIRING;
    } else {
        fprintf(stderr, "Error: Tipo de servicio desconocido: %s\n", service_item->valuestring);
        cJSON_Delete(root);
        return -1;
    }
    const cJSON* time_item = cJSON_GetObjectItem(root, "time_task");
    if (cJSON_IsString(time_item) && (time_item->valuestring != NULL)) {
        strncpy(petition->time_task, time_item->valuestring, sizeof(petition->time_task) - 1);
    }
    cJSON_Delete(root);
    return 0;
}

void close_connection(int server_fd) {
    printf("Cerrando conexión.\n");
    close(server_fd);
}