import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
import requests
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import numpy as np
from types import MethodType

from api_dane_from_coords_via_tunnel import full_example_dane_tunnel

# --- Constants ---
BASE_API = "127.0.0.1"
BASE_EP = "analyze"

JEISSON_PORT = 8000
OSCAR_PORT = 8001

JEISSON_URL = f"http://{BASE_API}:{JEISSON_PORT}/{BASE_EP}"
OSCAR_URL = f"http://{BASE_API}:{OSCAR_PORT}/{BASE_EP}"

DEFAULT_THRESHOLD = 5
DEFAULT_LIC_CSV = (
    Path(__file__).resolve().parent.parent
    / "postprocesamiento.backup-20260420-165829"
    / "consolidado_bbdd_asignación.csv"
)

FOLDER_RESPONSES_JEISSON_API = Path(__file__).resolve().parent / "responses_jeisson_api_no_compliance"
FOLDER_RESPONSES_JEISSON_API.mkdir(exist_ok=True)
print(f"Responses from JEISSON API will be saved in: {FOLDER_RESPONSES_JEISSON_API.resolve()}")

#== Helper Functions ==#
def _human_timestamp(iso_string):
    try:
        if not isinstance(iso_string, str) or not iso_string:
            return "N/A"
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        return f"Error in format ISO timestamp: {e}"


def _iso_to_unix_ms(iso_string):
    if not isinstance(iso_string, str) or not iso_string:
        return None

    normalized = iso_string.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    dt = datetime.fromisoformat(normalized)
    return int(dt.timestamp() * 1000)
    
