from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

POSTPRO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = POSTPRO_DIR.parent
if str(POSTPRO_DIR) not in sys.path:
    sys.path.insert(0, str(POSTPRO_DIR))

from src.payload_parser import frame_from_payload
from src.processor import get_detector_run
from src.spectrum_frame import SpectrumFrame

FM_MIN_HZ = 87.5e6
FM_MAX_HZ = 108.0e6
UHF_TV_MIN_HZ = 470.0e6
UHF_TV_MAX_HZ = 698.0e6


def _resolve_default_dataset_dir() -> Path:
    return REPO_ROOT / "tes_signals"


def _overlap_hz(lo_a: float, hi_a: float, lo_b: float, hi_b: float) -> float:
    return max(0.0, min(hi_a, hi_b) - max(lo_a, lo_b))


def adapt_tes_signal_to_frame_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    psd = payload.get("psd", {}) if isinstance(payload, dict) else {}
    meta = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    frame_payload: Dict[str, Any] = {
        "Pxx": psd.get("pxx", []),
        "start_freq_hz": meta.get("frecuencia_min_hz"),
        "end_freq_hz": meta.get("frecuencia_max_hz"),
    }
    if meta.get("timestamp") is not None:
        frame_payload["timestamp"] = meta.get("timestamp")
    if payload.get("id") is not None:
        frame_payload["mac"] = payload.get("id")
    return frame_payload


def classify_capture_family(frame: SpectrumFrame) -> str:
    lo = float(min(frame.f_start_hz, frame.f_stop_hz))
    hi = float(max(frame.f_start_hz, frame.f_stop_hz))
    span = float(max(0.0, hi - lo))
    center = 0.5 * (lo + hi)

    fm_overlap = _overlap_hz(lo, hi, FM_MIN_HZ, FM_MAX_HZ)
    if fm_overlap >= min(1.0e6, 0.10 * max(span, 1.0)) or (FM_MIN_HZ <= center <= FM_MAX_HZ):
        return "fm_broadcast"

    tv_overlap = _overlap_hz(lo, hi, UHF_TV_MIN_HZ, UHF_TV_MAX_HZ)
    if tv_overlap >= 1.0e6 and span >= 4.0e6:
        return "uhf_tv"

    return f"window_{lo / 1e6:.3f}-{hi / 1e6:.3f}_MHz"


def choose_simple_preset(frame: SpectrumFrame, family: str, preset_mode: str = "auto") -> str:
    preset_mode = str(preset_mode or "auto").strip().lower()
    if preset_mode in {"general", "fm_dense", "high_res", "uhf_tv"}:
        return preset_mode

    if family == "fm_broadcast":
        return "fm_dense"
    if family == "uhf_tv":
        return "uhf_tv"

    span_hz = float(abs(frame.f_stop_hz - frame.f_start_hz))
    bin_hz = float(frame.get_bin_width())
    center_hz = 0.5 * (float(frame.f_start_hz) + float(frame.f_stop_hz))
    if bin_hz <= 2_000.0 and span_hz <= 2.5e6 and center_hz >= 900.0e6:
        return "high_res"
    if center_hz >= 1.0e9 and 5.0e6 <= span_hz <= 30.0e6:
        return "fm_dense"
    return "general"


