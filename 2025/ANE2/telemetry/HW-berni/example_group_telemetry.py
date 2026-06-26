#example_group_telemetry.py

import argparse
import logging
from pathlib import Path

from csv_dataclasses import GroupTelemetryParser


def print_preview(grouped_records: dict[str, list], preview_rows: int) -> None:
    for filename, records in grouped_records.items():
        print(f"\n{'='*70}")
        print(f"Archivo: {filename}")
        print(f"Registros limpios: {len(records)}")
        print(f"Primeras {preview_rows} filas limpias:")
        print(f"{'='*70}")

        if not records:
            print("(sin filas limpias)")
            continue

        for idx, record in enumerate(records[:preview_rows], start=1):
            print(
                f"{idx:>2}. ts={record.timestamp} | "
                f"time_min={record.time_min:.3f} | "
                f"cpu={record.get('cpu_percent')} | "
                f"arm_temp={record.get('arm_temp')} | "
                f"EXT5V_V={record.get('EXT5V_V')}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Carga todos los CSV de una carpeta con GroupTelemetryParser, "
            "limpia registros en RAM y muestra una vista previa por archivo."
        )
    )
    parser.add_argument("folder", type=str, help="Carpeta con CSVs")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Buscar CSVs en subcarpetas",
    )
    parser.add_argument(
        "--preview-rows",
        type=int,
        default=3,
        help="Cantidad de filas limpias a mostrar por archivo",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Umbral de vacíos para el análisis de columnas (0.75 = 75%%)",
    )

    args = parser.parse_args()
    folder = Path(args.folder)

    group_parser = GroupTelemetryParser()

    analysis = group_parser.analyze_columns(
        folder=folder,
        threshold=args.threshold,
        recursive=args.recursive,
    )

    print("\nColumnas +75% vacías:")
    for col in analysis["mas_75_vacias"]:
        print(f"- {col}")

    print("\nColumnas que no cambian en ningún CSV:")
    for col in analysis["no_cambian_en_ningun_csv"]:
        print(f"- {col}")

    grouped_records = group_parser.load_clean_group(
        folder=folder,
        recursive=args.recursive,
    )

    print_preview(grouped_records, preview_rows=args.preview_rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
