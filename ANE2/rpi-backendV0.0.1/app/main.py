"""@file main.py
@brief Main application entry point for Spectrum Sensing Node (functional, no classes).
"""
from __future__ import annotations

import asyncio
import pathlib
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple
import httpx
import os
import sys
from enum import Enum, auto

# local imports
import libs
from utils import TimeHelper, run_until_stopped, sleep_or_stop, append_job_tail, fill_final_alive_json, force_ntp_update_async

import dummy


# -------- CONFIG ----------
API_HOST = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"
JOBS_URL = "/jobs"
DATA_URL = "/data"

ALIVE_HEARTBEAT = 5  # seconds
NTP_FORCE_SYNC = 60 * 5 # seconds
MAX_JOBS_TAIL = 10
POST_DATA_RETRIES = 5
RETRY_DELAY_SECONDS = 10 # Delay before retrying a failed job

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.resolve()
METRICS_PATH = str((PROJECT_ROOT / "libs_C" / "metrics.so").resolve())
ACQUIRE_PATH = str((PROJECT_ROOT / "libs_C" / "acquire.so").resolve())

@asynccontextmanager
async def manage_resources(metrics_path: str, acquire_path: str):
    """Open/close resources cleanly."""
    metrics_lib = libs.init_metrics_lib(metrics_path)
    acquire_lib = libs.init_acquire_lib(acquire_path)
    async with httpx.AsyncClient(base_url=API_URL) as client:
        yield client, metrics_lib, acquire_lib


