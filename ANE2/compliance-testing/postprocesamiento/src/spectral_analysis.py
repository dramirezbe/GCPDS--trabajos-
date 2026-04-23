# **Servicio único**: ruido + picos + potencia + ocupación (OBW 99%, −XdB)

import math
from typing import Dict, List, Optional

import numpy as np

from .spectrum_frame import SpectrumFrame
from .power_utils import trapz_compat

# ---------------------------
# TDT gating (Colombia)
# Rango UHF TDT (DVB-T2): 470–698 MHz (canales 14–51)
# ---------------------------
TDT_MIN_HZ: float = 470e6
TDT_MAX_HZ: float = 698e6


def is_tdt_frequency_hz(f_hz: float) -> bool:
    """True si la frecuencia (Hz) cae en la banda TDT (Colombia)."""
    try:
        f = float(f_hz)
    except Exception:
        return False
    if not math.isfinite(f):
        return False
    return (TDT_MIN_HZ <= f <= TDT_MAX_HZ)


def _gaussian_smooth1d(x: np.ndarray, sigma: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x.copy()
    sigma = float(max(0.5, sigma))
    try:
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(x, sigma=sigma)
    except Exception:
        k = max(1, int(round(3.0 * sigma)))
        ax = np.arange(-k, k + 1, dtype=float)
        ker = np.exp(-0.5 * (ax / sigma) ** 2)
        ker /= np.sum(ker)
        return np.convolve(x, ker, mode="same")


def _robust_nf_for_detection(x_dbm: np.ndarray, nf_hist_dbm: float) -> float:
    """Piso de ruido robusto para detección sin inflarlo por señales dominantes."""
    x = np.asarray(x_dbm, dtype=float)
    if x.size == 0:
        return float(nf_hist_dbm)
    finite = np.isfinite(x)
    x = x[finite]
    if x.size == 0:
        return float(nf_hist_dbm)
    try:
        q20 = float(np.percentile(x, 20.0))
        q10 = float(np.percentile(x, 10.0))
    except Exception:
        return float(nf_hist_dbm)
    if np.isfinite(nf_hist_dbm) and np.isfinite(q20) and (nf_hist_dbm > (q20 + 1.0)):
        return float(q10)
    return float(nf_hist_dbm)


def _lower_noise_stats(x_dbm: np.ndarray, q: float = 25.0) -> Dict[str, float]:
    x = np.asarray(x_dbm, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"nf_dbm": float("nan"), "sigma_db": float("nan")}
    qv = float(np.percentile(x, float(q)))
    lower = x[x <= (qv + 3.0)]
    if lower.size < max(16, int(0.05 * x.size)):
        lower = x[x <= qv]
    if lower.size == 0:
        lower = x
    med = float(np.median(lower))
    mad = float(np.median(np.abs(lower - med)) + 1e-12)
    sigma = float(1.4826 * mad)
    nf = float(med + 0.20 * sigma)
    return {"nf_dbm": nf, "sigma_db": sigma, "sample_size": int(lower.size)}


def _edge_noise_stats(x_dbm: np.ndarray, edge_frac: float = 0.10) -> Dict[str, float]:
    """Estadística robusta del ruido usando las orillas de la captura.

    Es útil cuando el centro de la ventana está ocupado por una meseta ancha
    (canal TDT o banda ancha genérica) y los percentiles globales inflan el NF.
    """
    x = np.asarray(x_dbm, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 8:
        return {"nf_dbm": float("nan"), "sigma_db": float("nan"), "edge_median_dbm": float("nan")}
    n = int(max(8, round(float(edge_frac) * x.size)))
    n = int(min(n, max(8, x.size // 2)))
    left = x[:n]
    right = x[-n:]
    edges = np.concatenate([left, right]) if right.size else left
    if edges.size == 0:
        return {"nf_dbm": float("nan"), "sigma_db": float("nan"), "edge_median_dbm": float("nan")}
    edge_med = float(min(np.median(left), np.median(right))) if right.size else float(np.median(left))
    q = float(np.percentile(edges, 35.0))
    lower = edges[edges <= q]
    if lower.size < max(8, int(0.2 * edges.size)):
        lower = edges
    med = float(np.median(lower))
    mad = float(np.median(np.abs(lower - med)) + 1e-12)
    sigma = float(1.4826 * mad)
    nf = float(med + 0.15 * sigma)
    return {
        "nf_dbm": nf,
        "sigma_db": sigma,
        "edge_median_dbm": edge_med,
        "sample_size": int(lower.size),
    }


def _otsu_threshold_dbm(x_dbm: np.ndarray, bins: int = 128) -> float:
    x = np.asarray(x_dbm, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    lo = float(np.percentile(x, 1.0))
    hi = float(np.percentile(x, 99.5))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return float("nan")
    counts, edges = np.histogram(np.clip(x, lo, hi), bins=int(max(32, bins)), range=(lo, hi))
    counts = counts.astype(float)
    if counts.sum() <= 0:
        return float("nan")
    centers = 0.5 * (edges[:-1] + edges[1:])
    prob = counts / counts.sum()
    omega = np.cumsum(prob)
    mu = np.cumsum(prob * centers)
    mu_t = mu[-1]
    denom = omega * (1.0 - omega)
    with np.errstate(divide="ignore", invalid="ignore"):
        sigma_b2 = np.where(denom > 0, (mu_t * omega - mu) ** 2 / denom, 0.0)
    idx = int(np.argmax(sigma_b2))
    return float(centers[idx])


def _histogram_valley_threshold_dbm(x_dbm: np.ndarray, bins: int = 192) -> float:
    x = np.asarray(x_dbm, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    lo = float(np.percentile(x, 1.0))
    hi = float(np.percentile(x, 99.5))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return float("nan")
    counts, edges = np.histogram(np.clip(x, lo, hi), bins=int(max(64, bins)), range=(lo, hi))
    centers = 0.5 * (edges[:-1] + edges[1:])
    counts_s = _gaussian_smooth1d(counts.astype(float), sigma=1.5)
    if counts_s.size < 5:
        return float("nan")
    mode_idx = int(np.argmax(counts_s))
    right = counts_s[mode_idx + 1:]
    if right.size < 3:
        return float("nan")
    valley_idx = None
    for i in range(1, len(right) - 1):
        if right[i] <= right[i - 1] and right[i] <= right[i + 1]:
            valley_idx = mode_idx + 1 + i
            break
    if valley_idx is None:
        search_hi = int(mode_idx + max(3, 0.35 * len(counts_s)))
        search_hi = min(search_hi, len(counts_s) - 1)
        valley_idx = int(mode_idx + np.argmin(counts_s[mode_idx:search_hi + 1]))
    return float(centers[int(valley_idx)])


def _segment_metrics_for_score(f_hz: np.ndarray, y_dbm: np.ndarray, segments: List[tuple[int, int]]) -> Dict[str, float]:
    if not segments:
        return {"n_segments": 0, "main_width_hz": 0.0, "occupancy": 0.0, "main_excess_db": 0.0, "energy_share": 0.0}
    N = len(y_dbm)
    p_lin = _dbm_to_mw(y_dbm)
    energies = []
    widths = []
    excesses = []
    total_occ = 0
    for s, e in segments:
        s = int(max(0, s)); e = int(min(N - 1, e))
        if e < s:
            continue
        widths.append(float(max(0.0, f_hz[e] - f_hz[s])))
        energies.append(float(np.sum(p_lin[s:e + 1])))
        total_occ += (e - s + 1)
        excesses.append(float(np.max(y_dbm[s:e + 1]) - np.median(y_dbm)))
    if not energies:
        return {"n_segments": 0, "main_width_hz": 0.0, "occupancy": 0.0, "main_excess_db": 0.0, "energy_share": 0.0}
    main_i = int(np.argmax(energies))
    return {
        "n_segments": int(len(energies)),
        "main_width_hz": float(widths[main_i]),
        "occupancy": float(total_occ / max(1, N)),
        "main_excess_db": float(excesses[main_i]),
        "energy_share": float(energies[main_i] / max(np.sum(energies), 1e-30)),
    }


def _score_threshold_broadband(
    f_hz: np.ndarray,
    y_dbm: np.ndarray,
    y_s_dbm: np.ndarray,
    thr_dbm: float,
    *,
    close_bins: int,
    max_gap_bins: int,
) -> Dict[str, float]:
    mask = np.asarray(y_s_dbm > float(thr_dbm), dtype=bool)
    try:
        from scipy.ndimage import binary_closing
        if np.any(mask):
            mask = np.asarray(binary_closing(mask, structure=np.ones(int(max(3, close_bins)), dtype=bool)), dtype=bool)
    except Exception:
        pass
    segs = _merge_close_segments(_segments_from_mask(mask), max_gap_bins=int(max_gap_bins))
    total_span_hz = float(max(1.0, f_hz[-1] - f_hz[0]))
    min_seg_hz = float(min(1.0e6, 0.06 * total_span_hz))
    segs = [(int(s), int(e)) for s, e in segs if float(f_hz[int(e)] - f_hz[int(s)]) >= min_seg_hz]
    segs = _merge_broadband_channel_segments(segs, f_hz)
    m = _segment_metrics_for_score(f_hz, y_s_dbm, segs)
    main_w = float(m["main_width_hz"])
    occ = float(m["occupancy"])
    nseg = int(m["n_segments"])
    eshare = float(m["energy_share"])
    excess = float(m["main_excess_db"])
    width_score = 1.0 - min(abs(main_w - 6.0e6) / 4.0e6, 1.0)
    occ_score = 1.0 - min(abs(occ - 0.35) / 0.35, 1.0)
    seg_score = 1.0 if nseg == 1 else (0.75 if nseg == 2 else max(0.0, 0.6 - 0.15 * (nseg - 2)))
    energy_score = min(max(eshare, 0.0), 1.0)
    excess_score = min(max(excess / 12.0, 0.0), 1.0)
    score = 0.33 * width_score + 0.22 * occ_score + 0.18 * seg_score + 0.17 * energy_score + 0.10 * excess_score
    return {"score": float(score), "segments": segs, "mask": mask}


def _score_threshold_narrowband(
    f_hz: np.ndarray,
    y_dbm: np.ndarray,
    y_s_dbm: np.ndarray,
    thr_dbm: float,
) -> Dict[str, float]:
    mask = np.asarray(y_s_dbm > float(thr_dbm), dtype=bool)
    segs = _merge_close_segments(_segments_from_mask(mask), max_gap_bins=max(2, len(y_dbm) // 300))
    span_hz = float(max(1.0, f_hz[-1] - f_hz[0]))
    max_seg_hz = 0.20 * span_hz
    segs = [(int(s), int(e)) for s, e in segs if float(f_hz[int(e)] - f_hz[int(s)]) <= max_seg_hz]
    m = _segment_metrics_for_score(f_hz, y_s_dbm, segs)
    occ = float(m["occupancy"])
    nseg = int(m["n_segments"])
    excess = float(m["main_excess_db"])
    eshare = float(m["energy_share"])
    occ_score = 1.0 - min(abs(occ - 0.06) / 0.20, 1.0)
    seg_score = 1.0 if 1 <= nseg <= 12 else max(0.0, 0.8 - 0.04 * abs(nseg - 12))
    excess_score = min(max(excess / 10.0, 0.0), 1.0)
    energy_score = min(max(eshare, 0.0), 1.0)
    score = 0.40 * occ_score + 0.25 * seg_score + 0.20 * excess_score + 0.15 * energy_score
    return {"score": float(score), "segments": segs, "mask": mask}


def _choose_intelligent_threshold(
    frame: SpectrumFrame,
    *,
    broadband: bool,
    sigma_smooth: float,
) -> Dict[str, float]:
    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    f = _frame_freq_axis(frame)
    y_s = _gaussian_smooth1d(y, sigma=sigma_smooth)
    nf_hist = float(estimate_noise_floor(frame))
    nf_rob = float(_robust_nf_for_detection(y_s, nf_hist))
    noise_stats = _lower_noise_stats(y_s, q=25.0 if not broadband else 30.0)
    nf_low = float(noise_stats.get("nf_dbm", nf_rob))
    sigma_low = float(noise_stats.get("sigma_db", 1.0))

    # En ventanas anchas UHF, la estadística global puede quedar inflada por una
    # meseta central. Por eso también proponemos candidatos basados en el ruido de
    # las orillas, que suelen representar mejor el piso de ruido real.
    edge_stats = _edge_noise_stats(y_s, edge_frac=0.10 if broadband else 0.08)
    edge_nf = float(edge_stats.get("nf_dbm", float("nan")))
    edge_sigma = float(edge_stats.get("sigma_db", float("nan")))
    edge_med = float(edge_stats.get("edge_median_dbm", float("nan")))

    cand = []
    cand.append(("robust_sigma", float(nf_low + max(1.25, 3.0 * sigma_low)), float(nf_low)))
    otsu_thr = _otsu_threshold_dbm(y_s, bins=128)
    if np.isfinite(otsu_thr):
        cand.append(("otsu", float(otsu_thr), float(nf_low)))
    valley_thr = _histogram_valley_threshold_dbm(y_s, bins=192)
    if np.isfinite(valley_thr):
        cand.append(("hist_valley", float(valley_thr), float(nf_low)))
    q70 = float(np.percentile(y_s, 70.0 if broadband else 80.0))
    cand.append(("percentile", float(0.55 * nf_low + 0.45 * q70), float(nf_low)))

    use_edge_candidates = bool(
        broadband
        and np.isfinite(edge_nf)
        and np.isfinite(edge_med)
        and (
            (edge_nf <= (nf_low - 2.0))
            or (edge_med <= (np.median(y_s) - 3.0))
        )
    )
    if use_edge_candidates:
        if not np.isfinite(edge_sigma) or edge_sigma <= 0.0:
            edge_sigma = max(0.8, sigma_low)
        # Candidatos tipo "ruido de borde + offset" para recuperar emisiones
        # anchas que ocupan gran parte del frame sin fragmentarlas en picos.
        cand.append(("edge_sigma", float(edge_nf + max(1.8, 3.2 * edge_sigma)), float(edge_nf)))
        for rel in (2.0, 3.0, 4.0, 5.0, 6.0, 7.0):
            cand.append((f"edge_{int(rel)}db", float(edge_nf + rel), float(edge_nf)))

    hi = float(np.percentile(y_s, 98.0) - 0.1)
    uniq = []
    seen = set()
    for name, thr, nf_cand in cand:
        if not np.isfinite(nf_cand):
            nf_cand = nf_low
        sigma_cand = edge_sigma if name.startswith("edge_") else sigma_low
        lo_cand = float(nf_cand + max(0.6, 0.8 * max(sigma_cand, 0.5)))
        if np.isfinite(hi) and hi > lo_cand:
            thr = float(np.clip(thr, lo_cand, hi))
        else:
            thr = float(max(thr, lo_cand))
        key = (name.split("_")[0], round(thr, 4))
        if key in seen:
            continue
        seen.add(key)
        uniq.append((name, thr, float(nf_cand), float(sigma_cand)))

    best = None
    for name, thr, nf_cand, sigma_cand in uniq:
        if broadband:
            scored = _score_threshold_broadband(
                f, y, y_s, thr,
                close_bins=(15 if len(y) >= 1024 else max(6, len(y) // 120)),
                max_gap_bins=(12 if len(y) >= 1024 else max(4, len(y) // 180)),
            )
        else:
            scored = _score_threshold_narrowband(f, y, y_s, thr)
        # Pequeña bonificación a los candidatos de borde cuando existe una gran
        # diferencia entre bordes y centro: eso ayuda a capturar una sola emisión
        # ancha en mesetas UHF en vez de decenas de picos falsos.
        if broadband and name.startswith("edge_") and use_edge_candidates:
            center_med = float(np.median(y_s[len(y_s)//4: 3*len(y_s)//4])) if len(y_s) >= 8 else float(np.median(y_s))
            plateau_contrast = max(0.0, center_med - edge_med)
            scored["score"] = float(scored["score"] + min(0.06, 0.01 * plateau_contrast))
        scored.update({
            "name": name,
            "threshold_dbm": float(thr),
            "noise_floor_dbm": float(nf_cand),
            "sigma_db": float(sigma_cand),
        })
        if best is None or float(scored["score"]) > float(best["score"]):
            best = scored
    if best is None:
        best = {
            "name": "fallback",
            "threshold_dbm": float(nf_low + max(0.6, 0.8 * max(sigma_low, 0.5))),
            "noise_floor_dbm": float(nf_low),
            "sigma_db": float(sigma_low),
            "score": 0.0,
            "segments": [],
        }
    return best







def _frame_freq_axis(frame: SpectrumFrame) -> np.ndarray:
    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    if getattr(frame, "freq_hz", None) is not None:
        return np.asarray(frame.freq_hz, dtype=float)
    return np.linspace(float(frame.f_start_hz), float(frame.f_stop_hz), y.size)


def _frame_span_hz(frame: SpectrumFrame) -> float:
    try:
        return float(abs(float(frame.f_stop_hz) - float(frame.f_start_hz)))
    except Exception:
        f = _frame_freq_axis(frame)
        if f.size < 2:
            return 0.0
        return float(abs(f[-1] - f[0]))


def is_colombia_broadband_frame(frame: SpectrumFrame) -> bool:
    """True si la ventana parece una captura TDT/banda ancha de Colombia."""
    try:
        f0 = float(frame.f_start_hz)
        f1 = float(frame.f_stop_hz)
    except Exception:
        f = _frame_freq_axis(frame)
        if f.size < 2:
            return False
        f0, f1 = float(f[0]), float(f[-1])
    lo = min(f0, f1)
    hi = max(f0, f1)
    overlap = max(0.0, min(hi, TDT_MAX_HZ) - max(lo, TDT_MIN_HZ))
    if overlap < 1e6:
        return False
    return _frame_span_hz(frame) >= 4.0e6


def _dbm_to_mw(x_dbm: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        y = 10.0 ** (np.asarray(x_dbm, dtype=float) / 10.0)
    return np.where(np.isfinite(y), np.maximum(y, 0.0), 0.0)


def _robust_noise_floor_broadband_dbm(x_dbm: np.ndarray) -> float:
    x = np.asarray(x_dbm, dtype=float)
    if x.size == 0:
        return float("nan")
    q20 = float(np.percentile(x, 20.0))
    lower = x[x <= (q20 + 3.0)]
    if lower.size == 0:
        lower = x
    med = float(np.median(lower))
    mad = float(np.median(np.abs(lower - med)) + 1e-12)
    return float(med + 0.3 * 1.4826 * mad)


def _smooth_broadband_trace(x_dbm: np.ndarray, sigma: float = 2.2) -> np.ndarray:
    x = np.asarray(x_dbm, dtype=float)
    if x.size == 0:
        return x.copy()
    try:
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(x, sigma=float(max(0.5, sigma)))
    except Exception:
        k = max(1, int(round(3.0 * float(max(0.5, sigma)))))
        if k <= 1:
            return x.copy()
        ax = np.arange(-k, k + 1, dtype=float)
        ker = np.exp(-0.5 * (ax / float(max(0.5, sigma))) ** 2)
        ker /= np.sum(ker)
        return np.convolve(x, ker, mode="same")


def _segments_from_mask(mask: np.ndarray) -> List[tuple[int, int]]:
    segs: List[tuple[int, int]] = []
    in_seg = False
    start = 0
    for i, v in enumerate(np.asarray(mask, dtype=bool)):
        if v and not in_seg:
            start = int(i)
            in_seg = True
        elif (not v) and in_seg:
            segs.append((start, int(i - 1)))
            in_seg = False
    if in_seg:
        segs.append((start, int(len(mask) - 1)))
    return segs


def _merge_close_segments(segments: List[tuple[int, int]], max_gap_bins: int = 12) -> List[tuple[int, int]]:
    if not segments:
        return []
    merged: List[tuple[int, int]] = [segments[0]]
    for s, e in segments[1:]:
        ps, pe = merged[-1]
        if int(s) - int(pe) - 1 <= int(max_gap_bins):
            merged[-1] = (int(ps), int(e))
        else:
            merged.append((int(s), int(e)))
    return merged


def _choose_main_segment(segments: List[tuple[int, int]], y_dbm: np.ndarray) -> Optional[tuple[int, int]]:
    if not segments:
        return None
    best = None
    best_en = -np.inf
    p_lin = _dbm_to_mw(y_dbm)
    for s, e in segments:
        en = float(np.sum(p_lin[int(s): int(e) + 1]))
        if en > best_en:
            best_en = en
            best = (int(s), int(e))
    return best


def _obw_99_limits_in_segment(f_hz: np.ndarray, y_dbm: np.ndarray, start: int, end: int) -> Optional[Dict[str, float]]:
    s = int(max(0, start))
    e = int(min(len(f_hz) - 1, end))
    if e <= s:
        return None
    f = np.asarray(f_hz[s:e + 1], dtype=float)
    p_lin = _dbm_to_mw(np.asarray(y_dbm[s:e + 1], dtype=float))
    if f.size < 2 or np.sum(p_lin) <= 0.0:
        return None
    c = np.cumsum(p_lin)
    total = float(c[-1])
    lo = 0.005 * total
    hi = 0.995 * total
    i0 = int(np.searchsorted(c, lo, side="left"))
    i1 = int(np.searchsorted(c, hi, side="left"))
    i0 = int(np.clip(i0, 0, len(f) - 1))
    i1 = int(np.clip(i1, 0, len(f) - 1))
    if i1 <= i0:
        i0, i1 = 0, len(f) - 1
    return {
        "f_lo_hz": float(f[i0]),
        "f_hi_hz": float(f[i1]),
        "obw_99_hz": float(max(0.0, f[i1] - f[i0])),
        "fc_obw_mid_hz": float(0.5 * (f[i0] + f[i1])),
    }


def _nearest_tdt_channel_center_hz(fc_hz: float) -> float:
    centers = np.arange(473.0e6, 695.0e6 + 1.0, 6.0e6, dtype=float)
    fc = float(fc_hz)
    if centers.size == 0 or (not np.isfinite(fc)):
        return float(fc_hz)
    return float(centers[int(np.argmin(np.abs(centers - fc)))])


def _window_min_idx(f_hz: np.ndarray, y_s_dbm: np.ndarray, target_hz: float, half_window_hz: float = 1.0e6) -> int:
    f = np.asarray(f_hz, dtype=float)
    y = np.asarray(y_s_dbm, dtype=float)
    idx = np.where((f >= (float(target_hz) - float(half_window_hz))) & (f <= (float(target_hz) + float(half_window_hz))))[0]
    if idx.size == 0:
        return int(np.argmin(np.abs(f - float(target_hz))))
    return int(idx[int(np.argmin(y[idx]))])


def _refine_tdt_segment_to_channel(
    f_hz: np.ndarray,
    y_dbm: np.ndarray,
    y_s_dbm: np.ndarray,
    seed_start: int,
    seed_end: int,
    provisional_fc_hz: float,
) -> Optional[Dict[str, float]]:
    f = np.asarray(f_hz, dtype=float)
    y = np.asarray(y_dbm, dtype=float)
    y_s = np.asarray(y_s_dbm, dtype=float)
    if f.size < 8:
        return None

    snapped_fc_hz = _nearest_tdt_channel_center_hz(float(provisional_fc_hz))
    if abs(float(provisional_fc_hz) - snapped_fc_hz) > 2.2e6:
        snapped_fc_hz = float(provisional_fc_hz)

    # 1) Intento preferido: raster fijo de 6 MHz alrededor del centro TDT nominal.
    fixed_L = int(np.argmin(np.abs(f - (snapped_fc_hz - 3.0e6))))
    fixed_R = int(np.argmin(np.abs(f - (snapped_fc_hz + 3.0e6))))
    if fixed_R > fixed_L and _is_plausible_tdt_channel(
        f, y, y_s, fixed_L, fixed_R,
        noise_floor_dbm=float(_robust_noise_floor_broadband_dbm(y_s)),
        snapped_fc_hz=float(snapped_fc_hz),
        strict=True,
    ):
        left_idx, right_idx = int(fixed_L), int(fixed_R)
        channel_bw_hz = float(f[right_idx] - f[left_idx])
    else:
        # 2) Respaldo: buscar valles laterales cerca de ±3 MHz.
        left_idx = _window_min_idx(f, y_s, snapped_fc_hz - 3.0e6, half_window_hz=1.0e6)
        right_idx = _window_min_idx(f, y_s, snapped_fc_hz + 3.0e6, half_window_hz=1.0e6)
        if right_idx <= left_idx:
            return None
        channel_bw_hz = float(f[right_idx] - f[left_idx])
        # Si la ventana por valles quedó demasiado corta pero el raster fijo sí es plausible,
        # forzar el raster nominal de 6 MHz evita submediciones como la de 485 MHz.
        if ((not np.isfinite(channel_bw_hz)) or channel_bw_hz < 5.4e6) and fixed_R > fixed_L and _is_plausible_tdt_channel(
            f, y, y_s, fixed_L, fixed_R,
            noise_floor_dbm=float(_robust_noise_floor_broadband_dbm(y_s)),
            snapped_fc_hz=float(snapped_fc_hz),
            strict=True,
        ):
            left_idx, right_idx = int(fixed_L), int(fixed_R)
            channel_bw_hz = float(f[right_idx] - f[left_idx])
        elif (not np.isfinite(channel_bw_hz)) or channel_bw_hz < 4.5e6 or channel_bw_hz > 6.8e6:
            return None

    obw = _obw_99_limits_in_segment(f, y, left_idx, right_idx)
    if obw is not None:
        # Para TDT plausible, la FC reportada debe anclarse al centro raster. El OBW
        # sigue sirviendo para BW medido, pero la frecuencia central no debe desplazarse
        # artificialmente por inclinaciones internas del canal.
        fc_hz = float(snapped_fc_hz)
        obw_hz = float(obw["obw_99_hz"])
        f_lo_hz = float(obw["f_lo_hz"])
        f_hi_hz = float(obw["f_hi_hz"])
        refined_L = int(np.argmin(np.abs(f - f_lo_hz)))
        refined_R = int(np.argmin(np.abs(f - f_hi_hz)))
    else:
        fc_hz = float(snapped_fc_hz)
        obw_hz = float(channel_bw_hz)
        f_lo_hz = float(f[left_idx])
        f_hi_hz = float(f[right_idx])
        refined_L = int(left_idx)
        refined_R = int(right_idx)

    peak_slice = y[left_idx:right_idx + 1]
    peak_idx = int(left_idx + np.argmax(peak_slice)) if peak_slice.size > 0 else int(np.clip(int(round(0.5 * (left_idx + right_idx))), 0, len(f) - 1))

    return {
        "candidate_L": int(seed_start),
        "candidate_R": int(seed_end),
        "refined_L": int(refined_L),
        "refined_R": int(refined_R),
        "measure_L": int(left_idx),
        "measure_R": int(right_idx),
        "refined_peak_idx": int(peak_idx),
        "fc_hz": float(fc_hz),
        "obw_hz": float(obw_hz),
        "bandwidth_hz": float(channel_bw_hz),
        "f_lo_hz": float(f_lo_hz),
        "f_hi_hz": float(f_hi_hz),
        "snapped_fc_hz": float(snapped_fc_hz),
    }



def _is_plausible_tdt_channel(
    f_hz: np.ndarray,
    y_dbm: np.ndarray,
    y_s_dbm: np.ndarray,
    left_idx: int,
    right_idx: int,
    *,
    noise_floor_dbm: float,
    snapped_fc_hz: Optional[float] = None,
    strict: bool = False,
) -> bool:
    """Valida si un segmento se parece de verdad a un canal TDT de 6 MHz."""
    f = np.asarray(f_hz, dtype=float)
    y = np.asarray(y_dbm, dtype=float)
    y_s = np.asarray(y_s_dbm, dtype=float)
    L = int(max(0, min(len(f) - 1, int(left_idx))))
    R = int(max(0, min(len(f) - 1, int(right_idx))))
    if R <= L:
        return False

    bw_hz = float(f[R] - f[L])
    if not np.isfinite(bw_hz):
        return False

    obw = _obw_99_limits_in_segment(f, y, L, R)
    obw_hz = float(obw["obw_99_hz"]) if obw is not None else float(bw_hz)
    fc_hz = float(obw["fc_obw_mid_hz"]) if obw is not None else float(0.5 * (f[L] + f[R]))

    snap = float(snapped_fc_hz) if snapped_fc_hz is not None and np.isfinite(snapped_fc_hz) else _nearest_tdt_channel_center_hz(fc_hz)
    raster_err_hz = abs(fc_hz - snap)

    y_seg = y_s[L:R + 1]
    if y_seg.size < 8:
        return False

    occ_ratio = float(np.mean(y_seg > (float(noise_floor_dbm) + 1.5)))
    p_lin = _dbm_to_mw(y_seg)
    if float(np.sum(p_lin)) <= 0.0:
        return False
    k = max(3, int(round(0.01 * len(p_lin))))
    top_ratio = float(np.sort(p_lin)[-k:].sum() / max(np.sum(p_lin), 1e-30))
    spread_db = float(np.percentile(y_seg, 95.0) - np.percentile(y_seg, 5.0))

    min_obw_hz = 3.8e6 if not strict else 4.1e6
    min_bw_hz = 4.0e6 if not strict else 4.4e6
    max_bw_hz = 6.8e6
    max_raster_err_hz = 1.6e6 if not strict else 1.3e6

    width_ok = ((obw_hz >= min_obw_hz) or (bw_hz >= min_bw_hz)) and (bw_hz <= max_bw_hz)
    shape_ok = (occ_ratio >= 0.42) and (top_ratio <= 0.35) and (spread_db <= 18.0)
    align_ok = (raster_err_hz <= max_raster_err_hz)
    return bool(width_ok and shape_ok and align_ok)




def _is_plausible_partial_tdt_channel(
    f_hz: np.ndarray,
    y_dbm: np.ndarray,
    y_s_dbm: np.ndarray,
    left_idx: int,
    right_idx: int,
    *,
    noise_floor_dbm: float,
    snapped_fc_hz: float,
) -> bool:
    """Valida un canal TDT recortado por el borde de la ventana.

    Se usa cuando solo vemos una fracción del canal de 6 MHz. En ese caso no
    podemos exigir OBW o ocupación tan altos como en un canal completo.
    """
    f = np.asarray(f_hz, dtype=float)
    y = np.asarray(y_dbm, dtype=float)
    y_s = np.asarray(y_s_dbm, dtype=float)
    L = int(max(0, min(len(f) - 1, int(left_idx))))
    R = int(max(0, min(len(f) - 1, int(right_idx))))
    if R <= L:
        return False
    ov_hz = float(f[R] - f[L])
    if (not np.isfinite(ov_hz)) or ov_hz < 1.2e6 or ov_hz > 3.3e6:
        return False
    seg = np.asarray(y[L:R + 1], dtype=float)
    seg_s = np.asarray(y_s[L:R + 1], dtype=float)
    if seg.size < 24:
        return False
    q75 = float(np.percentile(seg, 75.0))
    q90 = float(np.percentile(seg, 90.0))
    q95 = float(np.percentile(seg, 95.0))
    q05 = float(np.percentile(seg, 5.0))
    spread_db = float(q95 - q05)
    excess75 = float(q75 - float(noise_floor_dbm))
    excess90 = float(q90 - float(noise_floor_dbm))
    # Proporción de bins que superan el NF; en parciales puede ser moderada.
    occ = float(np.mean(seg_s > (float(noise_floor_dbm) + 0.8)))
    # Alineación raster: el borde de la ventana debe cortar el canal cerca de
    # uno de sus bordes nominales.
    ch_lo = float(snapped_fc_hz - 3.0e6)
    ch_hi = float(snapped_fc_hz + 3.0e6)
    edge_align = min(abs(float(f[L]) - ch_lo), abs(float(f[R]) - ch_hi), abs(float(f[L]) - ch_hi), abs(float(f[R]) - ch_lo))
    align_ok = bool(edge_align <= 0.35e6)
    shape_ok = bool(excess75 >= 1.0 and excess90 >= 2.5 and 4.0 <= spread_db <= 18.0 and occ >= 0.22)
    return bool(align_ok and shape_ok)


def _find_edge_partial_tdt_segments(
    f_hz: np.ndarray,
    y_dbm: np.ndarray,
    y_s_dbm: np.ndarray,
    *,
    noise_floor_dbm: float,
    existing_segments: List[Dict[str, float]],
) -> List[Dict[str, float]]:
    """Busca canales TDT recortados por el borde de la ventana."""
    f = np.asarray(f_hz, dtype=float)
    y = np.asarray(y_dbm, dtype=float)
    y_s = np.asarray(y_s_dbm, dtype=float)
    if f.size < 32:
        return []
    out: List[Dict[str, float]] = []
    centers = np.arange(473.0e6, 695.0e6 + 1.0, 6.0e6, dtype=float)
    frame_lo = float(f[0]); frame_hi = float(f[-1])
    for c in centers:
        ch_lo = float(c - 3.0e6)
        ch_hi = float(c + 3.0e6)
        ov_lo = max(frame_lo, ch_lo)
        ov_hi = min(frame_hi, ch_hi)
        ov_hz = float(ov_hi - ov_lo)
        if ov_hz < 1.2e6:
            continue
        # Solo parciales: el canal nominal debe quedar cortado por un borde.
        if not (ch_lo < frame_lo or ch_hi > frame_hi):
            continue
        L = int(np.argmin(np.abs(f - ov_lo)))
        R = int(np.argmin(np.abs(f - ov_hi)))
        if R <= L:
            continue
        # Si ya tenemos un segmento medido que cubre gran parte del solape, no duplicar.
        dup = False
        for seg in existing_segments:
            s = int(seg.get("measure_L", seg.get("refined_L", seg.get("candidate_L", 0))))
            e = int(seg.get("measure_R", seg.get("refined_R", seg.get("candidate_R", 0))))
            inter = max(0, min(R, e) - max(L, s) + 1)
            union = max(1, max(R, e) - min(L, s) + 1)
            if (inter / union) >= 0.45:
                dup = True
                break
        if dup:
            continue
        if not _is_plausible_partial_tdt_channel(f, y, y_s, L, R, noise_floor_dbm=float(noise_floor_dbm), snapped_fc_hz=float(c)):
            continue
        obw = _obw_99_limits_in_segment(f, y, L, R)
        peak_idx = int(L + np.argmax(y[L:R + 1]))
        visible_mid_hz = float(0.5 * (f[L] + f[R]))
        out.append({
            "candidate_L": int(L),
            "candidate_R": int(R),
            "refined_L": int(L),
            "refined_R": int(R),
            "measure_L": int(L),
            "measure_R": int(R),
            "refined_peak_idx": int(peak_idx),
            # Para canales parciales reportamos la FC del tramo visible. Esto hace
            # coherente el par (fc,bw) cuando el usuario dibuja la caja con fc±bw/2.
            # El centro raster nominal se conserva por separado para matching.
            "fc_hz": float(visible_mid_hz),
            "match_fc_hz": float(c),
            "obw_hz": float(obw["obw_99_hz"]) if obw is not None else float(ov_hz),
            "bandwidth_hz": float(ov_hz),
            "f_lo_hz": float(f[L]),
            "f_hi_hz": float(f[R]),
            "snapped_fc_hz": float(c),
            "is_tdt_candidate": True,
            "is_partial_tdt": True,
            "suppress_narrow": True,
        })
    return out


def _band_is_plausible_tdt(
    frame: SpectrumFrame,
    f_start_hz: float,
    f_stop_hz: float,
) -> bool:
    """Valida si la banda medida corresponde a un canal TDT plausible."""
    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    if y.size < 8:
        return False
    f = _frame_freq_axis(frame)
    y_s = _smooth_broadband_trace(y, sigma=2.0)
    nf = float(_robust_noise_floor_broadband_dbm(y_s))

    f0 = float(min(f_start_hz, f_stop_hz))
    f1 = float(max(f_start_hz, f_stop_hz))
    idx = np.where((f >= f0) & (f <= f1))[0]
    if idx.size < 8:
        return False

    fc_hz = 0.5 * (f0 + f1)
    snap = _nearest_tdt_channel_center_hz(fc_hz)
    return _is_plausible_tdt_channel(
        f, y, y_s, int(idx[0]), int(idx[-1]),
        noise_floor_dbm=nf,
        snapped_fc_hz=snap,
        strict=False,
    )


def _merge_broadband_channel_segments(
    segments: List[tuple[int, int]],
    f_hz: np.ndarray,
    *,
    max_gap_hz: float = 1.2e6,
    max_combined_hz: float = 6.6e6,
) -> List[tuple[int, int]]:
    if not segments:
        return []
    merged: List[tuple[int, int]] = []
    cur_s, cur_e = segments[0]
    for s, e in segments[1:]:
        gap_hz = float(f_hz[int(s)] - f_hz[int(cur_e)])
        comb_hz = float(f_hz[int(e)] - f_hz[int(cur_s)])
        if gap_hz <= float(max_gap_hz) and comb_hz <= float(max_combined_hz):
            cur_e = int(e)
        else:
            merged.append((int(cur_s), int(cur_e)))
            cur_s, cur_e = int(s), int(e)
    merged.append((int(cur_s), int(cur_e)))
    return merged




def _generic_broadband_segment_ok(
    f_hz: np.ndarray,
    y_dbm: np.ndarray,
    y_s_dbm: np.ndarray,
    start: int,
    end: int,
    *,
    noise_floor_dbm: float,
) -> bool:
    """Acepta solo segmentos realmente anchos/coherentes como fallback broadband.

    Evita que mesetas UHF de ~0.5–1.3 MHz o zonas elevadas con picos internos
    se reporten como una sola emisión ancha; en esos casos es mejor dejar que
    la ruta narrowband capture los picos individuales.
    """
    f = np.asarray(f_hz, dtype=float)
    y = np.asarray(y_dbm, dtype=float)
    y_s = np.asarray(y_s_dbm, dtype=float)
    L = int(max(0, min(len(f) - 1, int(start))))
    R = int(max(0, min(len(f) - 1, int(end))))
    if R <= L:
        return False
    bw_hz = float(f[R] - f[L])
    if (not np.isfinite(bw_hz)) or bw_hz < 1.6e6:
        return False

    y_seg = y_s[L:R + 1]
    if y_seg.size < 8:
        return False
    obw = _obw_99_limits_in_segment(f, y, L, R)
    obw_hz = float(obw["obw_99_hz"]) if obw is not None else bw_hz
    if obw_hz < 1.4e6:
        return False

    occ_ratio = float(np.mean(y_seg > (float(noise_floor_dbm) + 1.25)))
    med_excess = float(np.median(y_seg) - float(noise_floor_dbm))
    p_lin = _dbm_to_mw(y_seg)
    if float(np.sum(p_lin)) <= 0.0:
        return False
    k = max(4, int(round(0.01 * len(p_lin))))
    top_ratio = float(np.sort(p_lin)[-k:].sum() / max(np.sum(p_lin), 1e-30))
    spread_db = float(np.percentile(y_seg, 95.0) - np.percentile(y_seg, 5.0))

    coherent_shape = (occ_ratio >= 0.22) and (med_excess >= 1.8) and (spread_db <= 24.0)
    not_too_spiky = (top_ratio <= 0.55)
    return bool(coherent_shape and not_too_spiky)

def _find_nominal_tdt_window_segments(
    f_hz: np.ndarray,
    y_dbm: np.ndarray,
    y_s_dbm: np.ndarray,
    *,
    noise_floor_dbm: float,
    threshold_dbm: float,
    threshold_selector: str,
) -> List[Dict[str, float]]:
    """Busca canales TDT directamente sobre el raster nominal de 6 MHz.

    Esto evita que, en ventanas donde el canal está recortado por el borde o por
    la propia captura, el refinamiento por valles deje el inicio/fin demasiado
    metido hacia adentro. Si una ventana nominal es plausible, se reporta con
    los bordes nominales visibles en la captura.
    """
    f = np.asarray(f_hz, dtype=float)
    y = np.asarray(y_dbm, dtype=float)
    y_s = np.asarray(y_s_dbm, dtype=float)
    if f.size < 32:
        return []
    frame_lo = float(f[0]); frame_hi = float(f[-1])
    centers = np.arange(473.0e6, 695.0e6 + 1.0, 6.0e6, dtype=float)
    out: List[Dict[str, float]] = []
    for c in centers:
        ch_lo = float(c - 3.0e6)
        ch_hi = float(c + 3.0e6)
        ov_lo = max(frame_lo, ch_lo)
        ov_hi = min(frame_hi, ch_hi)
        ov_hz = float(ov_hi - ov_lo)
        if ov_hz < 1.2e6:
            continue
        L = int(np.argmin(np.abs(f - ov_lo)))
        R = int(np.argmin(np.abs(f - ov_hi)))
        if R <= L:
            continue
        seg = np.asarray(y[L:R + 1], dtype=float)
        seg_s = np.asarray(y_s[L:R + 1], dtype=float)
        if seg.size < 24:
            continue
        q50 = float(np.percentile(seg_s, 50.0))
        q75 = float(np.percentile(seg, 75.0))
        q90 = float(np.percentile(seg, 90.0))
        q95 = float(np.percentile(seg, 95.0))
        q05 = float(np.percentile(seg, 5.0))
        spread_db = float(q95 - q05)
        occ = float(np.mean(seg_s > (float(noise_floor_dbm) + (1.2 if ov_hz >= 4.5e6 else 0.8))))
        med_excess = float(q50 - float(noise_floor_dbm))
        excess75 = float(q75 - float(noise_floor_dbm))
        excess90 = float(q90 - float(noise_floor_dbm))
        p_lin = _dbm_to_mw(seg_s)
        if float(np.sum(p_lin)) <= 0.0:
            continue
        k = max(3, int(round(0.01 * len(p_lin))))
        top_ratio = float(np.sort(p_lin)[-k:].sum() / max(np.sum(p_lin), 1e-30))

        full_visible = bool(ov_hz >= 5.2e6)
        frame_cut = bool(ch_lo < frame_lo or ch_hi > frame_hi)
        plausible = False
        if full_visible:
            plausible = _is_plausible_tdt_channel(
                f, y, y_s, L, R,
                noise_floor_dbm=float(noise_floor_dbm),
                snapped_fc_hz=float(c),
                strict=True,
            )
            if (not plausible) and occ >= 0.46 and med_excess >= 2.4 and top_ratio <= 0.28 and spread_db <= 18.5:
                plausible = True
        else:
            if frame_cut:
                plausible = _is_plausible_partial_tdt_channel(
                    f, y, y_s, L, R,
                    noise_floor_dbm=float(noise_floor_dbm),
                    snapped_fc_hz=float(c),
                )
                if (not plausible) and ov_hz >= 3.6e6 and occ >= 0.40 and med_excess >= 2.0 and excess90 >= 4.0 and top_ratio <= 0.28 and spread_db <= 20.5:
                    plausible = True
                if (not plausible) and 2.6e6 <= ov_hz <= 3.4e6 and occ >= 0.28 and excess75 >= 1.3 and excess90 >= 3.0 and top_ratio <= 0.22 and spread_db <= 18.0:
                    plausible = True
        if not plausible:
            continue
        obw = _obw_99_limits_in_segment(f, y, L, R)
        peak_idx = int(L + np.argmax(y[L:R + 1]))
        if full_visible:
            obw_hz = float(obw["obw_99_hz"]) if obw is not None else float(ov_hz)
        else:
            # En canales parciales interesa más respetar el tramo visible del raster.
            obw_hz = float(ov_hz)
        visible_mid_hz = float(c if full_visible else 0.5 * (f[L] + f[R]))
        out.append({
            "candidate_L": int(L),
            "candidate_R": int(R),
            "refined_L": int(L),
            "refined_R": int(R),
            "measure_L": int(L),
            "measure_R": int(R),
            "refined_peak_idx": int(peak_idx),
            # En canales completos reportamos el centro raster; en canales parciales,
            # el centro del tramo visible para que la caja (fc,bw) respete el inicio/fin visibles.
            "fc_hz": float(visible_mid_hz),
            "match_fc_hz": float(c),
            "obw_hz": float(obw_hz),
            "bandwidth_hz": float(ov_hz),
            "f_lo_hz": float(f[L]),
            "f_hi_hz": float(f[R]),
            "snapped_fc_hz": float(c),
            "is_tdt_candidate": True,
            "is_partial_tdt": bool(not full_visible),
            "suppress_narrow": True,
            "noise_floor_dbm": float(noise_floor_dbm),
            "threshold_dbm": float(threshold_dbm),
            "threshold_selector": str(threshold_selector),
            "snr_db": float(max(0.0, y[int(peak_idx)] - float(noise_floor_dbm))),
            "source": "nominal_tdt_window",
        })
    return out


def analyze_colombia_broadband_segments(
    frame: SpectrumFrame,
    detect_threshold_db: Optional[float] = None,
) -> List[Dict[str, float]]:
    """Detectar emisiones TDT/banda ancha con umbral explícito o automático inteligente."""
    if not is_colombia_broadband_frame(frame):
        return []

    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    f = _frame_freq_axis(frame)
    N = y.size
    if N < 8:
        return []

    y_s = _smooth_broadband_trace(y, sigma=2.2)
    nf = float(_robust_noise_floor_broadband_dbm(y_s))

    if detect_threshold_db is not None:
        try:
            rel = float(detect_threshold_db)
        except Exception:
            rel = 2.5
        rel = max(0.0, rel)
        # En banda ancha, offsets absurdamente grandes vuelven inútil la detección.
        # Se acota a un rango físicamente razonable sin romper el contrato de entrada.
        rel = min(rel, 6.0)
        thr = float(nf + rel)
        selector_name = "manual_offset"
    else:
        selector = _choose_intelligent_threshold(frame, broadband=True, sigma_smooth=2.2)
        thr = float(selector["threshold_dbm"])
        nf = float(selector.get("noise_floor_dbm", nf))
        selector_name = str(selector.get("name", "smart_auto"))

    mask = np.asarray(y_s > thr, dtype=bool)
    close_bins = 15 if N >= 1024 else max(8, N // 120)
    max_gap_bins = 12 if N >= 1024 else max(4, N // 180)

    try:
        from scipy.ndimage import binary_closing
        if np.any(mask):
            mask = np.asarray(binary_closing(mask, structure=np.ones(close_bins, dtype=bool)), dtype=bool)
    except Exception:
        pass

    coarse = _merge_close_segments(_segments_from_mask(mask), max_gap_bins=max_gap_bins)
    total_span_hz = float(max(1.0, f[-1] - f[0]))
    min_seg_hz = float(min(1.0e6, 0.06 * total_span_hz))
    coarse = [(int(s), int(e)) for s, e in coarse if float(f[int(e)] - f[int(s)]) >= min_seg_hz]
    coarse = _merge_broadband_channel_segments(coarse, f)

    # 0) Detectores directos sobre el raster nominal TDT. Si una ventana raster es
    # plausible, preferimos sus bordes visibles antes que un refinamiento por valles.
    out: List[Dict[str, float]] = list(_find_nominal_tdt_window_segments(
        f, y, y_s,
        noise_floor_dbm=float(nf),
        threshold_dbm=float(thr),
        threshold_selector=selector_name,
    ))

    def _overlaps_existing(L: int, R: int, segs: List[Dict[str, float]], min_iou: float = 0.20) -> bool:
        for seg in segs:
            s = int(seg.get("measure_L", seg.get("refined_L", seg.get("candidate_L", 0))))
            e = int(seg.get("measure_R", seg.get("refined_R", seg.get("candidate_R", 0))))
            inter = max(0, min(R, e) - max(L, s) + 1)
            union = max(1, max(R, e) - min(L, s) + 1)
            if (inter / union) >= float(min_iou):
                return True
        return False

    grouped: Dict[int, Dict[str, float]] = {}
    for s, e in coarse:
        if e <= s:
            continue
        if _overlaps_existing(int(s), int(e), out, min_iou=0.18):
            continue
        seed_obw = _obw_99_limits_in_segment(f, y, s, e)
        seed_fc_hz = float(seed_obw["fc_obw_mid_hz"]) if seed_obw is not None else float(0.5 * (f[int(s)] + f[int(e)]))
        snapped_fc_hz = _nearest_tdt_channel_center_hz(seed_fc_hz)
        if abs(seed_fc_hz - snapped_fc_hz) > 2.2e6:
            snapped_fc_hz = seed_fc_hz
        key = int(round(snapped_fc_hz))
        prev = grouped.get(key)
        if prev is None:
            grouped[key] = {"s": int(s), "e": int(e), "fc_seed_hz": float(seed_fc_hz), "snap_fc_hz": float(snapped_fc_hz)}
        else:
            prev["s"] = int(min(int(prev["s"]), int(s)))
            prev["e"] = int(max(int(prev["e"]), int(e)))
            prev["fc_seed_hz"] = float(0.5 * (float(prev["fc_seed_hz"]) + float(seed_fc_hz)))

    for key in sorted(grouped.keys()):
        g = grouped[key]
        s = int(g["s"])
        e = int(g["e"])
        fc_seed_hz = float(g["fc_seed_hz"])
        refined = _refine_tdt_segment_to_channel(f, y, y_s, s, e, fc_seed_hz)
        if refined is not None and _is_plausible_tdt_channel(
            f, y, y_s,
            int(refined["measure_L"]), int(refined["measure_R"]),
            noise_floor_dbm=float(nf),
            snapped_fc_hz=float(refined.get("snapped_fc_hz", np.nan)),
            strict=True,
        ):
            local_peak = int(refined["refined_peak_idx"])
            snr_db = float(max(0.0, y[local_peak] - nf))
            refined.update({
                "noise_floor_dbm": float(nf),
                "threshold_dbm": float(thr),
                "threshold_selector": selector_name,
                "snr_db": float(snr_db),
                "is_tdt_candidate": True,
            })
            out.append(refined)
            continue

        # Fallback genérico de banda ancha: consérvalo solo si la región es
        # realmente ancha y coherente. Si no, dejamos que la ruta narrowband
        # capture los picos individuales sobre la meseta.
        if not _generic_broadband_segment_ok(f, y, y_s, s, e, noise_floor_dbm=float(nf)):
            continue

        obw = _obw_99_limits_in_segment(f, y, s, e)
        if obw is not None:
            fc_hz = float(obw["fc_obw_mid_hz"])
            obw_hz = float(obw["obw_99_hz"])
            f_lo_hz = float(obw["f_lo_hz"])
            f_hi_hz = float(obw["f_hi_hz"])
            i0 = int(np.argmin(np.abs(f - f_lo_hz)))
            i1 = int(np.argmin(np.abs(f - f_hi_hz)))
        else:
            fc_hz = float(0.5 * (f[int(s)] + f[int(e)]))
            obw_hz = float(max(0.0, f[int(e)] - f[int(s)]))
            f_lo_hz = float(f[int(s)])
            f_hi_hz = float(f[int(e)])
            i0, i1 = int(s), int(e)

        snap_fc = _nearest_tdt_channel_center_hz(fc_hz)
        is_tdt_candidate = _is_plausible_tdt_channel(
            f, y, y_s, int(s), int(e),
            noise_floor_dbm=float(nf),
            snapped_fc_hz=float(snap_fc),
            strict=False,
        )
        # Si el segmento es claramente ancho y razonablemente alineado con el raster,
        # anclar la FC al centro raster evita falsos desplazamientos y mejora el match.
        if (not is_tdt_candidate) and np.isfinite(obw_hz) and (obw_hz >= 3.2e6) and (abs(float(fc_hz) - float(snap_fc)) <= 1.8e6):
            fc_hz = float(snap_fc)

        local_peak = int(s + np.argmax(y[int(s): int(e) + 1]))
        snr_db = float(max(0.0, y[local_peak] - nf))
        out.append({
            "noise_floor_dbm": float(nf),
            "threshold_dbm": float(thr),
            "threshold_selector": selector_name,
            "candidate_L": int(s),
            "candidate_R": int(e),
            "refined_L": int(i0),
            "refined_R": int(i1),
            "measure_L": int(s),
            "measure_R": int(e),
            "refined_peak_idx": int(local_peak),
            "fc_hz": float(fc_hz),
            "obw_hz": float(obw_hz),
            "bandwidth_hz": float(max(0.0, f[int(e)] - f[int(s)])),
            "snr_db": float(snr_db),
            "f_lo_hz": float(f_lo_hz),
            "f_hi_hz": float(f_hi_hz),
            "snapped_fc_hz": float(snap_fc),
            "is_tdt_candidate": bool(is_tdt_candidate),
            "suppress_narrow": bool(obw_hz >= 1.6e6),
        })

    # Complemento: canales TDT parciales recortados por el borde de la ventana.
    # Se añaden solo si no duplican un segmento ya aceptado.
    for seg in _find_edge_partial_tdt_segments(f, y, y_s, noise_floor_dbm=float(nf), existing_segments=out):
        seg.update({
            "noise_floor_dbm": float(nf),
            "threshold_dbm": float(thr),
            "threshold_selector": selector_name,
            "snr_db": float(max(0.0, y[int(seg["refined_peak_idx"])] - nf)),
        })
        out.append(seg)
    return out


def analyze_colombia_broadband(frame: SpectrumFrame) -> Optional[Dict[str, float]]:
    """Compatibilidad: retorna la emisión TDT/banda ancha dominante."""
    segs = analyze_colombia_broadband_segments(frame)
    if not segs:
        return None
    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    p_lin = _dbm_to_mw(y)
    def _energy(seg: Dict[str, float]) -> float:
        s = int(seg.get("measure_L", seg.get("refined_L", 0)))
        e = int(seg.get("measure_R", seg.get("refined_R", 0)))
        return float(np.sum(p_lin[s:e+1])) if e >= s else -np.inf
    return max(segs, key=_energy)

def estimate_noise_floor(frame: SpectrumFrame) -> float: #Estima un piso de ruido. Toma la moda con tolerancia +-3, y si hay más de 8 emisiones, usa la media, si no, la mediana
    """Estimar de forma básica el piso de ruido global del espectro provisto."""
    if is_colombia_broadband_frame(frame):
        try:
            y = np.asarray(frame.amplitudes_dbm, dtype=float)
            y_s = _smooth_broadband_trace(y, sigma=2.2)
            nf_bb = _robust_noise_floor_broadband_dbm(y_s)
            if np.isfinite(nf_bb):
                return float(nf_bb)
        except Exception:
            pass

    x = np.asarray(frame.amplitudes_dbm, dtype=float)
    bins = min(256, max(32, int(np.sqrt(x.size))))
    counts, edges = np.histogram(x, bins=bins)
    i = int(np.argmax(counts))
    mode = (edges[i] + edges[i + 1]) / 2.0
    win_db = 6.0
    mask = (x >= mode - win_db / 2) & (x <= mode + win_db / 2)
    if mask.sum() >= 8:
        return float(x[mask].mean())
    return float(np.median(x))

def estimate_noise_floor_robust(
    frame: SpectrumFrame, method: str = "median") -> float: # Se deja para MC
    """Calcular el piso de ruido mediante técnicas robustas seleccionables.

    Args:
        frame: Datos espectrales en los que se medirá el ruido de fondo.
        method: Estrategia a utilizar (p. ej. ``"median"`` para median-of-minima,
            ``"percentile"`` para k-percentile o ``"histogram"`` para enfoques basados
            en histogramas).

    Returns:
        Nivel de ruido estimado en dBm conforme al método elegido, pensado para soportar
        señales con interferencias o emisiones fuertes cercanas.

    Uso previsto: reemplazo del estimador simple cuando se requiera resiliencia a picos
    espurios o entornos con alta variabilidad.
    """

    x = np.asarray(frame.amplitudes_dbm, dtype=float)
    m = (method or "median").lower()

    if m == "median":
        return float(np.median(x))

    if m == "percentile":
        # Percentil bajo robusto frente a colas/picos
        return float(np.percentile(x, 25.0))

    if m == "histogram":
        bins = min(256, max(32, int(np.sqrt(x.size))))
        counts, edges = np.histogram(x, bins=bins)
        i = int(np.argmax(counts))
        return float((edges[i] + edges[i + 1]) / 2.0)

    # Fallback robusto (t-Student IRLS liviano)
    mu = np.median(x)
    r = x - mu
    mad = np.median(np.abs(r)) + 1e-12
    sigma2 = (1.4826 * mad) ** 2
    nu = 6.0
    tol = 1e-5
    itmax = 50

    for _ in range(itmax):
        tval = (r * r) / max(sigma2, 1e-18)
        w = (nu + 1.0) / (nu + tval)
        wsum = np.sum(w) + 1e-18
        mu_new = float(np.sum(w * x) / wsum)
        r = x - mu_new
        tval = (r * r) / max(sigma2, 1e-18)
        w = (nu + 1.0) / (nu + tval)
        wsum = np.sum(w) + 1e-18
        sigma2_new = float(np.sum(w * r * r) / wsum)
        if (abs(mu_new - mu) <= tol * (abs(mu) + 1e-12)) and \
           (abs(sigma2_new - sigma2) <= tol * (sigma2 + 1e-12)):
            mu, sigma2 = mu_new, sigma2_new
            break
        mu, sigma2 = mu_new, max(1e-18, sigma2_new)
    return float(mu)

def _dedupe_peak_bins(cand: List[int], y_dbm: np.ndarray, *, min_sep_bins: int) -> List[int]:
    if len(cand) <= 1:
        return sorted(int(c) for c in cand)
    cand2 = sorted([int(c) for c in cand], key=lambda idx: float(y_dbm[idx]), reverse=True)
    kept: List[int] = []
    taken = np.zeros(len(y_dbm), dtype=np.bool_)
    for idx in cand2:
        left = max(0, int(idx) - int(min_sep_bins))
        right = min(len(y_dbm), int(idx) + int(min_sep_bins))
        if not taken[left:right].any():
            kept.append(int(idx))
            taken[left:right] = True
    return sorted(kept)


def _detect_peak_bins_narrow_core(
    frame: SpectrumFrame,
    detect_threshold_db: Optional[float] = None,
    *,
    n_sigma_seed: float = 3.5,
    min_snr_db_default: float = 0.73,
    exclude_ranges: Optional[List[tuple[int, int]]] = None,
) -> List[int]:
    """Detector narrowband reutilizable.

    Estrategia:
    - En ventanas normales combina segmentos por umbral + máximos locales.
    - En ventanas UHF anchas trabaja sobre el residual respecto a una línea base
      lenta y suprime picos espurios montados sobre mesetas elevadas.
    """
    y_dbm = np.asarray(frame.amplitudes_dbm, dtype=float)
    f_hz = _frame_freq_axis(frame)
    N = y_dbm.size
    if N == 0:
        return []

    kernel = np.array([0.25, 0.5, 0.25], dtype=float)
    y_smooth = np.convolve(y_dbm, kernel, mode="same")

    work_mask = np.ones(N, dtype=np.bool_)
    if exclude_ranges:
        guard = max(6, int(0.0015 * N))
        for L, R in exclude_ranges:
            l = max(0, int(L) - guard)
            r = min(N - 1, int(R) + guard)
            if r >= l:
                work_mask[l:r + 1] = False
    if not np.any(work_mask):
        return []

    y_work = y_dbm[work_mask]
    stats = _lower_noise_stats(y_work, q=25.0)
    nf = float(stats.get("nf_dbm", np.median(y_work)))
    sigma = float(stats.get("sigma_db", 1.0))
    if not np.isfinite(nf):
        nf = float(np.median(y_work))
    if not np.isfinite(sigma) or sigma <= 0.0:
        sigma = 1.0

    broadband_mode = bool(is_colombia_broadband_frame(frame))
    cand: List[int] = []

    # 1) Segmentación absoluta: mantenla solo fuera de capturas broadband.
    # En mesetas anchas esta ruta produce muchos máximos falsos.
    if not broadband_mode:
        if detect_threshold_db is not None:
            try:
                x = float(detect_threshold_db)
            except Exception:
                x = 0.0
            if not np.isfinite(x):
                raise ValueError("detect_threshold_db inválido (no finito)")
            x = max(0.0, x)
            thr_seed = float(nf + min(1.0, x))
            min_snr_db = float(max(x, min_snr_db_default))
        else:
            thr_seed = float(nf + max(1.2, 4.0 * sigma))
            min_snr_db = float(max(1.5, 2.0 * sigma, min_snr_db_default))

        mask = work_mask & (y_smooth > thr_seed)
        segs = _merge_close_segments(_segments_from_mask(mask), max_gap_bins=max(4, N // 160))
        span_hz = float(max(1.0, f_hz[-1] - f_hz[0])) if f_hz.size >= 2 else float(max(1.0, N))
        min_width_hz = float(max(1.5e4, 0.00025 * span_hz))
        for s, e in segs:
            s = int(max(0, s))
            e = int(min(N - 1, e))
            if e < s:
                continue
            seg_w_hz = float(f_hz[e] - f_hz[s]) if f_hz.size == N else float(e - s)
            if seg_w_hz < min_width_hz:
                continue
            pk_local = int(np.argmax(y_dbm[s:e + 1]) + s)
            if float(y_dbm[pk_local] - nf) >= float(min_snr_db):
                cand.append(int(pk_local))

    # 2) Máximos locales sobre residual respecto a baseline lenta.
    try:
        from scipy.signal import find_peaks, peak_widths
        sigma_base = float(max(10.0, min(45.0, N / 600.0)))
        baseline = _gaussian_smooth1d(y_smooth, sigma=sigma_base)
        residual = y_smooth - baseline
        res_work = residual[work_mask]
        if res_work.size >= 8:
            med_r = float(np.median(res_work))
            mad_r = float(np.median(np.abs(res_work - med_r)) + 1e-12)
            sigma_r = float(1.4826 * mad_r)

            if broadband_mode:
                # En capturas UHF anchas trabajamos por regiones no excluidas.
                # Así recuperamos picos reales del residual y también jorobas
                # angostas/moderadas del espectro sin volver a llenar una meseta
                # ancha de picos falsos.
                regions = _segments_from_mask(work_mask)
                for a, b in regions:
                    a = int(a); b = int(b)
                    if (b - a + 1) < max(12, N // 400):
                        continue
                    seg_s = y_smooth[a:b + 1]
                    seg_r = residual[a:b + 1]
                    region_width_hz = float(f_hz[b] - f_hz[a]) if len(f_hz) == N else float(b - a)
                    # Si la región remanente es una meseta/shelf ancha y muy ocupada,
                    # no la llenamos de picos narrowband; suele ser clutter elevado o
                    # un bloque ancho ambiguo. En esos casos preferimos 0 picos antes
                    # que decenas de falsos positivos.
                    reg_stats0 = _lower_noise_stats(seg_s, q=35.0)
                    reg_nf0 = float(reg_stats0.get("nf_dbm", np.median(seg_s)))
                    reg_occ = float(np.mean(seg_s > (reg_nf0 + 1.0)))
                    reg_spread = float(np.percentile(seg_s, 95.0) - np.percentile(seg_s, 5.0)) if len(seg_s) >= 8 else 0.0
                    if region_width_hz >= 1.5e6 and reg_occ >= 0.35 and reg_spread >= 7.0:
                        continue
                    stats_loc = reg_stats0
                    nf_loc = float(stats_loc.get("nf_dbm", nf))
                    sigma_loc = float(stats_loc.get("sigma_db", sigma_r))
                    if (not np.isfinite(nf_loc)):
                        nf_loc = float(nf)
                    if (not np.isfinite(sigma_loc)) or sigma_loc <= 0.0:
                        sigma_loc = float(max(0.4, sigma_r))

                    # 2.a) Picos directos sobre la traza suavizada: captura jorobas
                    # medianas (p. ej. 496.7, 500.6, 504.5 MHz) que el residual
                    # puro no siempre retiene.
                    d_peaks, d_props = find_peaks(
                        seg_s,
                        prominence=float(max(1.2, 2.1 * sigma_loc)),
                        distance=int(max(14, min(100, 0.0045 * N))),
                    )
                    d_widths = peak_widths(seg_s, d_peaks, rel_height=0.5)[0] if len(d_peaks) else np.array([])
                    for j, pk0 in enumerate(d_peaks.tolist()):
                        pk = int(a + pk0)
                        amp = float(seg_s[pk0])
                        prom0 = float(d_props["prominences"][j]) if "prominences" in d_props else 0.0
                        width_bins = float(d_widths[j]) if j < len(d_widths) else 0.0
                        if (amp - nf_loc) < max(1.0, 1.4 * sigma_loc) and prom0 < max(2.0, 2.8 * sigma_loc):
                            continue
                        width_khz = float(width_bins * abs(f_hz[1] - f_hz[0]) / 1e3) if len(f_hz) >= 2 else 0.0
                        if width_bins < 2.0:
                            continue
                        if width_bins > max(420.0, 0.18 * max(1, (b - a + 1))):
                            continue
                        if width_khz < 20.0 and prom0 < 6.0:
                            continue
                        cand.append(pk)

                    # 2.b) Picos agudos sobre el residual lento: conserva líneas o
                    # picos estrechos realmente sobresalientes.
                    r_peaks, r_props = find_peaks(
                        seg_r,
                        height=float(max(1.0, 3.8 * sigma_r)),
                        prominence=float(max(1.4, 4.4 * sigma_r)),
                        distance=int(max(10, min(70, 0.0035 * N))),
                    )
                    r_widths = peak_widths(seg_r, r_peaks, rel_height=0.5)[0] if len(r_peaks) else np.array([])
                    for j, pk0 in enumerate(r_peaks.tolist()):
                        pk = int(a + pk0)
                        amp = float(seg_s[pk0])
                        prom0 = float(r_props["prominences"][j]) if "prominences" in r_props else float(seg_r[pk0])
                        width_bins = float(r_widths[j]) if j < len(r_widths) else 0.0
                        if (amp - nf_loc) < max(1.1, 1.2 * sigma_loc) and prom0 < max(1.6, 3.0 * sigma_r):
                            continue
                        width_khz = float(width_bins * abs(f_hz[1] - f_hz[0]) / 1e3) if len(f_hz) >= 2 else 0.0
                        if width_bins < 1.5:
                            continue
                        if width_bins > max(120.0, 0.06 * max(1, (b - a + 1))):
                            continue
                        if width_khz < 18.0 and prom0 < 6.0:
                            continue
                        cand.append(pk)
            else:
                height = float(max(1.0, 3.8 * sigma_r))
                prom = float(max(1.25, 4.5 * sigma_r))
                distance = int(max(10, 0.004 * N))
                peaks, props = find_peaks(residual, height=height, prominence=prom, distance=distance)
                for pk in peaks.tolist():
                    pk = int(pk)
                    if pk < 0 or pk >= N or (not work_mask[pk]):
                        continue
                    amp = float(y_smooth[pk])
                    if (amp - nf) < max(1.0, 0.8 * min_snr_db_default):
                        continue
                    cand.append(pk)
    except Exception:
        pass

    min_sep = max(10, int(0.0085 * N)) if broadband_mode else max(6, int(0.0035 * N))
    return _dedupe_peak_bins(cand, y_dbm, min_sep_bins=min_sep)

def detect_peak_bins(
    frame: SpectrumFrame,
    detect_threshold_db: Optional[float] = None,
    *,
    n_sigma_seed: float = 3.5,
    min_snr_db_default: float = 0.73,
) -> List[int]:
    """Localizar bins que funcionen como picos iniciales para análisis detallados.

    En capturas UHF anchas mezcla:
    - canales banda ancha/TDT detectados por la ruta híbrida, y
    - picos narrowband residuales fuera de esos canales.
    """
    if is_colombia_broadband_frame(frame):
        bb_segs = analyze_colombia_broadband_segments(frame, detect_threshold_db=detect_threshold_db)
        bb_peaks = [int(seg["refined_peak_idx"]) for seg in bb_segs]
        exclude = []
        for seg in bb_segs:
            if not bool(seg.get("is_tdt_candidate", False) or seg.get("suppress_narrow", False)):
                continue
            L = int(seg.get("measure_L", seg.get("refined_L", seg.get("candidate_L", 0))))
            R = int(seg.get("measure_R", seg.get("refined_R", seg.get("candidate_R", 0))))
            if R >= L:
                exclude.append((L, R))
        narrow_peaks = _detect_peak_bins_narrow_core(
            frame,
            detect_threshold_db=detect_threshold_db,
            n_sigma_seed=n_sigma_seed,
            min_snr_db_default=min_snr_db_default,
            exclude_ranges=exclude,
        )
        # Evita picos pegados a los bordes de una emisión ancha ya aceptada: suelen
        # ser artefactos de borde y duplican visualmente la misma emisión.
        if narrow_peaks and exclude:
            f = _frame_freq_axis(frame)
            kept_narrow = []
            has_plausible_tdt = any(bool(seg.get("is_tdt_candidate", False)) for seg in bb_segs)
            for pk in narrow_peaks:
                fp = float(f[int(pk)])
                near_edge = False
                # En presencia de un canal TDT plausible, los picos estrechos pegados
                # a los bordes del canal o al borde de la ventana suelen ser artefactos.
                if has_plausible_tdt:
                    frame_edge_guard_hz = 0.60e6
                    if fp <= (float(f[0]) + frame_edge_guard_hz) or fp >= (float(f[-1]) - frame_edge_guard_hz):
                        near_edge = True
                for seg in bb_segs:
                    if near_edge:
                        break
                    L = int(seg.get("measure_L", seg.get("refined_L", seg.get("candidate_L", 0))))
                    R = int(seg.get("measure_R", seg.get("refined_R", seg.get("candidate_R", 0))))
                    fL = float(f[int(max(0, L))])
                    fR = float(f[int(min(len(f)-1, R))])
                    seg_guard_hz = 0.90e6 if bool(seg.get("is_tdt_candidate", False)) else 0.55e6
                    if (fL - seg_guard_hz) <= fp <= (fL + seg_guard_hz) or (fR - seg_guard_hz) <= fp <= (fR + seg_guard_hz):
                        near_edge = True
                        break
                if not near_edge:
                    kept_narrow.append(int(pk))
            narrow_peaks = kept_narrow
        y_dbm = np.asarray(frame.amplitudes_dbm, dtype=float)
        return _dedupe_peak_bins(bb_peaks + narrow_peaks, y_dbm, min_sep_bins=max(3, int(0.001 * len(y_dbm))))

    return _detect_peak_bins_narrow_core(
        frame,
        detect_threshold_db=detect_threshold_db,
        n_sigma_seed=n_sigma_seed,
        min_snr_db_default=min_snr_db_default,
        exclude_ranges=None,
    )

def measure_emission_power( #Calcula la potencia integrada, revisar metricas
    frame: SpectrumFrame, f_center_hz: float, metric: str) -> Dict[str, float]:
    """Calcular métricas de potencia y ocupación para una emisión centrada en ``f_center_hz``.

    Args:
        frame: Medición espectral que contiene la emisión de interés.
        f_center_hz: Frecuencia objetivo alrededor de la cual se localizará el pico
            principal para integrar potencia y calcular anchuras.
        metric: Variante a aplicar (p. ej. ``"obw"`` para potencia acumulada, ``"xdb``
            para anchos a −XdB); permitirá reutilizar la función en distintos reportes.

    Returns:
        Diccionario con métricas específicas (potencia integrada, OBW 99 %, anchos a
        3/10/26 dB, etc.). La implementación decidirá qué claves se rellenan según
        ``metric`` y cómo se formatean los valores.

    Uso previsto: centralizar el cómputo de métricas de emisiones detectadas a fin de
    generar reportes de conformidad u optimización de espectro.
    """

    y_dbm = np.asarray(frame.amplitudes_dbm, dtype=float)
    N = y_dbm.size
    if hasattr(frame, "freq_hz") and frame.freq_hz is not None:
        f = np.asarray(frame.freq_hz, dtype=float)
    else:
        f = np.linspace(float(frame.f_start_hz), float(frame.f_stop_hz), N)

    if hasattr(frame, "bin_hz") and frame.bin_hz:
        df = float(frame.bin_hz)
    else:
        df = float((f[-1] - f[0]) / max(1, N - 1))

    # Pico más cercano al centro solicitado
    peak_idx = int(np.argmin(np.abs(f - float(f_center_hz))))

    # Potencia integrada en ventana local (aprox) alrededor del pico
    p_w_hz = 10 ** ((y_dbm - 30.0) / 10.0)  # dBm/Hz -> W/Hz
    K = max(1, int(0.01 * N))               # ±1% del total de bins como ventana simple
    sl = slice(max(0, peak_idx - K), min(N, peak_idx + K + 1))
    p_w = p_w_hz[sl].sum() * max(df, 1.0)
    out: Dict[str, float] = {"power_dBm": 10.0 * np.log10(max(p_w, 1e-18)) + 30.0}

    m = (metric or "").lower()
    if m == "obw":
        out["obw_percent"] = 99.0  # el ancho exacto lo obtienes con measure_obw en tests
    elif m == "xdb":
        out["xdb_ref_dB"] = 3.0    # el ancho exacto lo obtienes con measure_bandwidth_xdb
    return out

def measure_bandwidth_xdb(
    frame: SpectrumFrame, peak_idx: int, x_db: float = 3.0
) -> float:
    """
    Determina el ancho de banda a -x dB respecto al pico usando:
      - Suavizado ligero
      - Cruces exactos por interpolación lineal
      - Detección robusta de las dos primeras intersecciones reales

    Esto es SIGNIFICATIVAMENTE más estable frente a ruido
    y funciona bien en señales reales FM/AM/LTE/WiFi.
    """

    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    N = len(y)

    if hasattr(frame, "freq_hz") and frame.freq_hz is not None:
        f = np.asarray(frame.freq_hz, dtype=float)
    else:
        f = np.linspace(frame.f_start_hz, frame.f_stop_hz, N)

    pk = int(np.clip(peak_idx, 0, N - 1))
    peak_val = y[pk]
    thr = peak_val - float(x_db)

    # -------------------------------------------------------
    # 1) SUAVIZADO LIGERO (sin destruir estructura)
    # -------------------------------------------------------
    kernel = np.array([0.25, 0.5, 0.25])
    y_s = np.convolve(y, kernel, mode="same")

    # -------------------------------------------------------
    # 2) Buscamos todos los cruces de y_s con el umbral
    #    f_cross = f[i] + (thr - y_s[i]) * (f[i+1]-f[i])/(y_s[i+1]-y_s[i])
    # -------------------------------------------------------
    fL = None
    fR = None

    for i in range(N - 1):
        yi, yj = y_s[i], y_s[i+1]

        # Si hay cruce (el umbral está entre yi y yj)
        if (yi - thr) == 0:
            # cruce exacto en bin
            fc = f[i]
        elif (yi - thr) * (yj - thr) < 0:
            # Interpolación lineal del cruce
            t = (thr - yi) / (yj - yi)
            t = np.clip(t, 0.0, 1.0)
            fc = f[i] + t * (f[i+1] - f[i])
        else:
            continue

        # Primer cruce a la izquierda del pico → fL
        if fL is None and fc < f[pk]:
            fL = fc

        # Primer cruce a la derecha del pico → fR
        if fR is None and fc > f[pk]:
            fR = fc

        if fL is not None and fR is not None:
            break

    # -------------------------------------------------------
    # 3) Casos degenerados
    # -------------------------------------------------------
    if fL is None:
        fL = f[0]
    if fR is None:
        fR = f[-1]

    bw = max(0.0, float(fR - fL))

    # Candado físico: no más grande que el span total
    return min(bw, float(f[-1] - f[0]))

def measure_obw(
    frame: SpectrumFrame,
    peak_idx: int,
    percentile: float = 99.0,
    x_db_window: float = 3.0,
) -> float:
    """Calcular OBW (Occupied Bandwidth) por potencia acumulada.

    Implementación estándar: OBW = ancho de banda que contiene ``percentile`` %
    de la POTENCIA total integrada de la emisión.

    **Importante**: este cálculo asume que ``frame.amplitudes_dbm`` representa
    una PSD en ``dBm/Hz`` (o al menos una densidad proporcional). Por eso:
      1) Convertimos a dominio lineal ``W/Hz``
      2) Integramos vs frecuencia
      3) Hallamos los cuantiles de potencia acumulada

    En este proyecto, normalmente se llama a ``measure_emission_parameters``
    con un ``frame`` ya recortado a la emisión (vía ``find_emission_span`` +
    ``slice_spectrum_frame``), que es el caso ideal para OBW.

    Args:
        frame: Captura espectral (idealmente recortada a la emisión).
        peak_idx: Índice del pico (se mantiene por compatibilidad; no es
            estrictamente necesario para el cálculo por potencia acumulada).
        percentile: Porcentaje de potencia a contener (p.ej. 99 => OBW 99%).
        x_db_window: Parámetro legacy (no se usa en esta versión). Se conserva
            para no romper compatibilidad con llamadas existentes.

    Returns:
        OBW en Hz (>= 0).
    """

    # Sanitizar percentile
    try:
        p = float(percentile)
    except Exception:
        p = 99.0
    p = float(np.clip(p, 0.0, 100.0))
    if p <= 0.0:
        return 0.0

    y_dbm = np.asarray(frame.amplitudes_dbm, dtype=float)
    N = y_dbm.size
    if N < 2:
        return 0.0

    # Eje de frecuencias
    if getattr(frame, "freq_hz", None) is not None:
        f = np.asarray(frame.freq_hz, dtype=float)
    else:
        f = np.linspace(float(frame.f_start_hz), float(frame.f_stop_hz), N)

    # Asegurar orden creciente
    if f[0] > f[-1]:
        f = f[::-1]
        y_dbm = y_dbm[::-1]

    # PSD dBm/Hz -> W/Hz
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        p_w_hz = 10.0 ** ((y_dbm - 30.0) / 10.0)
    p_w_hz = np.where(np.isfinite(p_w_hz), p_w_hz, 0.0)
    p_w_hz = np.maximum(p_w_hz, 0.0)

    # Integral acumulada (trapecio)
    df = np.diff(f)
    if not np.all(np.isfinite(df)) or np.any(df <= 0.0):
        # si el eje es patológico, no hay un OBW confiable
        return 0.0

    # dP[i] = integral entre i-1 e i
    dP = 0.5 * (p_w_hz[:-1] + p_w_hz[1:]) * df
    dP = np.where(np.isfinite(dP), dP, 0.0)
    cum = np.empty(N, dtype=float)
    cum[0] = 0.0
    cum[1:] = np.cumsum(dP)

    total = float(cum[-1])
    if not np.isfinite(total) or total <= 0.0:
        return 0.0

    frac = p / 100.0
    tail = (1.0 - frac) / 2.0
    lo_target = tail * total
    hi_target = (1.0 - tail) * total

    def _interp_f_at_target(target: float) -> float:
        # encuentra primer i tal que cum[i] >= target
        i = int(np.searchsorted(cum, target, side="left"))
        if i <= 0:
            return float(f[0])
        if i >= N:
            return float(f[-1])
        c0 = float(cum[i - 1])
        c1 = float(cum[i])
        if c1 <= c0:
            return float(f[i])
        t = (float(target) - c0) / (c1 - c0)
        return float(f[i - 1] + t * (f[i] - f[i - 1]))

    f_lo = _interp_f_at_target(lo_target)
    f_hi = _interp_f_at_target(hi_target)
    return float(max(0.0, f_hi - f_lo))

def measure_channel_power(
    frame: SpectrumFrame, f_center: float, bw: float
) -> float:
    """
    Integrar la potencia contenida dentro de un canal centrado en ``f_center``.

    Se asume que las amplitudes están en PSD [dBm/Hz].
    La integración se hace en el dominio lineal (W/Hz) usando la
    regla del trapecio sobre el eje de frecuencias real.

    Args:
        frame: Datos espectrales que cubren el canal objetivo.
        f_center: Frecuencia central del canal a integrar.
        bw: Ancho de banda del canal (en Hz) que define los límites de integración.

    Returns:
        Potencia total del canal en dBm (señal+ruido) integrada sobre BW.
        Si no hay suficientes puntos dentro del canal, devuelve -inf.
    """

    y_dbm = np.asarray(frame.amplitudes_dbm, dtype=float)
    N = y_dbm.size
    if N < 2:
        return float("-inf")

    # Eje de frecuencias
    if getattr(frame, "freq_hz", None) is not None:
        f = np.asarray(frame.freq_hz, dtype=float)
    else:
        f = np.linspace(float(frame.f_start_hz), float(frame.f_stop_hz), N)

    # Validación ancho de banda
    f_center = float(f_center)
    bw = float(bw)
    if bw <= 0.0:
        return float("-inf")

    # Límites del canal, recortados al span disponible
    span_min = float(f[0])
    span_max = float(f[-1])
    fL = max(f_center - bw / 2.0, span_min)
    fR = min(f_center + bw / 2.0, span_max)

    if fR <= fL:
        return float("-inf")

    # Seleccionar muestras dentro del canal
    mask = (f >= fL) & (f <= fR)
    if mask.sum() < 2:
        return float("-inf")

    f_sel = f[mask]
    y_sel_dbm = y_dbm[mask]

    # dBm/Hz -> W/Hz en dominio lineal
    p_w_per_hz = 10.0 ** ((y_sel_dbm - 30.0) / 10.0)

    # Integración en frecuencia (W) usando trapecios
    p_w = float(trapz_compat(p_w_per_hz, f_sel))

    if p_w <= 0.0:
        return float("-inf")

    # W -> dBm
    return 10.0 * np.log10(p_w) + 30.0

def compute_snr(frame: SpectrumFrame, peaks: List[int]) -> Dict[int, float]:
    """Calcular la relación señal/ruido (SNR) para cada pico o emisión identificada.

    Args:
        frame: Espectro de referencia para extraer potencias de señal y ruido.
        peaks: Lista de índices de bins que representan las señales a evaluar.

    Returns:
        Diccionario que asocia cada índice de pico con su SNR en dB, calculado a partir
        de la potencia de la señal frente al piso de ruido estimado.

    Uso previsto: cuantificar calidad de señales detectadas y alimentar decisiones de
    demodulación, asignación de espectro o validación de enlaces.
    """

    y_dbm = np.asarray(frame.amplitudes_dbm, dtype=float)
    nf = float(np.median(y_dbm))

    out: Dict[int, float] = {}
    for pk in peaks:
        idx = int(max(0, min(len(y_dbm) - 1, int(pk))))
        out[idx] = float(y_dbm[idx] - nf)
    return out

def adaptive_threshold(frame: SpectrumFrame, n_sigma: float = 3.0) -> float:
    """Elegir un umbral automático inteligente.

    - En banda ancha/TDT: selecciona el umbral que mejor segmenta la región ocupada.
    - En banda angosta: balancea separación señal/ruido, ocupación y fragmentación.
    """
    broadband = is_colombia_broadband_frame(frame)
    try:
        selector = _choose_intelligent_threshold(
            frame,
            broadband=broadband,
            sigma_smooth=(2.2 if broadband else 1.0),
        )
        thr = float(selector["threshold_dbm"])
        if np.isfinite(thr):
            return thr
    except Exception:
        pass

    x = np.asarray(frame.amplitudes_dbm, dtype=float)
    try:
        nf_hist = float(estimate_noise_floor(frame))
    except Exception:
        nf_hist = float(np.median(x))
    nf = _robust_nf_for_detection(x, nf_hist)
    stats = _lower_noise_stats(x, q=25.0)
    sigma = float(stats.get("sigma_db", 1.0))
    thr = float(nf + max(0.8, float(n_sigma) * sigma))
    mx = float(np.max(x)) if x.size > 0 else thr
    thr = min(thr, mx - 0.1)
    thr = max(thr, float(nf + 0.5))
    return float(thr)

def find_emission_span(frame: SpectrumFrame,peak_idx: int,margin_db: float = 0.5) -> tuple[int, int]:
    """
    Devuelve los índices [L, R] que delimitan la emisión alrededor de un pico dado.

    Para TDT/banda ancha de Colombia usa la región ocupada principal del método
    híbrido del notebook. Para el resto conserva el comportamiento histórico.
    """
    bb = analyze_colombia_broadband(frame)
    if bb is not None:
        pk = int(np.clip(int(peak_idx), 0, len(frame.amplitudes_dbm) - 1))
        cand_L = int(bb["candidate_L"])
        cand_R = int(bb["candidate_R"])
        if cand_L <= pk <= cand_R:
            return cand_L, cand_R

    y_dbm = np.asarray(frame.amplitudes_dbm, dtype=float)
    N = y_dbm.size
    pk = int(max(0, min(N - 1, int(peak_idx))))
    nf = float(estimate_noise_floor(frame))
    thr = nf + float(margin_db)

    L = pk
    while L > 0 and y_dbm[L] > thr:
        L -= 1
    R = pk
    while R < N - 1 and y_dbm[R] > thr:
        R += 1

    L = max(0, L)
    R = min(N - 1, R)
    if R <= L:
        L = max(0, pk - 1)
        R = min(N - 1, pk + 1)
    return L, R

def slice_spectrum_frame(frame: SpectrumFrame, L: int, R: int) -> SpectrumFrame:
    """
    Crea un SpectrumFrame nuevo recortado a los índices [L, R].
    """
    L = int(L)
    R = int(R)
    amps = frame.amplitudes_dbm[L:R+1]
    freqs = frame.freq_hz[L:R+1]
    return SpectrumFrame(
        amplitudes_dbm=amps,
        f_start_hz=float(freqs[0]),
        f_stop_hz=float(freqs[-1]),
        freq_hz=freqs,
        bin_hz=frame.bin_hz,  # misma resolución
    )


def estimate_ber_in_band_mqam(
    frame: SpectrumFrame,
    f_start_hz: float,
    f_stop_hz: float,
    M: int
) -> Dict[str, float]:
    """Estimar MER/BER solo para TDT usando guardas laterales cuando existen.

    La estimación es coherente con Pxx: usa el canal recortado para la señal y, cuando
    el frame completo lo permite, usa bandas laterales cercanas como referencia de ruido.
    """
    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    if y.size == 0:
        return {}
    M = int(M)
    if M < 4:
        return {}

    if getattr(frame, "freq_hz", None) is not None:
        f = np.asarray(frame.freq_hz, dtype=float)
    else:
        f = np.linspace(float(frame.f_start_hz), float(frame.f_stop_hz), y.size)

    f_start_hz = float(f_start_hz)
    f_stop_hz = float(f_stop_hz)
    if f_stop_hz < f_start_hz:
        f_start_hz, f_stop_hz = f_stop_hz, f_start_hz
    f_center = 0.5 * (f_start_hz + f_stop_hz)
    if not is_tdt_frequency_hz(f_center):
        return {}
    if not _band_is_plausible_tdt(frame, f_start_hz, f_stop_hz):
        return {}

    y_s = _smooth_broadband_trace(y, sigma=2.0)
    in_mask = (f >= f_start_hz) & (f <= f_stop_hz)
    if int(np.sum(in_mask)) < 8:
        return {}

    bw_hz = float(max(1.0, f_stop_hz - f_start_hz))
    guard_hz = 0.75 * bw_hz
    guard_mask = ((f >= (f_start_hz - guard_hz)) & (f < f_start_hz)) | ((f > f_stop_hz) & (f <= (f_stop_hz + guard_hz)))
    y_guard = y_s[guard_mask]
    if y_guard.size < 8:
        y_guard = y_s[~in_mask]
    if y_guard.size >= 8:
        q50 = float(np.percentile(y_guard, 50.0))
        lower = y_guard[y_guard <= q50]
        if lower.size == 0:
            lower = y_guard
        med = float(np.median(lower))
        mad = float(np.median(np.abs(lower - med)) + 1e-12)
        nf_dbm = float(med + 0.15 * 1.4826 * mad)
    else:
        nf_dbm = float(_lower_noise_stats(y_s[in_mask], q=20.0).get("nf_dbm", np.median(y_s[in_mask])))

    y_in = y_s[in_mask]
    p_in = _dbm_to_mw(y_in)
    n_lin = float(10.0 ** (nf_dbm / 10.0))
    sig_lin = np.maximum(p_in - n_lin, 0.0)
    cn_db = float(10.0 * np.log10(max(float(np.mean(sig_lin) / max(n_lin, 1e-30)), 1e-12)))

    med_excess_db = float(np.median(y_in) - nf_dbm)
    p90_excess_db = float(np.percentile(y_in, 90.0) - nf_dbm)
    p99_excess_db = float(np.percentile(y_in, 99.0) - nf_dbm)
    ripple_db = float(np.std(y_in - np.median(y_in)))
    notch_depth_db = float(max(0.0, np.median(y_in) - float(np.percentile(y_in, 10.0))))

    mer_db = float(
        0.55 * cn_db + 0.30 * p90_excess_db + 0.15 * med_excess_db
        - 0.35 * ripple_db - 0.20 * max(0.0, notch_depth_db - 1.5)
    )
    mer_db = float(np.clip(mer_db, 0.0, 40.0))

    k = math.log2(M)
    snr_lin = 10.0 ** (mer_db / 10.0)
    xq = math.sqrt(max(1e-18, 3.0 * k * snr_lin / max(M - 1.0, 1.0)))
    qx = 0.5 * math.erfc(xq / math.sqrt(2.0))
    ber = float((4.0 / k) * (1.0 - 1.0 / math.sqrt(M)) * qx)
    ber = float(np.clip(ber, 1e-12, 0.5))

    return {
        "f_center_hz": f_center,
        "band_start_hz": f_start_hz,
        "band_stop_hz": f_stop_hz,
        "snr_db": float(np.clip(cn_db, -5.0, 50.0)),
        "ber_est": ber,
        "mer_db": mer_db,
    }

def estimate_mer_from_ber_mqam(ber: float, M: int) -> float:
    """
    Estimar MER (dB) a partir de un BER teórico para M-QAM cuadrada.

    Se usa una aproximación tipo:
        MER_dB ≈ 10*log10(1 / BER)

    Esto interpreta MER como relación señal-a-error en la constelación.
    Es una aproximación práctica cuando solo se dispone de BER y el
    modelo teórico subyacente es M-QAM en AWGN.

    Args:
        ber: BER teórico (0 < ber < 0.5).
        M: Orden de la modulación (no se usa directamente aquí,
           pero se mantiene por coherencia de interfaz).

    Returns:
        MER aproximado en dB.
    """
    ber = float(ber)
    if ber <= 0.0:
        return 99.0  # límite superior arbitrario
    if ber >= 0.5:
        return 0.0   # enlace destruido

    mer_db = 10.0 * math.log10(1.0 / ber)
    return float(mer_db)

def measure_emission_parameters(
    frame: SpectrumFrame,
    fc: float,
    xdb: float = 3.0,
    obw_percent: float = 99.0
) -> Dict[str, float]:
    """Mide los parámetros principales de una emisión sin romper compatibilidad."""

    y_dbm = np.asarray(frame.amplitudes_dbm, dtype=float)
    N = y_dbm.size
    if N == 0:
        return {
            "fc_hz": float(fc),
            "power_dbm": float("-inf"),
            "bandwidth_xdb_hz": 0.0,
            "obw_hz": 0.0,
            "channel_power_dbm": float("-inf"),
            "snr_db": float("nan"),
        }

    if frame.freq_hz is not None:
        f = np.asarray(frame.freq_hz, dtype=float)
    else:
        f = np.linspace(float(frame.f_start_hz), float(frame.f_stop_hz), N)

    if is_colombia_broadband_frame(frame):
        try:
            y_s = _smooth_broadband_trace(y_dbm, sigma=2.2)
            nf_dbm = float(_robust_noise_floor_broadband_dbm(y_s))
        except Exception:
            y_s = y_dbm
            nf_dbm = float(np.median(y_dbm))
        obw_info = _obw_99_limits_in_segment(f, y_dbm, 0, N - 1)
        if obw_info is not None:
            fc_eff = float(obw_info["fc_obw_mid_hz"])
            obw_hz = float(obw_info["obw_99_hz"])
        else:
            fc_eff = float(0.5 * (f[0] + f[-1]))
            obw_hz = float(max(0.0, f[-1] - f[0]))
        bw_seg = float(max(0.0, f[-1] - f[0]))
        p_lin = _dbm_to_mw(y_dbm)
        mean_dbm = float(10.0 * np.log10(max(np.mean(p_lin), 1e-30)))
        sig_lin = np.maximum(p_lin - 10.0 ** (nf_dbm / 10.0), 1e-30)
        ch_dbm = float(10.0 * np.log10(max(np.mean(sig_lin), 1e-30)))
        snr_db = float(max(0.0, np.max(y_s) - nf_dbm))
        return {
            "fc_hz": fc_eff,
            "power_dbm": mean_dbm,
            "bandwidth_xdb_hz": bw_seg,
            "obw_hz": obw_hz,
            "channel_power_dbm": ch_dbm,
            "snr_db": snr_db,
        }

    fc = float(fc)
    pk = int(np.argmin(np.abs(f - fc)))
    pk = int(np.clip(pk, 0, N - 1))
    fc_eff = float(f[pk])
    bw_xdb = measure_bandwidth_xdb(frame, pk, x_db=xdb)
    if bw_xdb <= 0.0:
        return {
            "fc_hz": fc_eff,
            "power_dbm": float("-inf"),
            "bandwidth_xdb_hz": 0.0,
            "obw_hz": 0.0,
            "channel_power_dbm": float("-inf"),
            "snr_db": float("nan"),
        }
    obw_hz = measure_obw(frame, peak_idx=pk, percentile=obw_percent, x_db_window=xdb)
    if obw_hz <= 0.0:
        obw_hz = bw_xdb * float(obw_percent) / 100.0
    total_bw_dbm = measure_channel_power(frame, f_center=fc_eff, bw=bw_xdb)
    power_dbm = float(total_bw_dbm) if not np.isneginf(total_bw_dbm) else float("-inf")
    total_ch_dbm = measure_channel_power(frame, f_center=fc_eff, bw=obw_hz)
    channel_power_dbm = float(total_ch_dbm) if not np.isneginf(total_ch_dbm) else float("-inf")
    snr_dict = compute_snr(frame, [pk])
    snr_db = float(snr_dict.get(pk, float("nan")))
    return {
        "fc_hz": fc_eff,
        "power_dbm": power_dbm,
        "bandwidth_xdb_hz": bw_xdb,
        "obw_hz": obw_hz,
        "channel_power_dbm": channel_power_dbm,
        "snr_db": snr_db,
    }
