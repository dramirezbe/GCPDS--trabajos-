"""@file utils/app_handler.py
@brief Lightweight asyncio application runner and POSIX signal helpers.

Detailed Description
--------------------
This module contains small utilities intended for short-running asyncio
applications (for example: Raspberry Pi background workers). The primary
helpers are:

  - :func:`setup_posix_signal_handlers` — installs POSIX signal handlers
    (SIGINT, SIGTERM) that set an :class:`asyncio.Event` used to request
    shutdown.
  - :func:`sleep_or_stop` — await up to a timeout or exit early if the
    provided stop event becomes set.
  - :func:`run_until_stopped` — high-level runner that starts a worker
    coroutine, installs POSIX signal handlers, and cancels the worker when
    a stop signal is received.

@note This module intentionally does not change the default runtime or
behaviour of the supplied worker coroutine; it only orchestrates lifecycle
(signals, cancellation, join). The signal installation uses
:py:meth:`asyncio.AbstractEventLoop.add_signal_handler`, which is supported on
POSIX platforms (Linux, macOS). On some non-POSIX platforms (notably some
Windows configurations) ``add_signal_handler`` may raise ``NotImplementedError``.
"""

from __future__ import annotations
import asyncio
import signal
from typing import Callable, Coroutine

# type: worker_coro is a callable that receives an asyncio.Event and returns a coroutine
WorkerCoroType = Callable[[asyncio.Event], Coroutine[None, None, None]]
"""Type alias for worker coroutine factories.

A WorkerCoroType is a zero-argument *callable* which accepts a single
``asyncio.Event`` used as a stop request, and returns an awaitable coroutine
that performs the background work:

    async def worker_loop(stop_event: asyncio.Event) -> None:
        ...

This module expects the callable passed to :func:`run_until_stopped` to
conform to this signature.
"""


def setup_posix_signal_handlers(stop_event: asyncio.Event) -> None:
    """
    Install POSIX signal handlers that set the provided ``stop_event``.

    The handlers are installed on the currently running asyncio event loop
    (``asyncio.get_running_loop()``) and will call ``stop_event.set()`` when
    SIGINT or SIGTERM are received, causing any code awaiting ``stop_event``
    to resume and perform shutdown.

    @param stop_event:
        An :class:`asyncio.Event` that will be set when a POSIX termination
        signal is received.

    @note:
        This function uses :py:meth:`asyncio.AbstractEventLoop.add_signal_handler`
        which is available on POSIX platforms. On platforms where this API is
        not implemented, ``add_signal_handler`` may raise
        ``NotImplementedError``. Callers that require cross-platform behavior
        should guard or catch that exception.

    @example
        >>> stop = asyncio.Event()
        >>> setup_posix_signal_handlers(stop)
    """
    loop = asyncio.get_running_loop()

    def _set_stop() -> None:
        if not stop_event.is_set():
            stop_event.set()

    # POSIX signal handlers (works on Raspberry Pi / Linux)
    loop.add_signal_handler(signal.SIGINT, _set_stop)
    loop.add_signal_handler(signal.SIGTERM, _set_stop)


async def sleep_or_stop(stop_event: asyncio.Event, timeout: float) -> None:
    """
    Await either until ``stop_event`` is set or until ``timeout`` seconds elapse.

    This utility is useful inside loops where you want to remain responsive to
    a shutdown request while still waiting for periodic work.

    Behavior:
      - If ``stop_event`` becomes set before ``timeout`` seconds, this coroutine
        returns immediately.
      - If the timeout elapses first, the function returns normally (no error).

    @param stop_event:
        An :class:`asyncio.Event` that indicates a stop request.
    @param timeout:
        The maximum number of seconds to wait.

    @return:
        None

    @example
        # inside async worker
        while not stop_event.is_set():
            do_work()
            await sleep_or_stop(stop_event, 5.0)
    """
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        # timeout expired -> continue loop
        return


async def run_until_stopped(worker_coro: WorkerCoroType) -> None:
    """
    High-level runner: start the worker coroutine, install POSIX signal
    handlers, wait until a signal sets the stop event, then cancel & await the
    worker to let it cleanup.

    The function performs the following steps:

      1. Create an ``asyncio.Event`` called ``stop_event``.
      2. Install POSIX signal handlers that set ``stop_event`` (SIGINT, SIGTERM).
      3. Create/launch the worker task using ``asyncio.create_task(worker_coro(stop_event))``.
      4. Await ``stop_event.wait()``.
      5. When the stop event becomes set, cancel the worker task and await it,
         suppressing ``asyncio.CancelledError`` so cleanup can complete.

    The worker coroutine should be cooperative and respond to the stop event —
    e.g. periodically check ``stop_event.is_set()`` or await ``stop_event.wait()``
    inside long-running operations.

    Example
    -------
    Usage in a script:

    >>> async def worker_loop(stop_event: asyncio.Event):
    ...     while not stop_event.is_set():
    ...         await do_periodic_work()
    ...
    >>> asyncio.run(run_until_stopped(worker_loop))

    @param worker_coro:
        A callable that accepts an :class:`asyncio.Event` and returns a coroutine.
        The returned coroutine will be scheduled as the worker task.

    @return:
        None
    """
    stop_event = asyncio.Event()
    setup_posix_signal_handlers(stop_event)

    # start worker
    worker = asyncio.create_task(worker_coro(stop_event))

    # wait until signal sets stop_event
    try:
        await stop_event.wait()
    finally:
        # request worker to stop and allow cleanup
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
