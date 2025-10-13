"""!
@file main.py
@brief Main application entry point for Spectrum Sensing Node.
"""

import asyncio
import datetime
import pathlib
import random
import signal
import sys
from typing import Optional

import httpx

# local imports
import libs
from utils import TimeHelper

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
    heartbeat_timer = TimeHelper(ALIVE_HEARTBEAT)

    async with httpx.AsyncClient() as client:
        while not stop_event.is_set():
            if heartbeat_timer.is_ready():
                new_job = await http_post_alive(client)
                if new_job:
                    jobs_tail.append(new_job)
                    if len(jobs_tail) > MAX_JOBS_TAIL:
                        jobs_tail.pop(0)

            await dummy_jobs()

            # Sleep but allow immediate wake on stop_event
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=LOOP_SLEEP_INTERVAL)
            except asyncio.TimeoutError:
                # timeout expired, continue loop
                pass
            except asyncio.CancelledError:
                break

    # Optionally: do final flush/cleanup here
    print("Worker loop exiting, final jobs_tail length:", len(jobs_tail))


async def main() -> None:
    """
    Set up graceful shutdown handlers and run the worker loop until signaled.
    """
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    # Signal handlers — prefer loop.add_signal_handler, fallback to signal.signal
    def _set_stop_event():
        if not stop_event.is_set():
            print("Shutdown signal received — stopping...")
            stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _set_stop_event)
        except NotImplementedError:
            # Fallback for platforms that don't support add_signal_handler (e.g. Windows sometimes)
            signal.signal(sig, lambda s, f: loop.call_soon_threadsafe(_set_stop_event))

    print(f"Starting worker at {datetime.datetime.now()}")
    worker = asyncio.create_task(worker_loop(stop_event))

    # Wait until stop_event is triggered
    try:
        await stop_event.wait()
    finally:
        # Initiate cancellation and allow cleanup
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass

    print(f"Worker stopped at {datetime.datetime.now()}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # final fallback
        print("KeyboardInterrupt received, exiting.")
        sys.exit(0)