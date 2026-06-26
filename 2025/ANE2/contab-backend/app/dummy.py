from typing import Dict
import random

def get_gps() -> Dict[str, float]:
    """Simulated GPS data (replace with real GPS call)."""
    return {
        "lat": 37.7749 + random.uniform(-0.01, 0.01),
        "lng": -122.4194 + random.uniform(-0.01, 0.01),
        "alt": 30 + random.uniform(-5, 5),
    }