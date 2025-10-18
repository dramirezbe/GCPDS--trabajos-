"""@file utils/timers.py
@brief Minimal dual-mode timer helper (stopwatch + periodic timer).

Detailed module-level description
---------------------------------
This module implements :class:`TimeHelper`, a compact utility that supports two
modes of operation:

  - **Timer mode** (`mode="timer"`) — periodic timer that can use either an
    asyncio.Task-based backend (when a running event loop is available or
    provided) or a thread-based backend (for synchronous programs). The timer
    supports two tick modes:
      - `"event"`: external code calls :meth:`is_ready()` which observes a
        transient event (set/clear) when a tick occurs.
      - `"count"`: external code calls :meth:`get_ticks()` to obtain the
        number of ticks that occurred since last read.

  - **Count mode** (`mode="count"`) — a simple stopwatch (start/init, stop,
    reset, state) for elapsed-time measurement.

The same API object intentionally supports both backends while preserving a
consistent public API; internal event storage is typed to a small Protocol so
static checkers like Pylance/mypy accept both ``threading.Event`` and
``asyncio.Event`` implementations.

@see TimeHelper
"""

from __future__ import annotations
import time
import asyncio
import threading
from typing import Optional, Callable, Protocol


class _EventLike(Protocol):
    """
    Protocol describing the minimal subset of methods used from event-like
    objects. Both :class:`threading.Event` and :class:`asyncio.Event` satisfy
    this protocol.

    Methods
    -------
    set()
        Set the event (mark it as triggered).
    clear()
        Clear the event (mark it as not triggered).
    is_set() -> bool
        Query whether the event is currently set.
    """

    def set(self) -> None: ...
    def clear(self) -> None: ...
    def is_set(self) -> bool: ...


