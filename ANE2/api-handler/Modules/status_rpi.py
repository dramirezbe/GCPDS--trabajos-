"""
@file status_rpi.py
@brief Library to check RPi status (CPU, RAM, Storage) by wrapping a C program.
"""
import ctypes
import os

# Define the location of the shared library.
# This makes the path relative to this file's location.
_LIB_PATH = os.path.join(os.path.dirname(__file__), 'status_rpi.so')

# --- Load the C Library ---
try:
    # Load the shared library from the defined path.
    _libc = ctypes.CDLL(_LIB_PATH)
except OSError as e:
    print(f"Error: Could not load the C library from {_LIB_PATH}")
    print(f"Details: {e}")
    # Exit or raise an exception if the library is essential.
    _libc = None

# --- Define C function prototypes for ctypes ---
if _libc:
    # Define the return type for get_status()
    # It returns a C-style string (pointer to char).
    _libc.get_status.restype = ctypes.c_char_p
    
    # Define the argument types for free_status_string()
    # It takes one argument: a generic pointer (void*).
    _libc.free_status_string.argtypes = [ctypes.c_void_p]
    # It doesn't return anything.
    _libc.free_status_string.restype = None


def get_rpi_status():
    """
    @brief Calls the C function to get RPi status and handles memory correctly.
    @return A string with the status in JSON format, or None on error.
    """
    if not _libc:
        print("C library is not loaded. Cannot get status.")
        return None

    # Call the C function to get the status string pointer.
    status_ptr = _libc.get_status()

    if not status_ptr:
        print("C function get_status() returned a null pointer.")
        return None

    try:
        # Decode the byte string from the C pointer into a Python string.
        # We create a copy of the data in Python's memory.
        status_string = status_ptr.decode('utf-8')
    except (UnicodeDecodeError, AttributeError) as e:
        print(f"Error decoding the string from C: {e}")
        status_string = None
    finally:
        # --- IMPORTANT MEMORY MANAGEMENT ---
        # Now that we have our own Python copy of the string,
        # we must tell the C library to free the original memory it allocated.
        _libc.free_status_string(status_ptr)

    return status_string