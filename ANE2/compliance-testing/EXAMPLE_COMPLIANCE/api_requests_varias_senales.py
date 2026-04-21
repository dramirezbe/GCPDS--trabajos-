from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from synthetic_frames import GENERATED_DIR, build_multi_signal_frame, save_frame


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejemplo de reporte de varias señales usando /analyze."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/analyze",
        help="URL base del endpoint /analyze.",
    )
    parser.add_argument(
        "--output-frame",
        default=str(GENERATED_DIR / "frame_ruido_gaussiano_multi.json"),
        help="Ruta opcional para guardar el frame enviado.",
    )
    parser.add_argument(
        "--umbral-db",
        type=float,
        default=6.0,
        help="Umbral de detección en dB sobre el piso de ruido.",
    )
    args = parser.parse_args()

    frame = build_multi_signal_frame()
    frame_path = save_frame(frame, Path(args.output_frame))

    payload = {
        "frame": frame,
        "cumplimiento": 0,
        "umbral_db": args.umbral_db,
    }

    response = requests.post(args.url, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    print(f"Frame guardado en: {frame_path}")
    print(f"HTTP {response.status_code}")
    print(f"Modo: {data.get('mode')}")
    print(f"Emisiones detectadas: {data.get('num_emissions')}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
