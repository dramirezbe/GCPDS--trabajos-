"""!
@file utils/timers.py
@brief Functions and Classes to help count async time.
"""

import time

class TimeHelper:
    
    def __init__(self, interval_seconds: int):
        
        if interval_seconds <= 0:
            raise ValueError("Interval must be postive")
        
        self.interval = interval_seconds
    
        self._last_triggered_time = time.monotonic() - self.interval

    def is_ready(self) -> bool:

        now = time.monotonic()
        if now - self._last_triggered_time >= self.interval:
            self._last_triggered_time = now
            return True
        return False