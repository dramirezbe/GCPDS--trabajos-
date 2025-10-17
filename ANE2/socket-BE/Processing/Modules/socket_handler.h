/**
 * @file socket_handler.h
 * @brief Public interface for socket communication and JSON message handling.
 */

#ifndef SOCKET_HANDLER_H
#define SOCKET_HANDLER_H

#include "../utils/cJSON.h"
#include "../utils/datatypes.h"

#define BUFFER_SIZE 4096

/**
 * @brief Connects to a UNIX domain socket, with a retry mechanism.
 * @param socket_path The file path of the UNIX socket.
 * @return The socket file descriptor on success, or exits on failure.
 */
int socket_connect_with_retry(const char *socket_path);

/**
 * @brief Receives a JSON string payload from the connected socket.
 * @note The returned string is dynamically allocated and MUST be freed by the caller.
 * @param client_socket_fd The file descriptor of the client socket.
 * @return A pointer to the dynamically allocated string containing the JSON payload, or NULL on error/disconnection.
 */
char* socket_receive_json_payload(int client_socket_fd);

/**
 * @brief Sends a JSON-formatted acquisition result to the server.
 * @param client_socket_fd The file descriptor for the connection.
 * @param acquisition_result Pointer to the result data to be sent.
 */
void socket_send_acquisition_result(int client_socket_fd, const AcquisitionResult_t *acquisition_result);

/**
 * @brief Parses a JSON string to determine the service type.
 * @param json_payload The JSON string received from the socket.
 * @return The corresponding ServiceType_t enum value.
 */
ServiceType_t json_get_service_type(const char *json_payload);

/**
 * @brief Parses the JSON job payload and fills the AcquisitionRequest_t struct.
 * @note This function allocates memory for the strings in the struct using strdup.
 *         Use acquisition_request_cleanup() to free this memory.
 * @param json_payload The JSON string to parse.
 * @param request_params The struct to populate.
 * @return 0 on success, -1 on parsing failure.
 */
int json_parse_acquisition_request(const char *json_payload, AcquisitionRequest_t *request_params);

/**
 * @brief Frees the memory allocated for the members of an AcquisitionRequest_t struct.
 * @param request_params Pointer to the struct whose members should be freed.
 */
void acquisition_request_cleanup(AcquisitionRequest_t *request_params);


#endif // SOCKET_HANDLER_H