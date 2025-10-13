"""!
@file main.py
@brief Main application entry point for Spectrum Sensing Node.
"""
import asyncio
import pathlib
import random
import sys
from typing import Optional

import httpx

# local imports
import libs
from utils import TimeHelper, run_until_stopped

# -------- API url ----------
API_HOST = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"
JOBS_URL = "/jobs"
DATA_URL = "/data"

# -------- DEFAULTS ----------
ALIVE_HEARTBEAT = 30  # seconds
LOOP_SLEEP_INTERVAL = 1  # seconds
MAX_JOBS_TAIL = 10  # max number of jobs to keep in memory, if full stop adding

# file paths
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.resolve()
METRICS_PATH = str((PROJECT_ROOT / "libs_C" / "metrics.so").resolve())


async def request_metrics(path: str) -> Optional[dict]:
    """
    Requests metrics from the C library in a non-blocking way.
    Returns JSON metrics dict on success, None on failure.
    """
    def sync_get_metrics():
        metrics_lib = libs.init_metrics_lib(path)
        raw_metrics = libs.get_metrics_system(metrics_lib)
        if not raw_metrics:
            print("Shared library error(metrics.so), null data returned", file=sys.stderr)
            return None
        return libs.metrics_to_json(raw_metrics)

    return await asyncio.to_thread(sync_get_metrics)


async def http_post_alive(client: httpx.AsyncClient) -> Optional[dict]:
    """
    Gets metrics and posts them to the server.
    Returns the new job from the server response, or None on failure.
    """
    metrics_json = await request_metrics(METRICS_PATH)
    if not metrics_json:
        print("Skipping alive signal due to metrics failure.")
        return None

    try:
        resp = await client.post(API_URL + JOBS_URL, json=metrics_json, timeout=10.0)
        resp.raise_for_status()
        print("Alive sent successfully.")
        return resp.json()
    except httpx.RequestError as e:
        print(f"Error sending alive: {e}")
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        print(f"Error response {status} while sending alive: {e}")
    except Exception as e:
        print(f"Unexpected error while sending alive: {e}")

    return None


async def dummy_jobs() -> None:
    """Simulates background work."""
    possible_jobs = ["completed", "failed", "in_progress"]
    print(f"Doing dummy job, status: {random.choice(possible_jobs)}")


async def worker_loop(stop_event: asyncio.Event) -> None:
    """
    Main worker loop: posts heartbeat when timer ready, runs dummy job,
    and sleeps in small intervals to remain responsive to shutdown.
    """
    jobs_tail = []
    heartbeat_timer = TimeHelper(mode="timer", interval_seconds=ALIVE_HEARTBEAT, tick_mode="event", start_immediately=True)

    try:


        async with httpx.AsyncClient() as client:
            while not stop_event.is_set():
                if heartbeat_timer.is_ready():
                    new_job = await http_post_alive(client)
                    if new_job:
                        jobs_tail.append(new_job)
                        if len(jobs_tail) > MAX_JOBS_TAIL:
                            jobs_tail.pop(0)

                await dummy_jobs()

                await asyncio.sleep(0.5)
    finally:
        await heartbeat_timer.stop_async()
        print("Worker exiting cleanly.")


async def main() -> None:
    # high-level one-liner: runs worker_loop until a POSIX signal arrives
    await run_until_stopped(worker_loop)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # fallback (shouldn't be reached if signals installed correctly)
        print("KeyboardInterrupt received, exiting.")