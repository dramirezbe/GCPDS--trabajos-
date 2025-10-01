#include <stdio.h>
#include <unistd.h>

int main() {
    setbuf(stdout, NULL); // Disable buffering for stdout

    while (1) {
        printf("Hello World!\n");
        sleep(1);
    }
    return 0;
}