# -------- networking ----------
async def send_alive(
    client: httpx.AsyncClient,
    metrics_lib: Any,
    last_delta_ms: int,
    url: str = API_URL + JOBS_URL,
    timeout: float = 10.0,
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """
    Send one alive heartbeat.
    Always returns (measured_delta_ms, server_json_or_none).
    """
    metrics_json = await libs.request_metrics(metrics_lib)
    if not metrics_json:
        print("Skipping alive: metrics unavailable")
        return last_delta_ms, None

    payload = fill_final_alive_json(metrics_json, dummy.get_gps(), last_delta_ms)

    start = time.perf_counter()
    try:
        resp = await client.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        delta_ms = int((time.perf_counter() - start) * 1000)
        print(f"Alive heartbeat OK — RTT {delta_ms} ms")
        return delta_ms, resp.json()
    except Exception as e:
        delta_ms = int((time.perf_counter() - start) * 1000)
        print(f"Alive heartbeat failed — RTT {delta_ms} ms — {type(e).__name__}: {e}")
        return delta_ms, None


# -------- main worker ----------
class JobState(Enum):
    NO_JOBS = auto()
    ERROR_JOB = auto()
    DONE_JOB = auto()

def _get_job_param(job: Dict[str, Any], names: List[str], cast, param_name: str):
    """
    Try several possible names for a job parameter and cast it.
    Raises TypeError/ValueError if missing or wrong type.
    """
    for n in names:
        v = job.get(n)
        if v is not None:
            return cast(v)
    raise TypeError(f"Missing required job parameter '{param_name}' (tried: {names})")

async def do_jobs(jobs_tail, acquire_lib, client: httpx.AsyncClient) -> JobState:
    if len(jobs_tail) < 1:
        return JobState.NO_JOBS
    current_job = jobs_tail[0]

    # The server may send demodulation: null -> becomes None in Python.
    demod_mode = current_job.get("demodulation")

    # Treat demodulation as active only if it's a dict with a known 'type'
    if isinstance(demod_mode, dict) and demod_mode.get("type") in ("AM", "FM"):
        # TODO: implement actual demodulation handling here.
        print("Start demodulation job (Not implemented). Demodulation block:", demod_mode)
        # If you want to send demodulated data, implement logic and POST it here.
        return JobState.DONE_JOB

    # Otherwise treat it as a plain spectrum acquisition job.
    try:
        # support both possible server key names (robustness)
        start_freq_hz = float(_get_job_param(current_job, ["start_freq_hz", "start_frequency_hz"], float, "start_freq_hz"))
        end_freq_hz = float(_get_job_param(current_job, ["end_freq_hz", "end_frequency_hz"], float, "end_freq_hz"))
        resolution_hz = int(_get_job_param(current_job, ["resolution_hz", "resolution"], int, "resolution_hz"))
        antenna_port = int(_get_job_param(current_job, ["antenna_port", "antenna"], int, "antenna_port"))
        print(
            "Doing acquisition job with parameters:",
            f"start_freq_hz={start_freq_hz}, end_freq_hz={end_freq_hz}, resolution_hz={resolution_hz}, antenna_port={antenna_port}"
        )
    except (TypeError, ValueError) as e:
        print(f"Error: Invalid job parameters in job {current_job}. Discarding. Error: {e}")
        return JobState.DONE_JOB  # Discard malformed job

    # Perform the acquisition (existing libs.request_signal)
    try:
        Pxx = await libs.request_signal(acquire_lib, start_freq_hz, end_freq_hz, resolution_hz, antenna_port)
    except Exception as e:
        print(f"Error during acquisition: {e}")
        return JobState.ERROR_JOB

    timestamp = time.time_ns()

    dict_acquisition = {
        "Pxx": Pxx,
        "start_frequency_hz": start_freq_hz,   # keep both names if your server expects one of them
        "start_freq_hz": start_freq_hz,
        "end_frequency_hz": end_freq_hz,
        "end_freq_hz": end_freq_hz,
        "resolution_hz": resolution_hz,
        "antenna_port": antenna_port,
        "timestamp_ns": timestamp
    }

    try:
        resp_acquisition = await client.post(API_URL + DATA_URL, json=dict_acquisition, timeout=10)
        resp_acquisition.raise_for_status()
        print("Acquisition data sent successfully.")
    except httpx.RequestError as e:
        print(f"Error sending acquisition data: {e}")
        return JobState.ERROR_JOB
    except Exception as e:
        print(f"An unexpected error occurred during data submission: {e}")
        return JobState.ERROR_JOB

    return JobState.DONE_JOB

async def worker_loop(stop_event: asyncio.Event) -> None:
    print("Starting worker loop")

    heartbeat_timer = TimeHelper(mode="timer", tick_mode="event", interval_seconds=ALIVE_HEARTBEAT, start_immediately=True)
    ntp_timer = TimeHelper(mode="timer", tick_mode="event", interval_seconds=NTP_FORCE_SYNC, start_immediately=True)
    
    delta_t_ms = 0
    jobs_tail: List[Dict[str, Any]] = []
    # This counter is for the CURRENT job at the head of the queue. It gets reset
    # when a job is successfully completed or finally discarded.
    current_job_retry_count = 0

    try:
        async with manage_resources(METRICS_PATH, ACQUIRE_PATH) as (client, metrics_lib, acquire_lib):
            await asyncio.sleep(1)

            # first immediate call
            delta_t_ms, server_json = await send_alive(client, metrics_lib, delta_t_ms)
            append_job_tail(jobs_tail, server_json)

            while not stop_event.is_set():
                if ntp_timer.is_ready():
                    print("Forcing NTP sync")
                    await force_ntp_update_async()
                
                if heartbeat_timer.is_ready():
                    delta_t_ms, server_json = await send_alive(client, metrics_lib, delta_t_ms)
                    append_job_tail(jobs_tail, server_json)

                job_state = await do_jobs(jobs_tail, acquire_lib, client)

                match job_state:
                    case JobState.NO_JOBS:
                        # No work to do, wait peacefully.
                        await sleep_or_stop(stop_event, 0.5)

                    case JobState.ERROR_JOB:
                        current_job_retry_count += 1
                        print(f"Job failed. Attempt {current_job_retry_count}/{POST_DATA_RETRIES}.")

                        if current_job_retry_count >= POST_DATA_RETRIES:
                            print("Max retries reached. Discarding job.")
                            jobs_tail.pop(0) # Give up and remove the job
                            current_job_retry_count = 0 # Reset for the next job
                        else:
                            # Wait before the next attempt on this same job
                            print(f"Will retry after a delay of {RETRY_DELAY_SECONDS} seconds.")
                            await sleep_or_stop(stop_event, RETRY_DELAY_SECONDS)

                    case JobState.DONE_JOB:
                        print("Job done, removing from queue.")
                        jobs_tail.pop(0)
                        # Reset retry counter for the next new job.
                        current_job_retry_count = 0
                        # Immediately try to process the next job without delay.

    finally:
        print(f"Worker loop stopped. Jobs remaining in queue: {jobs_tail}")
        try:
            await heartbeat_timer.stop_async()
        except Exception:
            print("heartbeat_timer.stop_async failed")
        try:
            await ntp_timer.stop_async()
        except Exception:
            print("ntp_timer.stop_async failed")

# -------- entrypoint ----------
async def main():
    print("Starting main()")
    await run_until_stopped(worker_loop)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script needs to be run with sudo to restart system services.", file=sys.stderr)
        sys.exit(1)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, exiting.")