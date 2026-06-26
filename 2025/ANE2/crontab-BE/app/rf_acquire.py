#!/usr/bin/env python3
"""!
@file rf_acquire.py
@brief CLI wrapper for RF signal acquisition using the shared C library.
"""
import sys
import cfg
import requests
import time
import json
from typing import Any, List

from libs import acquire_signal, init_acquire_lib

log = cfg.get_logger()

if cfg.VERBOSE:
    log.info("Started")

#dummy
def get_gps():
    import random
    return {
        "lat": random.uniform(-90.0, 90.0),
        "lng": random.uniform(-180.0, 180.0),
        "alt": random.uniform(0, 5000),  #m
    }

def main():
    if len(sys.argv) != 5:
        log.error("Use it as: acquire_runner.py <f_min_Hz> <f_max_Hz> <resolution> <antenna_port>")
        sys.exit(2)

    try:
        f_min = float(sys.argv[1])
        f_max = float(sys.argv[2])
        resolution = int(sys.argv[3])
        antenna_port = int(sys.argv[4])
    except ValueError as e:
        log.error("Invalid arguments: %s", e)
        sys.exit(3)

    try:
        lib = init_acquire_lib(cfg.ACQUIRE_PATH)
    except OSError as e:
        log.error("Failed initing shared library (acquire.so): %s", e)
        sys.exit(4)

    result = acquire_signal(lib, f_min, f_max, resolution, antenna_port)
    if not result:
        log.error("Error acquiring signal (acquire.so) -> result falsy")
        sys.exit(5)

    post_dict = {
        "Pxx": result,
        "gps": get_gps(),
        "timestamp": int(time.time() * 1000),  # ms unix
    }
    if cfg.VERBOSE:
        log.info("data to POST: %s", post_dict)

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(cfg.API_URL + cfg.DATA_URL, json=post_dict, headers=headers, timeout=5)
        
        resp.raise_for_status()
        try:
            body = resp.json()
            if cfg.VERBOSE:
                log.info("POST OK, JSON response: %s", body)
        except ValueError:
            if cfg.VERBOSE:
                log.info("POST OK")

    except requests.exceptions.Timeout:
        log.error("Timeout to send json POST")
 
    except requests.exceptions.ConnectionError as e:
        log.error("ConnectionError in POST")

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        text = e.response.text[:400] if e.response is not None else ""
        log.error("HTTP error %s in POST: %s", status, text)

    except requests.exceptions.RequestException as e:
        log.error("Error: %s", e)

    sys.exit(0)

if __name__ == "__main__":
    main()
