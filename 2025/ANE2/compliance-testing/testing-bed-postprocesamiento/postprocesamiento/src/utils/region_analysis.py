import numpy as np
from .signal_processing import find_local_minima_indices, estimate_local_trend
from .noise_floor import detect_noise_floor_from_psd

def get_adaptive_valley_height_ratio(
    local_idx: int,
    n_points: int,
    left_section_ratio: float = 0.15,
    center_section_ratio: float = 0.60,
    right_section_ratio: float = 0.15,
    lateral_valley_height_ratio: float = 0.05,
    center_valley_height_ratio: float = 0.20
):
    """
    Devuelve el ratio de altura permitido para un valle según su posición
    dentro de la emisión.

    Segmentación:
    - lateral izquierdo : left_section_ratio
    - centro            : center_section_ratio
    - lateral derecho   : right_section_ratio

    Umbrales:
    - laterales -> lateral_valley_height_ratio
    - centro    -> center_valley_height_ratio
    """
    if n_points <= 1:
        return center_valley_height_ratio, "center"

    total_ratio = left_section_ratio + center_section_ratio + right_section_ratio
    if total_ratio <= 0:
        raise ValueError("La suma de ratios de sección debe ser positiva.")

    left_r = left_section_ratio / total_ratio
    center_r = center_section_ratio / total_ratio
    right_r = right_section_ratio / total_ratio

    pos_ratio = local_idx / max(n_points - 1, 1)

    left_limit = left_r
    center_limit = left_r + center_r

    if pos_ratio < left_limit:
        return lateral_valley_height_ratio, "left"
    elif pos_ratio < center_limit:
        return center_valley_height_ratio, "center"
    else:
        return lateral_valley_height_ratio, "right"



def expand_region_by_factor(
    freqs_hz: np.ndarray,
    start_idx: int,
    end_idx: int,
    expansion_factor: float = 1.1
):
    """
    Expande una región por factor en ancho total.
    Ej: factor=1.1 -> agrega 5% a cada lado aproximadamente.

    La expansión es SOLO para el análisis local del piso de ruido.
    """
    n = len(freqs_hz)

    f_start = freqs_hz[start_idx]
    f_end = freqs_hz[end_idx]
    bw = f_end - f_start

    if n < 2:
        return start_idx, end_idx

    df = np.median(np.diff(freqs_hz))

    bw_eff = max(bw, df)
    extra_total = bw_eff * (expansion_factor - 1.0)
    extra_side = 0.5 * extra_total

    f_start_exp = max(freqs_hz[0], f_start - extra_side)
    f_end_exp = min(freqs_hz[-1], f_end + extra_side)

    start_exp_idx = int(np.searchsorted(freqs_hz, f_start_exp, side="left"))
    end_exp_idx = int(np.searchsorted(freqs_hz, f_end_exp, side="right")) - 1

    start_exp_idx = max(0, min(start_exp_idx, n - 1))
    end_exp_idx = max(0, min(end_exp_idx, n - 1))

    if end_exp_idx < start_exp_idx:
        start_exp_idx, end_exp_idx = start_idx, end_idx

    return start_exp_idx, end_exp_idx


def deduplicate_close_valleys(
    valley_indices,
    valley_values,
    freqs_hz_segment: np.ndarray,
    min_valley_distance_hz: float
):
    """
    Si hay varios valles muy cercanos, conserva el más profundo.
    """
    if not valley_indices:
        return []

    order = np.argsort(valley_values)  # primero los más profundos (menor dB)
    selected = []

    for idx_order in order:
        v_idx = valley_indices[idx_order]
        f_v = freqs_hz_segment[v_idx]

        too_close = False
        for s_idx in selected:
            if abs(f_v - freqs_hz_segment[s_idx]) < min_valley_distance_hz:
                too_close = True
                break

        if not too_close:
            selected.append(v_idx)

    return sorted(selected)


