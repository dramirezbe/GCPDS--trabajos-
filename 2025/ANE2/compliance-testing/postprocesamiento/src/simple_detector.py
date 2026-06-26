from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

import numpy as np

from .spectrum_frame import SpectrumFrame


@dataclass(frozen=True)
class SimpleDetectorConfig:
    preset_name: str
    noise_percentile: float
    threshold_margin_db: float
    min_bandwidth_hz: float
    max_gap_hz: float
    smooth_sigma_bins: float = 1.0
    local_baseline_window_hz: float = 250_000.0
    min_prominence_db: float = 5.0
    min_support_ratio: float = 0.35
    grow_threshold_relax_db: float = 2.0
    seed_prominence_db: float = 3.5
    edge_prominence_db: float = 1.5
    slow_rescue_window_scale: float = 0.0
    slow_rescue_delta_db: float = 0.0
    slow_rescue_peak_prominence_db: float = 0.0
    slow_rescue_max_width_factor: float = 0.0
    slow_rescue_gap_hz: float = 0.0
    slow_rescue_max_existing_segments: float = 0.0


SIMPLE_DETECTOR_PRESETS: Dict[str, SimpleDetectorConfig] = {
    "general": SimpleDetectorConfig(
        preset_name="general",
        noise_percentile=15.0,
        threshold_margin_db=6.0,
        min_bandwidth_hz=8_000.0,
        max_gap_hz=6_000.0,
        smooth_sigma_bins=1.0,
        local_baseline_window_hz=300_000.0,
        min_prominence_db=5.5,
        min_support_ratio=0.55,
        grow_threshold_relax_db=2.0,
        seed_prominence_db=3.5,
        edge_prominence_db=2.0,
    ),
    "fm_dense": SimpleDetectorConfig(
        preset_name="fm_dense",
        noise_percentile=20.0,
        threshold_margin_db=5.0,
        min_bandwidth_hz=25_000.0,
        max_gap_hz=30_000.0,
        smooth_sigma_bins=1.0,
        local_baseline_window_hz=1_000_000.0,
        min_prominence_db=4.5,
        min_support_ratio=0.45,
        grow_threshold_relax_db=1.5,
        seed_prominence_db=2.5,
        edge_prominence_db=1.5,
    ),
    "high_res": SimpleDetectorConfig(
        preset_name="high_res",
        noise_percentile=15.0,
        threshold_margin_db=6.0,
        min_bandwidth_hz=2_500.0,
        max_gap_hz=2_000.0,
        smooth_sigma_bins=0.8,
        local_baseline_window_hz=120_000.0,
        min_prominence_db=5.5,
        min_support_ratio=0.50,
        grow_threshold_relax_db=1.5,
        seed_prominence_db=3.5,
        edge_prominence_db=2.0,
    ),
    "uhf_tv": SimpleDetectorConfig(
        preset_name="uhf_tv",
        noise_percentile=12.0,
        threshold_margin_db=5.5,
        min_bandwidth_hz=120_000.0,
        max_gap_hz=200_000.0,
        smooth_sigma_bins=2.0,
        local_baseline_window_hz=8_000_000.0,
        min_prominence_db=5.0,
        min_support_ratio=0.15,
        grow_threshold_relax_db=2.5,
        seed_prominence_db=2.75,
        edge_prominence_db=1.25,
        slow_rescue_window_scale=3.0,
        slow_rescue_delta_db=1.35,
        slow_rescue_peak_prominence_db=2.0,
        slow_rescue_max_width_factor=8.0,
        slow_rescue_gap_hz=120_000.0,
        slow_rescue_max_existing_segments=1.0,
    ),
}


