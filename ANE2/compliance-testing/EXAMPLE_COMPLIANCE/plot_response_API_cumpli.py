from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SIGNALS_DIR = BASE_DIR / "camp_signals"
DEFAULT_RESPONSES_DIR = BASE_DIR / "camp-278-new-API"


@dataclass(frozen=True)
class PlotPair:
    signal_path: Path
    response_path: Path


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _response_to_signal_path(response_path: Path, signals_dir: Path) -> Path:
    stem = response_path.stem
    if stem.endswith("_response"):
        stem = stem[:-9]
    return signals_dir / f"{stem}.json"


def _build_pairs(signals_dir: Path, responses_dir: Path, pattern: Optional[str]) -> List[PlotPair]:
    pairs: List[PlotPair] = []
    for response_path in sorted(responses_dir.glob("*_response.json")):
        if pattern and pattern not in response_path.name:
            continue
        signal_path = _response_to_signal_path(response_path, signals_dir)
        if not signal_path.exists():
            print(f"[skip] no signal JSON for {response_path.name}")
            continue
        pairs.append(PlotPair(signal_path=signal_path, response_path=response_path))
    return pairs


def _build_freq_axis_mhz(frame_json: Dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    pxx = np.asarray(frame_json.get("Pxx", []), dtype=float).reshape(-1)
    if pxx.size == 0:
        raise ValueError("frame.Pxx is empty")

    start_hz = _as_float(frame_json.get("start_freq_hz"))
    end_hz = _as_float(frame_json.get("end_freq_hz"))
    if start_hz is None or end_hz is None:
        raise ValueError("frame.start_freq_hz / frame.end_freq_hz missing")

    freqs_mhz = np.linspace(start_hz, end_hz, pxx.size) / 1e6
    return freqs_mhz, pxx


def _result_sort_key(row: Dict[str, Any]) -> float:
    return _as_float(row.get("fc_medida_MHz", row.get("fc_mhz"))) or -1e18


def _result_color(row: Dict[str, Any]) -> str:
    lic = str(row.get("Licencia", "")).upper()
    fc_ok = str(row.get("Cumple_FC", "")).upper()
    bw_ok = str(row.get("Cumple_BW", "")).upper()
    p_ok = str(row.get("Cumple_P", "")).upper()

    if lic != "SI":
        return "#d62728"
    if fc_ok == "SI" and bw_ok == "SI" and p_ok == "SI":
        return "#2ca02c"
    if "NO" in {fc_ok, bw_ok, p_ok}:
        return "#ff7f0e"
    return "#1f77b4"


def _format_value(value: Optional[float], fmt: str) -> str:
    if value is None:
        return "-"
    return format(value, fmt)


def _build_summary_lines(response_path: Path, response_json: Dict[str, Any], results: List[Dict[str, Any]]) -> List[str]:
    threshold = _as_float(response_json.get("umbral"))
    lines = [
        f"response: {response_path.name}",
        (
            f"mode={response_json.get('mode')}  "
            f"num_emissions={response_json.get('num_emissions')}  "
            f"umbral={_format_value(threshold, '.2f')} dBm  "
            f"danes={len(response_json.get('danes', []))}"
        ),
        "",
        "id  lic  FC/BW/P   fc_med(MHz)  bw_med(kHz)  p_med(dBm)  fc_nom(MHz)  bw_nom(kHz)",
        "--  ---  -------   -----------  -----------  ----------  -----------  -----------",
    ]

    for idx, row in enumerate(results, start=1):
        fc_med = _as_float(row.get("fc_medida_MHz", row.get("fc_mhz")))
        bw_med = _as_float(row.get("bw_medido_kHz", row.get("bw_khz")))
        p_med = _as_float(row.get("p_medida_dBm", row.get("power_dbm")))
        fc_nom = _as_float(row.get("fc_nominal_MHz"))
        bw_nom = _as_float(row.get("bw_nominal_kHz"))

        lic = str(row.get("Licencia", "-"))
        flags = (
            f"{str(row.get('Cumple_FC', '-'))}/"
            f"{str(row.get('Cumple_BW', '-'))}/"
            f"{str(row.get('Cumple_P', '-'))}"
        )
        lines.append(
            f"{idx:02d}  "
            f"{lic:>3}  "
            f"{flags:>7}   "
            f"{_format_value(fc_med, '11.4f'):>11}  "
            f"{_format_value(bw_med, '11.1f'):>11}  "
            f"{_format_value(p_med, '10.2f'):>10}  "
            f"{_format_value(fc_nom, '11.4f'):>11}  "
            f"{_format_value(bw_nom, '11.1f'):>11}"
        )
    return lines


def _add_result_overlays(ax: plt.Axes, freqs_mhz: np.ndarray, pxx: np.ndarray, results: List[Dict[str, Any]]) -> None:
    for idx, row in enumerate(results, start=1):
        color = _result_color(row)

        fc_med_mhz = _as_float(row.get("fc_medida_MHz", row.get("fc_mhz")))
        bw_med_khz = _as_float(row.get("bw_medido_kHz", row.get("bw_khz")))
        if fc_med_mhz is not None and bw_med_khz is not None:
            half_bw_mhz = bw_med_khz / 2000.0
            left_med = fc_med_mhz - half_bw_mhz
            right_med = fc_med_mhz + half_bw_mhz
            ax.axvspan(left_med, right_med, color=color, alpha=0.18, zorder=1)
            ax.axvline(fc_med_mhz, color=color, linewidth=1.4, alpha=0.9, zorder=2)

            label_y = _as_float(row.get("p_medida_dBm", row.get("power_dbm")))
            if label_y is None:
                mask = (freqs_mhz >= left_med) & (freqs_mhz <= right_med)
                label_y = float(np.max(pxx[mask])) if np.any(mask) else float(np.max(pxx))
            ax.text(
                fc_med_mhz,
                label_y + 0.8,
                str(idx),
                color=color,
                fontsize=8,
                ha="center",
                va="bottom",
                fontweight="bold",
                zorder=3,
            )

        fc_nom_mhz = _as_float(row.get("fc_nominal_MHz"))
        bw_nom_khz = _as_float(row.get("bw_nominal_kHz"))
        if fc_nom_mhz is not None and bw_nom_khz is not None:
            half_nom_mhz = bw_nom_khz / 2000.0
            left_nom = fc_nom_mhz - half_nom_mhz
            right_nom = fc_nom_mhz + half_nom_mhz
            ax.axvspan(
                left_nom,
                right_nom,
                facecolor=color,
                edgecolor=color,
                hatch="//",
                alpha=0.07,
                linewidth=0.8,
                zorder=0,
            )
            ax.axvline(fc_nom_mhz, color=color, linestyle="--", linewidth=1.0, alpha=0.95, zorder=2)


def _plot_pair(pair: PlotPair, signal_json: Dict[str, Any], response_json: Dict[str, Any]) -> plt.Figure:
    frame_json = signal_json.get("frame", {})
    freqs_mhz, pxx = _build_freq_axis_mhz(frame_json)
    results = sorted(response_json.get("results", []), key=_result_sort_key)

    fig = plt.figure(figsize=(16, 9), constrained_layout=True)
    grid = fig.add_gridspec(2, 1, height_ratios=[3.2, 1.8], hspace=0.18)
    ax = fig.add_subplot(grid[0, 0])
    ax_info = fig.add_subplot(grid[1, 0])

    ax.plot(freqs_mhz, pxx, color="#202020", linewidth=1.0, zorder=2)

    threshold = _as_float(response_json.get("umbral"))
    if threshold is not None:
        ax.axhline(threshold, color="#7f7f7f", linestyle="--", linewidth=1.0, alpha=0.9, zorder=1)

    _add_result_overlays(ax, freqs_mhz, pxx, results)

    ax.set_title(
        f"{pair.response_path.name} | mode={response_json.get('mode')} | "
        f"emissions={response_json.get('num_emissions')}",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Pxx")
    ax.grid(True, alpha=0.22)
    ax.set_xlim(float(freqs_mhz.min()), float(freqs_mhz.max()))

    legend_handles = [
        Line2D([0], [0], color="#202020", lw=1.5, label="Pxx"),
        Line2D([0], [0], color="#7f7f7f", lw=1.0, linestyle="--", label="API threshold"),
        Patch(facecolor="#1f77b4", alpha=0.18, label="Measured BW"),
        Patch(facecolor="#1f77b4", edgecolor="#1f77b4", hatch="//", alpha=0.07, label="Nominal BW"),
        Line2D([0], [0], color="#2ca02c", lw=4, label="All checks pass"),
        Line2D([0], [0], color="#ff7f0e", lw=4, label="License exists, some check fails"),
        Line2D([0], [0], color="#d62728", lw=4, label="No license match"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8)

    ax_info.axis("off")
    summary_lines = _build_summary_lines(pair.response_path, response_json, results)
    fontsize = 8 if len(summary_lines) <= 24 else 7
    ax_info.text(
        0.01,
        0.98,
        "\n".join(summary_lines),
        va="top",
        ha="left",
        family="monospace",
        fontsize=fontsize,
        transform=ax_info.transAxes,
    )

    if hasattr(fig.canvas.manager, "set_window_title"):
        fig.canvas.manager.set_window_title(pair.response_path.name)

    fig.suptitle(
        f"Signal: {pair.signal_path.name}",
        x=0.5,
        y=0.995,
        fontsize=11,
    )
    return fig


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Visualiza secuencialmente la respuesta JSON de la API de cumplimiento "
            "sobre la Pxx original."
        )
    )
    parser.add_argument("--signals-dir", type=Path, default=DEFAULT_SIGNALS_DIR)
    parser.add_argument("--responses-dir", type=Path, default=DEFAULT_RESPONSES_DIR)
    parser.add_argument("--pattern", type=str, default=None, help="Filtra por nombre de archivo.")
    parser.add_argument("--start-index", type=int, default=0, help="Indice inicial dentro de la lista ordenada.")
    parser.add_argument("--limit", type=int, default=None, help="Cantidad maxima de plots a mostrar.")
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Construye los plots pero no abre la ventana. Util para validacion rapida.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    signals_dir = args.signals_dir.expanduser().resolve()
    responses_dir = args.responses_dir.expanduser().resolve()

    if not signals_dir.exists():
        raise SystemExit(f"Signals directory not found: {signals_dir}")
    if not responses_dir.exists():
        raise SystemExit(f"Responses directory not found: {responses_dir}")

    pairs = _build_pairs(signals_dir, responses_dir, args.pattern)
    if args.start_index > 0:
        pairs = pairs[args.start_index :]
    if args.limit is not None:
        pairs = pairs[: args.limit]

    if not pairs:
        raise SystemExit("No matching signal/response pairs were found.")

    total = len(pairs)
    print(f"Found {total} plots from {responses_dir}")

    for idx, pair in enumerate(pairs, start=1):
        print(f"[{idx}/{total}] showing {pair.response_path.name}")
        signal_json = _load_json(pair.signal_path)
        response_json = _load_json(pair.response_path)

        fig = _plot_pair(pair, signal_json, response_json)
        if args.no_show:
            plt.close(fig)
            continue

        plt.show()
        plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
