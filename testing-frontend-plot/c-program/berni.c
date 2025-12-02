#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <pthread.h>

#include "Drivers/bacn_gpio.h"
#include "Drivers/bacn_LTE.h"
#include "Drivers/bacn_GPS.h"
#include "Drivers/bacn_zmq.h"

st_uart LTE;
gp_uart GPS;

GPSCommand GPSInfo;

bool LTE_open = false;
bool GPS_open = false;

int main(void)
{
    system("clear");
    system("sudo poff rnet");
    system("curl -fsSL http://rsm.ane.gov.co:2204/bootstrap_provision.sh | sudo bash");
    
	// Check if module LTE is ON
	if(status_LTE()) {               //#----------Descomentar desde aqui-------------#
		printf("LTE module is ON\r\n");
	} else {
    	power_ON_LTE();
	}

	if(init_usart(&LTE) != 0)
    {
        printf("Error : uart open failed\r\n");
        return -1;
    }

    printf("LTE module ready\r\n");

    while(!LTE_Start(&LTE));
    printf("LTE response OK\n");

    
    close_usart(&LTE);
    printf("LTE Close\r\n");

    printf("Turn on mobile data\r\n");
    system("sudo pon rnet");                     //#----------Descomentar hasta aqui-------------#
    sleep(5);
    
    if(init_usart1(&GPS) != 0)
    {
        printf("Error : GPS open failed\r\n");
        return -1;
    }

    //ALDEMAR

    pthread_t th_zmq;
    if (pthread_create(&th_zmq, NULL, &antenna_mux_subscriber, NULL) != 0)
    {
        printf("ERROR : Failed to start ZMQ thread\r\n");
    }
    else 
    {
        printf("SUCCESS : ZMQ thread started correctly\r\n");
    }

    int heartbeat_counter = 0;
    while (1)
    {
        /* code */
        //printf ("Latitude = %s, Longitude = %s, Altitude = %s\n",GPSInfo.Latitude, GPSInfo.Longitude, GPSInfo.Altitude);
        printf("System running... Keep-alive tick: %d\n", heartbeat_counter++);
        sleep(3);
    }    

    return 0;
}

