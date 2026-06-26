#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include "cJSON.h" // Make sure you have the cJSON library

#define SOCKET_PATH "/tmp/my_unix_socket"
#define BUFFER_SIZE 1024

// Function to build and send the final processed data
void send_job_result(int socket, const char *service_name, int time, int code, const char *message) {
    cJSON *result_json = cJSON_CreateObject();
    if (result_json == NULL) {
        fprintf(stderr, "Failed to create JSON object for result.\n");
        return;
    }

    cJSON_AddStringToObject(result_json, "original_service", service_name);
    cJSON_AddNumberToObject(result_json, "time_taken", time);
    cJSON_AddNumberToObject(result_json, "result_code", code);
    cJSON_AddStringToObject(result_json, "message", message);

    char *result_string = cJSON_PrintUnformatted(result_json);
    if (result_string == NULL) {
        fprintf(stderr, "Failed to print result JSON to string.\n");
    } else {
        printf("Sending processed data: %s\n", result_string);
        if (send(socket, result_string, strlen(result_string), 0) == -1) {
            perror("send result error");
        }
        free(result_string); // Must free the string allocated by cJSON
    }
    cJSON_Delete(result_json); // Free the cJSON object
}


int main() {
    int client_socket;
    struct sockaddr_un server_addr;
    char buffer[BUFFER_SIZE];

    // Superloop for the client
    while (1) {
        if ((client_socket = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
            perror("socket error");
            sleep(2);
            continue;
        }

        memset(&server_addr, 0, sizeof(struct sockaddr_un));
        server_addr.sun_family = AF_UNIX;
        strncpy(server_addr.sun_path, SOCKET_PATH, sizeof(server_addr.sun_path) - 1);

        printf("Connecting to master server...\n");
        if (connect(client_socket, (struct sockaddr *)&server_addr, sizeof(struct sockaddr_un)) == -1) {
            perror("connect error");
            close(client_socket);
            sleep(2);
            continue;
        }

        printf("Connected. Waiting for a job...\n");

        // 1. Receive the job from the server
        ssize_t num_bytes = recv(client_socket, buffer, BUFFER_SIZE - 1, 0);
        if (num_bytes > 0) {
            buffer[num_bytes] = '\0';
            printf("Received job: %s\n", buffer);

            // 2. Process the job
            cJSON *json = cJSON_Parse(buffer);
            if (json == NULL) {
                fprintf(stderr, "Error: Could not parse job JSON.\n");
                // Report the failure back to the master
                send_job_result(client_socket, "unknown", 0, -1, "Failed to parse incoming JSON job");
            } else {
                cJSON *service = cJSON_GetObjectItemCaseSensitive(json, "service");
                cJSON *timeService = cJSON_GetObjectItemCaseSensitive(json, "timeService");
                int delay_seconds = 0;
                const char *service_name_str = "unknown";

                if (cJSON_IsString(service) && (service->valuestring != NULL)) {
                    service_name_str = service->valuestring;
                    printf("Processing service: %s\n", service_name_str);
                }
                if (cJSON_IsString(timeService) && (timeService->valuestring != NULL)) {
                    // Extract integer from string like "5seconds"
                    sscanf(timeService->valuestring, "%d", &delay_seconds);
                }

                // 3. Simulate doing the work
                printf("Simulating work for %d seconds...\n", delay_seconds);
                sleep(delay_seconds > 0 ? delay_seconds : 1);
                printf("Work finished.\n");
                
                // 4. Send the "processed dummy data" back as a result
                send_job_result(client_socket, service_name_str, delay_seconds, 0, "Task completed successfully");
                
                cJSON_Delete(json);
            }
        } else {
            printf("Connection closed by server or recv error.\n");
        }

        close(client_socket);
        printf("Disconnected. Will try to reconnect.\n\n");
        sleep(2);
    }

    return 0;
}