def split_one_region_by_valleys(
    freqs_hz: np.ndarray,
    Pxx_smooth_dB: np.ndarray,
    start_idx: int,
    end_idx: int,
    split_min_bw_hz: float = 1e6,
    lateral_valley_height_ratio: float = 0.05,
    center_valley_height_ratio: float = 0.20,
    left_section_ratio: float = 0.15,
    center_section_ratio: float = 0.60,
    right_section_ratio: float = 0.15,
    min_shoulder_drop_db: float = 1.5,
    min_valley_distance_hz: float = 100e3,
    min_edge_margin_hz: float = 50e3,
    min_bw_hz: float = 10e3
):
    """
    Revisa una región ancha y decide si debe partirse por uno o varios valles internos.

    Nueva lógica:
    - la validación de profundidad del valle es adaptativa según la zona:
        * laterales: umbral más estricto
        * centro   : umbral más permisivo

    Segmentación:
    - lateral izquierdo : 15%
    - centro            : 60%
    - lateral derecho   : 15%

    Umbrales por defecto:
    - laterales: 5% de la altura
    - centro   : 20% de la altura
    """
    freqs_hz = np.asarray(freqs_hz, dtype=float)
    Pxx_smooth_dB = np.asarray(Pxx_smooth_dB, dtype=float)

    f_start = freqs_hz[start_idx]
    f_end = freqs_hz[end_idx]
    bw_hz = float(f_end - f_start)

    info = {
        "original_start_idx": int(start_idx),
        "original_end_idx": int(end_idx),
        "original_bw_hz": bw_hz,
        "analyzed_for_split": False,
        "split_applied": False,
        "num_valid_valleys": 0,
        "valid_valley_global_indices": [],
        "region_height_db": np.nan,
        "candidate_valleys": [],
        "reason": "region_not_analyzed",
        "left_section_ratio": float(left_section_ratio),
        "center_section_ratio": float(center_section_ratio),
        "right_section_ratio": float(right_section_ratio),
        "lateral_valley_height_ratio": float(lateral_valley_height_ratio),
        "center_valley_height_ratio": float(center_valley_height_ratio),
    }

    if bw_hz < split_min_bw_hz:
        info["reason"] = "bw_below_split_threshold"
        return [(start_idx, end_idx)], info

    seg = Pxx_smooth_dB[start_idx:end_idx + 1]
    seg_freqs = freqs_hz[start_idx:end_idx + 1]
    n = len(seg)

    if n < 5:
        info["reason"] = "region_too_short"
        return [(start_idx, end_idx)], info

    info["analyzed_for_split"] = True

    seg_min = float(np.min(seg))
    seg_max = float(np.max(seg))
    seg_height = float(seg_max - seg_min)

    info["region_height_db"] = seg_height

    if seg_height <= 0:
        info["reason"] = "zero_region_height"
        return [(start_idx, end_idx)], info

    df_hz = float(np.median(np.diff(seg_freqs))) if len(seg_freqs) > 1 else 1.0
    min_edge_margin_bins = max(1, int(np.ceil(min_edge_margin_hz / max(df_hz, 1.0))))

    local_minima = find_local_minima_indices(seg)
    if not local_minima:
        info["reason"] = "no_local_minima"
        return [(start_idx, end_idx)], info

    candidate_indices = []
    candidate_values = []

    for v_idx in local_minima:
        if v_idx < min_edge_margin_bins or v_idx > (n - 1 - min_edge_margin_bins):
            continue

        valley_db = float(seg[v_idx])

        left_peak = float(np.max(seg[:v_idx])) if v_idx > 0 else valley_db
        right_peak = float(np.max(seg[v_idx + 1:])) if v_idx < n - 1 else valley_db

        drop_left = left_peak - valley_db
        drop_right = right_peak - valley_db

        local_ratio, zone = get_adaptive_valley_height_ratio(
            local_idx=v_idx,
            n_points=n,
            left_section_ratio=left_section_ratio,
            center_section_ratio=center_section_ratio,
            right_section_ratio=right_section_ratio,
            lateral_valley_height_ratio=lateral_valley_height_ratio,
            center_valley_height_ratio=center_valley_height_ratio
        )

        valley_level_limit = float(seg_min + local_ratio * seg_height)

        valid_by_height = valley_db <= valley_level_limit
        valid_by_shoulders = (drop_left >= min_shoulder_drop_db) and (drop_right >= min_shoulder_drop_db)

        info["candidate_valleys"].append({
            "local_idx": int(v_idx),
            "global_idx": int(start_idx + v_idx),
            "freq_hz": float(seg_freqs[v_idx]),
            "zone": zone,
            "local_height_ratio": float(local_ratio),
            "valley_level_limit_db": float(valley_level_limit),
            "valley_db": valley_db,
            "left_peak_db": left_peak,
            "right_peak_db": right_peak,
            "drop_left_db": float(drop_left),
            "drop_right_db": float(drop_right),
            "valid_by_height": bool(valid_by_height),
            "valid_by_shoulders": bool(valid_by_shoulders),
        })

        if valid_by_height and valid_by_shoulders:
            candidate_indices.append(v_idx)
            candidate_values.append(valley_db)

    if not candidate_indices:
        info["reason"] = "no_valid_valleys"
        return [(start_idx, end_idx)], info

    valid_local_valleys = deduplicate_close_valleys(
        valley_indices=candidate_indices,
        valley_values=candidate_values,
        freqs_hz_segment=seg_freqs,
        min_valley_distance_hz=min_valley_distance_hz
    )

    if not valid_local_valleys:
        info["reason"] = "valid_valleys_deduplicated_to_zero"
        return [(start_idx, end_idx)], info

    split_regions = []
    current_start = start_idx

    for v_local in valid_local_valleys:
        v_global = start_idx + v_local

        left_bw = float(freqs_hz[v_global] - freqs_hz[current_start])
        right_bw_remaining = float(freqs_hz[end_idx] - freqs_hz[v_global + 1]) if (v_global + 1) <= end_idx else 0.0

        if left_bw >= min_bw_hz and right_bw_remaining >= min_bw_hz:
            split_regions.append((current_start, v_global))
            current_start = v_global + 1

    split_regions.append((current_start, end_idx))

    if len(split_regions) <= 1:
        info["reason"] = "no_effective_split"
        return [(start_idx, end_idx)], info

    final_regions = []
    for s_idx, e_idx in split_regions:
        sub_bw = float(freqs_hz[e_idx] - freqs_hz[s_idx])
        if sub_bw >= min_bw_hz:
            final_regions.append((s_idx, e_idx))

    if len(final_regions) <= 1:
        info["reason"] = "split_rejected_by_min_bw"
        return [(start_idx, end_idx)], info

    info["split_applied"] = True
    info["reason"] = "valid_internal_valleys"
    info["num_valid_valleys"] = len(valid_local_valleys)
    info["valid_valley_global_indices"] = [int(start_idx + v) for v in valid_local_valleys]

    return final_regions, info

