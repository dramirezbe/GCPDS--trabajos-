from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from synthetic_frames import GENERATED_DIR, build_single_signal_frame, save_frame


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejemplo simple de consumo de /analyze con requests."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/analyze",
        help="URL base del endpoint /analyze.",
    )
    parser.add_argument(
        "--output-frame",
        default=str(GENERATED_DIR / "frame_ruido_gaussiano_single.json"),
        help="Ruta opcional para guardar el frame enviado.",
    )
    args = parser.parse_args()

    frame = build_single_signal_frame()
    frame_path = save_frame(frame, Path(args.output_frame))

    payload = {
        "frame": frame,
        "cumplimiento": 0,
        "umbral_db": 6,
    }

    response = requests.post(args.url, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    print(f"Frame guardado en: {frame_path}")
    print(f"HTTP {response.status_code}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
