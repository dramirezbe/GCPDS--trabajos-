import numpy as np

def detect_noise_floor_from_psd(
    Pxx,
    delta_dB: float = 1.0,
    noise_percentile: float = 40.0,
    min_points_after_filter: int = 20
) -> float:
    """
    Detecta el piso de ruido en una PSD (en dB) usando:
    1) Filtro por percentil para descartar potencias altas (señales/emisiones).
    2) Búsqueda de la ventana en dB con mayor densidad (modo aproximado).
    """
    Pxx = np.asarray(Pxx, dtype=float)

    if Pxx.size == 0:
        raise ValueError("PSD vacía, no se puede detectar piso de ruido.")

    cutoff = np.percentile(Pxx, noise_percentile)
    candidates = Pxx[Pxx <= cutoff]

    if candidates.size < min_points_after_filter:
        candidates = Pxx

    Pmin = np.min(candidates)
    Pmax = np.max(candidates)

    centers = np.arange(Pmin + delta_dB / 2.0, Pmax + delta_dB / 2.0, delta_dB / 2.0)
    results = []

    for c in centers:
        lower = c - delta_dB / 2.0
        upper = c + delta_dB / 2.0

        segment = candidates[(candidates >= lower) & (candidates < upper)]
        if segment.size == 0:
            continue

        results.append({
            "center_dB": c,
            "count": int(segment.size),
        })

    if not results:
        raise RuntimeError("No se generaron histogramas válidos tras el filtrado.")

    best_segment = max(results, key=lambda x: x["count"])
    return float(best_segment["center_dB"])