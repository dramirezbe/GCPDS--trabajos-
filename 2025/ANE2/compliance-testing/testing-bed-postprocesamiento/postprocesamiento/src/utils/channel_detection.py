import numpy as np
from .noise_floor import detect_noise_floor_from_psd

def contiguous_regions(mask: np.ndarray):
    """
    Devuelve lista de (start_idx, end_idx) para regiones True contiguas.
    """
    mask = np.asarray(mask, dtype=bool)

    regions = []
    in_region = False
    start = None

    for i, v in enumerate(mask):
        if v and not in_region:
            in_region = True
            start = i
        elif (not v) and in_region:
            regions.append((start, i - 1))
            in_region = False
            start = None

    if in_region and start is not None:
        regions.append((start, len(mask) - 1))

    return regions




def merge_and_filter_regions(
    freqs_hz: np.ndarray,
    regions_idx,
    merge_gap_hz: float = 10e3,
    min_bw_hz: float = 10e3
):
    """
    Une regiones si el gap entre ellas es < merge_gap_hz
    y elimina regiones con BW < min_bw_hz.
    """
    if not regions_idx:
        return np.array([]), np.array([]), []

    merged_regions = [regions_idx[0]]

    for curr_start, curr_end in regions_idx[1:]:
        prev_start, prev_end = merged_regions[-1]

        gap_hz = freqs_hz[curr_start] - freqs_hz[prev_end]

        if gap_hz < merge_gap_hz:
            merged_regions[-1] = (prev_start, curr_end)
        else:
            merged_regions.append((curr_start, curr_end))

    filtered_regions = []
    bandwidths = []
    centers = []

    for start_idx, end_idx in merged_regions:
        f_start = freqs_hz[start_idx]
        f_end = freqs_hz[end_idx]
        bw = f_end - f_start

        if bw >= min_bw_hz:
            fc = 0.5 * (f_start + f_end)
            filtered_regions.append((start_idx, end_idx))
            bandwidths.append(bw)
            centers.append(fc)

    if not filtered_regions:
        return np.array([]), np.array([]), []

    return np.array(bandwidths), np.array(centers), filtered_regions


def detect_channels_from_psd(
    freqs_hz: np.ndarray,
    Pxx_dB: np.ndarray,
    noise_floor_db: float,
    delta_above_nf_db: float = 3.0,
    merge_gap_hz: float = 10e3,
    min_bw_hz: float = 10e3
):
    """
    Detección con piso de ruido escalar (global).
    """
    freqs_hz = np.asarray(freqs_hz, dtype=float)
    Pxx_dB = np.asarray(Pxx_dB, dtype=float)

    if freqs_hz.size == 0 or Pxx_dB.size == 0:
        raise ValueError("Vectores vacíos: no se puede detectar canales.")

    if freqs_hz.size != Pxx_dB.size:
        raise ValueError("freqs_hz y Pxx_dB deben tener la misma longitud.")

    threshold = noise_floor_db + delta_above_nf_db
    mask = Pxx_dB >= threshold

    if not np.any(mask):
        return np.array([]), np.array([]), []

    initial_regions = contiguous_regions(mask)
    return merge_and_filter_regions(
        freqs_hz=freqs_hz,
        regions_idx=initial_regions,
        merge_gap_hz=merge_gap_hz,
        min_bw_hz=min_bw_hz
    )


def detect_channels_from_variable_threshold(
    freqs_hz: np.ndarray,
    Pxx_dB: np.ndarray,
    threshold_dB: np.ndarray,
    merge_gap_hz: float = 10e3,
    min_bw_hz: float = 10e3
):
    """
    Detección con umbral variable punto a punto, pero construido por steps.
    """
    freqs_hz = np.asarray(freqs_hz, dtype=float)
    Pxx_dB = np.asarray(Pxx_dB, dtype=float)
    threshold_dB = np.asarray(threshold_dB, dtype=float)

    if freqs_hz.size == 0 or Pxx_dB.size == 0 or threshold_dB.size == 0:
        raise ValueError("Vectores vacíos: no se puede detectar canales.")

    if not (freqs_hz.size == Pxx_dB.size == threshold_dB.size):
        raise ValueError("freqs_hz, Pxx_dB y threshold_dB deben tener la misma longitud.")

    mask = Pxx_dB >= threshold_dB

    if not np.any(mask):
        return np.array([]), np.array([]), []

    initial_regions = contiguous_regions(mask)
    return merge_and_filter_regions(
        freqs_hz=freqs_hz,
        regions_idx=initial_regions,
        merge_gap_hz=merge_gap_hz,
        min_bw_hz=min_bw_hz
    )