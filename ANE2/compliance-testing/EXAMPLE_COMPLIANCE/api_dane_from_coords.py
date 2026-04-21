from __future__ import annotations

import argparse
import json

import requests


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta el servicio ANE que resuelve coordenadas a codigo DANE."
    )
    parser.add_argument("--url", default="http://127.0.0.1:4155/localizar", help="URL del servicio.")
    parser.add_argument("--lat", type=float, required=True, help="Latitud decimal.")
    parser.add_argument("--lon", type=float, required=True, help="Longitud decimal.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout en segundos.")
    args = parser.parse_args()

    payload = {
        "lat": args.lat,
        "lon": args.lon,
    }

    response = requests.post(
        args.url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=args.timeout,
    )
    response.raise_for_status()

    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

    central = (data.get("resultado") or {}).get("central") or {}
    if central.get("codigo_dane"):
        print()
        print(f"codigo_dane={central['codigo_dane']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
