"""@file main.py
@brief Main application entry point for Spectrum Sensing Node (functional, no classes).
"""
from __future__ import annotations

import asyncio
import pathlib
import random
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

import httpx

# local imports
import libs
from utils import TimeHelper, run_until_stopped, sleep_or_stop


# -------- CONFIG ----------
API_HOST = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"
JOBS_URL = "/jobs"

ALIVE_HEARTBEAT = 10  # seconds
MAX_JOBS_TAIL = 10

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.resolve()
METRICS_PATH = str((PROJECT_ROOT / "libs_C" / "metrics.so").resolve())


# -------- helpers ----------
def get_gps() -> Dict[str, float]:
    """Simulated GPS data (replace with real GPS call)."""
    return {
        "lat": 37.7749 + random.uniform(-0.01, 0.01),
        "lng": -122.4194 + random.uniform(-0.01, 0.01),
        "alt": 30 + random.uniform(-5, 5),
    }


def fill_final_alive_json(metrics: Dict[str, Any], gps: Dict[str, float], delta_t_ms: int) -> Dict[str, Any]:
    """Compose the alive JSON payload."""
    return {
        "device": metrics["device"],
        "metrics": metrics["metrics"],
        "gps": gps,
        "delta_t": int(delta_t_ms),
    }


def append_job_tail(jobs_tail: List[Dict[str, Any]], job: Optional[Dict[str, Any]], max_tail: int = MAX_JOBS_TAIL) -> None:
    """Append job payload to tail, keep bounded length."""
    if not job:
        return
    jobs_tail.append(job)
    if len(jobs_tail) > max_tail:
        jobs_tail.pop(0)


@asynccontextmanager
async def manage_resources(metrics_path: str):
    """Open/close resources cleanly."""
    metrics_lib = libs.init_metrics_lib(metrics_path)
    async with httpx.AsyncClient() as client:
        yield client, metrics_lib


# -------- dummy jobs simulation ----------
async def dummy_jobs():
    """Simulated job handler."""
    statuses = ["in_progress", "failed", "completed"]
    for _ in range(random.randint(1, 3)):
        status = random.choice(statuses)
        print(f"Doing dummy job, status: {status}")
        await asyncio.sleep(0.1)


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

    payload = fill_final_alive_json(metrics_json, get_gps(), last_delta_ms)

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
async def worker_loop(stop_event: asyncio.Event) -> None:
    print("Starting worker loop")

    heartbeat_timer = TimeHelper(mode="timer", tick_mode="event", interval_seconds=ALIVE_HEARTBEAT, start_immediately=True)
    delta_t_ms = 0
    jobs_tail: List[Dict[str, Any]] = []

    try:
        async with manage_resources(METRICS_PATH) as (client, metrics_lib):
            await asyncio.sleep(1)

            # first immediate call
            new_delta, server_json = await send_alive(client, metrics_lib, delta_t_ms)
            delta_t_ms = new_delta
            append_job_tail(jobs_tail, server_json)

            while not stop_event.is_set():
                if heartbeat_timer.is_ready():
                    new_delta, server_json = await send_alive(client, metrics_lib, delta_t_ms)
                    delta_t_ms = new_delta
                    append_job_tail(jobs_tail, server_json)

                await dummy_jobs()
                await sleep_or_stop(stop_event, 0.5)

    finally:
        print(f"Jobs recorded: {jobs_tail}")


# -------- entrypoint ----------
async def main():
    print("Starting main()")
    await run_until_stopped(worker_loop)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, exiting.")
