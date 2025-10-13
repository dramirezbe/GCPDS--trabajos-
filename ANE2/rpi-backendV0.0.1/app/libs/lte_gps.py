"""!
@file libs/lte_gps.py
@brief lte_gps shared library module
"""

import ctypes
import sys

def init_lte_gps_lib(lte_gps_path):
    """
    Load lte_gps shared library and configure ctypes types.
    Returns the loaded library object.
    """
    # Load the shared library
    try:
        lib = ctypes.CDLL(lte_gps_path)
    except OSError as e:
        print(f"Error loading shared library (lte_gps.so): {e}", file=sys.stderr)
        raise


        # Missing Code Here


    return lib