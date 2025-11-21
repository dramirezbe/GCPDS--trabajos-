CC = gcc
CFLAGS = -fPIC -O2 -IDrivers -Wall -Wextra
LDFLAGS = -shared -lpthread -lgpiod
SRC = Drivers/bacn_LTE.c Drivers/bacn_GPS.c Drivers/bacn_gpio.c Drivers/bacn_api.c
OUT = libbacn.so

all: $(OUT)

$(OUT): $(SRC)
	$(CC) $(CFLAGS) $(SRC) -o $(OUT) $(LDFLAGS)

clean:
	rm -f $(OUT)
