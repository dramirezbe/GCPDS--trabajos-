#!/usr/bin/env python3
import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import welch


def read_iq_i8(path, max_iq=None, skip_iq=0):
    file_size = os.path.getsize(path)
    total_iq = file_size // 2

    if skip_iq < 0 or skip_iq >= total_iq:
        raise ValueError(f"skip_iq must be between 0 and {max(total_iq - 1, 0)}")

    available_iq = total_iq - skip_iq
    iq_to_read = available_iq if max_iq is None else min(max_iq, available_iq)

    raw = np.fromfile(
        path,
        dtype=np.int8,
        count=iq_to_read * 2,
        offset=skip_iq * 2,
    )

    if raw.size < 2:
        raise ValueError("File does not contain enough IQ samples.")

    raw = raw[: (raw.size // 2) * 2]
    iq = raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)
    iq /= 128.0
    return iq, total_iq


def compute_psd(iq, sample_rate_hz, nfft):
    freqs_hz, psd = welch(
        iq,
        fs=sample_rate_hz,
        window="hamming",
        nperseg=nfft,
        noverlap=nfft // 2,
        detrend=False,
        return_onesided=False,
        scaling="density",
    )

    freqs_hz = np.fft.fftshift(freqs_hz)
    psd = np.fft.fftshift(psd)
    psd_db = 10.0 * np.log10(np.maximum(psd, 1e-20))
    return freqs_hz, psd_db


def main():
    parser = argparse.ArgumentParser(
        description="Plot PSD from HackRF raw int8 IQ capture."
    )
    parser.add_argument("input", help="Path to HackRF .bin capture")
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=20e6,
        help="Sample rate in Hz (default: 20e6)",
    )
    parser.add_argument(
        "--center-freq",
        type=float,
        default=98e6,
        help="Center frequency in Hz (default: 98e6)",
    )
    parser.add_argument(
        "--nfft",
        type=int,
        default=16384,
        help="Welch FFT size (default: 16384)",
    )
    parser.add_argument(
        "--max-iq",
        type=int,
        default=4_000_000,
        help="Maximum IQ samples to read (default: 4000000)",
    )
    parser.add_argument(
        "--skip-iq",
        type=int,
        default=0,
        help="IQ samples to skip before reading (default: 0)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional PNG output path. If omitted, a window is shown.",
    )
    args = parser.parse_args()

    iq, total_iq = read_iq_i8(args.input, max_iq=args.max_iq, skip_iq=args.skip_iq)
    freqs_hz, psd_db = compute_psd(iq, args.sample_rate, args.nfft)
    freqs_mhz = (freqs_hz + args.center_freq) / 1e6

    duration_s = total_iq / args.sample_rate
    print(f"Input file: {args.input}")
    print(f"Total IQ samples in file: {total_iq}")
    print(f"Capture duration: {duration_s:.3f} s")
    print(f"IQ samples used for PSD: {iq.size}")

    plt.figure(figsize=(12, 6))
    plt.plot(freqs_mhz, psd_db, linewidth=1.0)
    plt.title("HackRF PSD")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("PSD (dB/Hz)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if args.out:
        plt.savefig(args.out, dpi=140)
        print(f"Saved plot to: {args.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
