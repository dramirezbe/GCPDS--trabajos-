"""!
@file processing_monitor.py
@brief A utility for managing and monitoring a long-running external process.
@author GCPDS
"""

import time
import os
import subprocess
import atexit
import threading
from .socket_handler import clean_socket
from .logger_config import backend_logger, processing_logger

class ProcessingMonitor:
    """!
    @brief A class to launch, monitor, and manage a secondary process in a background thread.
    
    This class handles the lifecycle of an external executable, ensuring it is always running.
    It will automatically restart the process if it terminates unexpectedly. It also captures
    and logs the standard output and standard error streams of the managed process.
    """

    def __init__(self, executable_path, socket_path=None):
        """!
        @brief Initializes the ProcessingMonitor.
        
        @param executable_path: Path to the executable to be monitored.
        @param socket_path: Optional. Path to a socket to be cleaned up.
        @raise FileNotFoundError: If the executable does not exist.
        """
        if not os.path.exists(executable_path):
            raise FileNotFoundError(f"The executable was not found at: {executable_path}")
            
        self.executable_path = executable_path
        self.socket_path = socket_path
        self.process = None
        self._monitor_thread = None
        self._stop_event = threading.Event()
        
        atexit.register(self.stop)

    def _stream_reader(self, stream, logger, is_error_stream=False):
        """!
        @brief Reads and logs lines from a given stream until it closes.
        
        @param stream: The stream to read from (e.g., process.stdout).
        @param logger: The logger instance to use for output.
        @param is_error_stream: Boolean to indicate if logging should be at the ERROR level.
        """
        try:
            for line in iter(stream.readline, ''):
                if line:
                    log_message = line.strip()
                    if is_error_stream:
                        logger.error(log_message)
                    else:
                        logger.info(log_message)
        finally:
            stream.close()

    def _run_and_monitor(self):
        """!
        @brief The main loop that runs and monitors the external process.
        """
        while not self._stop_event.is_set():
            try:
                if self.socket_path and os.path.exists(self.socket_path):
                    backend_logger.info(f"Deleting old socket at {self.socket_path}...")
                    os.unlink(self.socket_path)

                # Use stdbuf to force line-buffering on the C process, solving the output issue globally.
                command = ["stdbuf", "-oL", self.executable_path]
                backend_logger.info(f"Starting process: {' '.join(command)}")

                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                backend_logger.info(f"C module started successfully with PID: {self.process.pid}")

                stdout_thread = threading.Thread(
                    target=self._stream_reader, 
                    args=(self.process.stdout, processing_logger, False), 
                    daemon=True
                )
                stderr_thread = threading.Thread(
                    target=self._stream_reader, 
                    args=(self.process.stderr, processing_logger, True), 
                    daemon=True
                )
                stdout_thread.start()
                stderr_thread.start()

                self.process.wait()

                if self._stop_event.is_set():
                    break # Exit loop if stop() was called

                backend_logger.warning(f"ATTENTION! The C process with PID {self.process.pid} has terminated.")
                exit_code = self.process.returncode
                if exit_code != 0:
                    backend_logger.error(f"The process failed with exit code: {exit_code}")
                else:
                    backend_logger.info("The process finished without an explicit error code.")

            except Exception as e:
                backend_logger.error(f"An unexpected error occurred in the monitor: {e}")

            if not self._stop_event.is_set():
                backend_logger.info("Attempting to restart the process in 5 seconds...")
                time.sleep(5)

    def start(self):
        """!
        @brief Starts the background monitoring thread.
        """
        if self._monitor_thread and self._monitor_thread.is_alive():
            backend_logger.info("The monitor is already running.")
            return

        backend_logger.info("Starting the C process monitor in a background thread...")
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._run_and_monitor, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        """!
        @brief Stops the monitored process and cleans up associated resources.
        """
        backend_logger.info("Starting the cleanup routine...")
        self._stop_event.set() # Signal the monitoring loop to stop
        
        if self.process and self.process.poll() is None:
            backend_logger.info(f"Terminating the C process with PID: {self.process.pid}...")
            self.process.kill()
            self.process.wait()
            backend_logger.info("C process terminated.")
        
        clean_socket(self.socket_path)
        backend_logger.info("Cleanup complete.")