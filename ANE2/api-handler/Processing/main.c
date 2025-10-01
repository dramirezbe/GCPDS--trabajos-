#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>

#define SOCKET_PATH "/tmp/test_socket"

int main() {
    int sockfd;
    struct sockaddr_un addr;
    char buffer[1024];

    // Crear socket
    sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("socket");
        exit(1);
    }

    // Configurar dirección
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);

    // Conectar al servidor
    if (connect(sockfd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("connect");
        exit(1);
    }

    printf("Conectado al servidor Python.\n");

    while (1) {
        // Leer JSON desde Python
        int n = read(sockfd, buffer, sizeof(buffer)-1);
        if (n > 0) {
            buffer[n] = '\0';
            printf("Python envió: %s\n", buffer);

            // Aquí podrías parsear JSON con cJSON o similar,
            // pero para lo básico, simplemente respondemos otro JSON.
            const char *reply = "{\"status\": \"ok\", \"msg\": \"Recibido JSON\"}";
            write(sockfd, reply, strlen(reply));
        }

        sleep(10);
    }

    close(sockfd);
    return 0;
}
