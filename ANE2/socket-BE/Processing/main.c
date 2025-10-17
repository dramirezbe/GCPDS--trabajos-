/**
 * @file main.c
 * @brief Main function for the Processing Module
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <math.h> // For sin() in dummy data generation

#include "utils/cJSON.h"
#include "datatypes.h"
#include "socket_handler.h"

#define SOCKET_PATH "/tmp/processing_unix_socket"

int main() {
    // Disable buffering for immediate log output
    setvbuf(stdout, NULL, _IONBF, 0);
    sleep(2);

    while (1) {
        int client_socket_fd = socket_connect_with_retry(SOCKET_PATH);
        char *json_payload = socket_receive_json_payload(client_socket_fd);

        if (json_payload == NULL) {
            printf("Disconnected from the server.\n");
            break;
        }

        if (json_payload != NULL) {
            printf("Received job: %s\n", json_payload);
            ServiceType_t service = json_get_service_type(json_payload);


            switch (service) {
                case ACQUISITION_SERVICE: {
                    AcquisitionRequest_t request = {0};
                    if (json_parse_acquisition_request(json_payload, &request) == 0) {
                        
                        // --- DYNAMIC ARRAY LOGIC START ---

                        // 1. Convert string parameters to numbers for calculation
                        double fi = atof(request.initial_frequency_hz);
                        double ff = atof(request.final_frequency_hz);
                        double rbw = atof(request.resolution_bandwidth_hz);

                        // 2. Calculate the number of points for the PSD array
                        // Formula: (Stop Freq - Start Freq) / Resolution Bandwidth
                        int num_points = 0;
                        if (rbw > 0 && ff > fi) {
                            num_points = (int)((ff - fi) / rbw);
                        }
                        
                        if (num_points <= 0) {
                            fprintf(stderr, "Invalid parameters for acquisition: fi=%f, ff=%f, rbw=%f. Cannot generate data.\n", fi, ff, rbw);
                            acquisition_request_cleanup(&request);
                            break;
                        }

                        // 3. Dynamically allocate memory for the results array
                        double *psd_values = malloc(num_points * sizeof(double));
                        if (psd_values == NULL) {
                            perror("Failed to allocate memory for PSD array");
                            acquisition_request_cleanup(&request);
                            break;
                        }

                        // 4. Fill the array with dummy data (e.g., a noisy sine wave)
                        printf("Generating %d dummy data points...\n", num_points);
                        for (int i = 0; i < num_points; i++) {
                            // A sample signal peak around the middle of the spectrum
                            double signal = 20.0 * exp(-pow(i - num_points / 2.0, 2.0) / (2 * pow(num_points / 10.0, 2.0)));
                            double noise = (rand() % 20) / 10.0; // Random noise between 0.0 and 2.0
                            psd_values[i] = -60.0 + signal + noise;
                        }

                        // 5. Populate the result struct (dummy data)
                        AcquisitionResult_t result = {
                            .num_psd_values = num_points,
                            .power_spectral_density = psd_values,
                            .initial_frequency_hz = fi,
                            .final_frequency_hz = ff
                        };

                        // 6. Send the result (the function is now array-aware)
                        socket_send_acquisition_result(client_socket_fd, &result);

                        free(psd_values);
                        acquisition_request_cleanup(&request);
                    }
                    break;
                }

                case DEMODULATION_SERVICE:
                    fprintf(stderr, "Received a job with the demodulation service type.\n");
                    break;
                
                case SYSTEM_STATUS_SERVICE:
                    fprintf(stderr, "Received a job with the system status service type.\n");
                    break;

                case SYSTEM_SUBSCRIBE_SERVICE:
                    fprintf(stderr, "Received a job with the system subscribe service type.\n");
                    break;

                case UNKNOWN_SERVICE:
                    fprintf(stderr, "Received a job with an unknown service type.\n");
                    break;

                default:
                    fprintf(stderr, "Received a job with an unknown or malformed service type.\n");
                    break;
            }
            free(json_payload);
        }

        printf("Closing connection.\n\n");
        close(client_socket_fd);
        sleep(1);
    }
    return 0;
}