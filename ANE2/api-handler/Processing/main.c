#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include "cJSON.h" // The cJSON header

// --- Constants ---
#define SOCKET_PATH "/tmp/processing_unix_socket"
#define BUFFER_SIZE 4096

// --- Function Prototypes ---
int connect_to_socket(const char *socket_path);
void process_job(int client_socket, const char *job_buffer);
void handle_acquire_service(int client_socket);
void handle_demodulate_service(int client_socket);
void send_json_response(int client_socket, cJSON *response_json);

/**
 * @brief Main entry point for the C client.
 *
 * Controls the main superloop, handling connection, job reception,
 * and dispatching the job to the appropriate processing function.
 */
int main() {
    // Disable stdout buffering to ensure printf calls are immediately visible,
    // which is useful when the stdout is piped (like by the Python monitor).
    setvbuf(stdout, NULL, _IONBF, 0);


    sleep(2); // Give some time for the server to start
    // The main "superloop" to ensure the client is always running.
    while (1) {
        int client_socket = connect_to_socket(SOCKET_PATH);
        if (client_socket < 0) {
            sleep(2); // Wait before retrying connection
            continue;
        }

        char buffer[BUFFER_SIZE];
        ssize_t num_bytes = recv(client_socket, buffer, BUFFER_SIZE - 1, 0);

        if (num_bytes > 0) {
            buffer[num_bytes] = '\0'; // Null-terminate the received string
            process_job(client_socket, buffer);
        } else {
            if (num_bytes == 0) {
                printf("Server closed the connection.\n");
            } else {
                perror("recv error");
            }
        }

        printf("Closing connection.\n\n");
        close(client_socket);
        sleep(1); // Brief pause before the loop repeats
    }

    return 0;
}

/**
 * @brief Creates and connects a UNIX domain socket.
 * @param socket_path The file path of the UNIX socket.
 * @return The socket file descriptor on success, or -1 on failure.
 */
int connect_to_socket(const char *socket_path) {
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

/**
 * @brief Parses the job string and calls the appropriate handler.
 * @param client_socket The active client socket descriptor.
 * @param job_buffer A null-terminated string containing the JSON job.
 */
void process_job(int client_socket, const char *job_buffer) {
    printf("Received job: %s\n", job_buffer);

    cJSON *incoming_json = cJSON_Parse(job_buffer);
    if (incoming_json == NULL) {
        fprintf(stderr, "Error: Could not parse incoming JSON.\n");
        return;
    }

    cJSON *service_item = cJSON_GetObjectItemCaseSensitive(incoming_json, "service");
    cJSON *time_item = cJSON_GetObjectItemCaseSensitive(incoming_json, "timeService");

    if (!cJSON_IsString(service_item) || (service_item->valuestring == NULL)) {
        fprintf(stderr, "Error: JSON job is missing 'service' string field.\n");
        cJSON_Delete(incoming_json);
        return;
    }

    const char *service_type = service_item->valuestring;
    int delay_seconds = cJSON_IsNumber(time_item) ? time_item->valueint : 1;

    printf("Job is '%s'. Simulating work for %d seconds...\n", service_type, delay_seconds);
    sleep(delay_seconds);
    printf("Work finished. Generating response data...\n");

    // --- LOGIC SWITCH BASED ON SERVICE TYPE ---
    if (strcmp(service_type, "acquire") == 0) {
        handle_acquire_service(client_socket);
    } else if (strcmp(service_type, "demodulate") == 0) {
        handle_demodulate_service(client_socket);
    } else {
        printf("Warning: Received unknown service type '%s'. No response will be sent.\n", service_type);
    }

    cJSON_Delete(incoming_json); // Clean up the parsed JSON object
}

/**
 * @brief Handles the "acquire" service: creates and sends dummy Pxx data.
 * @param client_socket The active client socket descriptor.
 */
void handle_acquire_service(int client_socket) {
    double pxx_data[] = {0.1, 0.5, 1.2, 2.5, 1.3, 0.4, 0.2, 3.1, 4.5, 2.1};

    cJSON *response_json = cJSON_CreateObject();
    if (response_json == NULL) return;

    cJSON_AddStringToObject(response_json, "service", "acquire");
    cJSON_AddItemToObject(response_json, "Pxx", cJSON_CreateDoubleArray(pxx_data, sizeof(pxx_data) / sizeof(double)));
    cJSON_AddNumberToObject(response_json, "fmin", 100.5);
    cJSON_AddNumberToObject(response_json, "fmax", 500.8);

    send_json_response(client_socket, response_json);
}

/**
 * @brief Handles the "demodulate" service: creates and sends dummy audio data.
 * @param client_socket The active client socket descriptor.
 */
void handle_demodulate_service(int client_socket) {
    int audio_dummy_data[] = {10, 25, -15, 40, 100, 120, 50, -30, -90, -110, -60};

    cJSON *response_json = cJSON_CreateObject();
    if (response_json == NULL) return;

    cJSON_AddStringToObject(response_json, "service", "demodulate");
    cJSON_AddItemToObject(response_json, "audio_data", cJSON_CreateIntArray(audio_dummy_data, sizeof(audio_dummy_data) / sizeof(int)));

    send_json_response(client_socket, response_json);
}

/**
 * @brief Converts a cJSON object to a string and sends it over the socket.
 *
 * This function handles the full lifecycle: print, send, and free memory.
 * @param client_socket The active client socket descriptor.
 * @param response_json The cJSON object to send. The function will delete this object.
 */
void send_json_response(int client_socket, cJSON *response_json) {
    if (response_json == NULL) return;

    char *response_string = cJSON_PrintUnformatted(response_json);
    if (response_string == NULL) {
        fprintf(stderr, "Failed to print JSON to string.\n");
    } else {
        printf("Sending response: %s\n", response_string);
        send(client_socket, response_string, strlen(response_string), 0);
        free(response_string); // Free the string allocated by cJSON
    }

    cJSON_Delete(response_json); // Free the cJSON object itself
}