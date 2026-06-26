#!/usr/bin/env python3
"""!
@file main.py
@brief Minimal high-level main for Raspberry Pi 5 (POSIX-only signals).
       Includes small helper functions to keep the main loop clean.
"""
import asyncio
from utils import TimeHelper, run_until_stopped


def heavy_work_simulation() -> int:
    """Simulated heavy CPU work (replace with real .so call)."""
    s = 0
    for i in range(5_000_000):
        s += i
    return s


async def worker_loop(stop_event: asyncio.Event) -> None:
    """
    Example worker:
      - timer_a: event-style timer (use is_ready())
      - counter: stopwatch to measure each heavy_work_simulation call
    """
    timer_a = TimeHelper(mode="timer", interval_seconds=2.0, tick_mode="event", start_immediately=True)
    timer_b = TimeHelper(mode="timer", interval_seconds=5.0, tick_mode="event", start_immediately=True)
    counter = TimeHelper(mode="count")

    try:
        while not stop_event.is_set():
            if timer_a.is_ready():
                print("timer_a tick (2s)")

            if timer_b.is_ready():
                print("timer_b tick (5s)")

            # measure heavy work off the event loop
            counter.init()
            await asyncio.to_thread(heavy_work_simulation)
            elapsed = counter.stop()  # float seconds
            print(f"Measured heavy_work_simulation: {elapsed:.3f} sec")
            counter.reset()

            # remain responsive to shutdown (wake early if stop_event.set())
            await asyncio.sleep(0.5)
            # alternative: await sleep_or_stop(stop_event, 0.5) if you prefer helper usage
    finally:
        # graceful timer shutdown (awaitable)
        await timer_a.stop_async()
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