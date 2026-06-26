import os
import json
import numpy as np
import matplotlib.pyplot as plt


def read_psd_json(json_path: str):
    """
    Lee un JSON con PSD y metadata, y retorna:
      - record_id
      - freqs_hz
      - pxx_dbm
      - etiquetas
      - metadata
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    record_id = data.get("id", os.path.basename(json_path))

    if "psd" not in data or "pxx" not in data["psd"]:
        raise ValueError(f"El JSON no contiene 'psd.pxx': {json_path}")

    if "metadata" not in data:
        raise ValueError(f"El JSON no contiene 'metadata': {json_path}")

    metadata = data["metadata"]
    etiquetas = data.get("etiquetas", {})

    pxx_dbm = np.asarray(data["psd"]["pxx"], dtype=float)

    if pxx_dbm.size < 2:
        raise ValueError(f"Muy pocos puntos en PSD para procesar: {json_path}")

    fmin = metadata.get("frecuencia_min_hz", None)
    fmax = metadata.get("frecuencia_max_hz", None)

    if fmin is None or fmax is None:
        raise ValueError(f"Faltan frecuencia_min_hz o frecuencia_max_hz en metadata: {json_path}")

    fmin = float(fmin)
    fmax = float(fmax)

    freqs_hz = np.linspace(fmin, fmax, num=pxx_dbm.size)

    return record_id, freqs_hz, pxx_dbm, etiquetas, metadata


def plot_psd_result(
    json_name: str,
    freqs_hz: np.ndarray,
    pxx_dbm: np.ndarray,
    pxx_smooth_dbm: np.ndarray,
    noise_floor,
    threshold,
    centers_hz: np.ndarray,
    regions_idx,
    etiquetas: dict | None = None,
    local_nf_info: list | None = None,
    show_expanded_windows: bool = True,
    global_threshold_db: float | None = None
):
    plt.figure(figsize=(14, 6))

    plt.plot(freqs_hz / 1e6, pxx_dbm, linewidth=0.8, alpha=0.40, label="PSD original")
    plt.plot(freqs_hz / 1e6, pxx_smooth_dbm, linewidth=1.2, label="PSD suavizada")

    noise_floor_arr = np.asarray(noise_floor) if np.ndim(noise_floor) > 0 else None
    threshold_arr = np.asarray(threshold) if np.ndim(threshold) > 0 else None

    if noise_floor_arr is not None and noise_floor_arr.size == len(freqs_hz):
        plt.plot(freqs_hz / 1e6, noise_floor_arr, linewidth=1.5, label="Noise floor step")
    else:
        plt.axhline(float(noise_floor), linestyle="--", linewidth=1.2, label="Noise floor global")

    if threshold_arr is not None and threshold_arr.size == len(freqs_hz):
        plt.plot(freqs_hz / 1e6, threshold_arr, linewidth=1.5, label="Threshold step (NF + Δ)")
    else:
        plt.axhline(float(threshold), linestyle="--", linewidth=1.2, label="Threshold global (NF + Δ)")

    for (s, e) in regions_idx:
        plt.axvspan(freqs_hz[s] / 1e6, freqs_hz[e] / 1e6, alpha=0.18)

    if local_nf_info and show_expanded_windows:
        for info in local_nf_info:
            s_exp = info["start_exp_idx"]
            e_exp = info["end_exp_idx"]
            plt.axvspan(
                freqs_hz[s_exp] / 1e6,
                freqs_hz[e_exp] / 1e6,
                alpha=0.08,
                hatch=None
            )

    if global_threshold_db is not None:
        plt.axhline(
            global_threshold_db,
            linestyle=":",
            linewidth=1.5,
            label="Threshold inicial (global)"
        )

    if len(centers_hz) > 0:
        y_centers = np.interp(centers_hz, freqs_hz, pxx_smooth_dbm)
        plt.scatter(centers_hz / 1e6, y_centers, s=25, label="Centros detectados")

    if etiquetas is not None:
        fc_true = etiquetas.get("frecuencias_centrales_hz", [])
        if fc_true:
            fc_true = np.asarray(fc_true, dtype=float)
            y_true = np.interp(fc_true, freqs_hz, pxx_smooth_dbm, left=np.nan, right=np.nan)
            plt.scatter(fc_true / 1e6, y_true, marker="x", s=60, label="Fc etiqueta")

    plt.xlabel("Frecuencia (MHz)")
    plt.ylabel("Potencia (dBm)")
    plt.title(f"PSD + noise floor step + detección final\n{json_name}")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.show()
