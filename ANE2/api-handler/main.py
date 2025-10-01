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
from libs import (
    ProcessingMonitor,
    socket_handler as soc
)

# --- Constants ---

# Defines the absolute path to the C processing module executable.
PROCESSING_PATH = os.path.join(os.getcwd(), "Processing", "build", "processing_module")

# Defines the path for the Unix domain socket used for Inter-Process Communication (IPC).
SOCKET_PATH = "/tmp/exchange_processing"

def print(*args, **kwargs):
    """!
    @brief Overrides the built-in print function for this script's scope.
    @details This override automatically prepends the '[Backend]' decorator to all
             messages printed from this script, ensuring a consistent log format.
    """
    __builtins__.print("[Backend]", *args, **kwargs)

if __name__ == "__main__":
    server_socket = None
    soc.clean_socket(SOCKET_PATH)
    
    # Initialize the monitor with the paths to the executable and the socket.
    monitor = ProcessingMonitor(
        executable_path=PROCESSING_PATH,
        socket_path=SOCKET_PATH
    )
    monitor.start()


    #---------------Here the socket------------------
    try:
        while True:
            time.sleep(1)
            print("Alive")

    except KeyboardInterrupt:
        # This block catches the Ctrl+C signal for a graceful shutdown.
        print("\n[MainApp] Keyboard interrupt detected. Exiting cleanly...")
    except Exception as e:
        print(f"[MainApp] An unexpected error occurred in the main loop: {e}")
    finally:
        monitor.stop()