def _parse_json_file(file_path: str, verbose: bool = True) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    def _vprint(message: str) -> None:
        if verbose:
            print(message)

    # Top-level sections
    psd = data.get("psd", {})
    labels = data.get("etiquetas", {})   # <-- top-level, not inside psd
    metadata = data.get("metadata", {})

    # Basic identifiers
    inner_name = data.get("id")
    _vprint(f"Inner Name: {inner_name if inner_name else 'N/A'}")

    # PSD data
    pxx = psd.get("pxx", [])  # already a Python list
    _vprint(f"PSD Pxx Values: {pxx[:5] if pxx else 'N/A'}")

    psd_len = psd.get("longitud")
    psd_len = int(psd_len) if psd_len is not None else None
    _vprint(f"PSD Length: {psd_len if psd_len is not None else 'N/A'}")

    # Reference labels (all label-derived variables use reference_*)
    reference_num_emisiones = labels.get("num_emisiones")
    _vprint(
        f"Reference Number of Emissions: "
        f"{reference_num_emisiones if reference_num_emisiones is not None else 'N/A'}"
    )

    reference_frecuencias_centrales_hz = labels.get("frecuencias_centrales_hz", [])
    _vprint(
        "Reference Central Frequencies (Hz): "
        f"{reference_frecuencias_centrales_hz if reference_frecuencias_centrales_hz else 'N/A'}"
    )

    reference_anchos_banda_hz = labels.get("anchos_banda_hz", [])
    _vprint(
        "Reference Bandwidths (Hz): "
        f"{reference_anchos_banda_hz if reference_anchos_banda_hz else 'N/A'}"
    )

    reference_noise_floor = labels.get("noise_floor_dbm")
    _vprint(
        "Reference Noise Floor (dBm): "
        f"{reference_noise_floor if reference_noise_floor is not None else 'N/A'}"
    )

    # Metadata / frame values
    sensor_name = metadata.get("sensor")
    _vprint(f"Sensor Name: {sensor_name if sensor_name else 'N/A'}")

    timestamp_iso = metadata.get("timestamp")
    date_measure = _human_timestamp(timestamp_iso)
    _vprint(f"Date of Measurement: {date_measure}")

    frame_start_freq_hz = metadata.get("frecuencia_min_hz")
    _vprint(
        "Frame Start Frequency (Hz): "
        f"{frame_start_freq_hz if frame_start_freq_hz is not None else 'N/A'}"
    )

    frame_end_freq_hz = metadata.get("frecuencia_max_hz")
    _vprint(
        "Frame End Frequency (Hz): "
        f"{frame_end_freq_hz if frame_end_freq_hz is not None else 'N/A'}"
    )

    try:
        frame_timestamp_unix_ms = _iso_to_unix_ms(timestamp_iso)
    except ValueError:
        frame_timestamp_unix_ms = None

    reference_latitud = metadata.get("latitud")
    _vprint(f"Reference Latitude: {reference_latitud if reference_latitud is not None else 'N/A'}")

    reference_longitud = metadata.get("longitud")
    _vprint(f"Reference Longitude: {reference_longitud if reference_longitud is not None else 'N/A'}")

    reference_altitud_m = metadata.get("altitud_m")
    _vprint(f"Reference Altitude (m): {reference_altitud_m if reference_altitud_m is not None else 'N/A'}")

    reference_num_puntos = metadata.get("num_puntos")
    _vprint(f"Reference Number of Points: {reference_num_puntos if reference_num_puntos is not None else 'N/A'}")

    reference_frecuencia_min_hz = metadata.get("frecuencia_min_hz")
    _vprint(
        "Reference Minimum Frequency (Hz): "
        f"{reference_frecuencia_min_hz if reference_frecuencia_min_hz is not None else 'N/A'}"
    )

    reference_frecuencia_max_hz = metadata.get("frecuencia_max_hz")
    _vprint(
        "Reference Maximum Frequency (Hz): "
        f"{reference_frecuencia_max_hz if reference_frecuencia_max_hz is not None else 'N/A'}"
    )

    reference_potencia_min_dbm = metadata.get("potencia_min_dbm")
    _vprint(
        "Reference Minimum Power (dBm): "
        f"{reference_potencia_min_dbm if reference_potencia_min_dbm is not None else 'N/A'}"
    )

    reference_potencia_max_dbm = metadata.get("potencia_max_dbm")
    _vprint(
        "Reference Maximum Power (dBm): "
        f"{reference_potencia_max_dbm if reference_potencia_max_dbm is not None else 'N/A'}"
    )

    reference_rbw_hz = metadata.get("rbw_hz")
    _vprint(f"Reference RBW (Hz): {reference_rbw_hz if reference_rbw_hz is not None else 'N/A'}")

    parsed_info = {
        "file_name": Path(file_path).name,
        "inner_name": inner_name,
        "frame": {
            "Pxx": pxx,
            "start_freq_hz": frame_start_freq_hz,
            "end_freq_hz": frame_end_freq_hz,
            "timestamp_iso": timestamp_iso,
            "timestamp": frame_timestamp_unix_ms,
        },
        "psd": {
            "pxx_values": pxx,
            "pxx_preview": pxx[:5] if pxx else [],
            "length": psd_len,
        },
        "reference": {
            "num_emisiones": reference_num_emisiones,
            "frecuencias_centrales_hz": reference_frecuencias_centrales_hz,
            "anchos_banda_hz": reference_anchos_banda_hz,
            "noise_floor_dbm": reference_noise_floor,
            "latitud": reference_latitud,
            "longitud": reference_longitud,
            "altitud_m": reference_altitud_m,
            "num_puntos": reference_num_puntos,
            "frecuencia_min_hz": reference_frecuencia_min_hz,
            "frecuencia_max_hz": reference_frecuencia_max_hz,
            "potencia_min_dbm": reference_potencia_min_dbm,
            "potencia_max_dbm": reference_potencia_max_dbm,
            "rbw_hz": reference_rbw_hz,
        },
        "metadata": {
            "sensor": sensor_name,
            "timestamp_iso": timestamp_iso,
            "timestamp_human": date_measure,
        },
    }

    return parsed_info

def build_json_api_no_cumpli(dict_measure, threshold, danes):
    frame = dict_measure.get("frame", {})
    return {
        "frame": {
            "Pxx": frame.get("Pxx", []),
            "start_freq_hz": frame.get("start_freq_hz"),
            "end_freq_hz": frame.get("end_freq_hz"),
            "timestamp": frame.get("timestamp"),
        },
        "cumplimiento": 0,
        #"lic": str(DEFAULT_LIC_CSV),
        #"danes": danes or [],
        #"picos": [],
        "umbral_db": threshold,
    }

def build_json_api_cumpli(dict_measure, threshold, danes):
    frame = dict_measure.get("frame", {})
    return {
        "frame": {
            "Pxx": frame.get("Pxx", []),
            "start_freq_hz": frame.get("start_freq_hz"),
            "end_freq_hz": frame.get("end_freq_hz"),
            "timestamp": frame.get("timestamp"),
        },
        "cumplimiento": 1,
        "lic": str(DEFAULT_LIC_CSV),
        "danes": danes or [],
        "picos": [],
        "umbral_db": threshold,
    }