def choose_simple_overrides(
    frame: SpectrumFrame,
    family: str,
    *,
    preset_mode: str = "auto",
    preset_name: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    preset_mode = str(preset_mode or "auto").strip().lower()
    if preset_mode != "auto":
        return None

    preset = str(preset_name or choose_simple_preset(frame, family, preset_mode=preset_mode)).strip().lower()
    lo = float(min(frame.f_start_hz, frame.f_stop_hz))
    hi = float(max(frame.f_start_hz, frame.f_stop_hz))
    span_hz = float(max(0.0, hi - lo))
    center_hz = 0.5 * (lo + hi)
    center_ghz = center_hz / 1.0e9
    span_mhz = span_hz / 1.0e6

    if family == "fm_broadcast" and preset == "fm_dense":
        return {
            "threshold_margin_db": 4.5,
            "min_prominence_db": 5.0,
            "min_bandwidth_hz": 30_000.0,
            "max_gap_hz": 30_000.0,
            "min_support_ratio": 0.45,
        }

    if preset == "fm_dense" and 2.10 <= center_ghz <= 2.16 and 18.0 <= span_mhz <= 22.0:
        return {
            "noise_percentile": 20.0,
            "threshold_margin_db": 1.5,
            "min_prominence_db": 1.5,
            "min_support_ratio": 0.25,
            "min_bandwidth_hz": 8_000.0,
            "max_gap_hz": 40_000.0,
            "smooth_sigma_bins": 0.0,
            "local_baseline_window_hz": 4_000_000.0,
            "grow_threshold_relax_db": 0.0,
            "seed_prominence_db": 1.5,
            "edge_prominence_db": 2.5,
        }

    if preset == "fm_dense" and 2.50 <= center_ghz <= 2.66 and 18.0 <= span_mhz <= 22.0:
        return {
            "threshold_margin_db": 4.0,
            "min_prominence_db": 3.5,
            "min_support_ratio": 0.40,
            "min_bandwidth_hz": 15_000.0,
            "max_gap_hz": 40_000.0,
        }

    return None


def _segment_interval(segment: Dict[str, Any]) -> Dict[str, float]:
    f_lo = segment.get("f_lo_hz", None)
    f_hi = segment.get("f_hi_hz", None)
    if f_lo is not None and f_hi is not None:
        try:
            lo = float(f_lo)
            hi = float(f_hi)
            if hi > lo:
                return {
                    "lo_hz": lo,
                    "hi_hz": hi,
                    "center_hz": 0.5 * (lo + hi),
                    "width_hz": hi - lo,
                }
        except Exception:
            pass

    fc_hz = float(segment.get("fc_hz", 0.0))
    bw_hz = float(segment.get("obw_hz", 0.0) or 0.0)
    if bw_hz <= 0.0:
        bw_hz = float(segment.get("bandwidth_hz", 0.0) or 0.0)
    lo = float(fc_hz - 0.5 * bw_hz)
    hi = float(fc_hz + 0.5 * bw_hz)
    return {
        "lo_hz": lo,
        "hi_hz": hi,
        "center_hz": float(fc_hz),
        "width_hz": float(max(0.0, bw_hz)),
    }


def _label_intervals(payload: Dict[str, Any]) -> List[Dict[str, float]]:
    etiquetas = payload.get("etiquetas", {}) if isinstance(payload, dict) else {}
    centers = etiquetas.get("frecuencias_centrales_hz", []) or []
    widths = etiquetas.get("anchos_banda_hz", []) or []
    out: List[Dict[str, float]] = []
    for fc_hz, bw_hz in zip(centers, widths):
        try:
            fc = float(fc_hz)
            bw = float(bw_hz)
        except Exception:
            continue
        lo = fc - 0.5 * bw
        hi = fc + 0.5 * bw
        out.append(
            {
                "lo_hz": float(lo),
                "hi_hz": float(hi),
                "center_hz": float(fc),
                "width_hz": float(max(0.0, bw)),
            }
        )
    return out


def _interval_iou(pred: Dict[str, float], gt: Dict[str, float]) -> float:
    lo = max(float(pred["lo_hz"]), float(gt["lo_hz"]))
    hi = min(float(pred["hi_hz"]), float(gt["hi_hz"]))
    inter = max(0.0, hi - lo)
    union = max(float(pred["hi_hz"]), float(gt["hi_hz"])) - min(float(pred["lo_hz"]), float(gt["lo_hz"]))
    if union <= 0.0:
        return 0.0
    return float(inter / union)


def match_intervals(
    predicted: Sequence[Dict[str, float]],
    labeled: Sequence[Dict[str, float]],
    *,
    min_iou: float,
) -> List[Tuple[int, int, float]]:
    candidates: List[Tuple[float, int, int]] = []
    for pi, pred in enumerate(predicted):
        for gi, gt in enumerate(labeled):
            iou = _interval_iou(pred, gt)
            if iou >= float(min_iou):
                candidates.append((float(iou), int(pi), int(gi)))

    candidates.sort(key=lambda item: item[0], reverse=True)
    used_pred = set()
    used_gt = set()
    matches: List[Tuple[int, int, float]] = []
    for iou, pi, gi in candidates:
        if pi in used_pred or gi in used_gt:
            continue
        used_pred.add(pi)
        used_gt.add(gi)
        matches.append((int(pi), int(gi), float(iou)))
    return matches


def compute_metrics(
    predicted: Sequence[Dict[str, float]],
    labeled: Sequence[Dict[str, float]],
    *,
    min_iou: float = 0.30,
    beta: float = 2.0,
) -> Dict[str, float]:
    matches = match_intervals(predicted, labeled, min_iou=min_iou)
    tp = int(len(matches))
    fp = int(len(predicted) - tp)
    fn = int(len(labeled) - tp)

    precision = float(tp / max(tp + fp, 1))
    recall = float(tp / max(tp + fn, 1))
    if precision + recall > 0.0:
        f1 = float(2.0 * precision * recall / (precision + recall))
    else:
        f1 = 0.0

    beta_sq = float(beta) ** 2
    denom = beta_sq * precision + recall
    f_beta = float(((1.0 + beta_sq) * precision * recall / denom) if denom > 0.0 else 0.0)

    sum_iou = 0.0
    sum_center_rel_error = 0.0
    sum_bw_rel_error = 0.0
    for pi, gi, iou in matches:
        pred = predicted[int(pi)]
        gt = labeled[int(gi)]
        gt_bw = max(float(gt["width_hz"]), 1.0)
        sum_iou += float(iou)
        sum_center_rel_error += abs(float(pred["center_hz"]) - float(gt["center_hz"])) / gt_bw
        sum_bw_rel_error += abs(float(pred["width_hz"]) - float(gt["width_hz"])) / gt_bw

    return {
        "pred_count": int(len(predicted)),
        "gt_count": int(len(labeled)),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "f_beta": f_beta,
        "match_count": tp,
        "sum_iou": float(sum_iou),
        "sum_center_rel_error": float(sum_center_rel_error),
        "sum_bw_rel_error": float(sum_bw_rel_error),
        "mean_iou": float(sum_iou / tp) if tp > 0 else 0.0,
        "mean_center_rel_error": float(sum_center_rel_error / tp) if tp > 0 else 0.0,
        "mean_bw_rel_error": float(sum_bw_rel_error / tp) if tp > 0 else 0.0,
    }


def _aggregate_metrics(rows: Sequence[Dict[str, Any]], *, beta: float) -> Dict[str, float]:
    tp = int(sum(int(r.get("tp", 0)) for r in rows))
    fp = int(sum(int(r.get("fp", 0)) for r in rows))
    fn = int(sum(int(r.get("fn", 0)) for r in rows))
    pred_count = int(sum(int(r.get("pred_count", 0)) for r in rows))
    gt_count = int(sum(int(r.get("gt_count", 0)) for r in rows))
    match_count = int(sum(int(r.get("match_count", 0)) for r in rows))
    sum_iou = float(sum(float(r.get("sum_iou", 0.0)) for r in rows))
    sum_center_rel_error = float(sum(float(r.get("sum_center_rel_error", 0.0)) for r in rows))
    sum_bw_rel_error = float(sum(float(r.get("sum_bw_rel_error", 0.0)) for r in rows))

    precision = float(tp / max(tp + fp, 1))
    recall = float(tp / max(tp + fn, 1))
    f1 = float(2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0.0 else 0.0
    beta_sq = float(beta) ** 2
    denom = beta_sq * precision + recall
    f_beta = float(((1.0 + beta_sq) * precision * recall / denom) if denom > 0.0 else 0.0)

    return {
        "pred_count": pred_count,
        "gt_count": gt_count,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "f_beta": f_beta,
        "match_count": match_count,
        "mean_iou": float(sum_iou / match_count) if match_count > 0 else 0.0,
        "mean_center_rel_error": float(sum_center_rel_error / match_count) if match_count > 0 else 0.0,
        "mean_bw_rel_error": float(sum_bw_rel_error / match_count) if match_count > 0 else 0.0,
    }


def run_benchmark(
    dataset_dir: Path,
    *,
    preset_mode: str = "auto",
    min_iou: float = 0.30,
    beta: float = 2.0,
    max_files: Optional[int] = None,
) -> Dict[str, Any]:
    files = sorted(Path(dataset_dir).glob("*.json"))
    if max_files is not None:
        files = files[: int(max_files)]

    per_file_rows: List[Dict[str, Any]] = []
    for json_path in files:
        with json_path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)

        frame_payload = adapt_tes_signal_to_frame_payload(payload)
        frame = frame_from_payload(frame_payload)
        family = classify_capture_family(frame)
        simple_preset = choose_simple_preset(frame, family, preset_mode=preset_mode)
        simple_overrides = choose_simple_overrides(
            frame,
            family,
            preset_mode=preset_mode,
            preset_name=simple_preset,
        )
        labeled = _label_intervals(payload)

        runs = [
            ("legacy", get_detector_run(frame, detector_name="legacy")),
            (
                "simple",
                get_detector_run(
                    frame,
                    detector_name="simple",
                    simple_preset_name=simple_preset,
                    simple_overrides=simple_overrides,
                ),
            ),
        ]

        for detector_name, run in runs:
            predicted = [_segment_interval(seg) for seg in run.get("segments", [])]
            metrics = compute_metrics(predicted, labeled, min_iou=min_iou, beta=beta)
            row: Dict[str, Any] = {
                "file": json_path.name,
                "family": family,
                "detector": detector_name,
                "simple_preset": simple_preset if detector_name == "simple" else "",
            }
            row.update(metrics)
            per_file_rows.append(row)

    global_rows: List[Dict[str, Any]] = []
    for detector_name in ("legacy", "simple"):
        rows = [r for r in per_file_rows if r["detector"] == detector_name]
        agg = _aggregate_metrics(rows, beta=beta)
        agg["detector"] = detector_name
        global_rows.append(agg)

    grouped_rows: List[Dict[str, Any]] = []
    families = sorted({str(r["family"]) for r in per_file_rows})
    for family in families:
        for detector_name in ("legacy", "simple"):
            rows = [r for r in per_file_rows if r["family"] == family and r["detector"] == detector_name]
            if not rows:
                continue
            agg = _aggregate_metrics(rows, beta=beta)
            agg["family"] = family
            agg["detector"] = detector_name
            grouped_rows.append(agg)

    return {
        "dataset_dir": str(Path(dataset_dir).resolve()),
        "num_files": len(files),
        "min_iou": float(min_iou),
        "beta": float(beta),
        "preset_mode": preset_mode,
        "per_file": per_file_rows,
        "global_summary": global_rows,
        "group_summary": grouped_rows,
    }


def _format_table(rows: Sequence[Dict[str, Any]], columns: Sequence[str]) -> str:
    if not rows:
        return "(sin datos)"
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    df = df.loc[:, list(columns)]
    return df.to_string(index=False)


def print_report(report: Dict[str, Any]) -> None:
    print(f"[BENCHMARK] dataset_dir = {report['dataset_dir']}")
    print(f"[BENCHMARK] num_files   = {report['num_files']}")
    print(f"[BENCHMARK] min_iou     = {report['min_iou']}")
    print(f"[BENCHMARK] beta        = {report['beta']}")
    print(f"[BENCHMARK] preset_mode = {report['preset_mode']}")

    global_cols = [
        "detector",
        "tp",
        "fp",
        "fn",
        "precision",
        "recall",
        "f1",
        "f_beta",
        "mean_iou",
        "mean_center_rel_error",
        "mean_bw_rel_error",
    ]
    group_cols = ["family"] + global_cols

    print("\n[GLOBAL]")
    print(_format_table(report.get("global_summary", []), global_cols))
    print("\n[POR BANDA/FAMILIA]")
    print(_format_table(report.get("group_summary", []), group_cols))


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark legacy vs detector simple sobre tes_signals.")
    parser.add_argument("--dataset-dir", type=str, default=str(_resolve_default_dataset_dir()))
    parser.add_argument("--preset", type=str, default="auto", help="auto|general|fm_dense|high_res|uhf_tv")
    parser.add_argument("--iou-threshold", type=float, default=0.30)
    parser.add_argument("--beta", type=float, default=2.0)
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--json-out", type=str, default=None, help="Ruta opcional para guardar el reporte en JSON.")
    args = parser.parse_args()

    report = run_benchmark(
        Path(args.dataset_dir),
        preset_mode=args.preset,
        min_iou=float(args.iou_threshold),
        beta=float(args.beta),
        max_files=args.max_files,
    )
    print_report(report)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\n[OK] Reporte JSON guardado en: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