def split_wide_regions_by_internal_valleys(
    freqs_hz: np.ndarray,
    Pxx_smooth_dB: np.ndarray,
    regions_idx,
    split_min_bw_hz: float = 1e6,
    lateral_valley_height_ratio: float = 0.05,
    center_valley_height_ratio: float = 0.20,
    left_section_ratio: float = 0.15,
    center_section_ratio: float = 0.60,
    right_section_ratio: float = 0.15,
    min_shoulder_drop_db: float = 1.5,
    min_valley_distance_hz: float = 100e3,
    min_edge_margin_hz: float = 50e3,
    min_bw_hz: float = 10e3
):
    """
    Aplica validación final de split por valles internos a todas las regiones finales,
    con umbral adaptativo según la zona de la emisión.
    """
    if not regions_idx:
        return np.array([]), np.array([]), [], []

    refined_regions = []
    split_info = []

    for region_idx, (start_idx, end_idx) in enumerate(regions_idx, start=1):
        subregions, info = split_one_region_by_valleys(
            freqs_hz=freqs_hz,
            Pxx_smooth_dB=Pxx_smooth_dB,
            start_idx=start_idx,
            end_idx=end_idx,
            split_min_bw_hz=split_min_bw_hz,
            lateral_valley_height_ratio=lateral_valley_height_ratio,
            center_valley_height_ratio=center_valley_height_ratio,
            left_section_ratio=left_section_ratio,
            center_section_ratio=center_section_ratio,
            right_section_ratio=right_section_ratio,
            min_shoulder_drop_db=min_shoulder_drop_db,
            min_valley_distance_hz=min_valley_distance_hz,
            min_edge_margin_hz=min_edge_margin_hz,
            min_bw_hz=min_bw_hz
        )
        info["region_idx"] = int(region_idx)
        split_info.append(info)
        refined_regions.extend(subregions)

    bandwidths = []
    centers = []

    for start_idx, end_idx in refined_regions:
        f_start = freqs_hz[start_idx]
        f_end = freqs_hz[end_idx]
        bw = float(f_end - f_start)
        fc = float(0.5 * (f_start + f_end))
        bandwidths.append(bw)
        centers.append(fc)

    return np.asarray(bandwidths), np.asarray(centers), refined_regions, split_info



