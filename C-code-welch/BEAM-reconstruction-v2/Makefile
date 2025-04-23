CC = gcc
CFLAGS = -Wall -Wextra
TARGET = welch_test
SRCS = welch_test.c src/cs8_to_iq.c src/welch.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS) -lfftw3 -lm

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)