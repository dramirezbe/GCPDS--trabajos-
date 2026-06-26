from __future__ import annotations

import sys
import unittest
from pathlib import Path

POSTPRO_DIR = Path(__file__).resolve().parents[2]
if str(POSTPRO_DIR) not in sys.path:
    sys.path.insert(0, str(POSTPRO_DIR))

try:  # noqa: E402
    from server_flask import app
except ModuleNotFoundError as exc:  # pragma: no cover - depende del entorno local
    app = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(app is None, f"Flask no disponible en el entorno de prueba: {_IMPORT_ERROR}")
class ServerCompatibilityTests(unittest.TestCase):
    def test_analyze_contract_shape_unchanged(self) -> None:
        amps = [-100.0] * 128
        for i in range(55, 61):
            amps[i] = -75.0

        body = {
            "frame": {
                "Pxx": amps,
                "start_freq_hz": 99_500_000.0,
                "end_freq_hz": 100_500_000.0,
                "timestamp": "2026-01-01T00:00:00",
                "mac": "fixture_mac",
            },
            "cumplimiento": 0,
        }

        client = app.test_client()
        resp = client.post("/analyze", json=body)
        self.assertEqual(resp.status_code, 200)

        payload = resp.get_json()
        self.assertIn("mode", payload)
        self.assertIn("results", payload)
        self.assertIn("num_emissions", payload)
        self.assertIn("correction_applied", payload)
        self.assertNotIn("detector_name", payload)
        self.assertNotIn("simple_preset", payload)


if __name__ == "__main__":
    unittest.main()
