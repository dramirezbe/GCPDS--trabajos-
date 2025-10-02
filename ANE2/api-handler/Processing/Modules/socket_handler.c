/**
 * @file socket_handler.c
 * @brief Implementation of socket communication and JSON message handling functions.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <math.h> // Included for dummy data generation
#include "socket_handler.h"

/**
 * @brief Creates and connects a UNIX domain socket. (Internal function)
 * @param socket_path The file path of the UNIX socket.
 * @return The socket file descriptor on success, or -1 on failure.
 */
static int create_and_connect_socket(const char *socket_path) {
    int sock_fd;
    struct sockaddr_un server_addr;

    if ((sock_fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
        perror("socket error");
        return -1;
    }

    memset(&server_addr, 0, sizeof(struct sockaddr_un));
    server_addr.sun_family = AF_UNIX;
    strncpy(server_addr.sun_path, socket_path, sizeof(server_addr.sun_path) - 1);

    printf("Attempting to connect to server at %s...\n", socket_path);
    if (connect(sock_fd, (struct sockaddr *)&server_addr, sizeof(struct sockaddr_un)) == -1) {
        perror("connect error");
        close(sock_fd);
        return -1;
    }

    printf("Connected to server. Waiting for a job...\n");
    return sock_fd;
}

int socket_connect_with_retry(const char *socket_path) {
    int client_socket_fd;
    while (1) {
        client_socket_fd = create_and_connect_socket(socket_path);
        if (client_socket_fd < 0) {
            printf("Connection failed. Retrying in 2 seconds...\n");
            sleep(2);
        } else {
            return client_socket_fd;
        }
    }
}

char* socket_receive_json_payload(int client_socket_fd) {
    char buffer[BUFFER_SIZE];
    ssize_t num_bytes = recv(client_socket_fd, buffer, BUFFER_SIZE - 1, 0);

    if (num_bytes > 0) {
        buffer[num_bytes] = '\0';
        char *json_payload = strdup(buffer); // Use strdup for safe memory allocation
        if (!json_payload) {
            perror("strdup error");
        }
        return json_payload; // Caller is responsible for freeing this memory
    }

    if (num_bytes == 0) {
        printf("Server closed the connection.\n");
    } else {
        perror("recv error");
    }
    return NULL; // Return NULL on error or disconnection
}

ServiceType_t json_get_service_type(const char *json_payload) {
    ServiceType_t service_type = UNKNOWN_SERVICE;
    cJSON *json = cJSON_Parse(json_payload);
    if (json == NULL) {
        fprintf(stderr, "Failed to parse JSON.\n");
        return UNKNOWN_SERVICE;
    }

    cJSON *service_item = cJSON_GetObjectItemCaseSensitive(json, "service");
    if (cJSON_IsString(service_item) && (service_item->valuestring != NULL)) {
        if (strcmp(service_item->valuestring, "acquire") == 0) service_type = ACQUISITION_SERVICE;
        else if (strcmp(service_item->valuestring, "demodulate") == 0) service_type = DEMODULATION_SERVICE;
    }

    cJSON_Delete(json);
    return service_type;
}

int json_parse_acquisition_request(const char *json_payload, AcquisitionRequest_t *request_params) {
    cJSON *json = cJSON_Parse(json_payload);
    if (json == NULL) {
        fprintf(stderr, "Failed to parse JSON for acquisition request.\n");
        return -1;
    }

    cJSON *fi = cJSON_GetObjectItemCaseSensitive(json, "fi");
    cJSON *ff = cJSON_GetObjectItemCaseSensitive(json, "ff");
    cJSON *rbw = cJSON_GetObjectItemCaseSensitive(json, "rbw");
    cJSON *time_task = cJSON_GetObjectItemCaseSensitive(json, "time_task");

    if (!cJSON_IsString(fi) || !cJSON_IsString(ff) || !cJSON_IsString(rbw) || !cJSON_IsString(time_task)) {
        fprintf(stderr, "JSON is missing required string fields for acquisition service.\n");
        cJSON_Delete(json);
        return -1;
    }

    // Safely copy strings into the struct. This prevents dangling pointers.
    request_params->initial_frequency_hz = strdup(fi->valuestring);
    request_params->final_frequency_hz = strdup(ff->valuestring);
    request_params->resolution_bandwidth_hz = strdup(rbw->valuestring);
    request_params->task_duration_s = strdup(time_task->valuestring);
    
    cJSON_Delete(json);

    // Check for allocation failures
    if (!request_params->initial_frequency_hz || !request_params->final_frequency_hz ||
        !request_params->resolution_bandwidth_hz || !request_params->task_duration_s) {
        perror("strdup error during request parsing");
        acquisition_request_cleanup(request_params); // Clean up partial allocations
        return -1;
    }
    
    return 0;
}

void acquisition_request_cleanup(AcquisitionRequest_t *request_params) {
    if (request_params) {
        free(request_params->initial_frequency_hz);
        free(request_params->final_frequency_hz);
        free(request_params->resolution_bandwidth_hz);
        free(request_params->task_duration_s);
        request_params->initial_frequency_hz = NULL;
        request_params->final_frequency_hz = NULL;
        request_params->resolution_bandwidth_hz = NULL;
        request_params->task_duration_s = NULL;
    }
}

void socket_send_acquisition_result(int client_socket_fd, const AcquisitionResult_t *acquisition_result) {
    cJSON *response_json = cJSON_CreateObject();
    if (response_json == NULL) {
        fprintf(stderr, "Failed to create cJSON object.\n");
        return;
    }

    // Add the single-value fields
    cJSON_AddNumberToObject(response_json, "fi", acquisition_result->initial_frequency_hz);
    cJSON_AddNumberToObject(response_json, "ff", acquisition_result->final_frequency_hz);
    cJSON_AddStringToObject(response_json, "service", "acquire");

    // Create a cJSON array for the power spectral density data
    cJSON *psd_json_array = cJSON_CreateArray();
    if (psd_json_array == NULL) {
        fprintf(stderr, "Failed to create cJSON array.\n");
        cJSON_Delete(response_json);
        return;
    }
    
    // Loop through the C array and add each element to the cJSON array
    for (int i = 0; i < acquisition_result->num_psd_values; i++) {
        cJSON_AddItemToArray(psd_json_array, cJSON_CreateNumber(acquisition_result->power_spectral_density[i]));
    }

    // Add the newly created array to the root JSON object
    cJSON_AddItemToObject(response_json, "Pxx", psd_json_array);

    // Convert to string, send, and clean up
    char *response_payload = cJSON_PrintUnformatted(response_json);
    if (response_payload == NULL) {
        fprintf(stderr, "Failed to print cJSON object to string.\n");
    } else {
        printf("Sending response with %d PSD points...\n", acquisition_result->num_psd_values);
        // To see the full payload, uncomment the line below
        // printf("Payload: %s\n", response_payload);
        send(client_socket_fd, response_payload, strlen(response_payload), 0);
        cJSON_free(response_payload);
    }

    cJSON_Delete(response_json);
}