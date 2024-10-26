CC = gcc
CFLAGS = -Wall -Wextra
TARGET = test_main
SRCS = main.c src/process_cs8/process_cs8.c src/my_complex/my_complex.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

