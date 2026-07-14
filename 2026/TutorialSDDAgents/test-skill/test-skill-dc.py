#!/usr/bin/env python3
"""
DC Spike Removal — simulation, removal, and validation using numpy/scipy.

Generates clean signals, contaminates them with varying DC offsets + additive
Gaussian noise, removes the DC using multiple methods, validates recovery
quality, and saves before/after plots to png-dc/.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from pathlib import Path

OUT_DIR = Path("png-dc")
OUT_DIR.mkdir(exist_ok=True)

SEED = 42
rng = np.random.default_rng(SEED)

FS = 1000
T = 1.0
N = int(FS * T)
t = np.linspace(0, T, N, endpoint=False)


# ── 1. Clean base signals ────────────────────────────────────────────────────

def make_clean_signals(t):
    return {
        "sine_5Hz": np.sin(2 * np.pi * 5 * t),
        "sine_50Hz": np.sin(2 * np.pi * 50 * t),
        "sawtooth_10Hz": signal.sawtooth(2 * np.pi * 10 * t),
        "chirp": signal.chirp(t, f0=5, f1=80, t1=T, method="linear"),
        "mix_5_20_50": (
            0.5 * np.sin(2 * np.pi * 5 * t)
            + 0.3 * np.sin(2 * np.pi * 20 * t)
            + 0.2 * np.sin(2 * np.pi * 50 * t)
        ),
    }


# ── 2. DC contamination types ────────────────────────────────────────────────

def add_dc_offset(signal, dc_value=2.5):
    return signal + dc_value


def add_dc_step(signal, step_at=0.4, low=0.0, high=3.0):
    dc = np.where(t >= step_at, high, low)
    return signal + dc


def add_dc_ramp(signal, start=0.0, end=3.0):
    dc = np.linspace(start, end, len(t))
    return signal + dc


def add_dc_spike(signal, center=0.5, width=0.05, amplitude=5.0):
    spike = amplitude * np.exp(-0.5 * ((t - center) / (width / 4)) ** 2)
    return signal + spike


def add_dc_sinusoidal(signal, freq=0.5, amplitude=2.0):
    dc = amplitude * np.sin(2 * np.pi * freq * t)
    return signal + dc


DC_TYPES = {
    "constant_2.5": lambda s: add_dc_offset(s, 2.5),
    "step_0_to_3": lambda s: add_dc_step(s, 0.4, 0.0, 3.0),
    "ramp_0_to_3": lambda s: add_dc_ramp(s, 0.0, 3.0),
    "gaussian_spike": lambda s: add_dc_spike(s, 0.5, 0.05, 5.0),
    "sinusoidal_drift": lambda s: add_dc_sinusoidal(s, 0.5, 2.5),
}


# ── 3. Gaussian noise ────────────────────────────────────────────────────────

def add_gaussian_noise(signal, snr_db=30):
    signal_power = np.mean(signal**2)
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = rng.normal(0, np.sqrt(noise_power), size=len(signal))
    return signal + noise, noise


# ── 4. DC removal methods ────────────────────────────────────────────────────

def remove_dc_mean(signal):
    return signal - np.mean(signal)


def remove_dc_median(signal):
    return signal - np.median(signal)


def remove_dc_detrend(x):
    return signal.detrend(x)


def remove_dc_butter_highpass(x, cutoff=1.0, fs=FS, order=4):
    nyq = fs / 2
    b, a = signal.butter(order, cutoff / nyq, btype="high")
    return signal.filtfilt(b, a, x)


def remove_dc_detrend_linear(x):
    return signal.detrend(x, type="linear")


def remove_dc_subtract_lpf_baseline(x, cutoff=1.0, fs=FS, order=4):
    nyq = fs / 2
    b, a = signal.butter(order, cutoff / nyq, btype="low")
    baseline = signal.filtfilt(b, a, x)
    return x - baseline


DC_REMOVERS = {
    "mean_subtraction": remove_dc_mean,
    "median_subtraction": remove_dc_median,
    "detrend_constant": remove_dc_detrend,
    "butter_highpass_1Hz": remove_dc_butter_highpass,
    "detrend_linear": remove_dc_detrend_linear,
    "lpf_baseline_subtraction": remove_dc_subtract_lpf_baseline,
}


# ── 5. Validation metrics ────────────────────────────────────────────────────

def validate(clean, recovered):
    mse = np.mean((clean - recovered) ** 2)
    rmse = np.sqrt(mse)
    corr = np.corrcoef(clean, recovered)[0, 1]
    signal_power = np.mean(clean**2)
    noise_power = np.mean((clean - recovered) ** 2)
    snr = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else np.inf
    return {"MSE": mse, "RMSE": rmse, "Corr": corr, "SNR_dB": snr}


# ── 6. Plotting ──────────────────────────────────────────────────────────────

def plot_comparison(
    clean, contaminated, recovered, dc_label, remover_label, signal_label, metrics, fname
):
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    fig.suptitle(
        f"{signal_label} | DC: {dc_label} | Remover: {remover_label}\n"
        f"Metrics: MSE={metrics['MSE']:.4f}  RMSE={metrics['RMSE']:.4f}  "
        f"Corr={metrics['Corr']:.4f}  SNR={metrics['SNR_dB']:.1f} dB",
        fontsize=11,
    )

    axes[0].plot(t, clean, linewidth=0.8, label="Clean (ground truth)")
    axes[0].set_ylabel("Amplitude")
    axes[0].set_title("Clean signal")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(t, clean, linewidth=0.6, alpha=0.4, label="Clean (ref)")
    axes[1].plot(t, contaminated, linewidth=0.8, label="Contaminated")
    axes[1].set_ylabel("Amplitude")
    axes[1].set_title(f"Contaminated with DC: {dc_label}")
    axes[1].legend(loc="upper right", fontsize=8)
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(t, clean, linewidth=0.6, alpha=0.4, label="Clean (ref)")
    axes[2].plot(t, recovered, linewidth=0.8, label=f"Recovered ({remover_label})")
    axes[2].set_xlabel("Time [s]")
    axes[2].set_ylabel("Amplitude")
    axes[2].set_title("DC removed")
    axes[2].legend(loc="upper right", fontsize=8)
    axes[2].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT_DIR / fname, dpi=150)
    plt.close(fig)


# ── 7. Summary table plot ────────────────────────────────────────────────────

def plot_summary_table(all_results):
    fig, ax = plt.subplots(figsize=(14, 3 + 0.4 * len(all_results)))
    ax.axis("off")

    rows = []
    for (sig, dc, rem), m in all_results:
        rows.append(
            f"{sig:20s} | {dc:20s} | {rem:30s} | "
            f"MSE={m['MSE']:7.4f} | RMSE={m['RMSE']:7.4f} | "
            f"Corr={m['Corr']:5.3f} | SNR={m['SNR_dB']:6.1f} dB"
        )

    header = (
        f"{'Signal':20s} | {'DC Type':20s} | {'Remover':30s} | "
        f"{'MSE':7s} | {'RMSE':7s} | {'Corr':5s} | {'SNR':7s}"
    )
    col_labels = ["Signal", "DC Type", "Remover", "MSE", "RMSE", "Corr", "SNR (dB)"]

    table_data = []
    for (sig, dc, rem), m in all_results:
        table_data.append(
            [sig, dc, rem, f"{m['MSE']:.4f}", f"{m['RMSE']:.4f}",
             f"{m['Corr']:.3f}", f"{m['SNR_dB']:.1f}"]
        )

    table = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(0.9, 1.2)

    ax.set_title("DC Removal Validation Summary — All Combinations", fontsize=12, pad=20)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "00_summary_table.png", dpi=150)
    plt.close(fig)


# ── 8. Main Pipeline ─────────────────────────────────────────────────────────

def main():
    print("Generating clean signals...")
    clean_signals = make_clean_signals(t)

    all_results = []
    n_combos = len(clean_signals) * len(DC_TYPES) * len(DC_REMOVERS)
    done = 0

    for sig_label, clean in clean_signals.items():
        for dc_label, dc_func in DC_TYPES.items():
            contaminated_pre_noise = dc_func(clean)
            contaminated, _ = add_gaussian_noise(contaminated_pre_noise, snr_db=30)

            for rem_label, rem_func in DC_REMOVERS.items():
                recovered = rem_func(contaminated)
                metrics = validate(clean, recovered)
                all_results.append(((sig_label, dc_label, rem_label), metrics))

                safename = f"{sig_label}__{dc_label}__{rem_label}".replace(" ", "_")
                plot_comparison(
                    clean, contaminated, recovered,
                    dc_label, rem_label, sig_label, metrics,
                    f"{safename}.png",
                )

                done += 1
                if done % 10 == 0 or done == n_combos:
                    print(f"  [{done}/{n_combos}] processed")

    print("\nGenerating summary table...")
    plot_summary_table(all_results)

    print(f"\nDone. {n_combos} plots saved to {OUT_DIR.resolve()}/")
    print(f"Summary table: {OUT_DIR / '00_summary_table.png'}")

    # Print top-3 best SNR per DC type
    print("\n=== Top-3 SNR per DC type ===")
    from collections import defaultdict
    by_dc = defaultdict(list)
    for (sig, dc, rem), m in all_results:
        by_dc[dc].append(((sig, dc, rem), m))
    for dc, entries in by_dc.items():
        entries.sort(key=lambda x: -x[1]["SNR_dB"])
        print(f"\n  DC={dc}:")
        for (sig, _, rem), m in entries[:3]:
            print(f"    {m['SNR_dB']:6.1f} dB | {sig:15s} | {rem}")


if __name__ == "__main__":
    main()