def _post_to_jeisson_api(payload):
    response = requests.post(JEISSON_URL, json=payload, timeout=60)
    if not response.ok:
        detail = None
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise requests.HTTPError(
            f"{response.status_code} Server Error for url: {response.url} | response={detail}",
            response=response,
        )
    return response.json()


def _print_payload_summary(payload):
    frame = payload.get("frame", {})
    pxx = frame.get("Pxx", []) or []
    print("Sending payload to JEISSON API...", flush=True)
    print(f"  url: {JEISSON_URL}", flush=True)
    print(f"  cumplimiento: {payload.get('cumplimiento')}", flush=True)
    print(f"  lic: {payload.get('lic')}", flush=True)
    print(f"  danes_count: {len(payload.get('danes', []) or [])}", flush=True)
    print(f"  pxx_len: {len(pxx)}", flush=True)
    print(f"  start_freq_hz: {frame.get('start_freq_hz')}", flush=True)
    print(f"  end_freq_hz: {frame.get('end_freq_hz')}", flush=True)
    print(f"  timestamp: {frame.get('timestamp')}", flush=True)


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_local_band_limits(freq_axis: np.ndarray, pxx: np.ndarray, center_hz: float, bw_hz: float) -> tuple[float, float]:
    """Encuentra límites más reales de una señal dentro de una ventana bw_hz.

    La idea es evitar que el fill comience en todo el borde del BW nominal si la
    señal arranca un poco después o termina antes.
    """
    if freq_axis.size == 0 or pxx.size == 0 or bw_hz <= 0:
        return center_hz - bw_hz / 2.0, center_hz + bw_hz / 2.0

    left0 = center_hz - bw_hz / 2.0
    right0 = center_hz + bw_hz / 2.0
    window = (freq_axis >= left0) & (freq_axis <= right0)

    if not np.any(window):
        return left0, right0

    idx_window = np.where(window)[0]
    y_win = np.asarray(pxx[idx_window], dtype=float)

    finite = np.isfinite(y_win)
    if not np.any(finite):
        return left0, right0

    y_win = y_win[finite]
    idx_window = idx_window[finite]

    peak_idx_local = idx_window[int(np.argmax(y_win))]
    peak_val = float(pxx[peak_idx_local])

    # Baseline robusta usando los bordes de la ventana.
    edge_len = max(1, min(10, len(idx_window) // 8))
    left_edge = np.asarray(pxx[idx_window[:edge_len]], dtype=float)
    right_edge = np.asarray(pxx[idx_window[-edge_len:]], dtype=float)
    baseline_candidates = np.concatenate([left_edge[np.isfinite(left_edge)], right_edge[np.isfinite(right_edge)]])
    if baseline_candidates.size == 0:
        baseline = float(np.nanmin(y_win))
    else:
        baseline = float(np.nanmedian(baseline_candidates))

    if not np.isfinite(peak_val):
        return left0, right0

    # Umbral relativo: toma el 35% de la altura entre baseline y pico.
    cutoff = baseline + 0.35 * (peak_val - baseline)
    if not np.isfinite(cutoff):
        cutoff = baseline

    # Expandir hacia la izquierda/derecha desde el pico hasta caer bajo cutoff.
    left_idx = peak_idx_local
    while left_idx > idx_window[0] and np.isfinite(pxx[left_idx - 1]) and pxx[left_idx - 1] >= cutoff:
        left_idx -= 1

    right_idx = peak_idx_local
    while right_idx < idx_window[-1] and np.isfinite(pxx[right_idx + 1]) and pxx[right_idx + 1] >= cutoff:
        right_idx += 1

    left_hz = float(freq_axis[left_idx])
    right_hz = float(freq_axis[right_idx])

    # Fallback para evitar bandas degeneradas.
    if right_hz <= left_hz:
        return left0, right0

    return left_hz, right_hz


def _parse_json_API(api_input, source_measure: dict | None = None, verbose: bool = False) -> dict:
    """
    Parsea respuesta de JEISSON API (dict en memoria o path a JSON guardado).
    Estructura observada en ejemplos reales:
    - mode, cumplimiento, num_emissions, umbral, umbral_db, results[]
    - results[] con fc_hz/fc_mhz, bw_hz/bw_khz, power_dbm, status, rni, rni_v_m
    """
    if isinstance(api_input, (str, Path)):
        with open(api_input, "r", encoding="utf-8") as f:
            data = json.load(f)
        source_name = Path(api_input).name
    elif isinstance(api_input, dict):
        data = api_input
        source_name = "in_memory_response"
    else:
        raise TypeError("api_input debe ser dict, str o Path")

    # La API de analyze normalmente NO devuelve Pxx/start/end.
    # Se inyectan desde el JSON original parseado por _parse_json_file si está disponible.
    frame_from_source = (source_measure or {}).get("frame", {})
    frame = {
        "Pxx": frame_from_source.get("Pxx", []),
        "start_freq_hz": frame_from_source.get("start_freq_hz"),
        "end_freq_hz": frame_from_source.get("end_freq_hz"),
        "timestamp": frame_from_source.get("timestamp"),
    }

    results = data.get("results") or []
    emissions = []

    for row in results:
        if not isinstance(row, dict):
            continue

        fc_hz = _safe_float(row.get("fc_hz"))
        if fc_hz is None:
            fc_mhz_alt = _safe_float(row.get("fc_mhz"))
            if fc_mhz_alt is not None:
                fc_hz = fc_mhz_alt * 1e6

        bw_hz = _safe_float(row.get("bw_hz"))
        if bw_hz is None:
            bw_khz_alt = _safe_float(row.get("bw_khz"))
            if bw_khz_alt is not None:
                bw_hz = bw_khz_alt * 1e3

        if fc_hz is None:
            continue

        power_dbm = _safe_float(row.get("power_dbm"))
        emissions.append({
            "fc_hz": fc_hz,
            "fc_mhz": fc_hz / 1e6,
            "bw_hz": bw_hz,
            "bw_khz": (bw_hz / 1e3) if bw_hz is not None else None,
            "power_dbm": power_dbm,
            "rni": _safe_float(row.get("rni")),
            "rni_v_m": _safe_float(row.get("rni_v_m")),
            "status": row.get("status"),
        })

    emissions.sort(key=lambda e: e["fc_hz"])

    parsed = {
        "source_name": source_name,
        "frame": frame,
        "mode": data.get("mode"),
        "cumplimiento": data.get("cumplimiento"),
        "num_emissions": data.get("num_emissions", len(emissions)),
        "umbral_db": _safe_float(data.get("umbral_db")),
        "umbral_abs_dbm": _safe_float(data.get("umbral")),
        "timestamp": data.get("timestamp"),
        "correction_applied": bool(data.get("correction_applied", False)),
        "emissions": emissions,
        "series": {
            "freq_hz": np.array([e["fc_hz"] for e in emissions], dtype=float) if emissions else np.array([], dtype=float),
            "power_dbm": np.array(
                [e["power_dbm"] if e["power_dbm"] is not None else np.nan for e in emissions],
                dtype=float,
            ) if emissions else np.array([], dtype=float),
        },
        "raw": data,
    }

    if verbose:
        print(f"[API PARSE] {parsed['source_name']}: {parsed['num_emissions']} emisiones")
        print(f"[API PARSE] mode={parsed['mode']} cumplimiento={parsed['cumplimiento']}")
        print(f"[API PARSE] umbral_db={parsed['umbral_db']} umbral_abs_dbm={parsed['umbral_abs_dbm']}")

    return parsed


def plot_API_spectrum(
    self,
    dict_api,
    freq_unit="MHz",
    show_bandwidth=True,
    show_threshold=True,
    alpha_band=0.16,
    marker="o",
    **plot_kwargs,
):
    """Grafica emisiones parseadas desde _parse_json_API() sobre un Axes."""
    unit_scale = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
    if freq_unit not in unit_scale:
        raise ValueError("freq_unit must be one of: 'Hz', 'kHz', 'MHz', 'GHz'")

    frame = dict_api.get("frame", {}) or {}
    pxx = np.asarray(frame.get("Pxx", []) or [], dtype=float)
    f_start = _safe_float(frame.get("start_freq_hz"))
    f_end = _safe_float(frame.get("end_freq_hz"))

    emissions = dict_api.get("emissions", [])
    if len(pxx) == 0 and not emissions:
        self.text(0.5, 0.5, "Sin emisiones en respuesta API", ha="center", va="center", transform=self.transAxes)
        self.set_title("API emissions (empty)")
        self.grid(True, alpha=0.3)
        return self

    scale = unit_scale[freq_unit]

    # Si tenemos frame base, dibujamos el espectro real (Pxx) como fondo.
    if len(pxx) > 0 and f_start is not None and f_end is not None:
        freq = np.linspace(f_start, f_end, len(pxx)) / scale
        self.plot(freq, pxx, color="gray", linewidth=0.9, alpha=0.65, label="PSD base (input)")

    x = np.array([e["fc_hz"] / scale for e in emissions], dtype=float) if emissions else np.array([], dtype=float)
    y = np.array([e["power_dbm"] if e["power_dbm"] is not None else np.nan for e in emissions], dtype=float) if emissions else np.array([], dtype=float)
    bw = np.array([e["bw_hz"] / scale if e["bw_hz"] is not None else np.nan for e in emissions], dtype=float) if emissions else np.array([], dtype=float)

    # Picos API por frecuencia (como reference_plot): marcador sin unir puntos
    if emissions:
        default_plot_kwargs = {
            "linestyle": "None",
            "markersize": 6,
            "marker": marker,
            "label": "API peaks",
        }
        default_plot_kwargs.update(plot_kwargs)
        self.plot(x, y, **default_plot_kwargs)

    if show_threshold:
        thr = dict_api.get("umbral_abs_dbm")
        if thr is not None:
            self.axhline(thr, linestyle="--", linewidth=1.2, label=f"API threshold ({thr:.2f} dBm)")

    if show_bandwidth and emissions:
        finite_y = y[np.isfinite(y)]
        if finite_y.size > 0:
            y_min = float(np.nanmin(finite_y))
        elif len(pxx) > 0 and np.isfinite(pxx).any():
            y_min = float(np.nanmin(pxx))
        else:
            y_min = -120.0

        freq_base = None
        if len(pxx) > 0 and f_start is not None and f_end is not None:
            freq_base = np.linspace(f_start, f_end, len(pxx)) / scale

        for i in range(len(x)):
            if np.isfinite(bw[i]) and bw[i] > 0 and np.isfinite(y[i]):
                left = x[i] - bw[i] / 2.0
                right = x[i] + bw[i] / 2.0

                # Igual que reference_plot: si hay PSD base, sombrear el segmento real del espectro
                if freq_base is not None:
                    left_real, right_real = _find_local_band_limits(freq_base, pxx, x[i], bw[i])
                    mask = (freq_base >= left_real) & (freq_base <= right_real)
                    if np.any(mask):
                        self.fill_between(
                            freq_base[mask],
                            pxx[mask],
                            y_min,
                            alpha=alpha_band,
                            label="API BW" if i == 0 else None,
                        )
                        self.axvline(left_real, linestyle=":", linewidth=1)
                        self.axvline(right_real, linestyle=":", linewidth=1)
                    else:
                        self.fill_between(
                            [left, right],
                            [y_min, y_min],
                            [y[i], y[i]],
                            alpha=alpha_band,
                            label="API BW" if i == 0 else None,
                        )
                else:
                    self.fill_between(
                        [left, right],
                        [y_min, y_min],
                        [y[i], y[i]],
                        alpha=alpha_band,
                        label="API BW" if i == 0 else None,
                    )

    self.set_xlabel(f"Frequency ({freq_unit})")
    self.set_ylabel("Power (dBm)")
    self.set_title(f"API spectrum | mode={dict_api.get('mode')} | n={dict_api.get('num_emissions')}")
    self.grid(True, alpha=0.3)

    handles, labels = self.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    self.legend(unique.values(), unique.keys())
    return self


#=========Plotting context=========

def plot_reference_spectrum(
    self,
    dict_measure,
    show_peaks=True,
    show_bandwidth=True,
    show_noise_floor=True,
    freq_unit="MHz",
    alpha_band=0.18,
    peak_marker="x",
    **plot_kwargs,
):
    """
    Plot PSD spectrum with reference overlays on an existing matplotlib Axes.

    Parameters
    ----------
    self : matplotlib.axes.Axes
        Axes instance (automatically passed when used as ax.plot_reference_spectrum)
    dict_measure : dict
        Parsed measurement dictionary.
    show_peaks : bool
        Whether to mark reference central frequencies.
    show_bandwidth : bool
        Whether to shade the reference bandwidth regions.
    show_noise_floor : bool
        Whether to draw the reference noise floor.
    freq_unit : str
        "Hz", "kHz", "MHz", or "GHz".
    alpha_band : float
        Transparency for bandwidth shading.
    peak_marker : str
        Marker for central frequencies.
    plot_kwargs : dict
        Extra kwargs forwarded to ax.plot for the PSD line.
    """

    # --- Extract data safely ---
    pxx = np.asarray(dict_measure["psd"]["pxx_values"], dtype=float)
    n = dict_measure["psd"]["length"]

    if n is None:
        n = len(pxx)

    start_freq = float(dict_measure["frame"]["start_freq_hz"])
    end_freq = float(dict_measure["frame"]["end_freq_hz"])

    centers = np.asarray(
        dict_measure["reference"].get("frecuencias_centrales_hz", []),
        dtype=float
    )
    bandwidths = np.asarray(
        dict_measure["reference"].get("anchos_banda_hz", []),
        dtype=float
    )
    noise_floor = dict_measure["reference"].get("noise_floor_dbm")

    # --- Frequency axis ---
    freq = np.linspace(start_freq, end_freq, n)

    # --- Unit scaling ---
    unit_scale = {
        "Hz": 1.0,
        "kHz": 1e3,
        "MHz": 1e6,
        "GHz": 1e9,
    }
    if freq_unit not in unit_scale:
        raise ValueError("freq_unit must be one of: 'Hz', 'kHz', 'MHz', 'GHz'")

    scale = unit_scale[freq_unit]
    freq_plot = freq / scale
    centers_plot = centers / scale
    bandwidths_plot = bandwidths / scale

    # --- Main PSD line ---
    default_plot_kwargs = {"label": "PSD"}
    default_plot_kwargs.update(plot_kwargs)
    self.plot(freq_plot, pxx, **default_plot_kwargs)

    # --- Noise floor ---
    if show_noise_floor and noise_floor is not None:
        self.axhline(
            y=noise_floor,
            linestyle="--",
            linewidth=1.2,
            label=f"Noise floor ({noise_floor:.1f} dBm)"
        )

    # --- Bandwidth regions + center markers ---
    for i, center in enumerate(centers_plot):
        bw = bandwidths_plot[i] if i < len(bandwidths_plot) else 0.0
        left = center - bw / 2
        right = center + bw / 2

        # Peak value estimated from PSD at closest frequency bin
        idx = np.argmin(np.abs(freq_plot - center))
        y_peak = pxx[idx]

        if show_bandwidth and bw > 0:
            mask = (freq_plot >= left) & (freq_plot <= right)
            self.fill_between(
                freq_plot[mask],
                pxx[mask],
                np.min(pxx),
                alpha=alpha_band,
                label="Reference BW" if i == 0 else None
            )

            # Optional vertical bounds
            self.axvline(left, linestyle=":", linewidth=1)
            self.axvline(right, linestyle=":", linewidth=1)

        if show_peaks:
            self.plot(
                center,
                y_peak,
                marker=peak_marker,
                markersize=8,
                linestyle="None",
                label="Reference center" if i == 0 else None
            )

            # Optional annotation
            self.annotate(
                f"{center:.3f} {freq_unit}",
                xy=(center, y_peak),
                xytext=(5, 8),
                textcoords="offset points",
                fontsize=8
            )

    # --- Labels / formatting ---
    self.set_xlabel(f"Frequency ({freq_unit})")
    self.set_ylabel("Power (dBm)")
    self.set_title("Spectrum with reference overlays")
    self.grid(True, alpha=0.3)

    # avoid duplicated legend entries
    handles, labels = self.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    self.legend(unique.values(), unique.keys())

    return self

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Process a folder with JSON files and send payloads to JEISSON API. "
            "Supports both positional args and short flags."
        )
    )
    # Compatibilidad hacia atrás (posicionales)
    parser.add_argument("folder_pos", nargs="?", type=Path, help="[legacy] Folder path")
    parser.add_argument("threshold_pos", nargs="?", type=float, help="[legacy] Threshold value")
    parser.add_argument("cumpli_pos", nargs="?", type=int, help="[legacy] Cumplimiento flag (0/1)")

    # Forma recomendada (flags cortas/largas)
    parser.add_argument(
        "-r", "--folder",
        dest="folder_opt",
        type=Path,
        help="Path to folder containing .json files"
    )
    parser.add_argument(
        "-t", "--threshold",
        dest="threshold_opt",
        type=float,
        default=None,
        help=f"Detection threshold (default: {DEFAULT_THRESHOLD})"
    )
    parser.add_argument(
        "-c", "--cumpli",
        dest="cumpli_opt",
        type=int,
        choices=[0, 1],
        default=None,
        help="Cumplimiento flag: 1=compliance, 0=no compliance (default: 0)"
    )
    args = parser.parse_args()

    target_folder = args.folder_opt or args.folder_pos
    threshold = args.threshold_opt if args.threshold_opt is not None else args.threshold_pos
    cumpli = args.cumpli_opt if args.cumpli_opt is not None else args.cumpli_pos

    if target_folder is None:
        parser.error("Debes indicar carpeta con -r/--folder (o posicional legacy).")

    if threshold is None:
        threshold = DEFAULT_THRESHOLD
        print(f"No threshold provided. Using default value: {threshold}")

    if cumpli is None:
        cumpli = 0
        print(f"No cumplimiento flag provided. Using default value: {cumpli}")

    if int(cumpli) not in (0, 1):
        parser.error("cumpli debe ser 0 o 1")

    if not target_folder.exists():
        print(f"Error: The path '{target_folder}' does not exist.")
        sys.exit(1)
    if not target_folder.is_dir():
        print(f"Error: The path '{target_folder}' is not a directory.")
        sys.exit(1)

    if int(cumpli) == 1:
        with_cumpli = True
        print("Payloads will be marked as compliant (cumplimiento=1).")
    else:        
        with_cumpli = False
        print("Payloads will be marked as non-compliant (cumplimiento=0).")

    print(f"Successfully accessed folder: {target_folder.resolve()}\n")
    
    #Bogota
    lat, lon = 4.6775, -74.0541
    dane_codes = full_example_dane_tunnel(lat, lon)
    print(f"DANE Codes for coordinates ({lat}, {lon}): {dane_codes}\n")
    
    json_files = list(target_folder.glob("*.json"))
    if not json_files:
        print("No .json files found in this directory.")
        return {}
    


    for file_path in json_files:
        print()
        print()
        print(f"--- File: {file_path.name} ---")
        measure_dict = _parse_json_file(file_path, verbose=False)

        if with_cumpli:
            api_payload = build_json_api_cumpli(measure_dict, threshold, dane_codes)
        else:
            api_payload = build_json_api_no_cumpli(measure_dict, threshold, dane_codes)
        _print_payload_summary(api_payload)

        api_dict = None

        try:
            api_response = _post_to_jeisson_api(api_payload)
            print("JEISSON API response received.", flush=True)
            #print(json.dumps(api_response, indent=2, ensure_ascii=False))

            # ---- SAVE PRETTY JSON ----
            output_file = FOLDER_RESPONSES_JEISSON_API / f"{file_path.stem}_response.json"

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(api_response, f, indent=2, ensure_ascii=False)

            print(f"Saved response to: {output_file}")

            # Parseo del JSON real devuelto por la API
            api_dict = _parse_json_API(api_response, source_measure=measure_dict, verbose=True)
        except requests.RequestException as e:
            print(f"\nError sending payload to JEISSON API: {e}")

        _, axs = plt.subplots(2, 1, figsize=(12, 8), sharex=False)
        # Bind de la función a cada Axes
        axs[0].plot_reference_spectrum = MethodType(plot_reference_spectrum, axs[0])
        axs[1].plot_API_spectrum = MethodType(plot_API_spectrum, axs[1])

        # Arriba: referencia del JSON etiquetado
        axs[0].plot_reference_spectrum(measure_dict, color="tab:blue", linewidth=1.5)

        # Abajo: respuesta real de API parseada
        if api_dict is not None:
            axs[1].plot_API_spectrum(api_dict, color="tab:orange", linewidth=1.3, marker="o")
        else:
            axs[1].text(
                0.5,
                0.5,
                "Sin respuesta API para graficar",
                ha="center",
                va="center",
                transform=axs[1].transAxes,
            )
            axs[1].set_title("API spectrum (no data)")
            axs[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    main()
