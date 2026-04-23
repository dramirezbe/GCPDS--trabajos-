import argparse
import json
import sys
from pathlib import Path
import numpy as np

POSTPRO_DIR = Path(__file__).resolve().parents[2]
if str(POSTPRO_DIR) not in sys.path:
    sys.path.insert(0, str(POSTPRO_DIR))

from src.payload_parser import frame_from_payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Paso 1: probar parser JSON -> SpectrumFrame (sin campañas, sin plots)."
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        required=True,
        help="Ruta al archivo .json (ej: 1765414521108.json)",
    )
    args = parser.parse_args()

    # 1) Cargar JSON
    with open(args.json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # 2) Convertir a SpectrumFrame
    frame = frame_from_payload(payload)

    # 3) Imprimir resumen (lo que verificamos en el Paso 1)
    y = np.asarray(frame.amplitudes_dbm)
    print("\n[OK] SpectrumFrame creado")
    print("     ", frame)
    print(f"     N puntos: {len(y)}")
    print(f"     f_start_hz: {frame.f_start_hz}")
    print(f"     f_stop_hz:  {frame.f_stop_hz}")
    print(f"     bin_hz:     {frame.bin_hz}")
    print(f"     min(Pxx):   {float(y.min())}")
    print(f"     max(Pxx):   {float(y.max())}")

    # Metadata si existe
    if isinstance(payload, dict):
        if "timestamp" in payload:
            print(f"     timestamp:  {payload['timestamp']}")
        if "mac" in payload:
            print(f"     mac:        {payload['mac']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
