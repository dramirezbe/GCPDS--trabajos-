"""!
@file main.py
@brief Main entry point for the backend application.
@details As the primary launcher, this script initializes and starts the ProcessingMonitor
         to manage a C-based signal processing module via Unix sockets (IPC).
         This module forms the core of a backend system designed to consume and
         process requests from an external REST API.
@author GCPDS
"""

import time
import os
import json
import socket
from libs import (
    ProcessingMonitor,
    socket_handler,
    backend_logger as logger
)

def send_json_dict(json_dict, connection):
    """
    Sends a JSON dictionary over a socket connection.

    @param json_dict The dictionary to send.
    @param connection The socket connection to send the data through.
    """
    try:
        message = json.dumps(json_dict).encode('utf-8')
        connection.sendall(message)
        logger.info(f"Sent JSON data: {json_dict}")
    except Exception as e:
        logger.error(f"Failed to send JSON data: {e}")

SERVICE_DUMMY = "acquire"
TIME_SERVICE_DUMMY = 5

def parse_response(response):
    response_data = json.loads(response.decode('utf-8'))

    try:
        service = response_data["service"]
    except KeyError:
        logger.error("Response missing 'service' field.")
        return None
    
    match service:
        case "acquire":
            Pxx = response_data.get("Pxx")
            fmin = response_data.get("fmin")
            fmax = response_data.get("fmax")
            if Pxx is not None and fmin is not None and fmax is not None:
                logger.info(f"Acquired data with fmin: {fmin}, fmax: {fmax}, Pxx length: {len(Pxx)}")
                return {"Pxx": Pxx, "fmin": fmin, "fmax": fmax}
            else:
                logger.error("Incomplete data received for 'acquire' service.")
                return None
        case "demodulate":
            audio_data = response_data.get("audio_data")
            if audio_data is not None:
                logger.info(f"Received demodulated audio data of length: {len(audio_data)}")
                return {"audio_data": audio_data}
        case "system_status": # Percentage in interval [0, 100]
            cpu = response_data.get("cpu") #Array for core usage
            disk = response_data.get("disk")
            ram = response_data.get("ram")
            swap = response_data.get("swap")
            temperature = response_data.get("temperature")
            if cpu is not None and disk is not None and ram is not None and swap is not None and temperature is not None:
                logger.info("Received system status data.")
                return {"cpu": cpu, "disk": disk, "ram": ram, "swap": swap, "temperature": temperature}
            else:
                logger.error("Incomplete data received for 'system_status' service.")
                return None

        case _:
            logger.warning(f"Unknown service in response: {response_data}")
            return None

# --- Constants ---

# Defines the absolute path to the C processing module executable.
PROCESSING_PATH = os.path.join(os.getcwd(), "Processing", "build", "processing_module")

# Defines the path for the Unix domain socket used for Inter-Process Communication (IPC).
SOCKET_PATH = "/tmp/processing_unix_socket"

if __name__ == "__main__":
    server_socket = None
    socket_handler.clean_socket(SOCKET_PATH)

    # Initialize the monitor with the paths to the executable and the socket.
    monitor = ProcessingMonitor(
        executable_path=PROCESSING_PATH,
        socket_path=SOCKET_PATH
    )
    monitor.start()

    try:
        server_socket = socket_handler.create_socket(SOCKET_PATH)
        server_socket.listen(1)
        time.sleep(1)  # Give some time for the socket to be ready

        while True:
            logger.info("Waiting for a client to connect...")
            
            
            connection, _ = server_socket.accept() #Waits here until a client connects.
            
            try:
                logger.info("Client connected.")



                # 1. Define and send the job to the client
                send_json_dict({"service": SERVICE_DUMMY, "fi": 88e6, "ff": 108e6, "rbw":4096, "time_task": TIME_SERVICE_DUMMY}, connection)

                # 2. Wait for and receive the response from the client
                response = connection.recv(4096)
                if response:
                    parsed_data = parse_response(response)
                    if parsed_data:
                        logger.info(f"Parsed data: {parsed_data}")
                    else:
                        logger.error("Failed to parse response data.")                   

                else:
                    logger.warning("No response received from client.")

            except socket.error as e:
                logger.error(f"Error during client communication: {e}")
            finally:
                connection.close()
                logger.info("Client connection closed.")


    except KeyboardInterrupt:
        logger.info("\nKeyboard interrupt detected. Exiting cleanly...")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main loop: {e}")
    finally:
        monitor.stop()