class TimeHelper:
    r"""
    @class TimeHelper
    @brief Minimal dual-mode timer helper.

    Detailed description
    --------------------
    The :class:`TimeHelper` object implements two orthogonal modes:

      * **Timer mode** (``mode="timer"``). Produces periodic ticks at a fixed
        `interval_seconds`. Two tick delivery options are supported:
          - **tick_mode="event"** — user polls :meth:`is_ready()` which clears
            and returns the transient event state (boolean).
          - **tick_mode="count"** — user polls :meth:`get_ticks()` which returns
            the number of ticks that occurred since the last call.

        The timer selects an asyncio-based backend when a running event loop
        is available (or when one is explicitly passed via the ``loop``
        parameter). Otherwise a thread-based backend is used.

      * **Count mode** (``mode="count"``). Acts as a stopwatch with
        :meth:`init`/:meth:`start`, :meth:`stop`, :meth:`state` and :meth:`reset`.

    Shutdown semantics
    ------------------
    For timer mode the object provides:
      - :meth:`stop_async` — cooperative asynchronous shutdown (awaitable).
      - :meth:`request_stop` / :meth:`stop` — synchronous stop request that is
        non-awaiting. For asyncio backend it will cancel the running task.

    Constants
    ---------
    MODE_TIMER : str
        Constant string (``"timer"``) identifying timer mode.
    MODE_COUNT : str
        Constant string (``"count"``) identifying count/stopwatch mode.

    @author
      (Generated documentation)
    """

    MODE_TIMER = "timer"
    MODE_COUNT = "count"

    def __init__(
        self,
        mode: str = MODE_TIMER,
        interval_seconds: Optional[float] = None,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        start_immediately: bool = True,
        tick_mode: str = "event",  # "event" or "count"
        on_tick: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Construct a TimeHelper.

        @param mode:
            Either ``"timer"`` or ``"count"``. In ``"count"`` mode the object
            behaves as a stopwatch; in ``"timer"`` mode it produces periodic
            ticks.
        @param interval_seconds:
            Required when ``mode=="timer"``; floating point seconds between ticks.
        @param loop:
            Optional asyncio event loop to use for the asyncio backend. If
            omitted the constructor will attempt to detect a running loop; if
            detection fails the thread-based backend is selected.
        @param start_immediately:
            If True, start the timer immediately for timer mode or start the
            stopwatch for count mode.
        @param tick_mode:
            For timer mode, either ``"event"`` (use :meth:`is_ready`) or
            ``"count"`` (use :meth:`get_ticks`).
        @param on_tick:
            Optional callable executed on each tick. For the asyncio backend it
            is scheduled with :meth:`loop.call_soon_threadsafe`; for the
            thread-based backend it is executed in a daemon thread.

        @raises ValueError:
            If ``mode`` is invalid or if ``interval_seconds`` is missing/invalid
            in timer mode.
        """
        mode = str(mode).lower()
        if mode not in (self.MODE_TIMER, self.MODE_COUNT):
            raise ValueError("mode must be 'timer' or 'count'")
        self.mode = mode

        # COUNT mode
        if self.mode == self.MODE_COUNT:
            self._start_time: Optional[float] = None
            self._elapsed: float = 0.0
            self._running: bool = False
            # nothing else required for count mode
            return

        # TIMER mode validation
        if interval_seconds is None or interval_seconds <= 0:
            raise ValueError("interval_seconds must be provided and > 0 for timer mode")
        self.interval = float(interval_seconds)
        self._tick_mode = tick_mode if tick_mode in ("event", "count") else "event"
        self._on_tick = on_tick

        # Choose backend: asyncio if running loop detected or provided
        self._loop = loop
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None

        self._use_asyncio = self._loop is not None

        # Typed / declared storage for event/counter/task/thread so static checkers are satisfied
        self._event: Optional[_EventLike] = None
        self._tick_count: int = 0
        self._tick_lock = threading.Lock()
        self._task: Optional[asyncio.Task] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_flag: Optional[threading.Event] = None

        if self._use_asyncio:
            self._event = asyncio.Event()
            self._task = None
        else:
            self._event = threading.Event()
            self._thread = None
            self._stop_flag = threading.Event()

        if start_immediately:
            self.start()

    # ---------------- COUNT (stopwatch) API ----------------
    def init(self) -> None:
        """
        Initialize/start the stopwatch (count mode).

        @note This method is only valid when the object was created with
              ``mode="count"``.

        @raises RuntimeError:
            If called when not in count mode.
        """
        if self.mode != self.MODE_COUNT:
            raise RuntimeError("init() is only available in count mode")
        if not self._running:
            self._start_time = time.monotonic()
            self._running = True

    def start(self) -> None:
        """
        Start operation for both modes.

        Behavior:
          - In count mode, this is an alias of :meth:`init`.
          - In timer mode, starts the asyncio Task or the thread backend.

        @raises RuntimeError:
            If the object was configured incorrectly (should not happen with
            validated constructor args).
        """
        if self.mode == self.MODE_COUNT:
            return self.init()

        # TIMER mode start
        if not self._use_asyncio:
            # thread backend
            t = getattr(self, "_thread", None)
            if t is not None and t.is_alive():
                return
            if self._stop_flag is not None:
                self._stop_flag.clear()
            else:
                self._stop_flag = threading.Event()
            self._thread = threading.Thread(target=self._thread_run, name="TimeHelperTimer", daemon=True)
            self._thread.start()
            return

        # asyncio backend
        if getattr(self, "_task", None) is None or getattr(self, "_task").done():
            if self._loop is None:
                self._loop = asyncio.get_running_loop()
            self._task = self._loop.create_task(self._async_run())

    def stop(self) -> float:
        """
        Stop operation and return elapsed seconds for count mode.

        Behavior:
          - In count mode, stop the stopwatch and return elapsed seconds.
          - In timer mode, perform a synchronous stop request: cancel the
            asyncio task (if used) or signal the thread-based backend and join.

        @return float
            Elapsed seconds for count mode; 0.0 for timer mode.
        """
        if self.mode == self.MODE_COUNT:
            if self._running and self._start_time is not None:
                now = time.monotonic()
                self._elapsed += now - self._start_time
                self._start_time = None
                self._running = False
            return self._elapsed

        # Timer-mode synchronous stop request
        if self._use_asyncio:
            task = getattr(self, "_task", None)
            self._task = None
            if task is not None and not task.done():
                task.cancel()
            if self._event is not None:
                try:
                    self._event.clear()
                except Exception:
                    pass
            return 0.0
        else:
            t = getattr(self, "_thread", None)
            self._thread = None
            if self._stop_flag is not None:
                self._stop_flag.set()
            if t is not None:
                t.join(timeout=2.0)
            if self._event is not None:
                try:
                    self._event.clear()
                except Exception:
                    pass
            return 0.0

    def state(self) -> float:
        """
        Return the currently accumulated elapsed time (count mode).

        @return float
            The elapsed seconds for the stopwatch.

        @raises RuntimeError:
            If called when not in count mode.
        """
        if self.mode != self.MODE_COUNT:
            raise RuntimeError("state() is only available in count mode")
        if self._running and self._start_time is not None:
            return self._elapsed + (time.monotonic() - self._start_time)
        return self._elapsed

    def reset(self) -> None:
        """
        Reset the stopwatch (count mode) to zero.

        @raises RuntimeError:
            If called when not in count mode.
        """
        if self.mode != self.MODE_COUNT:
            raise RuntimeError("reset() is only available in count mode")
        self._start_time = None
        self._elapsed = 0.0
        self._running = False

    def __enter__(self) -> "TimeHelper":
        """
        Context manager enter (count mode).
        Starts the stopwatch when used in a ``with`` statement.

        @raises RuntimeError:
            If used when not in count mode.
        """
        if self.mode != self.MODE_COUNT:
            raise RuntimeError("context manager only supported in count mode")
        self.init()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Context manager exit (count mode).
        Stops the stopwatch on context exit.
        """
        self.stop()

    # ---------------- TIMER API ----------------
    async def _async_run(self) -> None:
        """
        Internal asyncio-backed timer loop that sets/accumulates ticks.

        This coroutine runs until cancelled. On each tick it either sets the
        shared event (``tick_mode=="event"``) or increments an internal tick
        counter (``tick_mode=="count"``). If an ``on_tick`` callable was
        provided it is scheduled via :meth:`loop.call_soon_threadsafe`.

        @note This is an internal implementation detail and not part of the
              public API.
        """
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        next_fire = self._loop.time() + self.interval
        try:
            while True:
                await asyncio.sleep(max(0.0, next_fire - self._loop.time()))
                if self._tick_mode == "event":
                    if self._event is not None:
                        self._event.set()
                else:
                    with self._tick_lock:
                        self._tick_count += 1
                if self._on_tick:
                    try:
                        self._loop.call_soon_threadsafe(self._on_tick)
                    except Exception:
                        pass
                next_fire += self.interval
        except asyncio.CancelledError:
            try:
                if self._tick_mode == "event":
                    if self._event is not None:
                        self._event.clear()
                else:
                    with self._tick_lock:
                        self._tick_count = 0
            except Exception:
                pass
            raise
        except Exception:
            try:
                if self._tick_mode == "event":
                    if self._event is not None:
                        self._event.clear()
                else:
                    with self._tick_lock:
                        self._tick_count = 0
            except Exception:
                pass
            return

    def _thread_run(self) -> None:
        """
        Internal thread-backed timer loop.

        Runs until :attr:`_stop_flag` is set. Mirrors the behaviour of the
        asyncio implementation: set the event or increment the tick counter,
        and optionally execute :attr:`_on_tick` in a daemon thread.
        """
        next_fire = time.monotonic() + self.interval
        while not (self._stop_flag is not None and self._stop_flag.is_set()):
            now = time.monotonic()
            wait_time = max(0.0, next_fire - now)
            stopped = False
            if self._stop_flag is not None:
                stopped = self._stop_flag.wait(wait_time)
            else:
                time.sleep(wait_time)
            if stopped:
                break
            if self._tick_mode == "event":
                if self._event is not None:
                    self._event.set()
            else:
                with self._tick_lock:
                    self._tick_count += 1
            if self._on_tick:
                try:
                    threading.Thread(target=self._on_tick, daemon=True).start()
                except Exception:
                    pass
            next_fire += self.interval
        try:
            if self._tick_mode == "event":
                if self._event is not None:
                    self._event.clear()
            else:
                with self._tick_lock:
                    self._tick_count = 0
        except Exception:
            pass

    def is_ready(self) -> bool:
        """
        Check (and clear) the event-based tick flag.

        This method is only meaningful when the object is in timer mode and
        ``tick_mode=="event"``. Calling it returns ``True`` exactly once per
        tick (it clears the underlying event).

        @return bool
            True if a tick had occurred since last call (and event was cleared),
            otherwise False.

        @raises RuntimeError:
            If called when not in timer mode or when called while ``tick_mode``
            is not ``"event"``.
        """
        if self.mode != self.MODE_TIMER:
            raise RuntimeError("is_ready() is only available in timer mode")
        if self._tick_mode != "event":
            raise RuntimeError("is_ready() only works when tick_mode='event'; use get_ticks() for 'count' mode'")
        if self._event is None:
            return False
        if self._event.is_set():
            try:
                self._event.clear()
            except Exception:
                pass
            return True
        return False

    def get_ticks(self) -> int:
        """
        Retrieve and reset the accumulated tick count (count-based tick mode).

        @return int
            Number of ticks that occurred since the last call.

        @raises RuntimeError:
            If called when not in timer mode or when ``tick_mode`` is not
            ``"count"``.
        """
        if self.mode != self.MODE_TIMER:
            raise RuntimeError("get_ticks() is only available in timer mode")
        if self._tick_mode != "count":
            raise RuntimeError("get_ticks() only available when tick_mode='count'")
        with self._tick_lock:
            n = self._tick_count
            self._tick_count = 0
        return n

    def is_running(self) -> bool:
        """
        Query whether the helper is currently active.

        In count mode this returns whether the stopwatch is running; in timer
        mode it returns whether the underlying task/thread is active.

        @return bool
            True when running, otherwise False.
        """
        if self.mode == self.MODE_COUNT:
            return self._running
        if self._use_asyncio:
            t = getattr(self, "_task", None)
            return t is not None and not t.done()
        else:
            t = getattr(self, "_thread", None)
            return t is not None and t.is_alive()

    async def stop_async(self) -> None:
        """
        Asynchronous shutdown for timer mode.

        Cancels the asyncio task (if running) and awaits its termination. For
        thread backend it signals the stop flag and joins the thread (blocking
        call — kept for API parity with :meth:`request_stop`).

        @note This method is a no-op in count mode.

        @raises asyncio.CancelledError:
            Propagated if the underlying task cancellation raises it.
        """
        if self.mode == self.MODE_COUNT:
            return
        if self._use_asyncio:
            task = getattr(self, "_task", None)
            self._task = None
            if task is None:
                try:
                    if self._tick_mode == "event":
                        if self._event is not None:
                            self._event.clear()
                    else:
                        with self._tick_lock:
                            self._tick_count = 0
                except Exception:
                    pass
                return
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                try:
                    if self._tick_mode == "event":
                        if self._event is not None:
                            self._event.clear()
                    else:
                        with self._tick_lock:
                            self._tick_count = 0
                except Exception:
                    pass
        else:
            t = getattr(self, "_thread", None)
            self._thread = None
            if self._stop_flag is not None:
                self._stop_flag.set()
            if t is not None:
                t.join(timeout=2.0)
            try:
                if self._tick_mode == "event":
                    if self._event is not None:
                        self._event.clear()
                else:
                    with self._tick_lock:
                        self._tick_count = 0
            except Exception:
                pass

    def request_stop(self) -> None:
        """
        Synchronous stop request for timer mode.

        Cancels the asyncio task (if used) or signals the thread-based stop
        flag and joins the thread.

        @note For count mode this simply behaves like :meth:`stop`.

        @see stop_async
        """
        if self.mode == self.MODE_COUNT:
            # behave as stop()
            self.stop()
            return
        if self._use_asyncio:
            task = getattr(self, "_task", None)
            self._task = None
            if task is not None and not task.done():
                task.cancel()
            if self._event is not None:
                try:
                    self._event.clear()
                except Exception:
                    pass
        else:
            t = getattr(self, "_thread", None)
            self._thread = None
            if self._stop_flag is not None:
                self._stop_flag.set()
            if t is not None:
                t.join(timeout=2.0)
            if self._event is not None:
                try:
                    self._event.clear()
                except Exception:
                    pass
