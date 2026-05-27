import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot instrument and radio traces from a CSV file."
    )
    parser.add_argument(
        "-r",
        "--record",
        required=True,
        help="Path to the CSV file to plot.",
    )
    return parser.parse_args()


def load_rows(csv_path: Path) -> list[dict]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def to_array(values: str) -> np.ndarray:
    return np.asarray(json.loads(values), dtype=float)


class CsvTraceViewer:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.index = len(rows) - 1

        # leave room on the right for metrics panel
        self.fig, self.ax = plt.subplots(figsize=(11, 6))
        self.fig.subplots_adjust(right=0.72)

        # dedicated axes for metrics to avoid overlapping the plot area
        self.metrics_ax = self.fig.add_axes([0.75, 0.2, 0.22, 0.65])
        self.metrics_ax.axis("off")

        self._build_buttons()
        self._render()

    def _build_buttons(self) -> None:
        self.fig.subplots_adjust(bottom=0.2)

        ax_prev = self.fig.add_axes([0.2, 0.05, 0.18, 0.08])
        ax_next = self.fig.add_axes([0.42, 0.05, 0.18, 0.08])
        ax_latest = self.fig.add_axes([0.64, 0.05, 0.18, 0.08])

        self.btn_prev = Button(ax_prev, "Previous")
        self.btn_next = Button(ax_next, "Next")
        self.btn_latest = Button(ax_latest, "Latest")

        self.btn_prev.on_clicked(self._on_prev)
        self.btn_next.on_clicked(self._on_next)
        self.btn_latest.on_clicked(self._on_latest)

    def _render(self) -> None:
        row = self.rows[self.index]
        method = row.get("method", "unknown")
        realization = row.get("realization", "0")
        nominal = to_array(row["nominal_signal"])
        received = to_array(row["received_signal"])

        mse = row.get("mse", "")
        mae = row.get("mae", "")
        spectral_distance = row.get("spectral_distance", "")
        pearson = row.get("pearsonCorrelation") or row.get("pearson") or ""

        self.ax.clear()
        plt.sca(self.ax)
        plt.plot(nominal, label="Instrument (Nominal)", color="#1f77b4", linewidth=1.0)
        plt.plot(received, label="Radio (Received)", color="#ff7f0e", linewidth=1.0)
        self.ax.set_title(f"Method: {method} | Realization: {realization}")
        self.ax.set_xlabel("Sample Index")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True, alpha=0.3)
        self.ax.legend(loc="upper right")

        metrics_text = f"MSE: {mse}\nMAE: {mae}\nSpectral Distance (dB): {spectral_distance}"
        if pearson:
            metrics_text += f"\nPearson: {pearson}"
        # draw metrics in the dedicated right-side panel
        self.metrics_ax.clear()
        self.metrics_ax.axis("off")
        self.metrics_ax.text(
            0,
            1,
            metrics_text,
            transform=self.metrics_ax.transAxes,
            fontsize=10,
            va="top",
            wrap=True,
        )

        self.fig.canvas.draw_idle()

    def _on_prev(self, _event) -> None:
        if self.index > 0:
            self.index -= 1
            self._render()

    def _on_next(self, _event) -> None:
        if self.index < len(self.rows) - 1:
            self.index += 1
            self._render()

    def _on_latest(self, _event) -> None:
        self.index = len(self.rows) - 1
        self._render()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.record).expanduser().resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 1

    rows = load_rows(csv_path)
    if not rows:
        print("CSV has no data rows.")
        return 1

    CsvTraceViewer(rows)
    plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