def find_adaptive_expansion_bins(
    side_segment_dB: np.ndarray,
    initial_region_height_db: float,
    short_window_bins: int = 9,
    long_window_bins: int = 21,
    short_slope_threshold_db_per_bin: float = 0.03,
    long_slope_threshold_db_per_bin: float = 0.01,
    min_rise_ratio_vs_region_height: float = 0.10,
    min_rise_db_abs: float = 0.30,
    confirm_windows: int = 2,
    post_confirm_windows: int = 2,
    min_side_bins: int = 3,
    max_side_bins: int = None
):
    """
    Busca cuántos bins expandir hacia un lado de forma adaptativa y robusta.

    side_segment_dB debe venir ordenado desde el borde de la región hacia afuera:
        - lado izquierdo: PSD[:start_idx][::-1]
        - lado derecho : PSD[end_idx+1:]

    Nueva lógica robusta:
    - Usa ventana corta y ventana larga.
    - La ventana corta detecta repuntes locales.
    - La ventana larga valida si la tendencia global realmente cambió.
    - La subida se mide respecto al mínimo reciente acumulado, no solo
      respecto a la ventana anterior.
    - La parada exige:
        1) evidencia local de subida,
        2) evidencia estructural en escala amplia,
        3) prominencia mínima relativa a la altura de la región inicial,
        4) persistencia posterior.
    """
    seg = np.asarray(side_segment_dB, dtype=float)
    n = seg.size

    debug = {
        "n_available_bins": int(n),
        "short_window_bins": int(short_window_bins),
        "long_window_bins": int(long_window_bins),
        "short_slope_threshold_db_per_bin": float(short_slope_threshold_db_per_bin),
        "long_slope_threshold_db_per_bin": float(long_slope_threshold_db_per_bin),
        "min_rise_ratio_vs_region_height": float(min_rise_ratio_vs_region_height),
        "min_rise_db_abs": float(min_rise_db_abs),
        "confirm_windows": int(confirm_windows),
        "post_confirm_windows": int(post_confirm_windows),
        "min_side_bins": int(min_side_bins),
        "initial_region_height_db": float(initial_region_height_db),
        "scan_history": []
    }

    if n == 0:
        debug["stop_reason"] = "empty_side"
        debug["selected_bins"] = 0
        return 0, debug

    if max_side_bins is None:
        max_side_bins = n
    max_side_bins = int(max(0, min(max_side_bins, n)))

    if max_side_bins == 0:
        debug["stop_reason"] = "max_side_bins_zero"
        debug["selected_bins"] = 0
        return 0, debug

    Ws = int(max(3, min(short_window_bins, max_side_bins)))
    Wl = int(max(Ws, min(long_window_bins, max_side_bins)))

    if max_side_bins < Ws:
        debug["stop_reason"] = "insufficient_bins_for_window"
        debug["selected_bins"] = max_side_bins
        return max_side_bins, debug

    min_rise_db = max(
        float(min_rise_db_abs),
        float(min_rise_ratio_vs_region_height) * max(float(initial_region_height_db), 0.0)
    )

    recent_min_level = np.inf
    short_positive_count = 0

    n_positions = max_side_bins - Ws + 1
    if n_positions <= 0:
        debug["stop_reason"] = "no_positions_to_scan"
        debug["selected_bins"] = max_side_bins
        return max_side_bins, debug

    for pos in range(n_positions):
        w_short = seg[pos:pos + Ws]
        slope_short, level_short = estimate_local_trend(w_short)

        # Ventana larga centrada en la misma zona de avance
        long_end = min(max_side_bins, pos + Wl)
        w_long = seg[pos:long_end]
        slope_long, level_long = estimate_local_trend(w_long)

        recent_min_level = min(recent_min_level, level_short)
        rise_from_recent_min = float(level_short - recent_min_level)

        local_upward = (slope_short >= short_slope_threshold_db_per_bin)
        structural_upward = (slope_long >= long_slope_threshold_db_per_bin)
        relevant_rise = (rise_from_recent_min >= min_rise_db)

        upward_candidate = local_upward and structural_upward and relevant_rise

        if pos >= min_side_bins:
            if upward_candidate:
                short_positive_count += 1
            else:
                short_positive_count = 0

            # Solo si ya hubo confirmación inicial, hacemos validación posterior
            if short_positive_count >= confirm_windows:
                candidate_start_pos = pos - confirm_windows + 1

                persist_ok = True
                for j in range(1, post_confirm_windows + 1):
                    pos_f = pos + j
                    if pos_f > max_side_bins - Ws:
                        break

                    wf_short = seg[pos_f:pos_f + Ws]
                    slope_short_f, level_short_f = estimate_local_trend(wf_short)

                    long_end_f = min(max_side_bins, pos_f + Wl)
                    wf_long = seg[pos_f:long_end_f]
                    slope_long_f, level_long_f = estimate_local_trend(wf_long)

                    rise_f = float(level_short_f - recent_min_level)

                    future_local_upward = (slope_short_f >= short_slope_threshold_db_per_bin)
                    future_structural_upward = (slope_long_f >= long_slope_threshold_db_per_bin)
                    future_relevant_rise = (rise_f >= min_rise_db)

                    if not (future_local_upward or future_structural_upward or future_relevant_rise):
                        persist_ok = False
                        break

                debug["scan_history"].append({
                    "pos": int(pos),
                    "slope_short_db_per_bin": float(slope_short),
                    "slope_long_db_per_bin": float(slope_long),
                    "level_short_db": float(level_short),
                    "level_long_db": float(level_long),
                    "recent_min_level_db": float(recent_min_level),
                    "rise_from_recent_min_db": float(rise_from_recent_min),
                    "local_upward": bool(local_upward),
                    "structural_upward": bool(structural_upward),
                    "relevant_rise": bool(relevant_rise),
                    "upward_candidate": bool(upward_candidate),
                    "positive_count": int(short_positive_count),
                    "persist_ok": bool(persist_ok),
                })

                if persist_ok:
                    selected_bins = max(0, candidate_start_pos)
                    debug["stop_reason"] = "confirmed_structural_upward_trend"
                    debug["selected_bins"] = int(selected_bins)
                    return selected_bins, debug

        debug["scan_history"].append({
            "pos": int(pos),
            "slope_short_db_per_bin": float(slope_short),
            "slope_long_db_per_bin": float(slope_long),
            "level_short_db": float(level_short),
            "level_long_db": float(level_long),
            "recent_min_level_db": float(recent_min_level),
            "rise_from_recent_min_db": float(rise_from_recent_min),
            "local_upward": bool(local_upward),
            "structural_upward": bool(structural_upward),
            "relevant_rise": bool(relevant_rise),
            "upward_candidate": bool(upward_candidate),
            "positive_count": int(short_positive_count),
        })

    debug["stop_reason"] = "full_scan_used"
    debug["selected_bins"] = int(max_side_bins)
    return max_side_bins, debug


