import argparse
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt

from csv_dataclasses import GroupTelemetryParser, ReducedTelemetryRecord

SKIP_FILES_DEFAULT = {}


def collect_numeric_series(
    grouped_records: Dict[str, List[ReducedTelemetryRecord]],
) -> Dict[str, Dict[str, tuple[list[float], list[float]]]]:
    """Build variable -> file -> (time_min, values) for numeric non-empty points."""
    series_by_variable: Dict[str, Dict[str, tuple[list[float], list[float]]]] = {}

    for filename, records in grouped_records.items():
        if not records:
            continue

        for record in records:
            for column, value in record.values.items():
                if value is None or not isinstance(value, (int, float)):
                    continue

                file_map = series_by_variable.setdefault(column, {})
                if filename not in file_map:
                    file_map[filename] = ([], [])

                t_vals, y_vals = file_map[filename]
                t_vals.append(record.time_min)
                y_vals.append(float(value))

    # Keep only variables that have at least one non-empty series.
    return {
        variable: file_map
        for variable, file_map in series_by_variable.items()
        if any(len(y_vals) > 0 for _, y_vals in file_map.values())
    }


def sanitize_filename(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return "".join(ch if ch in allowed else "_" for ch in value)


def plot_all_series(
    series_by_variable: Dict[str, Dict[str, tuple[list[float], list[float]]]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for variable, file_series in sorted(series_by_variable.items()):
        plt.figure(figsize=(11, 5))

        for filename, (x_values, y_values) in sorted(file_series.items()):
            if not y_values:
                continue
            plt.plot(x_values, y_values, linewidth=1.1, label=filename)

        plt.title(f"Serie temporal: {variable}")
        plt.xlabel("Tiempo (min)")
        plt.ylabel(variable)
        plt.grid(True, linestyle="--", alpha=0.35)
        plt.legend(loc="best", fontsize=8)
        plt.tight_layout()

        output_path = output_dir / f"{sanitize_filename(variable)}.png"
        plt.savefig(output_path, dpi=150)
        plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analiza y grafica todas las series temporales numéricas válidas de una carpeta de CSVs, "
            "comparando todos los archivos en cada variable."
        )
    )
    parser.add_argument("folder", type=str, help="Carpeta con CSVs")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Buscar CSVs en subcarpetas",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Umbral de vacíos para análisis de columnas (0.75 = 75%%)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="plots_valid_series",
        help="Carpeta de salida para las gráficas",
    )
    parser.add_argument(
        "--skip-files",
        nargs="*",
        default=sorted(SKIP_FILES_DEFAULT),
        help="Nombres exactos de CSV a excluir",
    )

    args = parser.parse_args()
    folder = Path(args.folder)
    out_dir = Path(args.out_dir)
    skip_files = set(args.skip_files)

    parser_group = GroupTelemetryParser()

    analysis = parser_group.analyze_columns(
        folder=folder,
        threshold=args.threshold,
        recursive=args.recursive,
        skip_filenames=skip_files,
    )

    print("\nColumnas +75% vacías (sin stress-test):")
    for col in analysis["mas_75_vacias"]:
        print(f"- {col}")

    print("\nColumnas que no cambian en ningún CSV (sin stress-test):")
    for col in analysis["no_cambian_en_ningun_csv"]:
        print(f"- {col}")

    grouped = parser_group.load_clean_group(
        folder=folder,
        recursive=args.recursive,
        threshold=args.threshold,
        skip_filenames=skip_files,
    )

    print("\nResumen de registros limpios:")
    total_rows = 0
    for filename, records in sorted(grouped.items()):
        print(f"- {filename}: {len(records)}")
        total_rows += len(records)
    print(f"Total filas limpias: {total_rows}")

    series_by_variable = collect_numeric_series(grouped)
    plot_all_series(series_by_variable, out_dir)

    print(f"\nVariables graficadas: {len(series_by_variable)}")
    print(f"Gráficas guardadas en: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
