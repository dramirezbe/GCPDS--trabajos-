from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api_dane_from_coords_via_tunnel import _query_location_via_tunnel


def _build_coords(count: int) -> list[tuple[float, float]]:
    """Build deterministic coordinates near and inside Colombia."""
    base_points: list[tuple[float, float]] = [
        (4.7110, -74.0721),   # Bogota
        (6.2442, -75.5812),   # Medellin
        (3.4516, -76.5320),   # Cali
        (10.3910, -75.4794),  # Cartagena
        (10.9685, -74.7813),  # Barranquilla
        (7.1193, -73.1227),   # Bucaramanga
        (11.2408, -74.1990),  # Santa Marta
        (4.4389, -75.2322),   # Ibague
        (2.4448, -76.6147),   # Popayan
        (1.2136, -77.2811),   # Pasto
        (8.7479, -75.8814),   # Monteria
        (5.0689, -75.5174),   # Manizales
        (4.8143, -75.6946),   # Pereira
        (4.1420, -73.6266),   # Villavicencio
        (2.9386, -75.2819),   # Neiva
        (11.0041, -72.9483),  # Riohacha
        (7.8939, -72.5078),   # Cucuta
        (-3.7703, -70.3730),  # Leticia
        (12.5833, -81.7000),  # San Andres
        (5.5439, -73.3564),   # Tunja
        (6.2518, -75.5636),   # Valle de Aburra
        (9.3047, -75.3978),   # Sincelejo
        (1.8280, -78.7646),   # Tumaco coast
        (12.4375, -71.6700),  # Alta Guajira
        (0.8300, -71.9300),   # Amazonia east
    ]

    rng = random.Random(2172026)
    coords: list[tuple[float, float]] = []

    # First use base points, then add small jitter around them if needed.
    while len(coords) < count:
        source = base_points[len(coords) % len(base_points)]
        if len(coords) < len(base_points):
            lat, lon = source
        else:
            lat = source[0] + rng.uniform(-0.18, 0.18)
            lon = source[1] + rng.uniform(-0.18, 0.18)

        coords.append((round(lat, 6), round(lon, 6)))

    return coords[:count]


def _safe_name(index: int, lat: float, lon: float) -> str:
    lat_s = str(lat).replace("-", "m").replace(".", "p")
    lon_s = str(lon).replace("-", "m").replace(".", "p")
    return f"dane_{index:03d}_lat_{lat_s}_lon_{lon_s}.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta /localizar por tunel SSH y guarda respuestas JSON crudas."
    )
    parser.add_argument("--count", type=int, default=20, help="Cantidad de consultas a guardar.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Timeout por consulta en segundos.")
    parser.add_argument(
        "--out-dir",
        default="responses_dane",
        help="Carpeta destino para guardar respuestas JSON.",
    )
    args = parser.parse_args()

    if args.count <= 0:
        raise SystemExit("--count debe ser mayor que 0")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    coords = _build_coords(args.count)
    ok = 0

    for idx, (lat, lon) in enumerate(coords, start=1):
        timestamp = datetime.now(timezone.utc).isoformat()
        filename = _safe_name(idx, lat, lon)
        target = out_dir / filename

        try:
            raw = _query_location_via_tunnel(lat, lon, timeout=args.timeout)
            doc: dict[str, Any] = {
                "meta": {
                    "index": idx,
                    "lat": lat,
                    "lon": lon,
                    "timestamp_utc": timestamp,
                    "source": "api_dane_from_coords_via_tunnel._query_location_via_tunnel",
                    "status": "ok",
                },
                "raw_response": raw,
            }
            _write_json(target, doc)
            ok += 1
            print(f"[{idx:02d}/{args.count}] OK  -> {target}")
        except Exception as exc:
            doc = {
                "meta": {
                    "index": idx,
                    "lat": lat,
                    "lon": lon,
                    "timestamp_utc": timestamp,
                    "source": "api_dane_from_coords_via_tunnel._query_location_via_tunnel",
                    "status": "error",
                },
                "error": str(exc),
            }
            _write_json(target, doc)
            print(f"[{idx:02d}/{args.count}] ERR -> {target} :: {exc}")

    print(f"\nFinalizado: {ok}/{args.count} respuestas exitosas guardadas en {out_dir}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
