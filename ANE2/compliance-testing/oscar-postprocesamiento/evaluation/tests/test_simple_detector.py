from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

POSTPRO_DIR = Path(__file__).resolve().parents[2]
if str(POSTPRO_DIR) not in sys.path:
    sys.path.insert(0, str(POSTPRO_DIR))

from src.simple_detector import (  # noqa: E402
    build_detection_mask,
    build_scalar_threshold,
    detect_emissions,
    estimate_global_noise_floor,
    get_simple_detector_config,
    segments_from_mask,
)
from src.spectrum_frame import SpectrumFrame  # noqa: E402


class SimpleDetectorTests(unittest.TestCase):
    def test_noise_floor_and_threshold_are_scalar(self) -> None:
        trace = np.array([-100.0] * 80 + [-85.0] * 20, dtype=float)
        nf = estimate_global_noise_floor(trace, noise_percentile=15.0)
        thr = build_scalar_threshold(nf, 6.0)
        self.assertLess(nf, -95.0)
        self.assertAlmostEqual(thr, nf + 6.0, places=6)

    def test_detect_emissions_merges_small_gap(self) -> None:
        amps = np.full(100, -100.0, dtype=float)
        amps[10:13] = -80.0
        amps[14:18] = -79.0
        frame = SpectrumFrame(amps, f_start_hz=0.0, f_stop_hz=99_000.0)

        run = detect_emissions(
            frame,
            preset_name="general",
            overrides={
                "threshold_margin_db": 6.0,
                "min_bandwidth_hz": 2_000.0,
                "max_gap_hz": 2_000.0,
                "smooth_sigma_bins": 0.0,
            },
        )
        self.assertEqual(run["detector_name"], "simple")
        self.assertEqual(len(run["segments"]), 1)
        seg = run["segments"][0]
        self.assertEqual(seg["measure_L"], 10)
        self.assertEqual(seg["measure_R"], 17)

    def test_presets_available(self) -> None:
        cfg = get_simple_detector_config("high_res")
        self.assertEqual(cfg.preset_name, "high_res")
        self.assertGreater(cfg.min_bandwidth_hz, 0.0)
        cfg_uhf = get_simple_detector_config("uhf_tv")
        self.assertEqual(cfg_uhf.preset_name, "uhf_tv")
        self.assertGreater(cfg_uhf.local_baseline_window_hz, cfg.local_baseline_window_hz)

    def test_detect_emissions_recovers_from_anomalous_scalar_threshold(self) -> None:
        x = np.arange(256, dtype=float)
        baseline = -50.5 + 0.35 * np.sin(np.linspace(0.0, 5.0 * np.pi, x.size))
        amps = baseline + 4.0 * np.exp(-0.5 * ((x - 120.0) / 6.0) ** 2)
        frame = SpectrumFrame(amps, f_start_hz=517.0e6, f_stop_hz=522.0e6)

        nf = estimate_global_noise_floor(amps, noise_percentile=12.0)
        thr = build_scalar_threshold(nf, 5.5)
        raw_mask = build_detection_mask(amps, thr)
        self.assertEqual(int(raw_mask.sum()), 0)

        run = detect_emissions(
            frame,
            preset_name="uhf_tv",
            overrides={
                "threshold_margin_db": 5.5,
                "min_bandwidth_hz": 80_000.0,
                "max_gap_hz": 60_000.0,
                "smooth_sigma_bins": 0.0,
                "local_baseline_window_hz": 800_000.0,
                "min_prominence_db": 3.5,
                "min_support_ratio": 0.10,
                "grow_threshold_relax_db": 2.5,
                "seed_prominence_db": 2.5,
                "edge_prominence_db": 1.0,
            },
        )
        self.assertGreaterEqual(len(run["segments"]), 1)
        seg = run["segments"][0]
        self.assertLess(seg["measure_L"], 120)
        self.assertGreater(seg["measure_R"], 120)

    def test_detect_emissions_expands_bandwidth_beyond_high_threshold_core(self) -> None:
        x = np.arange(256, dtype=float)
        amps = np.full(x.shape, -100.0, dtype=float)
        amps += 7.0 * np.exp(-0.5 * ((x - 128.0) / 11.0) ** 2)
        frame = SpectrumFrame(amps, f_start_hz=0.0, f_stop_hz=255_000.0)

        nf = estimate_global_noise_floor(amps, noise_percentile=15.0)
        thr = build_scalar_threshold(nf, 6.0)
        raw_segments = segments_from_mask(build_detection_mask(amps, thr))
        self.assertEqual(len(raw_segments), 1)
        raw_width = raw_segments[0][1] - raw_segments[0][0] + 1

        run = detect_emissions(
            frame,
            preset_name="general",
            overrides={
                "threshold_margin_db": 6.0,
                "min_bandwidth_hz": 2_000.0,
                "max_gap_hz": 2_000.0,
                "smooth_sigma_bins": 0.0,
                "local_baseline_window_hz": 40_000.0,
                "min_prominence_db": 3.0,
                "min_support_ratio": 0.10,
                "grow_threshold_relax_db": 3.0,
                "seed_prominence_db": 2.5,
                "edge_prominence_db": 1.0,
            },
        )
        self.assertEqual(len(run["segments"]), 1)
        seg = run["segments"][0]
        grown_width = seg["measure_R"] - seg["measure_L"] + 1
        self.assertGreater(grown_width, raw_width)

    def test_uhf_slow_rescue_adds_segments_when_spikes_dominate(self) -> None:
        x = np.arange(512, dtype=float)
        baseline = -51.0 + 0.2 * np.sin(np.linspace(0.0, 4.0 * np.pi, x.size))
        amps = baseline.copy()
        for center in (140.0, 260.0, 380.0):
            amps += 2.8 * np.exp(-0.5 * ((x - center) / 7.0) ** 2)
        amps += 6.8 * np.exp(-0.5 * ((x - 260.0) / 1.0) ** 2)
        frame = SpectrumFrame(amps, f_start_hz=517.0e6, f_stop_hz=537.0e6)

        run_no_rescue = detect_emissions(
            frame,
            preset_name="uhf_tv",
            overrides={
                "smooth_sigma_bins": 0.0,
                "min_prominence_db": 4.8,
                "min_support_ratio": 0.12,
                "slow_rescue_window_scale": 0.0,
            },
        )
        run_with_rescue = detect_emissions(
            frame,
            preset_name="uhf_tv",
            overrides={
                "smooth_sigma_bins": 0.0,
                "min_prominence_db": 4.8,
                "min_support_ratio": 0.12,
                "slow_rescue_window_scale": 3.0,
                "slow_rescue_delta_db": 1.2,
                "slow_rescue_peak_prominence_db": 1.8,
                "slow_rescue_max_width_factor": 8.0,
                "slow_rescue_gap_hz": 120_000.0,
                "slow_rescue_max_existing_segments": 1.0,
            },
        )
        self.assertLessEqual(len(run_no_rescue["segments"]), 1)
        self.assertGreaterEqual(len(run_with_rescue["segments"]), 2)
        self.assertTrue(any(bool(seg.get("slow_rescue", False)) for seg in run_with_rescue["segments"]))


if __name__ == "__main__":
    unittest.main()