def expand_region_adaptively(
    freqs_hz: np.ndarray,
    Pxx_smooth_dB: np.ndarray,
    start_idx: int,
    end_idx: int,
    short_window_bins: int = 9,
    long_window_bins: int = 21,
    short_slope_threshold_db_per_bin: float = 0.03,
    long_slope_threshold_db_per_bin: float = 0.01,
    min_rise_ratio_vs_region_height: float = 0.10,
    min_rise_db_abs: float = 0.30,
    confirm_windows: int = 2,
    post_confirm_windows: int = 2,
    min_side_bins: int = 3,
    max_side_bins: int = None,
    fallback_expansion_factor: float = 1.1
):
    """
    Expande una región de forma adaptativa y asimétrica con criterio robusto
    multiescala y prominencia relativa.
    """
    freqs_hz = np.asarray(freqs_hz, dtype=float)
    Pxx_smooth_dB = np.asarray(Pxx_smooth_dB, dtype=float)

    n = len(freqs_hz)
    debug = {
        "method": "adaptive_trend_expansion_multiscale",
        "left_debug": None,
        "right_debug": None,
        "left_bins": 0,
        "right_bins": 0,
        "fallback_used": False,
    }

    try:
        if n < 2 or start_idx < 0 or end_idx >= n or end_idx < start_idx:
            raise ValueError("Índices o vectores inválidos para expansión adaptativa.")

        original_segment = Pxx_smooth_dB[start_idx:end_idx + 1]
        if original_segment.size == 0:
            raise ValueError("Segmento original vacío.")

        initial_region_height_db = float(np.max(original_segment) - np.min(original_segment))

        left_side = Pxx_smooth_dB[:start_idx][::-1]
        right_side = Pxx_smooth_dB[end_idx + 1:]

        left_bins, left_debug = find_adaptive_expansion_bins(
            side_segment_dB=left_side,
            initial_region_height_db=initial_region_height_db,
            short_window_bins=short_window_bins,
            long_window_bins=long_window_bins,
            short_slope_threshold_db_per_bin=short_slope_threshold_db_per_bin,
            long_slope_threshold_db_per_bin=long_slope_threshold_db_per_bin,
            min_rise_ratio_vs_region_height=min_rise_ratio_vs_region_height,
            min_rise_db_abs=min_rise_db_abs,
            confirm_windows=confirm_windows,
            post_confirm_windows=post_confirm_windows,
            min_side_bins=min_side_bins,
            max_side_bins=max_side_bins
        )

        right_bins, right_debug = find_adaptive_expansion_bins(
            side_segment_dB=right_side,
            initial_region_height_db=initial_region_height_db,
            short_window_bins=short_window_bins,
            long_window_bins=long_window_bins,
            short_slope_threshold_db_per_bin=short_slope_threshold_db_per_bin,
            long_slope_threshold_db_per_bin=long_slope_threshold_db_per_bin,
            min_rise_ratio_vs_region_height=min_rise_ratio_vs_region_height,
            min_rise_db_abs=min_rise_db_abs,
            confirm_windows=confirm_windows,
            post_confirm_windows=post_confirm_windows,
            min_side_bins=min_side_bins,
            max_side_bins=max_side_bins
        )

        start_exp_idx = max(0, start_idx - left_bins)
        end_exp_idx = min(n - 1, end_idx + right_bins)

        if end_exp_idx < start_exp_idx:
            raise RuntimeError("La expansión adaptativa produjo una ventana inválida.")

        debug["left_debug"] = left_debug
        debug["right_debug"] = right_debug
        debug["left_bins"] = int(left_bins)
        debug["right_bins"] = int(right_bins)
        debug["initial_region_height_db"] = float(initial_region_height_db)

        return start_exp_idx, end_exp_idx, debug

    except Exception:
        start_exp_idx, end_exp_idx = expand_region_by_factor(
            freqs_hz=freqs_hz,
            start_idx=start_idx,
            end_idx=end_idx,
            expansion_factor=fallback_expansion_factor
        )
        debug["fallback_used"] = True
        debug["method"] = "fallback_symmetric_expansion"
        return start_exp_idx, end_exp_idx, debug

