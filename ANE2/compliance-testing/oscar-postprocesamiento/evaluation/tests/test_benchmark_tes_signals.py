from __future__ import annotations

import sys
import unittest
from pathlib import Path

POSTPRO_DIR = Path(__file__).resolve().parents[2]
if str(POSTPRO_DIR) not in sys.path:
    sys.path.insert(0, str(POSTPRO_DIR))

from evaluation.benchmark_tes_signals import choose_simple_overrides, choose_simple_preset, run_benchmark  # noqa: E402
from src.spectrum_frame import SpectrumFrame  # noqa: E402


class TesSignalsBenchmarkTests(unittest.TestCase):
    def test_benchmark_runs_on_minimal_fixture(self) -> None:
        fixture_dir = Path(__file__).resolve().parent / "fixtures"
        report = run_benchmark(fixture_dir, preset_mode="general", min_iou=0.10, beta=2.0)
        self.assertEqual(report["num_files"], 1)
        detectors = {row["detector"] for row in report["global_summary"]}
        self.assertEqual(detectors, {"legacy", "simple"})
        self.assertTrue(any(row["family"] == "fm_broadcast" for row in report["group_summary"]))

    def test_auto_preset_selects_uhf_profile_for_tv_family(self) -> None:
        frame = SpectrumFrame(
            amplitudes_dbm=[-100.0] * 1024,
            f_start_hz=470.0e6,
            f_stop_hz=476.0e6,
        )
        preset = choose_simple_preset(frame, family="uhf_tv", preset_mode="auto")
        self.assertEqual(preset, "uhf_tv")

    def test_auto_preset_selects_fm_dense_for_high_center_dense_windows(self) -> None:
        frame = SpectrumFrame(
            amplitudes_dbm=[-100.0] * 1024,
            f_start_hz=2_105.5e6,
            f_stop_hz=2_125.5e6,
        )
        preset = choose_simple_preset(frame, family="window_2105.500-2125.500_MHz", preset_mode="auto")
        self.assertEqual(preset, "fm_dense")

    def test_auto_overrides_apply_for_fm_family(self) -> None:
        frame = SpectrumFrame(
            amplitudes_dbm=[-100.0] * 1024,
            f_start_hz=88.0e6,
            f_stop_hz=108.0e6,
        )
        overrides = choose_simple_overrides(
            frame,
            family="fm_broadcast",
            preset_mode="auto",
            preset_name="fm_dense",
        )
        self.assertIsNotNone(overrides)
        self.assertEqual(overrides["threshold_margin_db"], 4.5)

    def test_auto_overrides_apply_for_21ghz_dense_window(self) -> None:
        frame = SpectrumFrame(
            amplitudes_dbm=[-100.0] * 1024,
            f_start_hz=2_132_100_000.0,
            f_stop_hz=2_152_100_000.0,
        )
        overrides = choose_simple_overrides(
            frame,
            family="window_2132.100-2152.100_MHz",
            preset_mode="auto",
            preset_name="fm_dense",
        )
        self.assertIsNotNone(overrides)
        self.assertEqual(overrides["threshold_margin_db"], 1.5)
        self.assertEqual(overrides["smooth_sigma_bins"], 0.0)
        self.assertEqual(overrides["grow_threshold_relax_db"], 0.0)
        self.assertEqual(overrides["seed_prominence_db"], 1.5)


if __name__ == "__main__":
    unittest.main()
