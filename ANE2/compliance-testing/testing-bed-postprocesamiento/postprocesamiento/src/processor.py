from __future__ import annotations

from typing import Any, Dict, List, Tuple, Union, Optional

import numpy as np
import pandas as pd
import re
import os
import time
from functools import lru_cache

from src.payload_parser import frame_from_payload
from src.simple_detector import detect_emissions as detect_emissions_simple
from src.spectrum_frame import SpectrumFrame
from src.spectral_analysis import (
    detect_peak_bins,
    find_emission_span,
    slice_spectrum_frame,
    measure_emission_parameters,
    estimate_ber_in_band_mqam,
    estimate_noise_floor,
    adaptive_threshold,
    analyze_colombia_broadband,
    analyze_colombia_broadband_segments,
    is_colombia_broadband_frame,
)
from src.power_utils import channel_power_dbm_uniform_bins
from src.calibration_io import comparar_parametros

PayloadInput = Union[Dict[str, Any], List[Any]]  # dict legacy o lista [json,picos,cumplimiento]
DetectorRun = Dict[str, Any]
DetectorSegment = Dict[str, Any]
from .utils import (
    smooth_psd,
    detect_noise_floor_from_psd,
    detect_channels_from_psd,
    split_wide_regions_by_internal_valleys,
    find_adaptive_expansion_bins,
    expand_region_by_factor,
    detect_channels_from_variable_threshold,
    build_step_noise_floor,
)


VERBOSE_PROCESSOR_LOGS = os.environ.get("ANE_VERBOSE_PROCESSOR", "1").lower() not in ("0", "false", "no")


def _proc_log(message: str) -> None:
    if not VERBOSE_PROCESSOR_LOGS:
        return
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[PROCESSOR {stamp}] {message}", flush=True)


def _build_debug_payload(
    step_noise_floor_db: Any,
    step_threshold_db: Any,
) -> Dict[str, Any]:
    return {
        "vector_piso_ruido": np.asarray(step_noise_floor_db, dtype=float).tolist(),
        "vector_umbral_dinamico": np.asarray(step_threshold_db, dtype=float).tolist(),
    }

def unpack_input(inp: PayloadInput) -> Tuple[Dict[str, Any], List[float], int]:
    """Normaliza la entrada.

    Formatos aceptados :
      1) [frame_json, picos_list, cumplimiento]
      2) { ...frame_json..., "picos": [...], "cumplimiento": 0/1 }
    """
    if isinstance(inp, list):
        if len(inp) != 3:
            raise ValueError("Entrada tipo lista debe ser exactamente [json, picos, cumplimiento].")

        frame_json = inp[0]
        picos_raw = inp[1]
        cumplimiento_raw = inp[2]

        if not isinstance(frame_json, dict):
            raise TypeError("El primer elemento debe ser un dict con Pxx/start_freq_hz/end_freq_hz.")

        if picos_raw is None:
            picos_list: List[float] = []
        else:
            if not isinstance(picos_raw, list):
                raise TypeError("El segundo elemento (picos) debe ser una lista o null.")
            picos_list = [float(x) for x in picos_raw]

        try:
            cumplimiento = int(cumplimiento_raw)
        except Exception:
            cumplimiento = 0

        return frame_json, picos_list, cumplimiento

    if isinstance(inp, dict):
        frame_json = inp
        picos_raw = inp.get("picos", [])
        cumplimiento_raw = inp.get("cumplimiento", 0)

        if picos_raw is None:
            picos_list = []
        else:
            if not isinstance(picos_raw, list):
                raise TypeError("La clave 'picos' debe ser lista o null.")
            picos_list = [float(x) for x in picos_raw]

        try:
            cumplimiento = int(cumplimiento_raw)
        except Exception:
            cumplimiento = 0

        return frame_json, picos_list, cumplimiento

    raise TypeError("Entrada inválida. Debe ser dict o lista [json, picos, cumplimiento].")


def route_mode(picos: List[float], cumplimiento: int) -> str:
    """Reglas de enrutamiento:

    - Si llegan picos: modo 'peaks' (NO hace cumplimiento)
    - Si no llegan picos y cumplimiento==1: modo 'compliance'
    - Si no llegan picos y cumplimiento==0: modo 'all_emissions'
    """
    if len(picos) > 0:
        return "peaks"
    if cumplimiento == 1:
        return "compliance"
    return "all_emissions"



@lru_cache(maxsize=8)
def _load_gain_correction_arrays(abs_path: str, mtime: float) -> Tuple[np.ndarray, np.ndarray]:
    """Carga el CSV de corrección una sola vez (solo lectura).

    Se invalida si cambia el mtime del archivo.
    """
    df_corr = pd.read_csv(abs_path)
    df_corr.columns = [c.strip().replace("\ufeff", "") for c in df_corr.columns]
    freq_corr_axis = df_corr["Frecuencia (MHz)"].values.astype(float) * 1e6
    gain_corr_values = df_corr["Error (dB)"].values.astype(float)
    return freq_corr_axis, gain_corr_values


def _get_gain_correction_arrays(corr_csv_path: str) -> Tuple[np.ndarray, np.ndarray]:
    abs_path = os.path.abspath(corr_csv_path)
    try:
        mtime = float(os.path.getmtime(abs_path))
    except OSError:
        mtime = 0.0
    return _load_gain_correction_arrays(abs_path, mtime)

def apply_gain_correction(frame: SpectrumFrame, corr_csv_path: str) -> SpectrumFrame:
    freqs = np.asarray(frame.freq_hz, dtype=float)
    amps = np.asarray(frame.amplitudes_dbm, dtype=float)

    freq_corr_axis, gain_corr_values = _get_gain_correction_arrays(corr_csv_path)

    correction_interpolated = np.interp(freqs, freq_corr_axis, gain_corr_values)
    amps_corr = amps + correction_interpolated

    return SpectrumFrame(
        amplitudes_dbm=amps_corr,
        f_start_hz=float(freqs[0]),
        f_stop_hz=float(freqs[-1]),
        freq_hz=freqs,
        bin_hz=frame.bin_hz,
    )


def pico_to_hz(p: float) -> float:
    """Convierte un pico.

    - Si |p| < 1e6 asume que viene en MHz.
    - Si no, asume Hz.
    """
    if abs(p) < 1e6:
        return float(p) * 1e6
    return float(p)


def nearest_bin(freq_axis_hz: np.ndarray, f_hz: float) -> int:
    return int(np.argmin(np.abs(freq_axis_hz - f_hz)))


def match_margin_hz(pico_hz: float) -> float:
    """Margen para matchear un pico solicitado con un pico detectado.

    Requisito: "30% del pico o 100 kHz, lo que sea mínimo".
    => margin = min(0.30 * |pico_hz|, 100_000)

    Nota: para frecuencias típicas (MHz), casi siempre será 100 kHz.
    """
    return float(min(0.30 * abs(float(pico_hz)), 100_000.0))


def compute_detection_threshold_dbm(
    frame: SpectrumFrame,
    *,
    umbral_db: Optional[float] = None,
    n_sigma_seed: float = 3.5,
) -> Optional[float]:
    """Calcular el umbral absoluto (dBm) realmente usado para detección."""
    try:
        bb = analyze_colombia_broadband_segments(frame, detect_threshold_db=umbral_db)
        bb = bb[0] if isinstance(bb, list) and len(bb) > 0 else None
    except Exception:
        bb = None
    if isinstance(bb, dict) and np.isfinite(float(bb.get("threshold_dbm", np.nan))):
        return float(bb["threshold_dbm"])

    try:
        nf = float(estimate_noise_floor(frame))
    except Exception:
        try:
            y = np.asarray(frame.amplitudes_dbm, dtype=float)
            nf = float(np.median(y))
        except Exception:
            return None

    if umbral_db is not None:
        try:
            x = float(umbral_db)
        except Exception:
            return None
        if not np.isfinite(x):
            return None
        if x < 0.0:
            x = 0.0
        return float(nf + x)

    try:
        thr = float(adaptive_threshold(frame, n_sigma=float(n_sigma_seed)))
        return thr if np.isfinite(thr) else float(nf + 2.0)
    except Exception:
        return float(nf + 2.0)



def _auto_span_margin_db(
    frame: SpectrumFrame,
    peak_idx: int,
    *,
    umbral_db: Optional[float] = None,
    min_margin_db: float = 1.0,
    max_margin_db: float = 6.0,
) -> float:
    """Elegir un margen (dB sobre el piso de ruido) para delimitar el span de una emisión.

    Problema que resuelve:
      - Con margin_db=0.0, en bandas congestionadas (p.ej. FM) el valle entre
        emisoras puede quedar apenas por encima del piso de ruido (≈ NF+0.5..2 dB),
        haciendo que find_emission_span se "coma" varias estaciones y luego el
        cálculo de BW resulte inflado (o inconsistente entre picos).

    Heurística (conservadora):
      - Estimar NF con estimate_noise_floor(frame) (histograma).
      - Tomar SNR = peak_dbm - NF.
      - margin_db = clamp(0.10*SNR, [min_margin_db, max_margin_db]).
      - Si el usuario entregó umbral_db (dB sobre NF), se usa como piso del margen,
        siempre clamped a max_margin_db.

    Importante: NO cambia detect_peak_bins; solo mejora el recorte del span usado
    para medir BW/potencia.
    """
    try:
        y = np.asarray(frame.amplitudes_dbm, dtype=float)
        peak_dbm = float(y[int(peak_idx)])
    except Exception:
        return float(min_margin_db)

    try:
        nf_dbm = float(estimate_noise_floor(frame))
    except Exception:
        try:
            nf_dbm = float(np.median(y))
        except Exception:
            return float(min_margin_db)

    snr_db = float(max(0.0, peak_dbm - nf_dbm))
    margin = float(0.10 * snr_db)
    margin = float(np.clip(margin, float(min_margin_db), float(max_margin_db)))

    return float(margin)

def is_ruido_por_umbral(
    frame: SpectrumFrame,
    idx: int,
    detect_threshold_db: Optional[float] = None,
    n_sigma: float = 1.51,
    min_snr_db: float = 0.5,
) -> Tuple[bool, float, float, float]:
    """Heurística para decidir si ese bin es ruido (umbral).

    Devuelve: (es_ruido, amp_dbm, nf_dbm, thr_seed_dbm)
    """
    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    kernel = np.array([0.25, 0.5, 0.25], dtype=float)
    y_smooth = np.convolve(y, kernel, mode="same")

    nf = float(estimate_noise_floor(frame))
    # Si el usuario define un umbral explícito (dB sobre NF), lo usamos.
    # Si no, conservamos el umbral histórico (adaptive_threshold).
    if detect_threshold_db is not None:
        try:
            x = float(detect_threshold_db)
        except Exception:
            x = None
        if x is None or (not np.isfinite(x)):
            raise ValueError("detect_threshold_db inválido (no finito)")
        if x < 0.0:
            x = 0.0
        thr_seed = nf + x
        min_snr_db = x
    else:
        try:
            thr_seed = float(adaptive_threshold(frame, n_sigma=n_sigma))
        except Exception:
            thr_seed = nf + 2.0

    amp = float(y[idx])
    cond1 = y_smooth[idx] <= thr_seed
    cond2 = (amp - nf) < float(min_snr_db)
    return (cond1 or cond2), amp, nf, thr_seed


def _safe_power_dbm(value: Any) -> Optional[float]:
    """Evita -inf/inf en la salida. NO inventa potencia.

    - Si es finito: devuelve float
    - Si es +-inf / NaN / error: devuelve None
    """
    try:
        v = float(value)
    except Exception:
        return None
    return v if np.isfinite(v) else None



def _select_bw_hz(params: Dict[str, Any]) -> float:
    """Selecciona el BW a reportar/usar para comparación.

    Preferimos OBW (percentil de potencia) porque es más estable en señales
    con mesetas/múltiples picos (p. ej. FM/OFDM). Si OBW no está disponible,
    cae a BW_xdB.
    """
    try:
        obw = float(params.get("obw_hz", 0.0))
        if np.isfinite(obw) and obw > 0.0:
            return float(obw)
    except Exception:
        pass
    try:
        bw = float(params.get("bandwidth_xdb_hz", 0.0))
        return float(bw) if np.isfinite(bw) else 0.0
    except Exception:
        return 0.0


