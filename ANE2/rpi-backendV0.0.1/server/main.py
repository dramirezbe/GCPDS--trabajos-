# main.py
from typing import List, Optional, Literal, Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import logging

# --- logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sensing-node-api")

# --- Pydantic models for request ---

# mac address pattern: 6 groups of 2 hex digits separated by '-' or ':'
MAC_REGEX = r"^[0-9A-Fa-f]{2}([-:][0-9A-Fa-f]{2}){5}$"

# Use Annotated + Field for constraints so we don't rely on specific *Constraints class names.
MACType = Annotated[str, Field(pattern=MAC_REGEX)]

# Constrained float for percentages 0..100 using Field
PercentFloat = Annotated[float, Field(ge=0.0, le=100.0)]

# Constrained non-negative integer
NonNegInt = Annotated[int, Field(ge=0)]

class MetricsModel(BaseModel):
    cpu: List[PercentFloat] = Field(..., description="Per-core CPU percentages (0-100)")
    ram: PercentFloat = Field(..., description="RAM percentage (0-100)")
    swap: PercentFloat = Field(..., description="Swap percentage (0-100)")
    disk: PercentFloat = Field(..., description="Disk percentage (0-100)")
    temp_c: float = Field(..., description="Temperature in Celsius")

class GPSModel(BaseModel):
    lat: float = Field(..., description="Latitude (degrees)")
    lng: float = Field(..., description="Longitude (degrees)")
    alt: float = Field(..., description="Altitude (meters)")

class AliveRequest(BaseModel):
    device: MACType = Field(..., description="Device MAC address")
    metrics: MetricsModel
    gps: GPSModel
    delta_t: NonNegInt = Field(..., description="Previous RTT in milliseconds (integer)")

class PxxModel(BaseModel):
    start_freq_hz: int
    end_freq_hz: int
    resolution_hz: int
    pxx: List[float]

# --- Pydantic models for response ---

class DemodulationModel(BaseModel):
    type: Literal["AM", "FM"]
    bandwidth_hz: int
    center_freq_hz: int

class AliveResponse(BaseModel):
    start_freq_hz: int
    end_freq_hz: int
    resolution_hz: int
    antenna_port: int
    demodulation: Optional[DemodulationModel] = None

# --- FastAPI app ---
app = FastAPI(title="Spectrum Sensing Node API", version="0.1")

@app.post("/jobs", response_model=AliveResponse)
async def post_alive(payload: AliveRequest):
    """
    Receive alive heartbeat from a sensing node and respond with a dummy job configuration.
    The request payload is validated; the response is dummy data (static).
    """
    # Log (structured-ish) the request; in real apps use structured logging
    logger.info(
        "Alive received: device=%s delta_t_ms=%d cpu=%s ram=%s swap=%s temp_c=%s gps=(%f,%f,%f)",
        payload.device,
        payload.delta_t,
        payload.metrics.cpu,
        payload.metrics.ram,
        payload.metrics.swap,
        payload.metrics.temp_c,
        payload.gps.lat,
        payload.gps.lng,
        payload.gps.alt,
    )

    # Optionally: perform lightweight sanity checks and possibly reject invalid payloads
    if len(payload.metrics.cpu) == 0:
        raise HTTPException(status_code=400, detail="cpu list must contain at least one core value")

    # Dummy response (static). Replace with real scheduler logic as needed.
    response = AliveResponse(
        start_freq_hz=88_000_000,
        end_freq_hz=108_000_000,
        resolution_hz=10_000,
        antenna_port=1,
        demodulation=None
    )

    return response

# Optional lightweight health endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}
