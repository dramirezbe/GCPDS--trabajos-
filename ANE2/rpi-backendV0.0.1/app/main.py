"""!
@file main.py
@brief Main file — loads metrics.so and prints percentage-only metrics
"""
#xtern
from fastapi import FastAPI
import httpx
import pathlib
import sys

# own
import libs

#--------API url----------
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
API_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"

#RESPONSE_URL = "/response"
REQUEST_URL = "/request"

# -------- DEFAULTS ----------
HEARTBEAT_REQUEST = 30  # in secs

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.resolve()
LIBS_C_DIR = (PROJECT_ROOT / "libs_C").resolve()
METRICS_PATH = str((PROJECT_ROOT / "libs_C" / "metrics.so").resolve())

def metrics_pipe(path):
    metrics_lib = libs.init_metrics_lib(path)
    raw_metrics = libs.get_metrics_system(metrics_lib)
    if not raw_metrics:
        print("No system information received from shared library.", file=sys.stderr)
        sys.exit(1)

    print("raw:", raw_metrics)

    json_metrics = libs.metrics_to_json(raw_metrics)
    print("json:", json_metrics)


if __name__ == "__main__":
    metrics_pipe(METRICS_PATH)


    