def apply_step_nf_on_interval(
    step_nf: np.ndarray,
    start_idx: int,
    end_idx: int,
    nf_value: float,
    overlap_policy: str = "max"
):
    """
    Aplica un NF local sobre un intervalo del step.

    overlap_policy:
    - "max": conservador. En solapes conserva el NF más alto
             (menos negativo, umbral más alto).
    - "min": expansivo. En solapes conserva el NF más bajo
             (más negativo, umbral más bajo).
    - "replace": reemplaza directamente el intervalo.
    """
    if start_idx > end_idx:
        return step_nf

    start_idx = max(0, int(start_idx))
    end_idx = min(len(step_nf) - 1, int(end_idx))

    if start_idx > end_idx:
        return step_nf

    current = step_nf[start_idx:end_idx + 1]

    if overlap_policy == "max":
        step_nf[start_idx:end_idx + 1] = np.maximum(current, nf_value)
    elif overlap_policy == "min":
        step_nf[start_idx:end_idx + 1] = np.minimum(current, nf_value)
    elif overlap_policy == "replace":
        step_nf[start_idx:end_idx + 1] = nf_value
    else:
        raise ValueError(f"overlap_policy no válido: {overlap_policy}")

    return step_nf


def build_step_noise_floor(
    freqs_hz: np.ndarray,
    Pxx_smooth_dB: np.ndarray,
    global_noise_floor_db: float,
    initial_regions_idx,
    nf_delta_db: float,
    nf_min_points: int,
    delta_above_nf_db: float,
    refine_percentile: float = 50.0,
    refine_expansion_factor: float = 1.1,
    refine_height_ratio_limit: float = 0.55,
    trend_window_bins: int = 9,
    trend_slope_threshold_db_per_bin: float = 0.03,
    trend_level_rise_threshold_db: float = 0.35,
    trend_confirm_windows: int = 2,
    trend_min_side_bins: int = 3,
    trend_max_side_bins: int = None,
    step_overlap_policy: str = "max"
):
    """
    Construye un piso de ruido por steps con refinamiento local y expansión
    adaptativa/asimétrica por tendencia local.

    Lógica actualizada:
    - Se expande cada región de forma adaptativa por izquierda y derecha.
    - En la ventana expandida se estima un NF local candidato.
    - Se valida si el refinamiento es confiable.
    - Si el refinamiento es válido, el NF local SE APLICA sobre la región
      expandida (no solo sobre la original), permitiendo que el step se ensanche.
    - En caso de solape entre regiones refinadas, se resuelve con una política
      configurable (por defecto "max", conservadora).
    """
    freqs_hz = np.asarray(freqs_hz, dtype=float)
    Pxx_smooth_dB = np.asarray(Pxx_smooth_dB, dtype=float)

    step_nf = np.full_like(Pxx_smooth_dB, fill_value=global_noise_floor_db, dtype=float)
    local_nf_info = []

    if not initial_regions_idx:
        return step_nf, local_nf_info

    for k, (start_idx, end_idx) in enumerate(initial_regions_idx, start=1):
        start_exp_idx, end_exp_idx, expansion_debug = expand_region_adaptively(
            freqs_hz=freqs_hz,
            Pxx_smooth_dB=Pxx_smooth_dB,
            start_idx=start_idx,
            end_idx=end_idx,
            short_window_bins=trend_window_bins,
            long_window_bins=max(2 * trend_window_bins + 1, 15),
            short_slope_threshold_db_per_bin=trend_slope_threshold_db_per_bin,
            long_slope_threshold_db_per_bin=0.01,
            min_rise_ratio_vs_region_height=0.10,
            min_rise_db_abs=trend_level_rise_threshold_db,
            confirm_windows=trend_confirm_windows,
            post_confirm_windows=2,
            min_side_bins=trend_min_side_bins,
            max_side_bins=trend_max_side_bins,
            fallback_expansion_factor=refine_expansion_factor
        )

        local_segment_expanded = Pxx_smooth_dB[start_exp_idx:end_exp_idx + 1]
        original_segment = Pxx_smooth_dB[start_idx:end_idx + 1]

        try:
            local_nf_candidate = detect_noise_floor_from_psd(
                Pxx=local_segment_expanded,
                delta_dB=nf_delta_db,
                noise_percentile=refine_percentile,
                min_points_after_filter=nf_min_points
            )
        except Exception:
            local_nf_candidate = global_noise_floor_db

        local_threshold_candidate = local_nf_candidate + delta_above_nf_db

        seg_min = float(np.min(original_segment))
        seg_max = float(np.max(original_segment))
        seg_height = seg_max - seg_min

        apply_refinement = False
        threshold_position = np.nan
        height_limit = np.nan

        if seg_height > 0:
            threshold_position = local_threshold_candidate - seg_min
            height_limit = refine_height_ratio_limit * seg_height

            if threshold_position < height_limit:
                apply_refinement = True

        if apply_refinement:
            final_local_nf = local_nf_candidate
            final_local_threshold = local_threshold_candidate

            # AQUÍ ESTÁ EL CAMBIO CLAVE:
            # el NF local se aplica sobre la región expandida validada,
            # no solo sobre la región original.
            apply_start_idx = start_exp_idx
            apply_end_idx = end_exp_idx

            step_nf = apply_step_nf_on_interval(
                step_nf=step_nf,
                start_idx=apply_start_idx,
                end_idx=apply_end_idx,
                nf_value=final_local_nf,
                overlap_policy=step_overlap_policy
            )
        else:
            final_local_nf = global_noise_floor_db
            final_local_threshold = global_noise_floor_db + delta_above_nf_db

            # Si no se valida el refinamiento, no se cambia el soporte:
            # se conserva el piso global en esa zona.
            apply_start_idx = start_idx
            apply_end_idx = end_idx

        info = {
            "region_idx": k,
            "start_idx": start_idx,
            "end_idx": end_idx,
            "start_exp_idx": start_exp_idx,
            "end_exp_idx": end_exp_idx,
            "apply_start_idx": apply_start_idx,
            "apply_end_idx": apply_end_idx,
            "f_start_hz": freqs_hz[start_idx],
            "f_end_hz": freqs_hz[end_idx],
            "f_start_exp_hz": freqs_hz[start_exp_idx],
            "f_end_exp_hz": freqs_hz[end_exp_idx],
            "f_apply_start_hz": freqs_hz[apply_start_idx],
            "f_apply_end_hz": freqs_hz[apply_end_idx],
            "seg_min_db": seg_min,
            "seg_max_db": seg_max,
            "seg_height_db": seg_height,
            "local_nf_candidate_db": local_nf_candidate,
            "local_threshold_candidate_db": local_threshold_candidate,
            "threshold_position_db": threshold_position,
            "height_limit_db": height_limit,
            "height_ratio_limit": refine_height_ratio_limit,
            "refinement_applied": apply_refinement,
            "final_local_nf_db": final_local_nf,
            "final_local_threshold_db": final_local_threshold,
            "expansion_method": expansion_debug["method"],
            "left_expansion_bins": expansion_debug["left_bins"],
            "right_expansion_bins": expansion_debug["right_bins"],
            "expansion_fallback_used": expansion_debug["fallback_used"],
            "left_expansion_debug": expansion_debug["left_debug"],
            "right_expansion_debug": expansion_debug["right_debug"],
            "step_overlap_policy": step_overlap_policy,
        }
        local_nf_info.append(info)

    return step_nf, local_nf_info