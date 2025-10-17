"""@file cfg.py
@brief Global configuration and context-aware logging helpers for the RF project.

Usage:
    import cfg

    log = cfg.get_logger()        # logger inferred from caller module
    log.info("Started")

Notes:
- get_logger() walks the call stack and picks the first module that is not cfg itself.
- This makes it safe to call get_logger() everywhere and obtain a logger named
  after the module where get_logger() was invoked.
"""

import logging
import inspect
from typing import Optional

# -----------------------
# --- CONFIGURATION ---
# -----------------------

#: Default logging level used by get_logger and configure_logging.
LOG_LEVEL = logging.INFO

#: Default NTP server used by ntp_sync.
NTP_SERVER = "pool.ntp.org"

#: Enable verbose logging (affects only user-level convenience; levels still honored).
VERBOSE = True

#: API configuration
API_IP = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_IP}:{API_PORT}"
JOBS_URL = "/jobs"
DATA_URL = "/data"

#: Retry delay between attempts (seconds).
RETRY_DELAY_SECONDS = 10

__all__ = [
    # Configuration
    "LOG_LEVEL",
    "NTP_SERVER",
    "VERBOSE",
    "API_IP",
    "API_PORT",
    "API_URL",
    "JOBS_URL",
    "DATA_URL",
    "RETRY_DELAY_SECONDS",
    # Logging functions
    "get_logger",
    "configure_logging",
]


# -----------------------
# --- LOGGING HELPERS ---
# -----------------------

_DEFAULT_LOG_FORMAT = "[%(name)s] %(message)s"


def _ensure_handler(logger: logging.Logger) -> None:
    """
    Ensure the logger has at least one StreamHandler to avoid duplicated
    messages when the module is imported multiple times.
    """
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(_DEFAULT_LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def _infer_caller_module_name(skip_modules: Optional[set] = None) -> str:
    """
    Walk the call stack and return the most-relevant caller module name.

    Strategy:
    - Iterate frames starting after this function.
    - Skip frames whose module name is in skip_modules (by default includes cfg.__name__).
    - Prefer the last segment of the module path (e.g. "package.module" -> "Module").
    - If running as '__main__' or cannot infer module, return "App".

    This is robust against wrappers, tests, and import aliases.
    """
    if skip_modules is None:
        skip_modules = set()

    stack = inspect.stack()
    # start at 1 to skip the frame of _infer_caller_module_name itself
    for frame_info in stack[1:]:
        module = inspect.getmodule(frame_info.frame)
        if not module:
            continue
        mod_name = module.__name__
        # skip module names that we don't want to use (e.g. cfg itself)
        if mod_name in skip_modules:
            continue
        # skip internal python/test harness frames
        if mod_name.startswith("unittest") or mod_name.startswith("pytest"):
            continue
        if mod_name == "__main__":
            # Try to use the filename (without extension) if available
            filename = frame_info.filename
            if filename:
                # extract basename and remove extension
                import os
                base = os.path.splitext(os.path.basename(filename))[0]
                if base:
                    return base.capitalize()
            # fallback to "App" and keep searching
            continue
        # take last component of module path and capitalize
        return mod_name.split(".")[-1].capitalize()
    # fallback
    return "App"


def get_logger(name: Optional[str] = None, level: int = LOG_LEVEL) -> logging.Logger:
    """
    Factory function that returns a configured logger.

    If `name` is None, the function infers the caller module's name by walking
    the call stack and returns a logger named after that module (capitalized).

    Returned logger will not propagate to the root logger and adding handlers
    is idempotent.

    Example:
        # in scheduler.py
        log = get_logger()   # -> logger named "Scheduler"
    """
    if name is None:
        # Skip this module's own name so callers are selected correctly.
        skip = {__name__}
        name = _infer_caller_module_name(skip_modules=skip)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    _ensure_handler(logger)
    # Prevent double logging when root handlers exist.
    logger.propagate = False
    return logger


def configure_logging(level: int = LOG_LEVEL) -> None:
    """
    Configure the root logger's level and ensure a default handler exists.

    Call this once from your application entrypoint (main) if you want to set
    global verbosity (e.g. to DEBUG).
    """
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_LOG_FORMAT))
        root.addHandler(handler)