def _bw_compliance_status(
    lic_match: str,
    bw_medido_kHz: Optional[float],
    bw_nominal_kHz: Optional[float],
    delta_bw_kHz: Optional[float],
    bw_margin_khz: float,
) -> Optional[str]:
    """Evalua cumplimiento de BW.

    Regla:
    - Si no hay match de licencia o faltan datos, retorna None.
    - Si BW medido < BW nominal, siempre cumple.
    - En caso contrario, falla solo si el exceso supera la tolerancia.
    """
    if lic_match != "SI" or bw_medido_kHz is None or bw_nominal_kHz is None:
        return None

    try:
        bw_med = float(bw_medido_kHz)
        bw_nom = float(bw_nominal_kHz)
        delta_bw = float(delta_bw_kHz) if delta_bw_kHz is not None else (bw_med - bw_nom)
        margin = float(bw_margin_khz)
    except Exception:
        return None

    if bw_med < bw_nom:
        return "SI"

    return "NO" if abs(delta_bw) > margin else "SI"

def _rni_isotropic_1m_from_power_dbm(power_dbm: Any) -> Dict[str, Any]:
    """Estimar magnitudes de RNI asumiendo radiador isotrópico a 1 m (espacio libre).

    Modelo:
      - Radiación isotrópica (G=1) en esfera de radio r=1 m
      - Densidad de potencia: S = P / (4*pi*r^2)
      - Onda plana (campo lejano): E = sqrt(S * eta0), H = sqrt(S / eta0)
      - eta0 (impedancia espacio libre): 377 ohm

    Nota: power_dbm se interpreta como potencia total (dBm) asociada a la emisión,
    y este cálculo es una aproximación NORMALIZADA (no sustituye un cálculo real de EIRP).
    """
    r_m = 1.0
    eta_ohm = 377.0

    p_dbm = _safe_power_dbm(power_dbm)
    if p_dbm is None:
        return {
            "model": "isotropic_free_space",
            "r_m": r_m,
            "eta_ohm": eta_ohm,
            "p_w": None,
            "s_w_m2": None,
            "e_v_m": None,
            "h_a_m": None,
        }

    # dBm -> W
    p_w = float(10.0 ** ((float(p_dbm) - 30.0) / 10.0))

    # Isotrópico a 1 m: S = P / (4*pi*r^2)
    s = float(p_w / (4.0 * float(np.pi) * (r_m ** 2)))

    # Onda plana en espacio libre: E/H usando eta0
    e = float(np.sqrt(s * eta_ohm))
    h = float(np.sqrt(s / eta_ohm))

    return {
        "model": "isotropic_free_space",
        "r_m": r_m,
        "eta_ohm": eta_ohm,
        "p_w": p_w,
        "s_w_m2": s,
        "e_v_m": e,
        "h_a_m": h,
    }


def _rni_field_dbuv_m_from_power_dbm_and_fc_hz(power_dbm: Any, fc_hz: Any) -> Optional[float]:
    """Estimar E en dBµV/m a partir de potencia (dBm) siguiendo la conversión del documento dbm_EMC.pdf.

    Conversión (modelo de onda plana en espacio libre):
      - eta0 = 377 ohm
      - Ganancia máxima antena: 6 dBi  ->  G = 10^(0.6)
      - Longitud de onda: lambda = c / f
      - Potencia: P[W] = 10^((P_dBm - 30)/10)
      - Campo:
            E[V/m] = sqrt( eta0 * P[W] * 4*pi / ( G * lambda^2 ) )
      - Unidad final:
            E[dBµV/m] = 20*log10(E[V/m]) + 120

    Nota: Esta es una estimación basada en supuestos ideales (condiciones tipo campo lejano).
    """
    try:
        p_dbm = float(power_dbm)
    except Exception:
        return None
    if not np.isfinite(p_dbm):
        return None

    try:
        f_hz = float(fc_hz)
    except Exception:
        return None
    if not np.isfinite(f_hz) or f_hz <= 0.0:
        return None

    # dBm -> W
    p_w = 10.0 ** ((p_dbm - 30.0) / 10.0)

    c = 3.0e8
    lam = c / f_hz
    if not np.isfinite(lam) or lam <= 0.0:
        return None

    eta0 = 377.0
    g_lin = 10.0 ** 0.6  # 6 dBi

    try:
        e_v_m = float(np.sqrt((eta0 * p_w * 4.0 * np.pi) / (g_lin * (lam ** 2))))
    except Exception:
        return None
    if not np.isfinite(e_v_m) or e_v_m <= 0.0:
        return None

    return float(20.0 * np.log10(e_v_m) + 120.0)




def _rni_field_v_m_from_power_dbm_and_fc_hz(power_dbm: Any, fc_hz: Any) -> Optional[float]:
    """Estimar E en V/m a partir de potencia (dBm) siguiendo la conversión del documento dbm_EMC.pdf.

    Usa los mismos supuestos que _rni_field_dbuv_m_from_power_dbm_and_fc_hz, pero retorna E[V/m].
    """
    try:
        p_dbm = float(power_dbm)
        f_hz = float(fc_hz)
    except Exception:
        return None
    if not np.isfinite(p_dbm) or not np.isfinite(f_hz) or f_hz <= 0.0:
        return None

    # dBm -> W
    p_w = 10.0 ** ((p_dbm - 30.0) / 10.0)

    c = 3.0e8
    lam = c / f_hz
    if not np.isfinite(lam) or lam <= 0.0:
        return None

    eta0 = 377.0
    g_lin = 10.0 ** 0.6  # 6 dBi

    try:
        e_v_m = float(np.sqrt((eta0 * p_w * 4.0 * np.pi) / (g_lin * (lam ** 2))))
    except Exception:
        return None
    if not np.isfinite(e_v_m) or e_v_m <= 0.0:
        return None

    return e_v_m

def _ocupacion_pct_from_rni_dbuv_m(rni_dbuv_m: Any, *, limit_dbuv_m: float = 162.7) -> Optional[float]:
    """Calcula porcentaje de ocupación coherente con un límite en dBµV/m.

    % = 100 * 10^((E_dBµV/m - E_lim_dBµV/m)/20)
    (20 porque E es magnitud de campo, no potencia).
    """
    try:
        e_db = float(rni_dbuv_m)
    except Exception:
        return None
    if not np.isfinite(e_db):
        return None
    try:
        return float(100.0 * (10.0 ** ((e_db - float(limit_dbuv_m)) / 20.0)))
    except Exception:
        return None



def _enrich_output_with_rni(out: Dict[str, Any]) -> None:
    """Añade 'rni' (E en dBµV/m) y 'ocupacion_pct' por emisión sin alterar la salida existente.

    - rni: E[dBµV/m] calculado desde la potencia (dBm) y la frecuencia central (Hz) usando dbm_EMC.pdf
    - ocupacion_pct: 100% corresponde a 162.7 dBµV/m (equivalente a ~137 V/m)
    """

    def _apply_to_results_list(results_obj: Any) -> None:
        if not isinstance(results_obj, list):
            return
        for row in results_obj:
            if not isinstance(row, dict):
                continue

            # Potencia (dBm): en compliance el campo se llama p_medida_dBm,
            # en peaks/all_emissions suele llamarse power_dbm.
            if "p_medida_dBm" in row:
                p_dbm = row.get("p_medida_dBm")
            else:
                p_dbm = row.get("power_dbm")

            # Frecuencia central (Hz): preferimos fc_hz si existe, si no, derivamos desde MHz.
            fc_hz = row.get("fc_hz")
            if fc_hz is None:
                if "fc_medida_MHz" in row:
                    try:
                        fc_hz = float(row.get("fc_medida_MHz")) * 1e6
                    except Exception:
                        fc_hz = None
                elif "fc_mhz" in row:
                    try:
                        fc_hz = float(row.get("fc_mhz")) * 1e6
                    except Exception:
                        fc_hz = None

            e_v_m = _rni_field_v_m_from_power_dbm_and_fc_hz(p_dbm, fc_hz)
            e_dbuv = _rni_field_dbuv_m_from_power_dbm_and_fc_hz(p_dbm, fc_hz)
            row["rni"] = e_dbuv
            row["rni_v_m"] = e_v_m
            row["ocupacion_pct"] = _ocupacion_pct_from_rni_dbuv_m(e_dbuv, limit_dbuv_m=162.7)

    _apply_to_results_list(out.get("results"))

    rbd = out.get("results_by_dane")
    if isinstance(rbd, dict):
        for _k, v in rbd.items():
            _apply_to_results_list(v)

def _normalize_dane_token(x: Any) -> Optional[str]:
    """Normaliza un token de DANE a string usable.

    - None / '' -> None
    - Limpia '11001.0' -> '11001'
    - Conserva ceros a la izquierda si vienen explícitos.
    """
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None
    # quita .0 típico (11001.0)
    if re.fullmatch(r"\d+\.0", s):
        try:
            s = str(int(float(s)))
        except Exception:
            pass
    return s


def _normalize_danes(
    danes_filtro: Optional[List[Any]],
    dane_filtro: Optional[str],
    municipio_filtro: Optional[str],
) -> List[str]:
    """Construye la lista final de DANEs en orden, sin duplicados.

    Regla:
      - Si llega 'danes_filtro' (lista) y tiene elementos válidos -> usarla.
      - Si no, y llega 'dane_filtro' -> lista de 1.
      - (municipio_filtro se maneja aparte; aquí solo armamos la lista de DANEs)
    """
    out: List[str] = []
    if isinstance(danes_filtro, list):
        for d in danes_filtro:
            nd = _normalize_dane_token(d)
            if nd is not None:
                out.append(nd)
    if not out and dane_filtro is not None:
        nd = _normalize_dane_token(dane_filtro)
        if nd is not None:
            out.append(nd)

    # Deduplicar preservando orden
    seen = set()
    out2: List[str] = []
    for d in out:
        if d in seen:
            continue
        seen.add(d)
        out2.append(d)
    return out2



def _match_licencia(
    *,
    fc_mhz: float,
    bw_khz: float,
    power_dbm: Optional[float],
    licencia_csv_path: Optional[str],
    dane_filtro: Optional[str] = None,
    municipio_filtro: Optional[str] = None,
    tolerancia_freq_mhz: float,
) -> Dict[str, Any]:
    """Wrapper para comparar_parametros con valores None-safe."""
    if not licencia_csv_path:
        return {"Licencia": None}

    # Evita falsos positivos: si la base contiene múltiples entidades (municipio o
    # código DANE) y no se especifica ningún filtro, NO hacemos matching.
    if dane_filtro is None and municipio_filtro is None:
        return {"Licencia": None, "reason": "filtro_no_especificado"}

    try:
        comp = comparar_parametros(
            f_medida=float(fc_mhz),
            bw_medido=float(bw_khz),
            p_medida=(float(power_dbm) if power_dbm is not None else 0.0),
            ruta_csv=licencia_csv_path,
            tolerancia_freq=float(tolerancia_freq_mhz),
            dane_filtro=dane_filtro,
            municipio_filtro=municipio_filtro,
        )
        # comparar_parametros ya devuelve claves como fc_nominal_MHz, delta_f_MHz, etc.
        return comp
    except Exception as exc:
        _proc_log(
            "_match_licencia failed "
            f"fc_mhz={fc_mhz} bw_khz={bw_khz} dane={dane_filtro} "
            f"municipio={municipio_filtro} error={type(exc).__name__}: {exc}"
        )
        return {"Licencia": "NO"}


