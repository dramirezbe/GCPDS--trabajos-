#!/usr/bin/env python3
"""Diagnostica ANE8 frente a otras carpetas *-experiment.

- Busca carpetas ANE*-experiment
- Carga CSVs usando TelemetryParser de csv_dataclasses.py
- Selecciona, por carpeta, el CSV con mas muestras validas
- Genera plots relevantes en /outs-experiment/plots
- Escribe reporte de hallazgos en /outs-experiment/reports
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from csv_dataclasses import TelemetryParser, TelemetryRecord


@dataclass
class CsvRun:
    experiment: str
    csv_path: Path
    records: List[TelemetryRecord]


@dataclass
class ExperimentSummary:
    experiment: str
    selected_csv: Optional[Path]
    sample_count: int
    duration_min: float
    cpu_mean: Optional[float]
    temp_mean: Optional[float]
    ext5v_mean: Optional[float]
    uv_occured_count: int
    throttle_occured_count: int


def _safe_mean(values: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return None
    return mean(vals)


def _count_yes(records: List[TelemetryRecord], attr: str) -> int:
    count = 0
    for r in records:
        value = getattr(r.status, attr, "")
        if isinstance(value, str) and value.strip().lower() == "yes":
            count += 1
    return count


def discover_experiments(root: Path) -> List[Path]:
    # Solo ANE*-experiment del nivel actual.
    return sorted(
        p for p in root.glob("ANE*-experiment") if p.is_dir() and p.name.endswith("-experiment")
    )


def load_runs(exp_dirs: List[Path]) -> Dict[str, List[CsvRun]]:
    parser = TelemetryParser()
    runs_by_exp: Dict[str, List[CsvRun]] = {}

    for exp_dir in exp_dirs:
        exp_name = exp_dir.name.replace("-experiment", "")
        csv_files = sorted(exp_dir.glob("*.csv"))
        runs: List[CsvRun] = []

        for csv_path in csv_files:
            try:
                records = list(parser.read_directory(csv_path))
            except Exception:
                records = []
            runs.append(CsvRun(exp_name, csv_path, records))

        runs_by_exp[exp_name] = runs

    return runs_by_exp


def select_best_run(runs: List[CsvRun]) -> Optional[CsvRun]:
    if not runs:
        return None
    # Elegimos el CSV con mas muestras validas.
    return max(runs, key=lambda r: len(r.records))


def summarize(experiment: str, run: Optional[CsvRun]) -> ExperimentSummary:
    if run is None or not run.records:
        return ExperimentSummary(
            experiment=experiment,
            selected_csv=run.csv_path if run else None,
            sample_count=0,
            duration_min=0.0,
            cpu_mean=None,
            temp_mean=None,
            ext5v_mean=None,
            uv_occured_count=0,
            throttle_occured_count=0,
        )

    records = run.records
    duration = records[-1].time_min if records else 0.0

    return ExperimentSummary(
        experiment=experiment,
        selected_csv=run.csv_path,
        sample_count=len(records),
        duration_min=duration,
        cpu_mean=_safe_mean([r.cpu_percent for r in records]),
        temp_mean=_safe_mean([r.arm_temp for r in records]),
        ext5v_mean=_safe_mean([r.voltages.v_ext5v for r in records]),
        uv_occured_count=_count_yes(records, "uv_occured"),
        throttle_occured_count=_count_yes(records, "throttle_occured"),
    )


def _series(records: List[TelemetryRecord], selector: str) -> Tuple[np.ndarray, np.ndarray]:
    x_vals: List[float] = []
    y_vals: List[float] = []

    for r in records:
        y: Optional[float]
        if selector == "cpu":
            y = r.cpu_percent
        elif selector == "temp":
            y = r.arm_temp
        elif selector == "ext5v":
            y = r.voltages.v_ext5v
        else:
            raise ValueError(f"selector desconocido: {selector}")

        if y is not None:
            x_vals.append(r.time_min)
            y_vals.append(y)

    if len(x_vals) < 2:
        return np.array([]), np.array([])

    x_arr = np.asarray(x_vals, dtype=float)
    y_arr = np.asarray(y_vals, dtype=float)

    # Garantiza monotonia por tiempo para interpolacion.
    order = np.argsort(x_arr)
    return x_arr[order], y_arr[order]


def _interp_to_grid(x: np.ndarray, y: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if x.size < 2:
        return np.full_like(grid, np.nan)
    left_mask = grid < x[0]
    right_mask = grid > x[-1]
    out = np.interp(grid, x, y)
    out[left_mask] = np.nan
    out[right_mask] = np.nan
    return out


def plot_sample_and_duration(summaries: List[ExperimentSummary], out_dir: Path) -> None:
    exps = [s.experiment for s in summaries]
    samples = [s.sample_count for s in summaries]
    durations = [s.duration_min for s in summaries]

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    bars = axes[0].bar(exps, samples, color="#4C78A8")
    for b, s in zip(bars, samples):
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height(), f"{s}", ha="center", va="bottom", fontsize=9)
    axes[0].set_ylabel("Muestras validas")
    axes[0].set_title("Conteo de muestras por experimento")
    axes[0].grid(axis="y", linestyle="--", alpha=0.4)

    bars = axes[1].bar(exps, durations, color="#F58518")
    for b, d in zip(bars, durations):
        axes[1].text(b.get_x() + b.get_width() / 2, b.get_height(), f"{d:.2f}", ha="center", va="bottom", fontsize=9)
    axes[1].set_ylabel("Duracion (min)")
    axes[1].set_title("Duracion efectiva por experimento")
    axes[1].grid(axis="y", linestyle="--", alpha=0.4)

    plt.xticks(rotation=0)
    plt.tight_layout()
    fig.savefig(out_dir / "01_samples_duration.png", dpi=150)
    plt.close(fig)


def plot_key_means(summaries: List[ExperimentSummary], out_dir: Path) -> None:
    exps = [s.experiment for s in summaries]

    cpu = [np.nan if s.cpu_mean is None else s.cpu_mean for s in summaries]
    temp = [np.nan if s.temp_mean is None else s.temp_mean for s in summaries]
    ext = [np.nan if s.ext5v_mean is None else s.ext5v_mean for s in summaries]

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)

    axes[0].bar(exps, cpu, color="#72B7B2")
    axes[0].set_ylabel("CPU %")
    axes[0].set_title("Promedio CPU")
    axes[0].grid(axis="y", linestyle="--", alpha=0.4)

    axes[1].bar(exps, temp, color="#E45756")
    axes[1].set_ylabel("Temp ARM (C)")
    axes[1].set_title("Promedio Temperatura")
    axes[1].grid(axis="y", linestyle="--", alpha=0.4)

    axes[2].bar(exps, ext, color="#54A24B")
    axes[2].set_ylabel("EXT5V (V)")
    axes[2].set_title("Promedio Voltaje EXT5V")
    axes[2].grid(axis="y", linestyle="--", alpha=0.4)

    plt.xticks(rotation=0)
    plt.tight_layout()
    fig.savefig(out_dir / "02_key_means.png", dpi=150)
    plt.close(fig)


def plot_events(summaries: List[ExperimentSummary], out_dir: Path) -> None:
    exps = [s.experiment for s in summaries]
    uv = [s.uv_occured_count for s in summaries]
    thr = [s.throttle_occured_count for s in summaries]

    x = np.arange(len(exps))
    w = 0.35

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(x - w / 2, uv, width=w, label="UV_occured=Yes", color="#B279A2")
    ax.bar(x + w / 2, thr, width=w, label="Throttle_occured=Yes", color="#FF9DA6")

    ax.set_xticks(x)
    ax.set_xticklabels(exps)
    ax.set_ylabel("Cantidad de eventos")
    ax.set_title("Eventos de UV y Throttle")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend()

    plt.tight_layout()
    fig.savefig(out_dir / "03_uv_throttle_events.png", dpi=150)
    plt.close(fig)


def plot_ane8_vs_others(
    runs_by_exp: Dict[str, Optional[CsvRun]],
    out_dir: Path,
) -> bool:
    ane8 = runs_by_exp.get("ANE8")
    if ane8 is None or not ane8.records:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.axis("off")
        ax.text(
            0.02,
            0.72,
            "ANE8 no tiene muestras validas en *-experiment",
            fontsize=14,
            fontweight="bold",
        )
        ax.text(
            0.02,
            0.46,
            "No se puede comparar serie temporal (CPU, Temp, EXT5V).",
            fontsize=11,
        )
        ax.text(
            0.02,
            0.30,
            "Revisar captura/guardado del logger para ANE8.",
            fontsize=11,
        )
        fig.savefig(out_dir / "04_ane8_vs_others_timeseries.png", dpi=150)
        plt.close(fig)
        return False

    other_runs = [r for exp, r in runs_by_exp.items() if exp != "ANE8" and r is not None and r.records]
    if not other_runs:
        return False

    max_common_t = min(
        ane8.records[-1].time_min,
        *[r.records[-1].time_min for r in other_runs],
    )
    if max_common_t <= 0:
        return False

    grid = np.linspace(0.0, max_common_t, 300)

    selectors = [
        ("cpu", "CPU %", "#72B7B2"),
        ("temp", "Temp ARM (C)", "#E45756"),
        ("ext5v", "EXT5V (V)", "#54A24B"),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)

    for ax, (sel, ylabel, color) in zip(axes, selectors):
        x8, y8 = _series(ane8.records, sel)
        y8_i = _interp_to_grid(x8, y8, grid)

        others_interp = []
        for run in other_runs:
            xo, yo = _series(run.records, sel)
            others_interp.append(_interp_to_grid(xo, yo, grid))
        others_arr = np.vstack(others_interp)

        mean_o = np.nanmean(others_arr, axis=0)
        std_o = np.nanstd(others_arr, axis=0)

        ax.plot(grid, mean_o, color="#4C78A8", linewidth=2.0, label="Media otras ANE")
        ax.fill_between(grid, mean_o - std_o, mean_o + std_o, color="#4C78A8", alpha=0.20, label="+-1 sigma")
        ax.plot(grid, y8_i, color=color, linewidth=2.0, label="ANE8")

        ax.set_ylabel(ylabel)
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.legend(loc="best")

    axes[0].set_title("ANE8 vs promedio de ANE7/9/10 (ventana temporal comun)")
    axes[-1].set_xlabel("Tiempo (min)")

    plt.tight_layout()
    fig.savefig(out_dir / "04_ane8_vs_others_timeseries.png", dpi=150)
    plt.close(fig)
    return True


def plot_ane8_file_sizes(runs_ane8: List[CsvRun], out_dir: Path) -> None:
    if not runs_ane8:
        return

    names = [r.csv_path.name for r in runs_ane8]
    sizes = [r.csv_path.stat().st_size for r in runs_ane8]
    rows = [len(r.records) for r in runs_ane8]

    x = np.arange(len(names))

    fig, ax1 = plt.subplots(figsize=(12, 5.5))
    bar = ax1.bar(x, sizes, color="#9D755D", alpha=0.9)
    ax1.set_ylabel("Tamano archivo (bytes)")
    ax1.set_title("ANE8: tamano de CSV y filas parseadas")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=15, ha="right")
    ax1.grid(axis="y", linestyle="--", alpha=0.35)

    ax2 = ax1.twinx()
    ax2.plot(x, rows, color="#2E4057", marker="o", linewidth=2.0)
    ax2.set_ylabel("Filas parseadas")

    for b, s in zip(bar, sizes):
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height(), str(s), ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    fig.savefig(out_dir / "05_ane8_filesize_rows.png", dpi=150)
    plt.close(fig)


def write_report(
    report_path: Path,
    summaries: List[ExperimentSummary],
    runs_by_exp: Dict[str, Optional[CsvRun]],
) -> None:
    by_exp = {s.experiment: s for s in summaries}
    ane8 = by_exp.get("ANE8")
    others = [s for s in summaries if s.experiment != "ANE8"]

    lines: List[str] = []
    lines.append("Diagnostico ANE8 vs otras carpetas *-experiment")
    lines.append("=" * 62)
    lines.append("")

    lines.append("1) Resumen por experimento")
    for s in summaries:
        lines.append(
            f"- {s.experiment}: muestras={s.sample_count}, duracion_min={s.duration_min:.2f}, "
            f"cpu_mean={s.cpu_mean}, temp_mean={s.temp_mean}, ext5v_mean={s.ext5v_mean}, "
            f"uv_occured={s.uv_occured_count}, throttle_occured={s.throttle_occured_count}, "
            f"csv={s.selected_csv.name if s.selected_csv else 'N/A'}"
        )

    lines.append("")
    lines.append("2) Diagnostico")

    if ane8 is None or ane8.sample_count == 0:
        lines.append("- ANE8 no tiene muestras validas en sus CSV de *-experiment.")
        run8 = runs_by_exp.get("ANE8")
        if run8 is not None:
            lines.append("- Evidencia ANE8:")
            for csv in sorted(run8.csv_path.parent.glob("*.csv")):
                lines.append(f"  * {csv.name}: {csv.stat().st_size} bytes")
        lines.append("- Causa probable: falla de captura o escritura del logger durante ANE8.")
        lines.append("- Impacto: no hay forma de comparar tendencia temporal ANE8 vs otras ANE.")
    else:
        def _avg(attr: str) -> Optional[float]:
            vals = [getattr(o, attr) for o in others if getattr(o, attr) is not None]
            return mean(vals) if vals else None

        for metric in ["cpu_mean", "temp_mean", "ext5v_mean"]:
            ref = _avg(metric)
            v8 = getattr(ane8, metric)
            if ref is None or v8 is None:
                lines.append(f"- {metric}: sin datos para comparacion.")
            else:
                delta = v8 - ref
                lines.append(f"- {metric}: ANE8={v8:.4f} vs otras={ref:.4f} (delta={delta:+.4f})")

    lines.append("")
    lines.append("3) Recomendaciones")
    lines.append("- Verificar comando de adquisicion usado en ANE8 y permisos de escritura.")
    lines.append("- Confirmar espacio en disco y que el proceso logger no finalize antes de flush/cierre.")
    lines.append("- Repetir ANE8 con el mismo protocolo de ANE7/9/10 y validar que el CSV crezca en tiempo real.")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnostico ANE8 frente a ANE7/9/10 en *-experiment")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directorio raiz donde buscar ANE*-experiment",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "outs-experiment",
        help="Directorio de salida",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    out_root = args.out.resolve()
    plot_dir = out_root / "plots"
    report_dir = out_root / "reports"
    plot_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    exp_dirs = discover_experiments(root)
    if not exp_dirs:
        raise RuntimeError(f"No se encontraron carpetas ANE*-experiment en {root}")

    all_runs = load_runs(exp_dirs)

    best_by_exp: Dict[str, Optional[CsvRun]] = {
        exp: select_best_run(runs) for exp, runs in all_runs.items()
    }

    summaries: List[ExperimentSummary] = [
        summarize(exp, best_by_exp.get(exp)) for exp in sorted(best_by_exp.keys())
    ]

    plot_sample_and_duration(summaries, plot_dir)
    plot_key_means(summaries, plot_dir)
    plot_events(summaries, plot_dir)
    plot_ane8_vs_others(best_by_exp, plot_dir)
    plot_ane8_file_sizes(all_runs.get("ANE8", []), plot_dir)

    write_report(report_dir / "ane8_diagnosis_report.txt", summaries, best_by_exp)

    print("Diagnostico completado")
    print(f"- Plots:   {plot_dir}")
    print(f"- Reporte: {report_dir / 'ane8_diagnosis_report.txt'}")


if __name__ == "__main__":
    main()