def _gaussian_smooth1d(x: np.ndarray, sigma: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x.copy()
    sigma = float(max(0.0, sigma))
    if sigma <= 0.0:
        return x.copy()
    try:
        from scipy.ndimage import gaussian_filter1d

        return gaussian_filter1d(x, sigma=max(0.5, sigma))
    except Exception:
        k = max(1, int(round(3.0 * max(0.5, sigma))))
        ax = np.arange(-k, k + 1, dtype=float)
        ker = np.exp(-0.5 * (ax / max(0.5, sigma)) ** 2)
        ker /= np.sum(ker)
        return np.convolve(x, ker, mode="same")


def _rolling_percentile(x: np.ndarray, percentile: float, window_bins: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x.copy()

    q = float(np.clip(percentile, 0.0, 100.0))
    window_bins = int(max(1, window_bins))
    if window_bins % 2 == 0:
        window_bins += 1
    if window_bins <= 1:
        return x.copy()
    window_bins = min(window_bins, int(x.size) if int(x.size) % 2 == 1 else max(1, int(x.size) - 1))
    if window_bins <= 1:
        return x.copy()

    try:
        from scipy.ndimage import percentile_filter

        return percentile_filter(x, percentile=q, size=window_bins, mode="nearest")
    except Exception:
        pad = window_bins // 2
        padded = np.pad(x, pad_width=pad, mode="edge")
        windows = np.lib.stride_tricks.sliding_window_view(padded, window_bins)
        return np.percentile(windows, q, axis=-1)


def get_simple_detector_config(
    preset_name: str = "general",
    overrides: Optional[Mapping[str, Any]] = None,
) -> SimpleDetectorConfig:
    preset_key = str(preset_name or "general").strip().lower()
    if preset_key not in SIMPLE_DETECTOR_PRESETS:
        raise ValueError(f"Preset desconocido para detector simple: {preset_name}")

    base = SIMPLE_DETECTOR_PRESETS[preset_key]
    data = {
        "preset_name": base.preset_name,
        "noise_percentile": float(base.noise_percentile),
        "threshold_margin_db": float(base.threshold_margin_db),
        "min_bandwidth_hz": float(base.min_bandwidth_hz),
        "max_gap_hz": float(base.max_gap_hz),
        "smooth_sigma_bins": float(base.smooth_sigma_bins),
        "local_baseline_window_hz": float(base.local_baseline_window_hz),
        "min_prominence_db": float(base.min_prominence_db),
        "min_support_ratio": float(base.min_support_ratio),
        "grow_threshold_relax_db": float(base.grow_threshold_relax_db),
        "seed_prominence_db": float(base.seed_prominence_db),
        "edge_prominence_db": float(base.edge_prominence_db),
        "slow_rescue_window_scale": float(base.slow_rescue_window_scale),
        "slow_rescue_delta_db": float(base.slow_rescue_delta_db),
        "slow_rescue_peak_prominence_db": float(base.slow_rescue_peak_prominence_db),
        "slow_rescue_max_width_factor": float(base.slow_rescue_max_width_factor),
        "slow_rescue_gap_hz": float(base.slow_rescue_gap_hz),
        "slow_rescue_max_existing_segments": float(base.slow_rescue_max_existing_segments),
    }

    if overrides:
        for key in data.keys():
            if key not in overrides or overrides[key] is None:
                continue
            if key == "preset_name":
                data[key] = str(overrides[key]).strip().lower() or base.preset_name
            else:
                data[key] = float(overrides[key])

    data["noise_percentile"] = float(np.clip(data["noise_percentile"], 1.0, 49.0))
    data["threshold_margin_db"] = float(max(0.0, data["threshold_margin_db"]))
    data["min_bandwidth_hz"] = float(max(0.0, data["min_bandwidth_hz"]))
    data["max_gap_hz"] = float(max(0.0, data["max_gap_hz"]))
    data["smooth_sigma_bins"] = float(max(0.0, data["smooth_sigma_bins"]))
    data["local_baseline_window_hz"] = float(max(0.0, data["local_baseline_window_hz"]))
    data["min_prominence_db"] = float(max(0.0, data["min_prominence_db"]))
    data["min_support_ratio"] = float(np.clip(data["min_support_ratio"], 0.0, 1.0))
    data["grow_threshold_relax_db"] = float(max(0.0, data["grow_threshold_relax_db"]))
    data["seed_prominence_db"] = float(max(0.0, data["seed_prominence_db"]))
    data["edge_prominence_db"] = float(max(0.0, data["edge_prominence_db"]))
    data["slow_rescue_window_scale"] = float(max(0.0, data["slow_rescue_window_scale"]))
    data["slow_rescue_delta_db"] = float(max(0.0, data["slow_rescue_delta_db"]))
    data["slow_rescue_peak_prominence_db"] = float(max(0.0, data["slow_rescue_peak_prominence_db"]))
    data["slow_rescue_max_width_factor"] = float(max(0.0, data["slow_rescue_max_width_factor"]))
    data["slow_rescue_gap_hz"] = float(max(0.0, data["slow_rescue_gap_hz"]))
    data["slow_rescue_max_existing_segments"] = float(max(0.0, data["slow_rescue_max_existing_segments"]))
    return SimpleDetectorConfig(**data)


def estimate_global_noise_floor(
    trace_dbm: np.ndarray,
    noise_percentile: float = 15.0,
) -> float:
    x = np.asarray(trace_dbm, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")

    q = float(np.clip(noise_percentile, 1.0, 49.0))
    qv = float(np.percentile(x, q))
    lower = x[x <= qv]
    if lower.size == 0:
        lower = x
    return float(np.median(lower))


def build_scalar_threshold(noise_floor_dbm: float, threshold_margin_db: float) -> float:
    nf = float(noise_floor_dbm)
    margin = float(max(0.0, threshold_margin_db))
    return float(nf + margin)


def build_detection_mask(trace_dbm: np.ndarray, threshold_dbm: float) -> np.ndarray:
    x = np.asarray(trace_dbm, dtype=float)
    thr = np.asarray(threshold_dbm, dtype=float)
    return np.asarray(x > thr, dtype=bool)


def estimate_residual_floor(
    residual_db: np.ndarray,
    percentile: float = 20.0,
) -> float:
    x = np.asarray(residual_db, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")

    q = float(np.clip(percentile, 5.0, 45.0))
    qv = float(np.percentile(x, q))
    lower = x[x <= qv]
    if lower.size == 0:
        lower = x
    return float(np.median(lower))


def segments_from_mask(mask: np.ndarray) -> List[tuple[int, int]]:
    segs: List[tuple[int, int]] = []
    in_seg = False
    start = 0
    for i, v in enumerate(np.asarray(mask, dtype=bool)):
        if v and not in_seg:
            in_seg = True
            start = int(i)
        elif (not v) and in_seg:
            segs.append((start, int(i - 1)))
            in_seg = False
    if in_seg:
        segs.append((start, int(len(mask) - 1)))
    return segs


def _fill_small_false_gaps(mask: np.ndarray, max_gap_bins: int) -> np.ndarray:
    out = np.asarray(mask, dtype=bool).copy()
    max_gap_bins = int(max(0, max_gap_bins))
    if out.size == 0 or max_gap_bins <= 0:
        return out

    idx = 0
    n = len(out)
    while idx < n:
        if out[idx]:
            idx += 1
            continue
        j = idx
        while j < n and (not out[j]):
            j += 1
        gap_len = j - idx
        left_on = idx > 0 and bool(out[idx - 1])
        right_on = j < n and bool(out[j])
        if left_on and right_on and gap_len <= max_gap_bins:
            out[idx:j] = True
        idx = j
    return out


def _seeded_components(seed_mask: np.ndarray, grow_mask: np.ndarray) -> List[tuple[int, int]]:
    seed = np.asarray(seed_mask, dtype=bool)
    grow = np.asarray(grow_mask, dtype=bool)
    if seed.size == 0 or grow.size == 0:
        return []

    seed_segments = segments_from_mask(seed)
    comps = segments_from_mask(np.asarray(grow | seed, dtype=bool))
    out: List[tuple[int, int]] = []
    for start, end in comps:
        members = []
        for seed_start, seed_end in seed_segments:
            if int(seed_end) < int(start) or int(seed_start) > int(end):
                continue
            members.append((int(seed_start), int(seed_end)))
        if not members:
            continue
        if len(members) == 1:
            out.append((int(start), int(end)))
            continue

        split_edges: List[tuple[int, int]] = []
        for idx, (seed_start, seed_end) in enumerate(members):
            left = int(start) if idx == 0 else int((members[idx - 1][1] + seed_start) // 2 + 1)
            right = int(end) if idx == (len(members) - 1) else int((seed_end + members[idx + 1][0]) // 2)
            if right >= left:
                split_edges.append((left, right))
        out.extend(split_edges)
    return out


def _merge_close_segments(segments: List[tuple[int, int]], max_gap_bins: int) -> List[tuple[int, int]]:
    if not segments:
        return []
    merged: List[tuple[int, int]] = [segments[0]]
    max_gap_bins = int(max(0, max_gap_bins))
    for s, e in segments[1:]:
        ps, pe = merged[-1]
        if int(s) - int(pe) - 1 <= max_gap_bins:
            merged[-1] = (int(ps), int(e))
        else:
            merged.append((int(s), int(e)))
    return merged


def _bin_hz(frame: SpectrumFrame) -> float:
    try:
        bin_hz = float(frame.bin_hz)
    except Exception:
        bin_hz = float("nan")
    if np.isfinite(bin_hz) and bin_hz > 0.0:
        return float(bin_hz)

    try:
        f = np.asarray(frame.freq_hz, dtype=float)
        if f.size >= 2:
            df = np.diff(f)
            df = np.abs(df[np.isfinite(df)])
            if df.size > 0:
                return float(np.median(df))
    except Exception:
        pass
    return 1.0


def _window_bins_for_hz(frame: SpectrumFrame, window_hz: float) -> int:
    bin_hz = _bin_hz(frame)
    bins = int(max(1, round(float(window_hz) / max(bin_hz, 1.0))))
    if bins % 2 == 0:
        bins += 1
    return bins


def estimate_local_baseline(
    frame: SpectrumFrame,
    trace_dbm: np.ndarray,
    *,
    noise_percentile: float,
    window_hz: float,
) -> np.ndarray:
    x = np.asarray(trace_dbm, dtype=float)
    if x.size == 0:
        return x.copy()
    window_bins = _window_bins_for_hz(frame, window_hz)
    return _rolling_percentile(x, percentile=float(noise_percentile), window_bins=window_bins)


def postprocess_segments(
    frame: SpectrumFrame,
    segments: List[tuple[int, int]],
    *,
    max_gap_hz: float,
    min_bandwidth_hz: float,
) -> List[tuple[int, int]]:
    if not segments:
        return []

    bin_hz = _bin_hz(frame)
    max_gap_bins = int(max(0, round(float(max_gap_hz) / max(bin_hz, 1.0))))
    min_bandwidth_bins = int(max(1, np.ceil(float(min_bandwidth_hz) / max(bin_hz, 1.0))))

    merged = _merge_close_segments(segments, max_gap_bins=max_gap_bins)
    out: List[tuple[int, int]] = []
    for s, e in merged:
        if (int(e) - int(s) + 1) >= min_bandwidth_bins:
            out.append((int(s), int(e)))
    return out


def _segment_support_ratio(mask: np.ndarray, start: int, end: int) -> float:
    lo = int(max(0, start))
    hi = int(max(lo, end))
    seg = np.asarray(mask[lo : hi + 1], dtype=bool)
    if seg.size == 0:
        return 0.0
    return float(np.mean(seg))


def _segment_peak_prominence(
    trace_dbm: np.ndarray,
    baseline_dbm: np.ndarray,
    start: int,
    end: int,
) -> float:
    lo = int(max(0, start))
    hi = int(max(lo, end))
    seg_y = np.asarray(trace_dbm[lo : hi + 1], dtype=float)
    seg_base = np.asarray(baseline_dbm[lo : hi + 1], dtype=float)
    if seg_y.size == 0 or seg_base.size == 0:
        return 0.0
    return float(np.max(seg_y - seg_base))


def _segment_overlap_fraction(segment_a: tuple[int, int], segment_b: tuple[int, int]) -> float:
    a0, a1 = int(segment_a[0]), int(segment_a[1])
    b0, b1 = int(segment_b[0]), int(segment_b[1])
    inter = max(0, min(a1, b1) - max(a0, b0) + 1)
    if inter <= 0:
        return 0.0
    denom = max(1, min(a1 - a0 + 1, b1 - b0 + 1))
    return float(inter / denom)


def _collect_slow_rescue_segments(
    frame: SpectrumFrame,
    trace_dbm: np.ndarray,
    cfg: SimpleDetectorConfig,
) -> List[tuple[int, int]]:
    if cfg.slow_rescue_window_scale <= 0.0:
        return []

    bin_hz = _bin_hz(frame)
    slow_window_hz = max(
        float(cfg.local_baseline_window_hz) * float(cfg.slow_rescue_window_scale),
        float(cfg.min_bandwidth_hz) * 12.0,
    )
    slow_baseline = estimate_local_baseline(
        frame,
        trace_dbm,
        noise_percentile=cfg.noise_percentile,
        window_hz=slow_window_hz,
    )
    slow_residual = np.asarray(trace_dbm - slow_baseline, dtype=float)
    slow_floor_db = estimate_residual_floor(slow_residual, percentile=max(10.0, cfg.noise_percentile))
    slow_mask = np.asarray(slow_residual > (slow_floor_db + float(cfg.slow_rescue_delta_db)), dtype=bool)

    rescue_gap_hz = float(cfg.slow_rescue_gap_hz or min(cfg.max_gap_hz, cfg.min_bandwidth_hz))
    rescue_gap_bins = int(max(0, round(rescue_gap_hz / max(bin_hz, 1.0))))
    slow_segments = _seeded_components(
        _fill_small_false_gaps(slow_mask, rescue_gap_bins),
        _fill_small_false_gaps(slow_mask, rescue_gap_bins),
    )

    min_bandwidth_bins = int(max(1, np.ceil(float(cfg.min_bandwidth_hz) / max(bin_hz, 1.0))))
    max_width_bins = int(
        max(
            min_bandwidth_bins,
            round(float(cfg.slow_rescue_max_width_factor or 0.0) * float(cfg.min_bandwidth_hz) / max(bin_hz, 1.0)),
        )
    )

    out: List[tuple[int, int]] = []
    for start, end in slow_segments:
        width_bins = int(end) - int(start) + 1
        if width_bins < min_bandwidth_bins:
            continue
        if cfg.slow_rescue_max_width_factor > 0.0 and width_bins > max_width_bins:
            continue
        prominence = _segment_peak_prominence(trace_dbm, slow_baseline, start, end)
        if prominence < float(cfg.slow_rescue_peak_prominence_db):
            continue
        out.append((int(start), int(end)))
    return out


def _build_support_mask(
    trace_dbm: np.ndarray,
    residual_db: np.ndarray,
    threshold_dbm: float,
    residual_floor_db: float,
    cfg: SimpleDetectorConfig,
) -> np.ndarray:
    support_threshold_dbm = float(threshold_dbm - 0.5 * max(0.0, cfg.grow_threshold_relax_db))
    support_prominence_db = float(residual_floor_db + max(cfg.edge_prominence_db, 0.75 * cfg.seed_prominence_db))
    return np.asarray((trace_dbm > support_threshold_dbm) | (residual_db > support_prominence_db), dtype=bool)


def detect_emissions(
    frame: SpectrumFrame,
    *,
    preset_name: str = "general",
    overrides: Optional[Mapping[str, Any]] = None,
    threshold_margin_db_override: Optional[float] = None,
) -> Dict[str, Any]:
    cfg = get_simple_detector_config(preset_name=preset_name, overrides=overrides)
    if threshold_margin_db_override is not None:
        cfg = get_simple_detector_config(
            preset_name=cfg.preset_name,
            overrides={
                "noise_percentile": cfg.noise_percentile,
                "threshold_margin_db": float(threshold_margin_db_override),
                "min_bandwidth_hz": cfg.min_bandwidth_hz,
                "max_gap_hz": cfg.max_gap_hz,
                "smooth_sigma_bins": cfg.smooth_sigma_bins,
                "local_baseline_window_hz": cfg.local_baseline_window_hz,
                "min_prominence_db": cfg.min_prominence_db,
                "min_support_ratio": cfg.min_support_ratio,
                "grow_threshold_relax_db": cfg.grow_threshold_relax_db,
                "seed_prominence_db": cfg.seed_prominence_db,
                "edge_prominence_db": cfg.edge_prominence_db,
                "slow_rescue_window_scale": cfg.slow_rescue_window_scale,
                "slow_rescue_delta_db": cfg.slow_rescue_delta_db,
                "slow_rescue_peak_prominence_db": cfg.slow_rescue_peak_prominence_db,
                "slow_rescue_max_width_factor": cfg.slow_rescue_max_width_factor,
                "slow_rescue_gap_hz": cfg.slow_rescue_gap_hz,
                "slow_rescue_max_existing_segments": cfg.slow_rescue_max_existing_segments,
            },
        )

    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    if y.size == 0:
        return {
            "detector_name": "simple",
            "preset_name": cfg.preset_name,
            "noise_floor_dbm": float("nan"),
            "threshold_dbm": float("nan"),
            "segments": [],
            "config": cfg,
        }

    y_work = _gaussian_smooth1d(y, sigma=cfg.smooth_sigma_bins)
    nf = estimate_global_noise_floor(y_work, noise_percentile=cfg.noise_percentile)
    thr = build_scalar_threshold(nf, cfg.threshold_margin_db)
    local_baseline = estimate_local_baseline(
        frame,
        y_work,
        noise_percentile=cfg.noise_percentile,
        window_hz=cfg.local_baseline_window_hz,
    )
    residual_db = np.asarray(y_work - local_baseline, dtype=float)
    residual_floor_db = estimate_residual_floor(residual_db, percentile=max(10.0, cfg.noise_percentile))

    raw_mask = build_detection_mask(y_work, thr)
    residual_seed_threshold = float(residual_floor_db + cfg.seed_prominence_db)
    residual_edge_threshold = float(residual_floor_db + cfg.edge_prominence_db)
    grow_threshold_dbm = float(thr - cfg.grow_threshold_relax_db)
    seed_mask = np.asarray(raw_mask | (residual_db > residual_seed_threshold), dtype=bool)
    grow_mask = np.asarray((y_work > grow_threshold_dbm) | (residual_db > residual_edge_threshold), dtype=bool)
    support_mask = _build_support_mask(y_work, residual_db, thr, residual_floor_db, cfg)

    bin_hz = _bin_hz(frame)
    max_gap_bins = int(max(0, round(float(cfg.max_gap_hz) / max(bin_hz, 1.0))))
    cleaned_seed_mask = _fill_small_false_gaps(seed_mask, max_gap_bins=max_gap_bins)
    cleaned_grow_mask = _fill_small_false_gaps(grow_mask, max_gap_bins=max_gap_bins)
    cleaned_support_mask = _fill_small_false_gaps(support_mask, max_gap_bins=max_gap_bins)

    raw_segments = _seeded_components(cleaned_seed_mask, cleaned_grow_mask)
    min_bandwidth_bins = int(max(1, np.ceil(float(cfg.min_bandwidth_hz) / max(bin_hz, 1.0))))
    cleaned_segments = [
        (int(start), int(end))
        for start, end in raw_segments
        if (int(end) - int(start) + 1) >= min_bandwidth_bins
    ]
    effective_min_prominence_db = float(cfg.min_prominence_db)
    if not np.any(raw_mask):
        effective_min_prominence_db = float(
            min(
                effective_min_prominence_db,
                max(cfg.seed_prominence_db + 1.25, cfg.edge_prominence_db + 2.0),
            )
        )

    out_segments: List[Dict[str, Any]] = []
    for start, end in cleaned_segments:
        support_ratio = _segment_support_ratio(cleaned_support_mask, start, end)
        peak_prominence_db = _segment_peak_prominence(y_work, local_baseline, start, end)
        if support_ratio < float(cfg.min_support_ratio):
            continue
        if peak_prominence_db < effective_min_prominence_db:
            continue

        peak_idx = int(start + np.argmax(y[int(start) : int(end) + 1]))
        out_segments.append(
            {
                "peak_idx": int(peak_idx),
                "measure_L": int(start),
                "measure_R": int(end),
                "noise_floor_dbm": float(nf),
                "threshold_dbm": float(thr),
                "preset_name": cfg.preset_name,
                "support_ratio": float(support_ratio),
                "peak_prominence_db": float(peak_prominence_db),
                "residual_floor_dbm": float(residual_floor_db),
            }
        )

    rescue_limit = int(round(float(cfg.slow_rescue_max_existing_segments)))
    if cfg.slow_rescue_window_scale > 0.0 and len(out_segments) <= max(0, rescue_limit):
        rescue_segments = _collect_slow_rescue_segments(frame, y_work, cfg)
        existing_bounds = [(int(seg["measure_L"]), int(seg["measure_R"])) for seg in out_segments]
        for start, end in rescue_segments:
            if any(_segment_overlap_fraction((start, end), bounds) >= 0.60 for bounds in existing_bounds):
                continue
            peak_idx = int(start + np.argmax(y[int(start) : int(end) + 1]))
            out_segments.append(
                {
                    "peak_idx": int(peak_idx),
                    "measure_L": int(start),
                    "measure_R": int(end),
                    "noise_floor_dbm": float(nf),
                    "threshold_dbm": float(thr),
                    "preset_name": cfg.preset_name,
                    "support_ratio": None,
                    "peak_prominence_db": None,
                    "residual_floor_dbm": float(residual_floor_db),
                    "slow_rescue": True,
                }
            )
            existing_bounds.append((int(start), int(end)))

    out_segments.sort(key=lambda seg: (int(seg["measure_L"]), int(seg["measure_R"])))

    return {
        "detector_name": "simple",
        "preset_name": cfg.preset_name,
        "noise_floor_dbm": float(nf),
        "threshold_dbm": float(thr),
        "residual_floor_dbm": float(residual_floor_db),
        "segments": out_segments,
        "config": cfg,
    }
