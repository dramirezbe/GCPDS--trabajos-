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
from matplotlib.widgets import Button


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CAMPAIGN_NUMBER = 275


@dataclass(frozen=True)
class PlotPair:
    signal_path: Path
    response_path: Path


def _campaign_dir_name(campaign_number: int, suffix: str) -> str:
    return f"camp-{campaign_number}-{suffix}"


def _resolve_data_dir(folder_arg: Optional[Path], default_name: str) -> Path:
    if folder_arg is None:
        return (BASE_DIR / default_name).resolve()

    return folder_arg.expanduser().resolve()


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


def _build_plot_title(pair: PlotPair, response_json: Dict[str, Any]) -> str:
    stem = pair.response_path.stem
    if stem.endswith("_response"):
        stem = stem[:-9]

    parts = stem.split("_")
    if len(parts) >= 6 and parts[2] == "signal" and parts[4] == "row":
        title = f"{parts[0]} | {parts[1]} | signal {parts[3]} | row {parts[5]}"
    else:
        title = stem.replace("_", " ")

    mode = _format_text_value(response_json.get("mode"))
    emissions = _format_text_value(response_json.get("num_emissions"))
    return f"{title}\nmode={mode} | emissions={emissions}"


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


def _format_text_value(value: Any) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text if text else "-"


def _resolve_result_dane_codes(response_json: Dict[str, Any], results: List[Dict[str, Any]]) -> List[str]:
    default_dane = response_json.get("dane")
    if default_dane is None:
        danes = response_json.get("danes") or []
        default_dane = danes[0] if danes else None
    default_dane_text = _format_text_value(default_dane)

    if not results:
        return []

    row_level_codes = [
        row.get("dane") or row.get("codigo_dane") or row.get("dane_code")
        for row in results
    ]
    if any(code is not None for code in row_level_codes):
        return [_format_text_value(code or default_dane) for code in row_level_codes]

    results_by_dane = response_json.get("results_by_dane")
    if isinstance(results_by_dane, dict):
        for dane_code, dane_rows in results_by_dane.items():
            if dane_rows == results:
                return [str(dane_code)] * len(results)

        resolved_codes: List[str] = []
        for idx, row in enumerate(results):
            matched_code = None

            for dane_code, dane_rows in results_by_dane.items():
                if idx < len(dane_rows) and dane_rows[idx] == row:
                    matched_code = dane_code
                    break

            if matched_code is None:
                for dane_code, dane_rows in results_by_dane.items():
                    if row in dane_rows:
                        matched_code = dane_code
                        break

            resolved_codes.append(_format_text_value(matched_code or default_dane))
        return resolved_codes

    return [default_dane_text] * len(results)


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
        "id  lic   dane  FC/BW/P   fc_med(MHz)  bw_med(kHz)  p_med(dBm)  fc_nom(MHz)  bw_nom(kHz)",
        "--  ---  -----  -------   -----------  -----------  ----------  -----------  -----------",
    ]
    dane_codes = _resolve_result_dane_codes(response_json, results)

    for idx, (row, dane_code) in enumerate(zip(results, dane_codes), start=1):
        fc_med = _as_float(row.get("fc_medida_MHz", row.get("fc_mhz")))
        bw_med = _as_float(row.get("bw_medido_kHz", row.get("bw_khz")))
        p_med = _as_float(row.get("p_medida_dBm", row.get("power_dbm")))
        fc_nom = _as_float(row.get("fc_nominal_MHz"))
        bw_nom = _as_float(row.get("bw_nominal_kHz"))

        lic = _format_text_value(row.get("Licencia"))
        flags = (
            f"{_format_text_value(row.get('Cumple_FC'))}/"
            f"{_format_text_value(row.get('Cumple_BW'))}/"
            f"{_format_text_value(row.get('Cumple_P'))}"
        )
        lines.append(
            f"{idx:02d}  "
            f"{lic:>3}  "
            f"{_format_text_value(dane_code):>5}  "
            f"{flags:>7}   "
            f"{_format_value(fc_med, '11.4f'):>11}  "
            f"{_format_value(bw_med, '11.1f'):>11}  "
            f"{_format_value(p_med, '10.2f'):>10}  "
            f"{_format_value(fc_nom, '11.4f'):>11}  "
            f"{_format_value(bw_nom, '11.1f'):>11}"
        )
    return lines


def _extract_debug_vector(response_json: Dict[str, Any], key: str, expected_len: int) -> Optional[np.ndarray]:
    debug_json = response_json.get("debug")
    if not isinstance(debug_json, dict):
        return None

    raw_values = debug_json.get(key)
    if raw_values is None:
        return None

    try:
        vector = np.asarray(raw_values, dtype=float).reshape(-1)
    except Exception:
        return None

    if vector.size != expected_len:
        return None

    return vector


