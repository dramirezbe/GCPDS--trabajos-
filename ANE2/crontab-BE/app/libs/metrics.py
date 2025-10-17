"""!
@file libs/metrics.py
@brief metrics shared library module
"""

import ctypes
import sys
import asyncio
from typing import Optional, Tuple

import cfg

log = cfg.get_logger()

def init_metrics_lib(metrics_path):
    """
    Load the metrics shared library and configure ctypes types.
    Returns the loaded library object.
    """
    # Load the shared library
    try:
        lib = ctypes.CDLL(metrics_path)
    except OSError as e:
        log.error(f"Error loading shared library(metrics.so): {e}")
        raise

    # Return raw pointer from get_system_info to avoid ctypes magic.
    lib.get_system_info.restype = ctypes.c_void_p
    lib.get_system_info.argtypes = []

    # Make the free wrapper accept c_void_p
    lib.free_system_info_string.restype = None
    lib.free_system_info_string.argtypes = [ctypes.c_void_p]

    return lib


def get_metrics_system(metrics_lib):
    """
    Calls the C library to get system information (percentage-only format)
    and returns it as a Python string. Uses raw pointers and ctypes.string_at
    so we can call the library's free correctly.
    """
    c_ptr = metrics_lib.get_system_info()
    if not c_ptr:
        return None

    try:
        raw_bytes = ctypes.string_at(c_ptr)  # reads until '\0'
        py_string = raw_bytes.decode("utf-8", errors="replace")
    finally:
        # Always free the pointer returned by the library
        try:
            metrics_lib.free_system_info_string(c_ptr)
        except Exception:
            # Avoid crashing on free errors; log to stderr
            log.warning("failed to free C string pointer")

    return py_string

async def request_metrics(metrics_lib) -> Optional[dict]:
    """Requests metrics from the already-loaded C library in a non-blocking way."""
    def sync_get_metrics():
        raw_metrics = get_metrics_system(metrics_lib)
        if not raw_metrics:
            log.error("Shared library error(metrics.so): null data returned")
            return None
        try:
            return metrics_to_json(raw_metrics)
        except ValueError as e:
            log.error(f"Failed parsing metrics from shared lib: {e}")
            return None

    return await asyncio.to_thread(sync_get_metrics)


def metrics_to_json(metrics_string):
    """
    Parse the C-library metrics string into a structured Python dict.

    Expected format:
      "<per-core-pct|...>,<ram_pct>,<overall_cpu_pct>,<swap_pct>,<disk_pct>,<temp_c>,<mac_address>"

    Returns:
    {
      "device": "<mac>",
      "metrics": {
         "cpu": [float, ...],  # per-core percentages (floats with 2 decimals)
         "ram": float,
         "swap": float,
         "disk": float,
         "temp_c": float
      }
    }
    Raises ValueError for malformed input.
    """
    if not metrics_string:
        raise ValueError("Empty metrics string")

    parts = metrics_string.strip().split(",")
    if len(parts) != 7:
        raise ValueError(f"Invalid metrics string: expected 7 fields, got {len(parts)} -> {metrics_string!r}")

    cores_part, ram_part, overall_cpu_part, swap_part, disk_part, temp_part, mac_part = parts

    # Parse per-core percentages (e.g. "57.32|10.15|11.00|23.90")
    per_core = []
    if cores_part:
        for s in cores_part.split("|"):
            s = s.strip()
            if s == "":
                continue
            try:
                per_core.append(round(float(s), 2))
            except ValueError:
                raise ValueError(f"Invalid per-core value: {s!r}")

    def to_float2(s, name):
        try:
            return round(float(s), 2)
        except ValueError:
            raise ValueError(f"Invalid numeric value for {name}: {s!r}")

    ram_pct = to_float2(ram_part, "ram")
    overall_cpu_pct = to_float2(overall_cpu_part, "overall_cpu")
    swap_pct = to_float2(swap_part, "swap")
    disk_pct = to_float2(disk_part, "disk")
    temp_c = to_float2(temp_part, "temp_c")
    mac = mac_part.strip()

    return {
        "device": mac,
        "metrics": {
            "cpu": per_core,
            "ram": ram_pct,
            "swap": swap_pct,
            "disk": disk_pct,
            "temp_c": temp_c
        }
    }
        