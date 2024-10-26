CC = gcc
CFLAGS = -Wall -Wextra
TARGET = test_main
SRCS = main.c src/BER/BER.c src/my_fft/my_fft.c src/process_cs8/process_cs8.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