def _add_debug_overlays(ax: plt.Axes, freqs_mhz: np.ndarray, response_json: Dict[str, Any]) -> List[Line2D]:
    legend_handles: List[Line2D] = []

    noise_floor = _extract_debug_vector(response_json, "vector_piso_ruido", freqs_mhz.size)
    if noise_floor is not None:
        ax.plot(
            freqs_mhz,
            noise_floor,
            color="#9467bd",
            linewidth=1.0,
            alpha=0.95,
            zorder=2,
        )
        legend_handles.append(
            Line2D([0], [0], color="#9467bd", lw=1.4, label="Debug noise floor")
        )

    dynamic_threshold = _extract_debug_vector(
        response_json,
        "vector_umbral_dinamico",
        freqs_mhz.size,
    )
    if dynamic_threshold is not None:
        ax.plot(
            freqs_mhz,
            dynamic_threshold,
            color="#17becf",
            linewidth=1.0,
            linestyle="--",
            alpha=0.95,
            zorder=2,
        )
        legend_handles.append(
            Line2D([0], [0], color="#17becf", lw=1.4, linestyle="--", label="Debug dynamic threshold")
        )

    return legend_handles


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


def _draw_plot(
    fig: plt.Figure,
    pair: PlotPair,
    signal_json: Dict[str, Any],
    response_json: Dict[str, Any],
    *,
    position_label: Optional[str] = None,
) -> None:
    frame_json = signal_json.get("frame", {})
    freqs_mhz, pxx = _build_freq_axis_mhz(frame_json)
    results = sorted(response_json.get("results", []), key=_result_sort_key)
    plot_title = _build_plot_title(pair, response_json)

    fig.clear()
    fig.patch.set_facecolor("white")
    grid = fig.add_gridspec(
        2,
        1,
        height_ratios=[3.1, 2.0],
        hspace=0.14,
        left=0.055,
        right=0.985,
        top=0.90,
        bottom=0.13,
    )
    ax = fig.add_subplot(grid[0, 0])
    ax_info = fig.add_subplot(grid[1, 0])

    ax.plot(freqs_mhz, pxx, color="#202020", linewidth=1.0, zorder=2)
    debug_handles = _add_debug_overlays(ax, freqs_mhz, response_json)

    threshold = _as_float(response_json.get("umbral"))
    if threshold is not None:
        ax.axhline(threshold, color="#7f7f7f", linestyle="--", linewidth=1.0, alpha=0.9, zorder=1)

    _add_result_overlays(ax, freqs_mhz, pxx, results)

    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Pxx")
    ax.grid(True, alpha=0.22)
    ax.set_xlim(float(freqs_mhz.min()), float(freqs_mhz.max()))

    legend_handles = [
        Line2D([0], [0], color="#202020", lw=1.5, label="Pxx"),
        Line2D([0], [0], color="#7f7f7f", lw=1.0, linestyle="--", label="API threshold"),
        *debug_handles,
        Patch(facecolor="#1f77b4", alpha=0.18, label="Measured BW"),
        Patch(facecolor="#1f77b4", edgecolor="#1f77b4", hatch="//", alpha=0.07, label="Nominal BW"),
        Line2D([0], [0], color="#2ca02c", lw=4, label="All checks pass"),
        Line2D([0], [0], color="#ff7f0e", lw=4, label="License exists, some check fails"),
        Line2D([0], [0], color="#d62728", lw=4, label="No license match"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8)

    ax_info.axis("off")
    summary_lines = _build_summary_lines(pair.response_path, response_json, results)
    fontsize = 9 if len(summary_lines) <= 24 else 8
    ax_info.text(
        0.01,
        0.98,
        "\n".join(summary_lines),
        va="top",
        ha="left",
        family="monospace",
        fontsize=fontsize,
        linespacing=1.15,
        transform=ax_info.transAxes,
    )

    if hasattr(fig.canvas.manager, "set_window_title"):
        fig.canvas.manager.set_window_title(pair.response_path.name)

    if position_label:
        plot_title = f"{position_label}\n{plot_title}"

    fig.suptitle(
        plot_title,
        x=0.5,
        y=0.992,
        fontsize=14,
        fontweight="bold",
        linespacing=1.25,
    )


def _plot_pair(
    pair: PlotPair,
    signal_json: Dict[str, Any],
    response_json: Dict[str, Any],
    *,
    position_label: Optional[str] = None,
) -> plt.Figure:
    fig = plt.figure(figsize=(17, 9.4))
    _draw_plot(
        fig,
        pair,
        signal_json,
        response_json,
        position_label=position_label,
    )
    return fig


class _PlotBrowser:
    def __init__(self, pairs: List[PlotPair]) -> None:
        self.pairs = pairs
        self.index = 0
        self.fig = plt.figure(figsize=(17, 9.4))
        self._buttons: List[Button] = []
        self.fig.canvas.mpl_connect("key_press_event", self._on_key_press)
        self.fig.canvas.mpl_connect("resize_event", self._on_resize)
        self._redraw()

    def show(self) -> None:
        plt.show()

    def _on_key_press(self, event: Any) -> None:
        if event.key in {"right", "n", " "}:
            self._go_next(event)
        elif event.key in {"left", "p", "backspace"}:
            self._go_previous(event)
        elif event.key == "r":
            self._reload_current(event)

    def _on_resize(self, _event: Any) -> None:
        self.fig.canvas.draw_idle()

    def _create_button(self, bounds: List[float], label: str, callback: Any) -> Button:
        ax_button = self.fig.add_axes(bounds)
        ax_button.set_in_layout(False)
        button = Button(ax_button, label)
        button.on_clicked(callback)
        self._buttons.append(button)
        return button

    def _set_button_enabled(self, button: Button, enabled: bool) -> None:
        facecolor = "#f0f0f0" if enabled else "#e0e0e0"
        text_color = "#111111" if enabled else "#999999"
        button.ax.set_facecolor(facecolor)
        button.hovercolor = "#d8ebff" if enabled else facecolor
        button.label.set_color(text_color)

    def _draw_controls(self) -> None:
        prev_button = self._create_button([0.33, 0.035, 0.10, 0.05], "Anterior", self._go_previous)
        reload_button = self._create_button([0.45, 0.035, 0.10, 0.05], "Recargar", self._reload_current)
        next_button = self._create_button([0.57, 0.035, 0.10, 0.05], "Siguiente", self._go_next)

        self._set_button_enabled(prev_button, self.index > 0)
        self._set_button_enabled(reload_button, True)
        self._set_button_enabled(next_button, self.index < len(self.pairs) - 1)

    def _redraw(self) -> None:
        pair = self.pairs[self.index]
        position_label = f"[{self.index + 1}/{len(self.pairs)}]"
        print(f"{position_label} showing {pair.response_path.name}")
        signal_json = _load_json(pair.signal_path)
        response_json = _load_json(pair.response_path)
        _draw_plot(
            self.fig,
            pair,
            signal_json,
            response_json,
            position_label=position_label,
        )
        self._buttons = []
        self._draw_controls()
        self.fig.canvas.draw()

    def _set_index(self, new_index: int) -> None:
        if new_index < 0 or new_index >= len(self.pairs) or new_index == self.index:
            return
        self.index = new_index
        self._redraw()

    def _go_previous(self, _event: Any) -> None:
        self._set_index(self.index - 1)

    def _go_next(self, _event: Any) -> None:
        self._set_index(self.index + 1)

    def _reload_current(self, _event: Any) -> None:
        self._redraw()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Visualiza la respuesta JSON de la API de cumplimiento "
            "sobre la Pxx original y permite navegar con botones."
        )
    )
    parser.add_argument(
        "-n",
        "--campaign-number",
        "--number-camp",
        dest="campaign_number",
        type=int,
        default=DEFAULT_CAMPAIGN_NUMBER,
        help=f"Numero de campana para resolver camp-<n>-signals y camp-<n>-responses (default: {DEFAULT_CAMPAIGN_NUMBER}).",
    )
    parser.add_argument(
        "--signals-dir",
        type=Path,
        default=None,
        help="Ruta manual a la carpeta de senales. Si se omite, usa camp-<n>-signals.",
    )
    parser.add_argument(
        "--responses-dir",
        type=Path,
        default=None,
        help="Ruta manual a la carpeta de respuestas. Si se omite, usa camp-<n>-responses.",
    )
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
    signals_dir = _resolve_data_dir(
        args.signals_dir,
        _campaign_dir_name(args.campaign_number, "signals"),
    )
    responses_dir = _resolve_data_dir(
        args.responses_dir,
        _campaign_dir_name(args.campaign_number, "responses"),
    )

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

    if args.no_show:
        for idx, pair in enumerate(pairs, start=1):
            print(f"[{idx}/{total}] validating {pair.response_path.name}")
            signal_json = _load_json(pair.signal_path)
            response_json = _load_json(pair.response_path)
            fig = _plot_pair(
                pair,
                signal_json,
                response_json,
                position_label=f"[{idx}/{total}]",
            )
            plt.close(fig)
        return 0

    print("Use los botones Anterior/Recargar/Siguiente o las teclas izquierda/derecha/r.")
    browser = _PlotBrowser(pairs)
    browser.show()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
