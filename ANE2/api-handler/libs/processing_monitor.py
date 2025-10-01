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

class ProcessingMonitor:
    """!
    @brief A class to launch, monitor, and manage a secondary process in a background thread.
    
    This class handles the lifecycle of an external executable, ensuring it is always running.
    It will automatically restart the process if it terminates unexpectedly. It also captures
    and logs the standard output and standard error streams of the managed process.
    """
    
    DECORATOR = "[Backend]"
    DECORATOR_PROCESSING = "[processing_module]"
    DECORATOR_PROCESSING_ERROR = "[processing_module_ERROR]"

    def __init__(self, executable_path, socket_path=None):
        """!
        @brief Initializes the ProcessingMonitor.
        
        @param executable_path: The file path to the executable that will be monitored.
        @type executable_path: str
        @param socket_path: Optional. The file path to a socket that should be cleaned up
                           before the process starts and after it stops.
        @type socket_path: str, optional
        
        @raise FileNotFoundError: If the executable specified by executable_path does not exist.
        """
        if not os.path.exists(executable_path):
            raise FileNotFoundError(f"The executable was not found at: {executable_path}")
            
        self.executable_path = executable_path
        self.socket_path = socket_path
        self.process = None
        self._monitor_thread = None
        
        atexit.register(self.stop)

    def _log(self, *args, **kwargs):
        """!
        @brief Logs a message with the default decorator.
        
        @param args: Variable length argument list to be passed to the print function.
        @param kwargs: Arbitrary keyword arguments to be passed to the print function.
        """
        print(self.DECORATOR, *args, **kwargs)

    def _log_c_output(self, decorator, message):
        """!
        @brief Logs a message from the monitored process's output stream.
        
        @param decorator: The decorator string to prepend to the message.
        @type decorator: str
        @param message: The message to be logged.
        @type message: str
        """
        print(decorator, message.strip())

    def _stream_reader(self, stream, decorator):
        """!
        @brief Reads and logs lines from a given stream until it closes.
        
        This method is intended to be run in a separate thread to continuously read
        from a process's stdout or stderr.
        
        @param stream: The stream to read from (e.g., process.stdout).
        @type stream: io.BufferedReader
        @param decorator: The decorator to use when logging messages from the stream.
        @type decorator: str
        """
        try:
            for line in iter(stream.readline, ''):
                if line:
                    self._log_c_output(decorator, line)
        finally:
            stream.close()

    def _run_and_monitor(self):
        """!
        @brief The main loop that runs and monitors the external process.
        
        This method is executed in a background thread. It starts the process,
        monitors its state, and restarts it if it terminates. It also sets up
        threads to capture and log the process's output.
        """
        while True:
            try:
                if self.socket_path and os.path.exists(self.socket_path):
                    self._log(f"Deleting old socket at {self.socket_path}...")
                    os.unlink(self.socket_path)

                self._log(f"Starting process: {self.executable_path}")
                self.process = subprocess.Popen(
                    [self.executable_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                self._log(f"C module started successfully with PID: {self.process.pid}")

                stdout_thread = threading.Thread(
                    target=self._stream_reader, 
                    args=(self.process.stdout, self.DECORATOR_PROCESSING), 
                    daemon=True
                )
                stderr_thread = threading.Thread(
                    target=self._stream_reader, 
                    args=(self.process.stderr, self.DECORATOR_PROCESSING_ERROR), 
                    daemon=True
                )
                stdout_thread.start()
                stderr_thread.start()

                self.process.wait()

                self._log(f"ATTENTION! The C process with PID {self.process.pid} has terminated.")
                exit_code = self.process.returncode
                if exit_code != 0:
                    self._log(f"The process failed with exit code: {exit_code}")
                else:
                    self._log("The process finished without an explicit error code.")

            except Exception as e:
                self._log(f"An unexpected error occurred in the Python monitor: {e}")

            self._log("Attempting to restart the process in 5 seconds...")
            time.sleep(5)

    def start(self):
        """!
        @brief Starts the background monitoring thread.
        
        If the monitor thread is not already running, this method will create and
        start a new daemon thread that executes the _run_and_monitor loop.
        """
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._log("The monitor is already running.")
            return

        self._log("Starting the C process monitor in a background thread...")
        self._monitor_thread = threading.Thread(target=self._run_and_monitor, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        """!
        @brief Stops the monitored process and cleans up associated resources.
        
        This method terminates the child process if it is running and deletes the
        socket file if one was specified. It is registered to be called automatically
        on program exit.
        """
        self._log("Starting the cleanup routine...")
        if self.process and self.process.poll() is None:
            self._log(f"Terminating the C process with PID: {self.process.pid}...")
            self.process.kill()
            self.process.wait()
            self._log("C process terminated.")
        
        clean_socket(self.socket_path)
        
        self._log("Cleanup complete.")