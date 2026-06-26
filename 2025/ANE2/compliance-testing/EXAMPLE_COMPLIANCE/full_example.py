from __future__ import annotations

import csv
import json
import re
from pathlib import Path
import sys
from typing import Any

import requests

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from api_dane_from_coords_via_tunnel import full_example_dane_tunnel


UMBRAL_DB = 5.0
ANALYZE_URL = "http://127.0.0.1:8000/analyze"

REAL_SIGNALS_DIR = CURRENT_DIR / "real_signals"

SENSOR_MACS = {
    "ANE9": "d8:3a:dd:f4:4e:d1",
    "ANE10": "d8:3a:dd:f7:1d:90",
}

SENSOR_COORDINATES = {
    "d8:3a:dd:f4:4e:d1": {"lat": 4.70851, "lon": -74.17519},
    "d8:3a:dd:f7:1d:90": {"lat": 4.67758, "lon": -74.05411},
}


def _extract_measurement_index(file_path: Path) -> int:
    match = re.search(r"_(\d+)$", file_path.stem)
    return int(match.group(1)) if match else 0


def _csvs_for_sensor(sensor_name: str) -> list[Path]:
    csv_paths = sorted(
        REAL_SIGNALS_DIR.glob(f"{sensor_name}_*.csv"),
        key=_extract_measurement_index,
    )
    if not csv_paths:
        raise FileNotFoundError(f"No encontré CSV para {sensor_name} en {REAL_SIGNALS_DIR}")
    return csv_paths


def _load_frame_from_real_signal(csv_path: Path, sensor_name: str, sensor_mac: str) -> dict[str, Any]:
    freqs_hz: list[float] = []
    powers_dbm: list[float] = []
    campaign_name = ""
    measurement_label = ""

    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue

            first = row[0].strip()
            if first.startswith("Campaña:"):
                campaign_name = first.split(":", 1)[1].strip()
                continue
            if first.startswith("Medición:"):
                measurement_label = first.split(":", 1)[1].strip()
                continue
            if first == "Frecuencia (Hz)":
                continue

            if len(row) < 2:
                continue

            freqs_hz.append(float(row[0]))
            powers_dbm.append(float(row[1]))

    if len(freqs_hz) < 4 or len(powers_dbm) < 4:
        raise ValueError(f"El CSV {csv_path} no contiene suficientes muestras.")

    measurement_index = _extract_measurement_index(csv_path)

    return {
        "Pxx": powers_dbm,
        "start_freq_hz": freqs_hz[0],
        "end_freq_hz": freqs_hz[-1],
        "timestamp": measurement_index,
        "mac": sensor_mac,
        "metadata": {
            "source_csv": str(csv_path),
            "sensor_name": sensor_name,
            "campaign_name": campaign_name,
            "measurement_label": measurement_label,
            "num_points": len(powers_dbm),
        },
    }


def _build_payload(frame: dict[str, Any], dane_codes: list[str] | None) -> dict[str, Any]:
    payload = {
        "frame": frame,
        "cumplimiento": 0,
        "umbral_db": UMBRAL_DB,
    }
    if dane_codes:
        payload["dane"] = dane_codes[0]
        payload["danes"] = dane_codes
    return payload


def _analyze_frame(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(ANALYZE_URL, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def _run_sensor(
    sensor_name: str,
    sensor_mac: str,
    dane_codes: list[str] | None,
    *,
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for csv_path in _csvs_for_sensor(sensor_name):
        frame = _load_frame_from_real_signal(csv_path, sensor_name, sensor_mac)
        payload = _build_payload(frame, dane_codes)
        analysis = _analyze_frame(payload)

        result = {
            #--------------------#
            # JSON de la API /analyze
            #--------------------#
            "analyze": analysis,
        }
        results.append(result)

        print()
        print(f"[{sensor_name}] {csv_path.name}")
        print(f"  mac: {sensor_mac}")
        print(f"  coords: {lat}, {lon}")
        print(f"  emisiones detectadas: {analysis.get('num_emissions')}")

    return results


def main() -> int:
    all_results: dict[str, Any] = {
        #--------------------#
        # Configuración del ejemplo
        #--------------------#
        "umbral_db": UMBRAL_DB,
        "sensors": {},
    }

    for sensor_name, sensor_mac in SENSOR_MACS.items():
        coords = SENSOR_COORDINATES[sensor_mac]
        lat = coords["lat"]
        lon = coords["lon"]
        dane_codes = full_example_dane_tunnel(lat, lon)

        print()
        print(f"[{sensor_name}]")
        print(f"  mac: {sensor_mac}")
        print(f"  lat/lon: {lat}, {lon}")
        print(f"  umbral dB: {UMBRAL_DB}")
        print(f"  DANEs usados: {dane_codes if dane_codes else 'ninguno'}")

        all_results["sensors"][sensor_name] = {
            #--------------------#
            # Datos nuevos del ejemplo
            #--------------------#
            "sensor_name": sensor_name,
            "sensor_mac": sensor_mac,
            "coordinates": {"lat": lat, "lon": lon},
            "dane_codes": dane_codes or [],

            #--------------------#
            # Resultado de la API /analyze
            #--------------------#
            "measurements": _run_sensor(sensor_name, sensor_mac, dane_codes, lat=lat, lon=lon),
        }

    print()
    print(json.dumps(all_results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
