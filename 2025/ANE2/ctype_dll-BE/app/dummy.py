from typing import Dict
import random
import asyncio

def get_gps() -> Dict[str, float]:
    """Simulated GPS data (replace with real GPS call)."""
    return {
        "lat": 37.7749 + random.uniform(-0.01, 0.01),
        "lng": -122.4194 + random.uniform(-0.01, 0.01),
        "alt": 30 + random.uniform(-5, 5),
    }

async def dummy_jobs():
    """Simulated job handler."""
    statuses = ["in_progress", "failed", "completed"]
    for _ in range(random.randint(1, 3)):
        status = random.choice(statuses)
        print(f"Doing dummy job, status: {status}")
        await asyncio.sleep(0.1)