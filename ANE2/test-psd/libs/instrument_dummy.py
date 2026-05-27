import asyncio
from typing import Optional

import numpy as np


class KeysightHandler:
    """Dummy asynchronous handler that mimics the real Keysight handler.

    Provides the same interface as libs.instrument.KeysightHandler and returns
    a synthetic FM-like spectrum with noise and multiple peaks.
    """

    def __init__(self, ip: str, timeout_ms: int = 5000):
        self.ip = ip
        self.timeout_ms = timeout_ms
        self.inst: Optional[bool] = None

    async def __aenter__(self):
        self.inst = True
        print(f"[DUMMY] Using dummy instrument for {self.ip} (no connection attempted)")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.inst = None

    def _require_inst(self):
        if self.inst is None:
            raise RuntimeError("Instrument session is not open.")
        return self.inst

    async def get_info(self) -> str:
        await asyncio.sleep(0)
        return "DUMMY,Keysight,MODEL-FAKE,0.0"

    async def clear_errors(self):
        await asyncio.sleep(0)

    async def get_trace(self, center_freq_hz: float, span_hz: float) -> np.ndarray:
        self._require_inst()

        n_points = 10_000
        freqs = np.linspace(
            center_freq_hz - span_hz / 2.0,
            center_freq_hz + span_hz / 2.0,
            n_points,
        )

        rng_seed = int(abs(center_freq_hz) + abs(span_hz)) % (2**32)
        rng = np.random.default_rng(rng_seed)

        noise_floor_db = -90.0
        noise_db = noise_floor_db + 6.0 * rng.standard_normal(n_points)
        spectrum_db = noise_db.copy()

        # Four FM-like peaks around the carrier (carrier + three sidebands).
        peak_offsets = np.array([0.0, -0.18 * span_hz, 0.12 * span_hz, 0.28 * span_hz])
        peak_heights = np.array([35.0, 20.0, 16.0, 12.0])
        peak_bw = 0.01 * span_hz

        for offset, height in zip(peak_offsets, peak_heights):
            center = center_freq_hz + offset
            spectrum_db += height * np.exp(-0.5 * ((freqs - center) / peak_bw) ** 2)

        return spectrum_db.astype(float)
