"""!
@file libs/acquire.py
@brief acquire shared library module
"""

import ctypes
import sys
import asyncio
from typing import Optional, List

def init_acquire_lib(library_path: str):
    """
    Load the acquire shared library and configure ctypes types.
    Returns the loaded library object.
    """
    try:
        # Load the shared library
        lib = ctypes.CDLL(library_path)
    except OSError as e:
        print(f"Error loading shared library(acquire.so): {e}", file=sys.stderr)
        raise

    # Define the argument types for the acquire function
    lib.acquire_signal.argtypes = [
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
    ]

    # Define the return type for the acquire function.
    # It returns a pointer to a double.
    lib.acquire_signal.restype = ctypes.POINTER(ctypes.c_double)

    # Define the argument types for the free_signal_array function
    lib.free_signal_array.argtypes = [ctypes.POINTER(ctypes.c_double)]
    lib.free_signal_array.restype = None

    return lib

def acquire_signal(acquire_lib, start_freq_hz: float, end_freq_hz: float, resolution_hz: int, antenna_port: int) -> Optional[List[float]]:
    """
    Calls the C library to acquire a signal and returns it as a Python list of floats.
    
    This function handles the full lifecycle: calling the C function, converting the
    resulting pointer to a Python list, and ensuring the C-allocated memory is freed.
    """
    signal_ptr = None
    try:
        # Call the C function with the specified parameters
        signal_ptr = acquire_lib.acquire_signal(start_freq_hz, end_freq_hz, resolution_hz, antenna_port)
        
        # Check for a NULL pointer, which indicates an error in the C function
        if not signal_ptr:
            print("Error: acquire_signal returned a NULL pointer (acquire.so)", file=sys.stderr)
            return None
        
        # Convert the C array pointer to a Python list
        # This copies the data from C memory into Python-managed memory
        pxx = [signal_ptr[i] for i in range(resolution_hz)]
        return pxx
        
    finally:
        # This block is crucial. It always runs, even if an error occurs above.
        # If signal_ptr is not None, we must free the memory allocated by the C library.
        if signal_ptr:
            try:
                acquire_lib.free_signal_array(signal_ptr)
            except Exception as e:
                # Avoid crashing on free errors; log to stderr for debugging
                print(f"Warning: failed to free C pointer: {e}", file=sys.stderr)


async def request_signal(acquire_lib, start_freq_hz: float, end_freq_hz: float, resolution_hz: int, antenna_port: int) -> Optional[List[float]]:
    """
    Requests a signal from the already-loaded C library in a non-blocking way.
    
    This is an async wrapper around the synchronous acquire_signal function.
    """
    def sync_acquire_signal():
        """The synchronous part that will be run in a separate thread."""
        return acquire_signal(acquire_lib, start_freq_hz, end_freq_hz, resolution_hz, antenna_port)

    # Run the synchronous C-call in a separate thread to avoid blocking the
    # asyncio event loop.
    return await asyncio.to_thread(sync_acquire_signal)