def _narrow_span_in_broad_frame(frame: SpectrumFrame, peak_idx: int) -> Tuple[int, int]:
    """Recorte angosto/local para picos dentro de una captura UHF ancha.

    Evita que find_emission_span() expanda un pico estrecho a toda una meseta
    elevada del frame. Usa una línea base lenta y el residual local del pico.
    """
    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    N = y.size
    if N < 8:
        return int(max(0, peak_idx)), int(min(N - 1, peak_idx))
    pk = int(np.clip(int(peak_idx), 0, N - 1))
    kernel = np.array([0.25, 0.5, 0.25], dtype=float)
    y_s = np.convolve(y, kernel, mode="same")
    try:
        from scipy.ndimage import gaussian_filter1d
        baseline = gaussian_filter1d(y_s, sigma=float(max(10.0, min(45.0, N / 600.0))))
    except Exception:
        baseline = pd.Series(y_s).rolling(window=max(11, int(N / 250)), center=True, min_periods=1).median().values
    residual = y_s - baseline
    peak_res = float(max(0.0, residual[pk]))
    if peak_res <= 0.8:
        return pk, pk
    thr = float(max(0.6, 0.35 * peak_res))

    f = np.asarray(frame.freq_hz, dtype=float) if getattr(frame, "freq_hz", None) is not None else np.linspace(float(frame.f_start_hz), float(frame.f_stop_hz), N)
    bin_hz = float(abs(f[1] - f[0])) if N >= 2 else 1.0
    max_half_bins = int(max(10, min(N // 4, round(0.55e6 / max(bin_hz, 1.0)))))

    L = pk
    while L > 0 and (pk - L) < max_half_bins and residual[L - 1] > thr:
        L -= 1
    R = pk
    while R < (N - 1) and (R - pk) < max_half_bins and residual[R + 1] > thr:
        R += 1

    # Si el residual local quedó demasiado pequeño, usar un respaldo local mínimo.
    if R <= L:
        L = max(0, pk - max_half_bins // 8)
        R = min(N - 1, pk + max_half_bins // 8)
    if (R - L) < 6:
        grow = int((6 - (R - L)) // 2 + 1)
        L = max(0, L - grow)
        R = min(N - 1, R + grow)
    return int(L), int(R)


def _is_duplicate_span(existing: List[Dict[str, Any]], L: int, R: int, fc_hz: float, bw_hz: float) -> bool:
    new_len = max(1, int(R) - int(L) + 1)
    for ex in existing:
        L0, R0 = int(ex["_L"]), int(ex["_R"])
        inter = max(0, min(R, R0) - max(L, L0) + 1)
        union = max(1, max(R, R0) - min(L, L0) + 1)
        iou = float(inter / union)
        fc0 = float(ex.get("_fc_hz", np.nan))
        bw0 = float(ex.get("_bw_hz", np.nan))
        if iou >= 0.60:
            return True
        if np.isfinite(fc0) and np.isfinite(fc_hz) and np.isfinite(bw0) and np.isfinite(bw_hz):
            tol_fc = max(1.5e5, 0.20 * max(bw0, bw_hz))
            bw_rel = abs(bw0 - bw_hz) / max(max(bw0, bw_hz), 1.0)
            if abs(fc0 - fc_hz) <= tol_fc and bw_rel <= 0.25:
                return True
    return False


def _frame_noise_floor_dbm(frame: SpectrumFrame) -> float:
    try:
        nf = float(estimate_noise_floor(frame))
        if np.isfinite(nf):
            return float(nf)
    except Exception:
        pass
    y = np.asarray(frame.amplitudes_dbm, dtype=float)
    return float(np.median(y)) if y.size > 0 else float("nan")


def _ensure_segment_bounds(frame: SpectrumFrame, L: int, R: int) -> Tuple[int, int]:
    N = int(len(frame.amplitudes_dbm))
    if N <= 0:
        return 0, 0

    L = int(np.clip(int(L), 0, N - 1))
    R = int(np.clip(int(R), 0, N - 1))
    if R < L:
        L, R = R, L

    if N == 1:
        return 0, 0

    min_span = 1  # al menos 2 bins para poder construir un sub-frame valido
    if (R - L) >= min_span:
        return int(L), int(R)

    if L > 0:
        L -= 1
    elif R < (N - 1):
        R += 1

    while (R - L) < min_span and R < (N - 1):
        R += 1
    while (R - L) < min_span and L > 0:
        L -= 1
    return int(L), int(R)


def _build_detector_segment(
    frame: SpectrumFrame,
    *,
    peak_idx: int,
    measure_L: int,
    measure_R: int,
    threshold_dbm: Optional[float],
    noise_floor_dbm: Optional[float],
    fc_hint_hz: Optional[float] = None,
    bandwidth_hint_hz: Optional[float] = None,
    obw_hint_hz: Optional[float] = None,
    match_fc_hz: Optional[float] = None,
    snr_hint_db: Optional[float] = None,
    f_lo_hz: Optional[float] = None,
    f_hi_hz: Optional[float] = None,
    detector_name: str = "legacy",
    preset_name: Optional[str] = None,
) -> DetectorSegment:
    freq_axis = np.asarray(frame.freq_hz, dtype=float)
    y = np.asarray(frame.amplitudes_dbm, dtype=float)

    L, R = _ensure_segment_bounds(frame, measure_L, measure_R)
    pk = int(np.clip(int(peak_idx), L, R))
    if (R - L) >= 0:
        pk = int(L + np.argmax(y[L : R + 1]))

    if fc_hint_hz is None:
        fc_hint_hz = float(freq_axis[pk])

    sub = slice_spectrum_frame(frame, L, R)
    params = measure_emission_parameters(sub, fc=float(fc_hint_hz), xdb=3.0, obw_percent=99.0)

    fc_hz = float(params.get("fc_hz", fc_hint_hz))

    if bandwidth_hint_hz is None or (not np.isfinite(float(bandwidth_hint_hz))):
        bandwidth_hint_hz = params.get("bandwidth_xdb_hz", 0.0)
    if obw_hint_hz is None or (not np.isfinite(float(obw_hint_hz))):
        obw_hint_hz = params.get("obw_hz", 0.0)

    bandwidth_xdb_hz = float(bandwidth_hint_hz) if np.isfinite(float(bandwidth_hint_hz)) else 0.0
    obw_hz = float(obw_hint_hz) if np.isfinite(float(obw_hint_hz)) else 0.0
    bw_report_hz = _select_bw_hz({"obw_hz": obw_hz, "bandwidth_xdb_hz": bandwidth_xdb_hz})

    if f_lo_hz is None or not np.isfinite(float(f_lo_hz)):
        f_lo_hz = float(freq_axis[L])
    if f_hi_hz is None or not np.isfinite(float(f_hi_hz)):
        f_hi_hz = float(freq_axis[R])

    if snr_hint_db is None or not np.isfinite(float(snr_hint_db)):
        try:
            snr_hint_db = float(params.get("snr_db", np.nan))
        except Exception:
            snr_hint_db = float("nan")
    if not np.isfinite(float(snr_hint_db)):
        try:
            snr_hint_db = float(max(0.0, y[pk] - float(noise_floor_dbm)))
        except Exception:
            snr_hint_db = float("nan")

    power_dbm = _safe_power_dbm(channel_power_dbm_uniform_bins(sub))

    seg: DetectorSegment = {
        "detector_name": detector_name,
        "peak_idx": int(pk),
        "measure_L": int(L),
        "measure_R": int(R),
        "f_lo_hz": float(f_lo_hz),
        "f_hi_hz": float(f_hi_hz),
        "fc_hz": float(fc_hz),
        "bandwidth_hz": float(bw_report_hz),
        "bandwidth_xdb_hz": float(bandwidth_xdb_hz),
        "obw_hz": float(obw_hz),
        "snr_db": float(snr_hint_db) if np.isfinite(float(snr_hint_db)) else float("nan"),
        "threshold_dbm": (float(threshold_dbm) if threshold_dbm is not None and np.isfinite(float(threshold_dbm)) else None),
        "noise_floor_dbm": (float(noise_floor_dbm) if noise_floor_dbm is not None and np.isfinite(float(noise_floor_dbm)) else None),
        "power_dbm": power_dbm,
    }

    if match_fc_hz is not None and np.isfinite(float(match_fc_hz)):
        seg["match_fc_hz"] = float(match_fc_hz)
    if preset_name:
        seg["preset_name"] = str(preset_name)
    return seg


def _build_legacy_detector_run(
    frame: SpectrumFrame,
    *,
    detect_threshold_db: Optional[float] = None,
) -> DetectorRun:
    freq_axis = np.asarray(frame.freq_hz, dtype=float)
    run_threshold_dbm = compute_detection_threshold_dbm(frame, umbral_db=detect_threshold_db, n_sigma_seed=3.5)
    run_noise_floor_dbm = _frame_noise_floor_dbm(frame)

    try:
        bb_segments = list(analyze_colombia_broadband_segments(frame, detect_threshold_db=detect_threshold_db))
    except Exception:
        bb_segments = []

    bb_by_peak: Dict[int, Dict[str, Any]] = {int(seg.get("refined_peak_idx", -1)): seg for seg in bb_segments}

    def _nearest_bb_segment(pk: int) -> Optional[Dict[str, Any]]:
        if not bb_segments:
            return None
        pk = int(pk)
        best = None
        best_dist = None
        for seg in bb_segments:
            rpk = int(seg.get("refined_peak_idx", -1))
            if rpk < 0:
                continue
            dist = abs(rpk - pk)
            L = int(seg.get("measure_L", seg.get("refined_L", rpk)))
            R = int(seg.get("measure_R", seg.get("refined_R", rpk)))
            inside = L <= pk <= R
            if (not inside) and dist > max(12, int(0.004 * len(freq_axis))):
                continue
            if best is None or dist < best_dist:
                best = seg
                best_dist = dist
        return best

    def _measure_emission_from_bin(pk: int, fc_default_hz: float) -> Tuple[int, int, Dict[str, Any], Optional[Dict[str, Any]]]:
        seg = bb_by_peak.get(int(pk)) or _nearest_bb_segment(int(pk))
        if seg is not None:
            L = int(seg.get("measure_L", seg.get("refined_L", pk)))
            R = int(seg.get("measure_R", seg.get("refined_R", pk)))
            L, R = _ensure_segment_bounds(frame, L, R)
            sub = slice_spectrum_frame(frame, L, R)
            params = measure_emission_parameters(sub, fc=float(seg.get("fc_hz", fc_default_hz)), xdb=3.0, obw_percent=99.0)
            params["fc_hz"] = float(seg.get("fc_hz", params.get("fc_hz", fc_default_hz)))
            params["bandwidth_xdb_hz"] = float(seg.get("bandwidth_hz", params.get("bandwidth_xdb_hz", 0.0)))
            params["obw_hz"] = float(seg.get("obw_hz", params.get("obw_hz", 0.0)))
            if "snr_db" in seg:
                params["snr_db"] = float(seg["snr_db"])
            if "match_fc_hz" in seg:
                params["match_fc_hz"] = float(seg.get("match_fc_hz"))
            if "f_lo_hz" in seg:
                params["f_lo_hz"] = float(seg.get("f_lo_hz"))
            if "f_hi_hz" in seg:
                params["f_hi_hz"] = float(seg.get("f_hi_hz"))
            return L, R, params, seg

        if is_colombia_broadband_frame(frame):
            L, R = _narrow_span_in_broad_frame(frame, pk)
            fL = float(freq_axis[int(L)]) if len(freq_axis) else 0.0
            fR = float(freq_axis[int(R)]) if len(freq_axis) else 0.0
            local_bw_hz = float(abs(fR - fL))
            if local_bw_hz <= 1.2e6 and R > L:
                L, R = _ensure_segment_bounds(frame, L, R)
                sub = slice_spectrum_frame(frame, L, R)
                params = measure_emission_parameters(sub, fc=float(freq_axis[pk]), xdb=3.0, obw_percent=99.0)
                return L, R, params, None

        span_margin_db = _auto_span_margin_db(frame, pk, umbral_db=detect_threshold_db)
        L, R = find_emission_span(frame, pk, margin_db=span_margin_db)
        L, R = _ensure_segment_bounds(frame, L, R)
        sub = slice_spectrum_frame(frame, L, R)
        params = measure_emission_parameters(sub, fc=fc_default_hz, xdb=3.0, obw_percent=99.0)
        return L, R, params, None

    raw_peaks = [int(b) for b in detect_peak_bins(frame, detect_threshold_db=detect_threshold_db)]
    out_segments: List[DetectorSegment] = []
    seen_meta: List[Dict[str, Any]] = []

    for pk in raw_peaks:
        fc_seed_hz = float(freq_axis[pk])
        L, R, params, src_seg = _measure_emission_from_bin(pk, fc_seed_hz)
        bw_hz_used = _select_bw_hz(params)
        if _is_duplicate_span(seen_meta, L, R, float(params["fc_hz"]), float(bw_hz_used)):
            continue

        seg_threshold = run_threshold_dbm
        seg_noise = run_noise_floor_dbm
        if isinstance(src_seg, dict):
            if src_seg.get("threshold_dbm", None) is not None:
                seg_threshold = float(src_seg["threshold_dbm"])
            if src_seg.get("noise_floor_dbm", None) is not None:
                seg_noise = float(src_seg["noise_floor_dbm"])

        seg_record = _build_detector_segment(
            frame,
            peak_idx=pk,
            measure_L=L,
            measure_R=R,
            threshold_dbm=seg_threshold,
            noise_floor_dbm=seg_noise,
            fc_hint_hz=float(params.get("fc_hz", fc_seed_hz)),
            bandwidth_hint_hz=float(params.get("bandwidth_xdb_hz", 0.0)),
            obw_hint_hz=float(params.get("obw_hz", 0.0)),
            match_fc_hz=params.get("match_fc_hz", None),
            snr_hint_db=params.get("snr_db", None),
            f_lo_hz=params.get("f_lo_hz", None),
            f_hi_hz=params.get("f_hi_hz", None),
            detector_name="legacy",
        )
        seen_meta.append(
            {
                "_L": int(seg_record["measure_L"]),
                "_R": int(seg_record["measure_R"]),
                "_fc_hz": float(seg_record["fc_hz"]),
                "_bw_hz": float(seg_record["bandwidth_hz"]),
            }
        )
        out_segments.append(seg_record)

    return {
        "detector_name": "legacy",
        "threshold_dbm": run_threshold_dbm,
        "noise_floor_dbm": run_noise_floor_dbm,
        "raw_peaks": raw_peaks,
        "peaks": [int(seg["peak_idx"]) for seg in out_segments],
        "segments": out_segments,
    }


def _build_simple_detector_run(
    frame: SpectrumFrame,
    *,
    detect_threshold_db: Optional[float] = None,
    preset_name: str = "general",
    overrides: Optional[Dict[str, Any]] = None,
) -> DetectorRun:
    raw = detect_emissions_simple(
        frame,
        preset_name=preset_name,
        overrides=overrides,
        threshold_margin_db_override=detect_threshold_db,
    )
    freq_axis = np.asarray(frame.freq_hz, dtype=float)
    out_segments: List[DetectorSegment] = []
    seen_meta: List[Dict[str, Any]] = []

    for raw_seg in raw.get("segments", []):
        pk = int(raw_seg.get("peak_idx", 0))
        L = int(raw_seg.get("measure_L", pk))
        R = int(raw_seg.get("measure_R", pk))
        L, R = _ensure_segment_bounds(frame, L, R)
        f_lo_hz = float(freq_axis[L])
        f_hi_hz = float(freq_axis[R])
        seg_record = _build_detector_segment(
            frame,
            peak_idx=pk,
            measure_L=L,
            measure_R=R,
            threshold_dbm=raw_seg.get("threshold_dbm", raw.get("threshold_dbm", None)),
            noise_floor_dbm=raw_seg.get("noise_floor_dbm", raw.get("noise_floor_dbm", None)),
            fc_hint_hz=float(freq_axis[int(np.clip(pk, 0, len(freq_axis) - 1))]),
            bandwidth_hint_hz=float(max(0.0, f_hi_hz - f_lo_hz)),
            obw_hint_hz=None,
            match_fc_hz=None,
            snr_hint_db=None,
            f_lo_hz=f_lo_hz,
            f_hi_hz=f_hi_hz,
            detector_name="simple",
            preset_name=str(raw.get("preset_name", preset_name)),
        )
        if _is_duplicate_span(seen_meta, int(seg_record["measure_L"]), int(seg_record["measure_R"]), float(seg_record["fc_hz"]), float(seg_record["bandwidth_hz"])):
            continue
        seen_meta.append(
            {
                "_L": int(seg_record["measure_L"]),
                "_R": int(seg_record["measure_R"]),
                "_fc_hz": float(seg_record["fc_hz"]),
                "_bw_hz": float(seg_record["bandwidth_hz"]),
            }
        )
        out_segments.append(seg_record)

    return {
        "detector_name": "simple",
        "threshold_dbm": raw.get("threshold_dbm", None),
        "noise_floor_dbm": raw.get("noise_floor_dbm", None),
        "raw_peaks": [int(seg["peak_idx"]) for seg in raw.get("segments", [])],
        "peaks": [int(seg["peak_idx"]) for seg in out_segments],
        "segments": out_segments,
        "preset_name": raw.get("preset_name", preset_name),
        "config": raw.get("config"),
    }


def get_detector_run(
    frame: SpectrumFrame,
    *,
    detector_name: str = "legacy",
    detect_threshold_db: Optional[float] = None,
    simple_preset_name: str = "general",
    simple_overrides: Optional[Dict[str, Any]] = None,
) -> DetectorRun:
    det = str(detector_name or "legacy").strip().lower()
    if det == "legacy":
        return _build_legacy_detector_run(frame, detect_threshold_db=detect_threshold_db)
    if det == "simple":
        return _build_simple_detector_run(
            frame,
            detect_threshold_db=detect_threshold_db,
            preset_name=simple_preset_name,
            overrides=simple_overrides,
        )
    raise ValueError(f"Detector interno desconocido: {detector_name}")


def _process_input_reference_legacy(
    inp: PayloadInput,
    corr_csv_path: Optional[str] = None,
    licencia_csv_path: Optional[str] = None,
    dane_filtro: Optional[str] = None,
    danes_filtro: Optional[List[Any]] = None,  # nuevo: lista de DANEs
    municipio_filtro: Optional[str] = None,  # compatibilidad hacia atrás
    umbral_db: Optional[float] = None,
    delta_fc_khz: Optional[float] = None,
    delta_bw_khz: Optional[float] = None,
) -> Dict[str, Any]:
    frame_json, picos, cumplimiento = unpack_input(inp)
    mode = route_mode(picos, cumplimiento)

    # Soporte extra: si el input legacy viene como dict y trae "danes", úsalo si no llegó por parámetro.
    if isinstance(inp, dict) and danes_filtro is None and isinstance(inp.get("danes", None), list):
        danes_filtro = inp.get("danes", None)

    # Soporte extra: si el input legacy viene como dict y trae "umbral_db", úsalo si no llegó por parámetro.
    if isinstance(inp, dict) and umbral_db is None and ("umbral_db" in inp):
        try:
            umbral_db = float(inp.get("umbral_db", None))
        except Exception:
            umbral_db = None


    # Soporte extra: si el input legacy viene como dict y trae "delta_fc_khz", úsalo si no llegó por parámetro.
    if isinstance(inp, dict) and delta_fc_khz is None and ("delta_fc_khz" in inp):
        try:
            delta_fc_khz = float(inp.get("delta_fc_khz", None))
        except Exception:
            delta_fc_khz = None

    # Soporte extra: si el input legacy viene como dict y trae "delta_bw_khz", úsalo si no llegó por parámetro.
    if isinstance(inp, dict) and delta_bw_khz is None and ("delta_bw_khz" in inp):
        try:
            delta_bw_khz = float(inp.get("delta_bw_khz", None))
        except Exception:
            delta_bw_khz = None

    # Tolerancia de frecuencia central para matching (kHz). Default: 100 kHz.
    try:
        _dfc = 100.0 if delta_fc_khz is None else float(delta_fc_khz)
    except Exception:
        _dfc = 100.0
    if (not np.isfinite(_dfc)) or (_dfc < 0.0):
        _dfc = 100.0
    fc_margin_mhz = float(_dfc) / 1000.0

    # Tolerancia de BW para cumplimiento (kHz). Default: 10 kHz.
    try:
        _dbw = 10.0 if delta_bw_khz is None else float(delta_bw_khz)
    except Exception:
        _dbw = 10.0
    if (not np.isfinite(_dbw)) or (_dbw < 0.0):
        _dbw = 10.0
    bw_margin_khz = float(_dbw)
    danes_list = _normalize_danes(danes_filtro, dane_filtro, municipio_filtro)
    # Compatibilidad: si solo hay 1 DANE en la lista, úsalo como dane_filtro tradicional.
    if len(danes_list) == 1 and dane_filtro is None:
        dane_filtro = danes_list[0]

    # En modo compliance, el matching de licencias es obligatorio
    # y requiere un filtro (preferiblemente código DANE).
    if mode == "compliance" and licencia_csv_path and (len(danes_list) == 0 and municipio_filtro is None):
        raise ValueError("Para mode=compliance debes pasar --dane (o --municipio legacy) cuando usas --lic")

    out: Dict[str, Any] = {
        "mode": mode,
        "cumplimiento": cumplimiento,
        "picos_count": len(picos),
        "picos": picos,
        "results": [],
        "num_emissions": 0,
        "correction_applied": bool(corr_csv_path),
    }

    if umbral_db is not None:
        out["umbral_db"] = float(umbral_db)

    if len(danes_list) > 1:
        out["danes"] = danes_list

    if "timestamp" in frame_json:
        out["timestamp"] = frame_json["timestamp"]
    if "mac" in frame_json:
        out["mac"] = frame_json["mac"]

    frame = frame_from_payload(frame_json)
    if corr_csv_path:
        frame = apply_gain_correction(frame, corr_csv_path)

    freq_axis = np.asarray(frame.freq_hz, dtype=float)

    # Reporte: umbral absoluto (dBm) realmente usado para detección (NF + umbral_db o adaptativo)
    thr_used_dbm = compute_detection_threshold_dbm(frame, umbral_db=umbral_db, n_sigma_seed=3.5)
    out["umbral"] = (float(thr_used_dbm) if thr_used_dbm is not None else None)

    try:
        bb_segments = list(analyze_colombia_broadband_segments(frame, detect_threshold_db=umbral_db))
    except Exception:
        bb_segments = []
    bb_by_peak: Dict[int, Dict[str, Any]] = {int(seg.get("refined_peak_idx", -1)): seg for seg in bb_segments}

    def _nearest_bb_segment(pk: int) -> Optional[Dict[str, Any]]:
        if not bb_segments:
            return None
        pk = int(pk)
        best = None
        best_dist = None
        for seg in bb_segments:
            rpk = int(seg.get("refined_peak_idx", -1))
            if rpk < 0:
                continue
            dist = abs(rpk - pk)
            # aceptar solo si cae cerca del pico refinado o dentro del rango medido
            L = int(seg.get("measure_L", seg.get("refined_L", rpk)))
            R = int(seg.get("measure_R", seg.get("refined_R", rpk)))
            inside = (L <= pk <= R)
            if (not inside) and dist > max(12, int(0.004 * len(freq_axis))):
                continue
            if best is None or dist < best_dist:
                best = seg
                best_dist = dist
        return best

    def _measure_emission_from_bin(pk: int, fc_default_hz: float) -> Tuple[int, int, SpectrumFrame, Dict[str, Any]]:
        seg = bb_by_peak.get(int(pk)) or _nearest_bb_segment(int(pk))
        if seg is not None:
            L = int(seg.get("measure_L", seg.get("refined_L", pk)))
            R = int(seg.get("measure_R", seg.get("refined_R", pk)))
            sub = slice_spectrum_frame(frame, L, R)
            params = measure_emission_parameters(sub, fc=float(seg.get("fc_hz", fc_default_hz)), xdb=3.0, obw_percent=99.0)
            params["fc_hz"] = float(seg.get("fc_hz", params.get("fc_hz", fc_default_hz)))
            params["bandwidth_xdb_hz"] = float(seg.get("bandwidth_hz", params.get("bandwidth_xdb_hz", 0.0)))
            params["obw_hz"] = float(seg.get("obw_hz", params.get("obw_hz", 0.0)))
            if "snr_db" in seg:
                params["snr_db"] = float(seg["snr_db"])
            if "match_fc_hz" in seg:
                params["match_fc_hz"] = float(seg.get("match_fc_hz"))
            if "f_lo_hz" in seg:
                params["f_lo_hz"] = float(seg.get("f_lo_hz"))
            if "f_hi_hz" in seg:
                params["f_hi_hz"] = float(seg.get("f_hi_hz"))
            return L, R, sub, params

        if is_colombia_broadband_frame(frame):
            L, R = _narrow_span_in_broad_frame(frame, pk)
            # Solo usar el recorte local si realmente quedó angosto/local.
            fL = float(freq_axis[int(L)]) if len(freq_axis) else 0.0
            fR = float(freq_axis[int(R)]) if len(freq_axis) else 0.0
            local_bw_hz = float(abs(fR - fL))
            if local_bw_hz <= 1.2e6 and R > L:
                sub = slice_spectrum_frame(frame, L, R)
                params = measure_emission_parameters(sub, fc=float(freq_axis[pk]), xdb=3.0, obw_percent=99.0)
                return L, R, sub, params

        span_margin_db = _auto_span_margin_db(frame, pk, umbral_db=umbral_db)
        L, R = find_emission_span(frame, pk, margin_db=span_margin_db)
        sub = slice_spectrum_frame(frame, L, R)
        params = measure_emission_parameters(sub, fc=fc_default_hz, xdb=3.0, obw_percent=99.0)
        return L, R, sub, params


    # =========================
    # MODO all_emissions
    # =========================
    if mode == "all_emissions":
        detected_bins = [int(b) for b in detect_peak_bins(frame, detect_threshold_db=umbral_db)]
        results: List[Dict[str, Any]] = []
        results_meta: List[Dict[str, Any]] = []

        for pk in detected_bins:
            fc_hz_seed = float(freq_axis[pk])

            L, R, sub, params = _measure_emission_from_bin(pk, fc_hz_seed)

            fc_mhz = float(params["fc_hz"]) / 1e6
            bw_hz_used = _select_bw_hz(params)
            if _is_duplicate_span(results_meta, L, R, float(params["fc_hz"]), float(bw_hz_used)):
                continue
            bw_khz = float(bw_hz_used) / 1e3
            p_dbm = _safe_power_dbm(channel_power_dbm_uniform_bins(sub))

            row: Dict[str, Any] = {
                "nearest_bin": int(pk),
                "status": "emision",
                "fc_hz": float(params["fc_hz"]),
                "fc_mhz": fc_mhz,
                "bw_hz": float(bw_hz_used),
                "bw_khz": bw_khz,
                "power_dbm": p_dbm,
            }

            results_meta.append({"_L": int(L), "_R": int(R), "_fc_hz": float(params["fc_hz"]), "_bw_hz": float(bw_hz_used)})
            results.append(row)

        out["results"] = results
        out["num_emissions"] = len(results)
        _enrich_output_with_rni(out)
        return out

    # =========================
    # MODO peaks
    # =========================
    if mode == "peaks":
        detected_bins = [int(b) for b in detect_peak_bins(frame, detect_threshold_db=umbral_db)]
        detected_freqs = [float(freq_axis[b]) for b in detected_bins] if detected_bins else []

        results: List[Dict[str, Any]] = []

        for p in picos:
            req_hz = pico_to_hz(p)
            req_idx = nearest_bin(freq_axis, req_hz)

            margin = match_margin_hz(req_hz)

            # match con pico detectado más cercano
            if detected_bins:
                deltas = [abs(f - req_hz) for f in detected_freqs]
                best_i = int(np.argmin(deltas))
                best_bin = int(detected_bins[best_i])
                best_f = float(detected_freqs[best_i])
                best_delta = float(deltas[best_i])
            else:
                best_bin = None
                best_f = None
                best_delta = float("inf")

            # Si no hay match cercano => ruido
            if best_f is None or best_delta > margin:
                results.append({
                    "requested_pico": p,
                    "requested_pico_hz": float(req_hz),
                    "nearest_bin": int(req_idx),
                    "fc_hz": float(freq_axis[req_idx]),
                    "fc_mhz": float(freq_axis[req_idx]) / 1e6,
                    "status": "ruido",
                    "reason": "no_hay_emision_cercana",
                    "match_margin_hz": float(margin),
                    "matched_peak_hz": (float(best_f) if best_f is not None else None),
                    "delta_match_hz": (float(best_delta) if np.isfinite(best_delta) else None),
                    "Licencia": None,
                })
                continue

            # Si hay match, ahora validamos por umbral
            es_ruido, amp_dbm, nf_dbm, thr_seed_dbm = is_ruido_por_umbral(
                frame,
                best_bin,
                detect_threshold_db=umbral_db,
            )

            if es_ruido:
                results.append({
                    "requested_pico": p,
                    "requested_pico_hz": float(req_hz),
                    "match_margin_hz": float(margin),
                    "matched_peak_hz": float(best_f),
                    "delta_match_hz": float(best_delta),
                    "nearest_bin": int(best_bin),
                    "fc_hz": float(best_f),
                    "fc_mhz": float(best_f) / 1e6,
                    "status": "ruido",
                    "reason": "por_umbral",
                    "amp_dbm": float(amp_dbm),
                    "nf_dbm": float(nf_dbm),
                    "thr_seed_dbm": float(thr_seed_dbm),
                    "Licencia": None,
                })
                continue

            # Medición de esa emisión
            L, R, sub, params = _measure_emission_from_bin(best_bin, float(best_f))

            fc_mhz = float(params["fc_hz"]) / 1e6
            bw_hz_used = _select_bw_hz(params)
            bw_khz = float(bw_hz_used) / 1e3
            p_dbm = _safe_power_dbm(channel_power_dbm_uniform_bins(sub))

            row: Dict[str, Any] = {
                "requested_pico": p,
                "requested_pico_hz": float(req_hz),
                "match_margin_hz": float(margin),
                "matched_peak_hz": float(best_f),
                "delta_match_hz": float(best_delta),
                "nearest_bin": int(best_bin),
                "status": "emision",
                "fc_hz": float(params["fc_hz"]),
                "fc_mhz": fc_mhz,
                "bw_hz": float(bw_hz_used),
                "bw_khz": bw_khz,
                "power_dbm": p_dbm,
            }

            # Comparación con licencias:
            # - Si llega una lista de DANEs, reporta el matching para cada uno.
            if licencia_csv_path and len(danes_list) > 1:
                comps_por_dane: List[Dict[str, Any]] = []
                for d in danes_list:
                    c = _match_licencia(
                        fc_mhz=fc_mhz,
                        bw_khz=bw_khz,
                        power_dbm=p_dbm,
                        licencia_csv_path=licencia_csv_path,
                        dane_filtro=d,
                        municipio_filtro=municipio_filtro,
                        tolerancia_freq_mhz=fc_margin_mhz,  # ±100 kHz
                    )
                    c2 = dict(c)
                    c2["dane"] = d
                    comps_por_dane.append(c2)

                row["comparaciones_por_dane"] = comps_por_dane

                # Compatibilidad: reflejar también el primer DANE en campos legacy.
                first = comps_por_dane[0] if len(comps_por_dane) > 0 else {}
                if first.get("Licencia") is not None:
                    row["Licencia"] = first.get("Licencia", "NO")
                    row["fc_nominal_MHz"] = first.get("fc_nominal_MHz")
                    row["delta_f_MHz"] = first.get("delta_f_MHz")
                    row["bw_nominal_kHz"] = first.get("bw_nominal_kHz")
                    row["delta_bw_kHz"] = first.get("delta_bw_kHz")
                    row["p_nominal_dBm"] = first.get("p_nominal_dBm")
                    row["delta_p_dB"] = None if p_dbm is None else first.get("delta_p_dB")
            else:
                comp = _match_licencia(
                    fc_mhz=fc_mhz,
                    bw_khz=bw_khz,
                    power_dbm=p_dbm,
                    licencia_csv_path=licencia_csv_path,
                    dane_filtro=dane_filtro,
                    municipio_filtro=municipio_filtro,
                    tolerancia_freq_mhz=fc_margin_mhz,  # ±100 kHz
                )

                if comp.get("Licencia") is not None:
                    row["Licencia"] = comp.get("Licencia", "NO")
                    row["fc_nominal_MHz"] = comp.get("fc_nominal_MHz")
                    row["delta_f_MHz"] = comp.get("delta_f_MHz")
                    row["bw_nominal_kHz"] = comp.get("bw_nominal_kHz")
                    row["delta_bw_kHz"] = comp.get("delta_bw_kHz")
                    row["p_nominal_dBm"] = comp.get("p_nominal_dBm")
                    row["delta_p_dB"] = None if p_dbm is None else comp.get("delta_p_dB")

            results.append(row)

        out["results"] = results
        out["num_emissions"] = len(results)
        _enrich_output_with_rni(out)
        return out

    # =========================
    # MODO compliance
    # =========================
    if mode == "compliance":
        if not licencia_csv_path:
            raise ValueError("Para modo compliance debes pasar --lic (ruta al CSV de licencias).")

        # Reglas de cumplimiento (ajusta según tu reglamentación):
        # - FC: debe estar dentro de ±FC_MARGIN_MHZ del nominal.
        # - BW: si el medido es menor que el nominal, cumple; si es mayor,
        #       solo falla cuando el exceso supera +BW_MARGIN_KHZ.
        # - P : potencia medida debe ser <= potencia nominal (si es mayor, NO cumple).
        FC_MARGIN_MHZ = fc_margin_mhz
        BW_MARGIN_KHZ = bw_margin_khz

        detected_bins = [int(b) for b in detect_peak_bins(frame, detect_threshold_db=umbral_db)]

        # Multi-DANE: generar un reporte independiente por cada DANE solicitado.
        if len(danes_list) > 1:
            # 1) Medimos emisiones una sola vez.
            base_emissions: List[Dict[str, Any]] = []
            base_meta: List[Dict[str, Any]] = []
            for pk in detected_bins:
                fc_seed = float(freq_axis[pk])
                L, R, sub, params = _measure_emission_from_bin(pk, fc_seed)

                fc_medida_MHz = float(params["fc_hz"]) / 1e6
                bw_hz_used = _select_bw_hz(params)
                if _is_duplicate_span(base_meta, L, R, float(params["fc_hz"]), float(bw_hz_used)):
                    continue
                bw_medido_kHz = float(bw_hz_used) / 1e3
                p_medida_dBm = _safe_power_dbm(channel_power_dbm_uniform_bins(sub))

                base_em = {
                    "fc_medida_MHz": fc_medida_MHz,
                    "bw_medido_kHz": bw_medido_kHz,
                    "p_medida_dBm": p_medida_dBm,
                    "_L": int(L),
                    "_R": int(R),
                    "_fc_hz": float(params["fc_hz"]),
                    "_match_fc_hz": float(params.get("match_fc_hz", params["fc_hz"])),
                    "_bw_hz": float(bw_hz_used),
                }

                # MER/BER: solo se calcula (y se reporta) para señales en banda TDT.
                # Si NO cae en el rango TDT, estimate_ber_in_band_mqam() retorna {}.
                fc_hz = float(params["fc_hz"])
                bw_hz = float(bw_hz_used)
                tdt_info = estimate_ber_in_band_mqam(
                    frame,
                    f_start_hz=float(sub.f_start_hz),
                    f_stop_hz=float(sub.f_stop_hz),
                    M=64,
                )
                if isinstance(tdt_info, dict) and len(tdt_info) > 0:
                    base_em.update(tdt_info)

                base_meta.append({"_L": int(L), "_R": int(R), "_fc_hz": float(params["fc_hz"]), "_bw_hz": float(bw_hz_used)})
                base_emissions.append(base_em)

            # 2) Para cada DANE, hacemos el matching + cumplimiento con las mismas emisiones medidas.
            results_by_dane: Dict[str, List[Dict[str, Any]]] = {}
            for d in danes_list:
                table_d: List[Dict[str, Any]] = []
                for base in base_emissions:
                    fc_medida_MHz = float(base["fc_medida_MHz"])
                    bw_medido_kHz = float(base["bw_medido_kHz"])
                    p_medida_dBm = base.get("p_medida_dBm", None)

                    fc_match_MHz = float(base.get("_match_fc_hz", base.get("_fc_hz", fc_medida_MHz*1e6))) / 1e6
                    comp = _match_licencia(
                        fc_mhz=fc_match_MHz,
                        bw_khz=bw_medido_kHz,
                        power_dbm=p_medida_dBm,
                        licencia_csv_path=licencia_csv_path,
                        dane_filtro=d,
                        municipio_filtro=municipio_filtro,
                        tolerancia_freq_mhz=FC_MARGIN_MHZ,
                    )

                    fc_nominal_MHz = comp.get("fc_nominal_MHz", None)
                    bw_nominal_kHz = comp.get("bw_nominal_kHz", None)
                    p_nominal_dBm = comp.get("p_nominal_dBm", None)

                    # Delta BW (si comparar_parametros no lo trae, lo calculamos)
                    delta_bw_kHz = comp.get("delta_bw_kHz", None)
                    if delta_bw_kHz is None and bw_nominal_kHz is not None:
                        try:
                            delta_bw_kHz = float(bw_medido_kHz) - float(bw_nominal_kHz)
                        except Exception:
                            delta_bw_kHz = None

                    # Cumplimiento FC/BW (solo tiene sentido si existe licencia/nominal)
                    lic_match = str(comp.get("Licencia", "NO") or "NO").upper()

                    delta_f_MHz = comp.get("delta_f_MHz", None)

                    cumple_fc = None
                    cumple_bw = None
                    cumple_p = None

                    if lic_match == "SI" and fc_nominal_MHz is not None and delta_f_MHz is not None:
                        try:
                            cumple_fc = "SI" if abs(float(delta_f_MHz)) <= FC_MARGIN_MHZ else "NO"
                        except Exception:
                            cumple_fc = None

                    cumple_bw = _bw_compliance_status(
                        lic_match=lic_match,
                        bw_medido_kHz=bw_medido_kHz,
                        bw_nominal_kHz=bw_nominal_kHz,
                        delta_bw_kHz=delta_bw_kHz,
                        bw_margin_khz=BW_MARGIN_KHZ,
                    )

                    # Potencia: p_medida_dBm <= p_nominal_dBm
                    if lic_match == "SI" and p_nominal_dBm is not None and p_medida_dBm is not None:
                        try:
                            cumple_p = "SI" if float(p_medida_dBm) <= float(p_nominal_dBm) else "NO"
                        except Exception:
                            cumple_p = None
                    # Licencia (match por frecuencia): SI si existe match, independientemente de BW/Potencia
                    licencia_final = "SI" if lic_match == "SI" else "NO"

                    # Delta potencia: si potencia medida es None, delta también None
                    delta_p_dB = None if p_medida_dBm is None else comp.get("delta_p_dB", None)

                    row = {
                        "fc_medida_MHz": fc_medida_MHz,
                        "fc_nominal_MHz": fc_nominal_MHz,
                        "delta_f_MHz": delta_f_MHz,
                        "bw_medido_kHz": bw_medido_kHz,
                        "bw_nominal_kHz": bw_nominal_kHz,
                        "delta_bw_kHz": delta_bw_kHz,
                        "p_medida_dBm": p_medida_dBm,
                        "p_nominal_dBm": p_nominal_dBm,
                        "delta_p_dB": delta_p_dB,
                        "Cumple_FC": cumple_fc,
                        "Cumple_BW": cumple_bw,
                        "Cumple_P": cumple_p,
                        "Licencia": licencia_final,
                    }

                    # MER/BER: solo se agrega cuando el cálculo aplica (p. ej., TDT en banda UHF)
                    if "mer_db" in base:
                        row["mer_db"] = base["mer_db"]
                    if "ber_est" in base:
                        row["ber_est"] = base["ber_est"]
                    table_d.append(row)

                results_by_dane[str(d)] = table_d

            out["results_by_dane"] = results_by_dane
            out["num_emissions"] = len(base_emissions)

            # Compatibilidad: 'results' sigue existiendo (primer DANE).
            out["results"] = results_by_dane[str(danes_list[0])]
            _enrich_output_with_rni(out)
            return out

        table: List[Dict[str, Any]] = []

        for pk in detected_bins:
            fc_seed = float(freq_axis[pk])
            L, R, sub, params = _measure_emission_from_bin(pk, fc_seed)

            # MER/BER: solo reportar si está en banda TDT (si no, dict vacío)
            fc_hz_f = float(params["fc_hz"])
            bw_hz_f = float(params["bandwidth_xdb_hz"])
            tdt_info = estimate_ber_in_band_mqam(
                frame,
                f_start_hz=float(sub.f_start_hz),
                f_stop_hz=float(sub.f_stop_hz),
                M=64,
            )

            fc_medida_MHz = float(params["fc_hz"]) / 1e6
            bw_hz_used = _select_bw_hz(params)
            bw_medido_kHz = float(bw_hz_used) / 1e3
            p_medida_dBm = _safe_power_dbm(channel_power_dbm_uniform_bins(sub))

            fc_match_MHz = float(params.get("match_fc_hz", params.get("fc_hz", fc_medida_MHz*1e6))) / 1e6
            comp = _match_licencia(
                fc_mhz=fc_match_MHz,
                bw_khz=bw_medido_kHz,
                power_dbm=p_medida_dBm,
                licencia_csv_path=licencia_csv_path,
                dane_filtro=dane_filtro,
                municipio_filtro=municipio_filtro,
                tolerancia_freq_mhz=FC_MARGIN_MHZ,
            )

            fc_nominal_MHz = comp.get("fc_nominal_MHz", None)
            bw_nominal_kHz = comp.get("bw_nominal_kHz", None)
            p_nominal_dBm = comp.get("p_nominal_dBm", None)

            # Delta BW (si comparar_parametros no lo trae, lo calculamos)
            delta_bw_kHz = comp.get("delta_bw_kHz", None)
            if delta_bw_kHz is None and bw_nominal_kHz is not None:
                try:
                    delta_bw_kHz = float(bw_medido_kHz) - float(bw_nominal_kHz)
                except Exception:
                    delta_bw_kHz = None

            # Cumplimiento FC/BW (solo tiene sentido si existe licencia/nominal)
            lic_match = str(comp.get("Licencia", "NO") or "NO").upper()

            delta_f_MHz = comp.get("delta_f_MHz", None)

            cumple_fc = None
            cumple_bw = None
            cumple_p = None

            if lic_match == "SI" and fc_nominal_MHz is not None and delta_f_MHz is not None:
                try:
                    cumple_fc = "SI" if abs(float(delta_f_MHz)) <= FC_MARGIN_MHZ else "NO"
                except Exception:
                    cumple_fc = None

            cumple_bw = _bw_compliance_status(
                lic_match=lic_match,
                bw_medido_kHz=bw_medido_kHz,
                bw_nominal_kHz=bw_nominal_kHz,
                delta_bw_kHz=delta_bw_kHz,
                bw_margin_khz=BW_MARGIN_KHZ,
            )

            # Potencia: p_medida_dBm <= p_nominal_dBm
            if lic_match == "SI" and p_nominal_dBm is not None and p_medida_dBm is not None:
                try:
                    cumple_p = "SI" if float(p_medida_dBm) <= float(p_nominal_dBm) else "NO"
                except Exception:
                    cumple_p = None
            # Licencia (match por frecuencia): SI si existe match, independientemente de BW/Potencia
            licencia_final = "SI" if lic_match == "SI" else "NO"
            # Delta potencia: si potencia medida es None, delta también None
            delta_p_dB = None if p_medida_dBm is None else comp.get("delta_p_dB", None)

            row = {
                "fc_medida_MHz": fc_medida_MHz,
                "fc_nominal_MHz": fc_nominal_MHz,
                "delta_f_MHz": delta_f_MHz,
                "bw_medido_kHz": bw_medido_kHz,
                "bw_nominal_kHz": bw_nominal_kHz,
                "delta_bw_kHz": delta_bw_kHz,
                "p_medida_dBm": p_medida_dBm,
                "p_nominal_dBm": p_nominal_dBm,
                "delta_p_dB": delta_p_dB,
                "Cumple_FC": cumple_fc,
                "Cumple_BW": cumple_bw,
                "Cumple_P": cumple_p,
                "Licencia": licencia_final,
            }

            if isinstance(tdt_info, dict) and ("ber_est" in tdt_info or "mer_db" in tdt_info):
                if "mer_db" in tdt_info:
                    row["mer_db"] = tdt_info["mer_db"]
                if "ber_est" in tdt_info:
                    row["ber_est"] = tdt_info["ber_est"]

            table.append(row)

        out["results"] = table
        out["num_emissions"] = len(table)
        _enrich_output_with_rni(out)
        return out

    _enrich_output_with_rni(out)
    return out


from types import SimpleNamespace


def _build_processing_args(umbral_db: Optional[float] = None) -> SimpleNamespace:
    """
    Defaults alineados con tu main actual y con los parámetros extra
    usados en process_one_file / split_wide_regions_by_internal_valleys.
    """

    if umbral_db is None:
        delta_above_nf_db = 3.0
    else:
        try:
            delta_above_nf_db = float(umbral_db)
        except Exception:
            delta_above_nf_db = 3.0
        if not np.isfinite(delta_above_nf_db):
            delta_above_nf_db = 3.0
        delta_above_nf_db = max(0.0, delta_above_nf_db)

    return SimpleNamespace(
        # Piso de ruido global
        nf_delta_db=0.5,
        nf_percentile=1.0,
        nf_min_points=4,
        delta_above_nf_db=delta_above_nf_db,

        # Suavizado
        smooth_window=18,
        smooth_polyorder=2,

        # Postproceso de regiones
        merge_gap_hz=15e3,
        min_bw_hz=15e3,

        # Refinamiento local por steps
        refine_percentile=50.0,
        refine_expansion_factor=1.30,
        refine_height_ratio_limit=0.40,

        # Parámetros extra que usa build_step_noise_floor y que no estaban
        # visibles en tu main, pero sí existen en la firma de la función
        trend_window_bins=9,
        trend_slope_threshold_db_per_bin=0.03,
        trend_level_rise_threshold_db=0.35,
        trend_confirm_windows=2,
        trend_min_side_bins=3,
        trend_max_side_bins=None,
        step_overlap_policy="max",

        # Parámetros de split final, tomados de tu código process_one_file
        split_min_bw_hz=1e6,
        split_lateral_valley_height_ratio=0.01,
        split_center_valley_height_ratio=0.15,
        split_left_section_ratio=0.15,
        split_center_section_ratio=0.60,
        split_right_section_ratio=0.15,
        split_min_shoulder_drop_db=1.5,
        split_min_valley_distance_hz=100e3,
        split_min_edge_margin_hz=50e3,

        # Plot / utilitarios
        plot=False,
        show_expanded_windows=False,
        max_files=None,
    )

def _frame_arrays_from_spectrum_frame(frame: "SpectrumFrame") -> Tuple[np.ndarray, np.ndarray]:
    freqs_hz = np.asarray(frame.freq_hz, dtype=float)
    pxx_dbm = np.asarray(frame.amplitudes_dbm, dtype=float).reshape(-1)
    if freqs_hz.size != pxx_dbm.size:
        raise ValueError("Inconsistencia entre freq_hz y amplitudes_dbm en el SpectrumFrame.")
    if freqs_hz.size < 4:
        raise ValueError("El frame debe tener al menos 4 puntos.")
    return freqs_hz, pxx_dbm


def _estimate_window_length(n: int) -> int:
    if n > 4096:
        return 20
    elif 1024 <= n <= 4096:
        return 16
    elif n >= 512:
        return 10
    return 7


def _region_peak_idx(Pxx_dB: np.ndarray, L: int, R: int) -> int:
    L = max(0, int(L))
    R = min(len(Pxx_dB) - 1, int(R))
    if R < L:
        return L
    return int(L + np.argmax(Pxx_dB[L:R + 1]))


def _region_power_dbm(Pxx_dB: np.ndarray, L: int, R: int) -> Optional[float]:
    L = max(0, int(L))
    R = min(len(Pxx_dB) - 1, int(R))
    if R < L:
        return None
    return float(np.max(Pxx_dB[L:R + 1]))


def _run_new_detector_on_frame(
    frame: "SpectrumFrame",
    args: SimpleNamespace,
) -> Dict[str, Any]:
    """
    Adaptador de tu nueva lógica para operar sobre SpectrumFrame en memoria.
    """
    t0 = time.perf_counter()
    freqs_hz, pxx_dbm = _frame_arrays_from_spectrum_frame(frame)

    # 0) Suavizado
    window_length = _estimate_window_length(len(pxx_dbm))
    pxx_smooth_dbm = smooth_psd(
        pxx_dbm,
        window_length=window_length,
        polyorder=args.smooth_polyorder,
    )

    # 1) ETAPA GLOBAL
    global_noise_floor_db = detect_noise_floor_from_psd(
        Pxx=pxx_smooth_dbm,
        delta_dB=args.nf_delta_db,
        noise_percentile=args.nf_percentile,
        min_points_after_filter=args.nf_min_points,
    )
    global_threshold_db = float(global_noise_floor_db + args.delta_above_nf_db)

    bandwidths_init_hz, centers_init_hz, regions_init_idx = detect_channels_from_psd(
        freqs_hz=freqs_hz,
        Pxx_dB=pxx_smooth_dbm,
        noise_floor_db=global_noise_floor_db,
        delta_above_nf_db=args.delta_above_nf_db,
        merge_gap_hz=args.merge_gap_hz,
        min_bw_hz=args.min_bw_hz,
    )

    # 2) ETAPA LOCAL
    step_noise_floor_db, local_nf_info = build_step_noise_floor(
        freqs_hz=freqs_hz,
        Pxx_smooth_dB=pxx_smooth_dbm,
        global_noise_floor_db=global_noise_floor_db,
        initial_regions_idx=regions_init_idx,
        nf_delta_db=args.nf_delta_db,
        nf_min_points=args.nf_min_points,
        delta_above_nf_db=args.delta_above_nf_db,
        refine_percentile=args.refine_percentile,
        refine_expansion_factor=args.refine_expansion_factor,
        refine_height_ratio_limit=args.refine_height_ratio_limit,
    )
    step_threshold_db = np.asarray(step_noise_floor_db, dtype=float) + float(args.delta_above_nf_db)

    # 3) DETECCIÓN FINAL
    bandwidths_hz, centers_hz, regions_idx = detect_channels_from_variable_threshold(
        freqs_hz=freqs_hz,
        Pxx_dB=pxx_smooth_dbm,
        threshold_dB=step_threshold_db,
        merge_gap_hz=args.merge_gap_hz,
        min_bw_hz=args.min_bw_hz,
    )

    # 4) SPLIT FINAL
    bandwidths_hz, centers_hz, regions_idx, split_info = split_wide_regions_by_internal_valleys(
        freqs_hz=freqs_hz,
        Pxx_smooth_dB=pxx_smooth_dbm,
        regions_idx=regions_idx,
        split_min_bw_hz=getattr(args, "split_min_bw_hz", 1e6),
        lateral_valley_height_ratio=getattr(args, "split_lateral_valley_height_ratio", 0.01),
        center_valley_height_ratio=getattr(args, "split_center_valley_height_ratio", 0.15),
        left_section_ratio=getattr(args, "split_left_section_ratio", 0.15),
        center_section_ratio=getattr(args, "split_center_section_ratio", 0.60),
        right_section_ratio=getattr(args, "split_right_section_ratio", 0.15),
        min_shoulder_drop_db=getattr(args, "split_min_shoulder_drop_db", 1.5),
        min_valley_distance_hz=getattr(args, "split_min_valley_distance_hz", 100e3),
        min_edge_margin_hz=getattr(args, "split_min_edge_margin_hz", 50e3),
        min_bw_hz=args.min_bw_hz,
    )

    detected_rows: List[Dict[str, Any]] = []
    for bw_hz, fc_hz, reg in zip(bandwidths_hz, centers_hz, regions_idx):
        L, R = int(reg[0]), int(reg[1])
        peak_idx = _region_peak_idx(pxx_smooth_dbm, L, R)
        power_dbm = _region_power_dbm(pxx_smooth_dbm, L, R)

        detected_rows.append(
            {
                "nearest_bin": int(peak_idx),
                "peak_idx": int(peak_idx),
                "measure_L": int(L),
                "measure_R": int(R),
                "status": "emision",
                "fc_hz": float(fc_hz),
                "fc_mhz": float(fc_hz) / 1e6,
                "bw_hz": float(bw_hz),
                "bw_khz": float(bw_hz) / 1e3,
                "power_dbm": power_dbm,
            }
        )

    _proc_log(
        "_run_new_detector_on_frame "
        f"bins={len(freqs_hz)} "
        f"global_regions={len(regions_init_idx)} "
        f"final_regions={len(regions_idx)} "
        f"detected_rows={len(detected_rows)} "
        f"global_nf_db={float(global_noise_floor_db)} "
        f"global_thr_db={float(global_threshold_db)} "
        f"median_step_nf_db={float(np.median(step_noise_floor_db)) if len(step_noise_floor_db) else None} "
        f"median_step_thr_db={float(np.median(step_threshold_db)) if len(step_threshold_db) else None} "
        f"elapsed_ms={(time.perf_counter() - t0) * 1000.0:.1f}"
    )
    if detected_rows:
        sample = detected_rows[0]
        _proc_log(
            "_run_new_detector_on_frame first_row "
            f"fc_hz={sample.get('fc_hz')} "
            f"bw_hz={sample.get('bw_hz')} "
            f"power_dbm={sample.get('power_dbm')} "
            f"measure_L={sample.get('measure_L')} "
            f"measure_R={sample.get('measure_R')}"
        )
    else:
        _proc_log("_run_new_detector_on_frame produced zero rows after final detection")

    return {
        "freqs_hz": freqs_hz,
        "pxx_dbm": pxx_dbm,
        "pxx_smooth_dbm": pxx_smooth_dbm,
        "global_noise_floor_db": float(global_noise_floor_db),
        "global_threshold_db": float(global_threshold_db),
        "num_detectadas_inicial": int(len(centers_init_hz)),
        "num_detectadas_final": int(len(centers_hz)),
        "centers_hz": [float(x) for x in centers_hz],
        "bandwidths_hz": [float(x) for x in bandwidths_hz],
        "regions_idx": [(int(a), int(b)) for a, b in regions_idx],
        "step_noise_floor_db": np.asarray(step_noise_floor_db, dtype=float),
        "step_threshold_db": np.asarray(step_threshold_db, dtype=float),
        "local_nf_info": local_nf_info,
        "split_info": split_info,
        "detected_rows": detected_rows,
    }


def _pick_best_detected_row_for_peak(
    req_hz: float,
    detected_rows: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
    if not detected_rows:
        return None, None
    deltas = [abs(float(row["fc_hz"]) - float(req_hz)) for row in detected_rows]
    i = int(np.argmin(deltas))
    return detected_rows[i], float(deltas[i])


def process_input(
    inp: PayloadInput,
    corr_csv_path: Optional[str] = None,
    licencia_csv_path: Optional[str] = None,
    dane_filtro: Optional[str] = None,
    danes_filtro: Optional[List[Any]] = None,
    municipio_filtro: Optional[str] = None,
    umbral_db: Optional[float] = None,
    delta_fc_khz: Optional[float] = None,
    delta_bw_khz: Optional[float] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    frame_json, picos, cumplimiento = unpack_input(inp)
    mode = route_mode(picos, cumplimiento)
    try:
        pxx_len = len(frame_json.get("Pxx", frame_json.get("pxx", []))) if isinstance(frame_json, dict) else None
    except Exception:
        pxx_len = None
    _proc_log(
        "process_input start "
        f"mode={mode} cumplimiento={cumplimiento} "
        f"picos_count={len(picos)} pxx_len={pxx_len} "
        f"corr={'yes' if corr_csv_path else 'no'} lic={'yes' if licencia_csv_path else 'no'} "
        f"dane={dane_filtro} danes_count={len(danes_filtro) if isinstance(danes_filtro, list) else 0} "
        f"municipio={municipio_filtro} umbral_db={umbral_db} "
        f"delta_fc_khz={delta_fc_khz} delta_bw_khz={delta_bw_khz}"
    )

    if isinstance(inp, dict) and danes_filtro is None and isinstance(inp.get("danes", None), list):
        danes_filtro = inp.get("danes", None)

    if isinstance(inp, dict) and umbral_db is None and ("umbral_db" in inp):
        try:
            umbral_db = float(inp.get("umbral_db", None))
        except Exception:
            umbral_db = None

    if isinstance(inp, dict) and delta_fc_khz is None and ("delta_fc_khz" in inp):
        try:
            delta_fc_khz = float(inp.get("delta_fc_khz", None))
        except Exception:
            delta_fc_khz = None

    if isinstance(inp, dict) and delta_bw_khz is None and ("delta_bw_khz" in inp):
        try:
            delta_bw_khz = float(inp.get("delta_bw_khz", None))
        except Exception:
            delta_bw_khz = None

    try:
        _dfc = 100.0 if delta_fc_khz is None else float(delta_fc_khz)
    except Exception:
        _dfc = 100.0
    if (not np.isfinite(_dfc)) or (_dfc < 0.0):
        _dfc = 100.0
    fc_margin_mhz = float(_dfc) / 1000.0

    try:
        _dbw = 10.0 if delta_bw_khz is None else float(delta_bw_khz)
    except Exception:
        _dbw = 10.0
    if (not np.isfinite(_dbw)) or (_dbw < 0.0):
        _dbw = 10.0
    bw_margin_khz = float(_dbw)

    danes_list = _normalize_danes(danes_filtro, dane_filtro, municipio_filtro)
    if len(danes_list) == 1 and dane_filtro is None:
        dane_filtro = danes_list[0]

    if mode == "compliance" and licencia_csv_path and (len(danes_list) == 0 and municipio_filtro is None):
        raise ValueError("Para mode=compliance debes pasar --dane (o --municipio legacy) cuando usas --lic")
    _proc_log(
        f"normalized filters dane={dane_filtro} danes_count={len(danes_list)} "
        f"municipio={municipio_filtro} fc_margin_mhz={fc_margin_mhz} bw_margin_khz={bw_margin_khz}"
    )

    out: Dict[str, Any] = {
        "mode": mode,
        "cumplimiento": cumplimiento,
        "picos_count": len(picos),
        "picos": picos,
        "results": [],
        "num_emissions": 0,
        "correction_applied": bool(corr_csv_path),
    }

    if umbral_db is not None:
        out["umbral_db"] = float(umbral_db)

    if len(danes_list) > 1:
        out["danes"] = danes_list

    if "timestamp" in frame_json:
        out["timestamp"] = frame_json["timestamp"]
    if "mac" in frame_json:
        out["mac"] = frame_json["mac"]

    frame = frame_from_payload(frame_json)
    _proc_log(
        f"frame parsed bins={len(frame.amplitudes_dbm)} "
        f"f_start_hz={float(frame.f_start_hz)} f_stop_hz={float(frame.f_stop_hz)} "
        f"bin_hz={float(frame.bin_hz)}"
    )
    if corr_csv_path:
        frame = apply_gain_correction(frame, corr_csv_path)
        _proc_log("gain correction applied")

    args = _build_processing_args(umbral_db=umbral_db)
    _proc_log(
        "detector args "
        f"smooth_window={getattr(args, 'smooth_window', None)} "
        f"smooth_polyorder={getattr(args, 'smooth_polyorder', None)} "
        f"refine_expansion_factor={getattr(args, 'refine_expansion_factor', None)} "
        f"delta_above_nf_db={getattr(args, 'delta_above_nf_db', None)} "
        f"merge_gap_hz={getattr(args, 'merge_gap_hz', None)} "
        f"min_bw_hz={getattr(args, 'min_bw_hz', None)}"
    )
    run = _run_new_detector_on_frame(frame, args)

    freqs_hz = run["freqs_hz"]
    pxx_smooth_dbm = run["pxx_smooth_dbm"]
    step_noise_floor_db = run["step_noise_floor_db"]
    step_threshold_db = run["step_threshold_db"]
    detected_rows = run["detected_rows"]
    _proc_log(
        "detector output "
        f"bins={len(freqs_hz)} detected_rows={len(detected_rows)} "
        f"median_threshold_dbm={float(np.median(step_threshold_db)) if step_threshold_db.size else None} "
        f"median_noise_floor_dbm={float(np.median(step_noise_floor_db)) if step_noise_floor_db.size else None}"
    )
    if detected_rows:
        sample = detected_rows[0]
        _proc_log(
            "first detection "
            f"fc_hz={sample.get('fc_hz')} bw_hz={sample.get('bw_hz')} "
            f"power_dbm={sample.get('power_dbm')} nearest_bin={sample.get('nearest_bin')}"
        )
    else:
        _proc_log("detector produced zero candidate emissions")

    out["umbral"] = float(np.median(step_threshold_db)) if step_threshold_db.size else None
    if debug:
        out["debug"] = _build_debug_payload(step_noise_floor_db, step_threshold_db)

    if mode == "all_emissions":
        _proc_log("entering all_emissions branch")
        out["results"] = [
            {
                "nearest_bin": int(row["nearest_bin"]),
                "status": "emision",
                "fc_hz": float(row["fc_hz"]),
                "fc_mhz": float(row["fc_mhz"]),
                "bw_hz": float(row["bw_hz"]),
                "bw_khz": float(row["bw_khz"]),
                "power_dbm": row.get("power_dbm", None),
            }
            for row in detected_rows
        ]
        out["num_emissions"] = len(out["results"])
        _proc_log(
            f"all_emissions completed num_emissions={out['num_emissions']} "
            f"elapsed_ms={(time.perf_counter() - t0) * 1000.0:.1f}"
        )
        _enrich_output_with_rni(out)
        return out

    if mode == "peaks":
        _proc_log(f"entering peaks branch requested_picos={len(picos)}")
        results: List[Dict[str, Any]] = []

        for p in picos:
            req_hz = pico_to_hz(p)
            req_idx = nearest_bin(freqs_hz, req_hz)
            margin = match_margin_hz(req_hz)

            best_row, best_delta = _pick_best_detected_row_for_peak(req_hz, detected_rows)
            if best_row is None or best_delta is None or best_delta > margin:
                results.append(
                    {
                        "requested_pico": p,
                        "requested_pico_hz": float(req_hz),
                        "nearest_bin": int(req_idx),
                        "fc_hz": float(freqs_hz[req_idx]),
                        "fc_mhz": float(freqs_hz[req_idx]) / 1e6,
                        "status": "ruido",
                        "reason": "no_hay_emision_cercana",
                        "match_margin_hz": float(margin),
                        "matched_peak_hz": (float(best_row["fc_hz"]) if best_row is not None else None),
                        "delta_match_hz": (float(best_delta) if best_delta is not None else None),
                        "Licencia": None,
                    }
                )
                continue

            best_bin = int(best_row["nearest_bin"])
            amp_dbm = float(pxx_smooth_dbm[best_bin])
            nf_dbm = float(step_noise_floor_db[best_bin])
            thr_seed_dbm = float(step_threshold_db[best_bin])

            if amp_dbm < thr_seed_dbm:
                results.append(
                    {
                        "requested_pico": p,
                        "requested_pico_hz": float(req_hz),
                        "match_margin_hz": float(margin),
                        "matched_peak_hz": float(best_row["fc_hz"]),
                        "delta_match_hz": float(best_delta),
                        "nearest_bin": int(best_bin),
                        "fc_hz": float(best_row["fc_hz"]),
                        "fc_mhz": float(best_row["fc_mhz"]),
                        "status": "ruido",
                        "reason": "por_umbral",
                        "amp_dbm": amp_dbm,
                        "nf_dbm": nf_dbm,
                        "thr_seed_dbm": thr_seed_dbm,
                        "Licencia": None,
                    }
                )
                continue

            row: Dict[str, Any] = {
                "requested_pico": p,
                "requested_pico_hz": float(req_hz),
                "match_margin_hz": float(margin),
                "matched_peak_hz": float(best_row["fc_hz"]),
                "delta_match_hz": float(best_delta),
                "nearest_bin": int(best_bin),
                "status": "emision",
                "fc_hz": float(best_row["fc_hz"]),
                "fc_mhz": float(best_row["fc_mhz"]),
                "bw_hz": float(best_row["bw_hz"]),
                "bw_khz": float(best_row["bw_khz"]),
                "power_dbm": best_row.get("power_dbm", None),
            }

            if licencia_csv_path and len(danes_list) > 1:
                comps_por_dane: List[Dict[str, Any]] = []
                for d in danes_list:
                    c = _match_licencia(
                        fc_mhz=float(best_row["fc_mhz"]),
                        bw_khz=float(best_row["bw_khz"]),
                        power_dbm=best_row.get("power_dbm", None),
                        licencia_csv_path=licencia_csv_path,
                        dane_filtro=d,
                        municipio_filtro=municipio_filtro,
                        tolerancia_freq_mhz=fc_margin_mhz,
                    )
                    c2 = dict(c)
                    c2["dane"] = d
                    comps_por_dane.append(c2)

                row["comparaciones_por_dane"] = comps_por_dane
                first = comps_por_dane[0] if comps_por_dane else {}
                if first.get("Licencia") is not None:
                    row["Licencia"] = first.get("Licencia", "NO")
                    row["fc_nominal_MHz"] = first.get("fc_nominal_MHz")
                    row["delta_f_MHz"] = first.get("delta_f_MHz")
                    row["bw_nominal_kHz"] = first.get("bw_nominal_kHz")
                    row["delta_bw_kHz"] = first.get("delta_bw_kHz")
                    row["p_nominal_dBm"] = first.get("p_nominal_dBm")
                    row["delta_p_dB"] = None if best_row.get("power_dbm", None) is None else first.get("delta_p_dB")
            else:
                comp = _match_licencia(
                    fc_mhz=float(best_row["fc_mhz"]),
                    bw_khz=float(best_row["bw_khz"]),
                    power_dbm=best_row.get("power_dbm", None),
                    licencia_csv_path=licencia_csv_path,
                    dane_filtro=dane_filtro,
                    municipio_filtro=municipio_filtro,
                    tolerancia_freq_mhz=fc_margin_mhz,
                )
                if comp.get("Licencia") is not None:
                    row["Licencia"] = comp.get("Licencia", "NO")
                    row["fc_nominal_MHz"] = comp.get("fc_nominal_MHz")
                    row["delta_f_MHz"] = comp.get("delta_f_MHz")
                    row["bw_nominal_kHz"] = comp.get("bw_nominal_kHz")
                    row["delta_bw_kHz"] = comp.get("delta_bw_kHz")
                    row["p_nominal_dBm"] = comp.get("p_nominal_dBm")
                    row["delta_p_dB"] = None if best_row.get("power_dbm", None) is None else comp.get("delta_p_dB")

            results.append(row)

        out["results"] = results
        out["num_emissions"] = len(results)
        matched = sum(1 for row in results if row.get("status") == "emision")
        ruido = sum(1 for row in results if row.get("status") == "ruido")
        _proc_log(
            f"peaks completed matched={matched} ruido={ruido} "
            f"elapsed_ms={(time.perf_counter() - t0) * 1000.0:.1f}"
        )
        _enrich_output_with_rni(out)
        return out

    if mode == "compliance":
        _proc_log(
            f"entering compliance branch detected_rows={len(detected_rows)} "
            f"danes_count={len(danes_list)}"
        )
        if not licencia_csv_path:
            raise ValueError("Para modo compliance debes pasar --lic (ruta al CSV de licencias).")

        FC_MARGIN_MHZ = fc_margin_mhz
        BW_MARGIN_KHZ = bw_margin_khz

        base_emissions: List[Dict[str, Any]] = []
        for row in detected_rows:
            base_emissions.append(
                {
                    "fc_medida_MHz": float(row["fc_mhz"]),
                    "bw_medido_kHz": float(row["bw_khz"]),
                    "p_medida_dBm": row.get("power_dbm", None),
                    "_L": int(row["measure_L"]),
                    "_R": int(row["measure_R"]),
                    "_fc_hz": float(row["fc_hz"]),
                    "_match_fc_hz": float(row["fc_hz"]),
                    "_bw_hz": float(row["bw_hz"]),
                }
            )
        _proc_log(f"base_emissions built count={len(base_emissions)}")

        if len(danes_list) > 1:
            _proc_log("compliance using multi-DANE matching")
            results_by_dane: Dict[str, List[Dict[str, Any]]] = {}
            for d in danes_list:
                table_d: List[Dict[str, Any]] = []
                for base in base_emissions:
                    fc_medida_MHz = float(base["fc_medida_MHz"])
                    bw_medido_kHz = float(base["bw_medido_kHz"])
                    p_medida_dBm = base.get("p_medida_dBm", None)

                    fc_match_MHz = float(base.get("_match_fc_hz", base.get("_fc_hz", fc_medida_MHz * 1e6))) / 1e6
                    comp = _match_licencia(
                        fc_mhz=fc_match_MHz,
                        bw_khz=bw_medido_kHz,
                        power_dbm=p_medida_dBm,
                        licencia_csv_path=licencia_csv_path,
                        dane_filtro=d,
                        municipio_filtro=municipio_filtro,
                        tolerancia_freq_mhz=FC_MARGIN_MHZ,
                    )

                    fc_nominal_MHz = comp.get("fc_nominal_MHz", None)
                    bw_nominal_kHz = comp.get("bw_nominal_kHz", None)
                    p_nominal_dBm = comp.get("p_nominal_dBm", None)

                    delta_bw_kHz = comp.get("delta_bw_kHz", None)
                    if delta_bw_kHz is None and bw_nominal_kHz is not None:
                        try:
                            delta_bw_kHz = float(bw_medido_kHz) - float(bw_nominal_kHz)
                        except Exception:
                            delta_bw_kHz = None

                    lic_match = str(comp.get("Licencia", "NO") or "NO").upper()
                    delta_f_MHz = comp.get("delta_f_MHz", None)

                    cumple_fc = None
                    cumple_bw = None
                    cumple_p = None

                    if lic_match == "SI" and fc_nominal_MHz is not None and delta_f_MHz is not None:
                        try:
                            cumple_fc = "SI" if abs(float(delta_f_MHz)) <= FC_MARGIN_MHZ else "NO"
                        except Exception:
                            cumple_fc = None

                    cumple_bw = _bw_compliance_status(
                        lic_match=lic_match,
                        bw_medido_kHz=bw_medido_kHz,
                        bw_nominal_kHz=bw_nominal_kHz,
                        delta_bw_kHz=delta_bw_kHz,
                        bw_margin_khz=BW_MARGIN_KHZ,
                    )

                    if lic_match == "SI" and p_nominal_dBm is not None and p_medida_dBm is not None:
                        try:
                            cumple_p = "SI" if float(p_medida_dBm) <= float(p_nominal_dBm) else "NO"
                        except Exception:
                            cumple_p = None

                    licencia_final = "SI" if lic_match == "SI" else "NO"
                    delta_p_dB = None if p_medida_dBm is None else comp.get("delta_p_dB", None)

                    table_d.append(
                        {
                            "fc_medida_MHz": fc_medida_MHz,
                            "fc_nominal_MHz": fc_nominal_MHz,
                            "delta_f_MHz": delta_f_MHz,
                            "bw_medido_kHz": bw_medido_kHz,
                            "bw_nominal_kHz": bw_nominal_kHz,
                            "delta_bw_kHz": delta_bw_kHz,
                            "p_medida_dBm": p_medida_dBm,
                            "p_nominal_dBm": p_nominal_dBm,
                            "delta_p_dB": delta_p_dB,
                            "Cumple_FC": cumple_fc,
                            "Cumple_BW": cumple_bw,
                            "Cumple_P": cumple_p,
                            "Licencia": licencia_final,
                        }
                    )

                results_by_dane[str(d)] = table_d
            sample_dane = str(danes_list[0]) if danes_list else None
            sample_rows = len(results_by_dane.get(sample_dane, [])) if sample_dane is not None else 0

            out["results_by_dane"] = results_by_dane
            out["num_emissions"] = len(base_emissions)
            out["results"] = results_by_dane[str(danes_list[0])]
            _proc_log(
                f"compliance multi-DANE completed num_emissions={out['num_emissions']} "
                f"results_by_dane={len(results_by_dane)} sample_rows={sample_rows} "
                f"elapsed_ms={(time.perf_counter() - t0) * 1000.0:.1f}"
            )
            _enrich_output_with_rni(out)
            return out

        table: List[Dict[str, Any]] = []
        for base in base_emissions:
            fc_medida_MHz = float(base["fc_medida_MHz"])
            bw_medido_kHz = float(base["bw_medido_kHz"])
            p_medida_dBm = base.get("p_medida_dBm", None)

            fc_match_MHz = float(base.get("_match_fc_hz", base.get("_fc_hz", fc_medida_MHz * 1e6))) / 1e6
            comp = _match_licencia(
                fc_mhz=fc_match_MHz,
                bw_khz=bw_medido_kHz,
                power_dbm=p_medida_dBm,
                licencia_csv_path=licencia_csv_path,
                dane_filtro=dane_filtro,
                municipio_filtro=municipio_filtro,
                tolerancia_freq_mhz=FC_MARGIN_MHZ,
            )

            fc_nominal_MHz = comp.get("fc_nominal_MHz", None)
            bw_nominal_kHz = comp.get("bw_nominal_kHz", None)
            p_nominal_dBm = comp.get("p_nominal_dBm", None)

            delta_bw_kHz = comp.get("delta_bw_kHz", None)
            if delta_bw_kHz is None and bw_nominal_kHz is not None:
                try:
                    delta_bw_kHz = float(bw_medido_kHz) - float(bw_nominal_kHz)
                except Exception:
                    delta_bw_kHz = None

            lic_match = str(comp.get("Licencia", "NO") or "NO").upper()
            delta_f_MHz = comp.get("delta_f_MHz", None)

            cumple_fc = None
            cumple_bw = None
            cumple_p = None

            if lic_match == "SI" and fc_nominal_MHz is not None and delta_f_MHz is not None:
                try:
                    cumple_fc = "SI" if abs(float(delta_f_MHz)) <= FC_MARGIN_MHZ else "NO"
                except Exception:
                    cumple_fc = None

            cumple_bw = _bw_compliance_status(
                lic_match=lic_match,
                bw_medido_kHz=bw_medido_kHz,
                bw_nominal_kHz=bw_nominal_kHz,
                delta_bw_kHz=delta_bw_kHz,
                bw_margin_khz=BW_MARGIN_KHZ,
            )

            if lic_match == "SI" and p_nominal_dBm is not None and p_medida_dBm is not None:
                try:
                    cumple_p = "SI" if float(p_medida_dBm) <= float(p_nominal_dBm) else "NO"
                except Exception:
                    cumple_p = None

            licencia_final = "SI" if lic_match == "SI" else "NO"
            delta_p_dB = None if p_medida_dBm is None else comp.get("delta_p_dB", None)

            table.append(
                {
                    "fc_medida_MHz": fc_medida_MHz,
                    "fc_nominal_MHz": fc_nominal_MHz,
                    "delta_f_MHz": delta_f_MHz,
                    "bw_medido_kHz": bw_medido_kHz,
                    "bw_nominal_kHz": bw_nominal_kHz,
                    "delta_bw_kHz": delta_bw_kHz,
                    "p_medida_dBm": p_medida_dBm,
                    "p_nominal_dBm": p_nominal_dBm,
                    "delta_p_dB": delta_p_dB,
                    "Cumple_FC": cumple_fc,
                    "Cumple_BW": cumple_bw,
                    "Cumple_P": cumple_p,
                    "Licencia": licencia_final,
                }
            )

        out["results"] = table
        out["num_emissions"] = len(table)
        _proc_log(
            f"compliance single-DANE completed num_emissions={out['num_emissions']} "
            f"elapsed_ms={(time.perf_counter() - t0) * 1000.0:.1f}"
        )
        _enrich_output_with_rni(out)
        return out

    raise ValueError(f"Modo no soportado: {mode}")
