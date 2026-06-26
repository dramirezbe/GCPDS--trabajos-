from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import math
import re
import unicodedata
import os
from functools import lru_cache

import numpy as np
import pandas as pd


def _to_float_series(series: pd.Series) -> pd.Series:
    """Convierte una serie a float de forma robusta.

    Soporta formatos comunes en exportaciones:
      - Decimal con coma: "88,9"
      - Miles con punto y decimal con coma: "1.234,56"
      - Espacios / NBSP / texto sucio
    """
    s = series.astype(str)
    s = s.str.strip().str.replace("\u00A0", " ", regex=False)

    # Dejar solo caracteres típicos de números (incluye signos y separadores)
    # (no borremos la coma/punto aún)
    s = s.str.replace(r"[^0-9,\.\-\+]", "", regex=True)

    def _norm_num(x: str) -> str:
        if x is None:
            return ""
        x = str(x).strip()
        if not x:
            return ""
        # Si tiene '.' y ',' asumimos formato 1.234,56 => quitar miles '.' y cambiar ',' por '.'
        if "," in x and "." in x:
            x = x.replace(".", "")
            x = x.replace(",", ".")
            return x
        # Si solo tiene ',' lo tomamos como decimal
        if "," in x and "." not in x:
            return x.replace(",", ".")
        return x

    s = s.map(_norm_num)
    return pd.to_numeric(s, errors="coerce")


def _norm_dane(x: Any) -> str:
    """Normaliza código DANE.

    - Conserva ceros a la izquierda.
    - Extrae solo dígitos.
    - Si tiene menos de 5 dígitos, rellena con ceros a la izquierda.
    """
    if x is None:
        return ""
    digits = re.sub(r"\D", "", str(x))
    if not digits:
        return ""
    if len(digits) < 5:
        digits = digits.zfill(5)
    return digits


def _norm_text(s: Any) -> str:
    """Normaliza texto: uppercase, sin tildes, espacios colapsados."""
    if s is None:
        return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # normaliza separadores raros
    s = s.replace("\u00A0", " ")
    s = " ".join(s.split())
    return s


def _bandwidth_to_khz_series(values: pd.Series, units: Optional[pd.Series] = None) -> pd.Series:
    """Convierte ancho de banda nominal a kHz respetando la unidad del CSV.

    Soporta Hz, kHz, MHz y GHz. Si la unidad viene vacía o desconocida,
    conserva el valor original para no romper compatibilidad con bases ya limpias.
    """
    bw = _to_float_series(values).astype(float)
    if units is None:
        return bw

    u = units.astype(str).str.strip().str.upper()
    u = u.str.replace(" ", "", regex=False)

    out = bw.copy()
    mask_ghz = u.str.contains("GHZ", na=False)
    mask_mhz = u.str.contains("MHZ", na=False)
    mask_khz = u.str.contains("KHZ", na=False)
    mask_hz = (~mask_khz & ~mask_mhz & ~mask_ghz) & u.str.contains("HZ", na=False)

    out.loc[mask_ghz] = bw.loc[mask_ghz] * 1_000_000.0
    out.loc[mask_mhz] = bw.loc[mask_mhz] * 1_000.0
    out.loc[mask_khz] = bw.loc[mask_khz]
    out.loc[mask_hz] = bw.loc[mask_hz] / 1_000.0
    return out


def _read_licencias_csv(path: str) -> pd.DataFrame:
    """
    Lee licencias robustamente:
    - soporta separador ';' o ',' (algunas bases vienen en uno u otro)
    - preferimos engine C (más estable en archivos grandes)
    """
    # 1) intentar con ';' (muy común en exportaciones ANE)
    try:
        df = pd.read_csv(path, sep=";", encoding="utf-8", on_bad_lines="skip", low_memory=False)
    except Exception:
        # Fallback de encoding típico en Windows
        df = pd.read_csv(path, sep=";", encoding="latin-1", on_bad_lines="skip", low_memory=False)

    # 2) si quedó como una sola columna, probablemente es ','
    if df.shape[1] == 1:
        try:
            df = pd.read_csv(path, sep=",", encoding="utf-8", on_bad_lines="skip", low_memory=False)
        except Exception:
            df = pd.read_csv(path, sep=",", encoding="latin-1", on_bad_lines="skip", low_memory=False)
    # Si viene BOM o nombres raros:
    df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]
    return df


@lru_cache(maxsize=8)
def _load_licencias_prepared(abs_path: str, mtime: float) -> pd.DataFrame:
    """Carga y prepara el CSV de licencias UNA sola vez (solo lectura).

    Optimización: evita re-leer y re-normalizar el CSV en cada comparación.
    Se invalida automáticamente si cambia el mtime del archivo.
    """
    df = _read_licencias_csv(abs_path)

    # =========================
    # Validación de esquema (una sola vez)
    # =========================
    # Mantiene la misma lógica que antes (mismas columnas requeridas),
    # pero evita re-validar en cada llamada a `comparar_parametros()`.
    expected_base = {
        "frecuencia",
        "ancho_de_banda",
        "unidad_ancho_de_banda",
        "potencia",
        "unidad_potencia",
    }
    missing_base = [c for c in expected_base if c not in set(df.columns)]
    if missing_base:
        raise ValueError(
            f"CSV licencias no tiene columnas esperadas. Faltan: {missing_base}. Columnas: {list(df.columns)}"
        )

    has_dane = "codigo_dane" in set(df.columns)
    has_mun = "municipio" in set(df.columns)
    if not (has_dane or has_mun):
        raise ValueError(
            "CSV licencias debe contener columna 'codigo_dane' (nuevo) o 'municipio' (legado). "
            f"Columnas: {list(df.columns)}"
        )

    # Pre-normalizaciones (no cambian la lógica; sólo evitan recomputar)
    if "codigo_dane" in df.columns and "_dane_norm" not in df.columns:
        def _norm_dane_str(x: Any) -> str:
            if x is None:
                return ""
            s = str(x).strip()
            if re.fullmatch(r"\d+\.0", s):
                s = s[:-2]
            digits = re.sub(r"\D", "", s)
            if not digits:
                return ""
            if len(digits) < 5:
                digits = digits.zfill(5)
            return digits

        df["_dane_norm"] = df["codigo_dane"].apply(_norm_dane_str)

    if "municipio" in df.columns and "_mun_norm" not in df.columns:
        df["_mun_norm"] = df["municipio"].apply(_norm_text)

    if "frecuencia" in df.columns and "_fc_nom_mhz" not in df.columns:
        df["_fc_nom_mhz"] = _to_float_series(df["frecuencia"]).astype(float)

    if "ancho_de_banda" in df.columns and "_bw_nom_khz" not in df.columns:
        units_bw = df["unidad_ancho_de_banda"] if "unidad_ancho_de_banda" in df.columns else None
        df["_bw_nom_khz"] = _bandwidth_to_khz_series(df["ancho_de_banda"], units_bw)

    if "potencia" in df.columns and "_p_nom_dbm" not in df.columns:
        p_nom = _to_float_series(df["potencia"]).astype(float)
        if "unidad_potencia" in df.columns:
            units = df["unidad_potencia"]
        else:
            units = pd.Series(["dBm"] * len(df), index=df.index)
        df["_p_nom_dbm"] = [_power_to_dbm(pp, uu) for pp, uu in zip(p_nom.values, units.values)]

    df = df.reset_index(drop=True)
    df.attrs["__schema_ok"] = True
    return df


def _get_licencias_prepared(path: str) -> pd.DataFrame:
    """Devuelve el DF de licencias cacheado (solo lectura)."""
    abs_path = os.path.abspath(path)
    try:
        mtime = float(os.path.getmtime(abs_path))
    except OSError:
        mtime = 0.0
    return _load_licencias_prepared(abs_path, mtime)



@lru_cache(maxsize=8)
def _load_licencias_indexed(abs_path: str, mtime: float) -> tuple[pd.DataFrame, Optional[dict]]:
    """Carga DF preparado y crea un índice por DANE (posiciones por _dane_norm).

    Mantiene el DF en modo solo lectura; el índice acelera el filtro por DANE
    evitando escanear todo el CSV en cada comparación.
    """
    df = _load_licencias_prepared(abs_path, mtime)

    dane_index = None
    if "_dane_norm" in df.columns:
        try:
            # dict[str, np.ndarray[int]] con posiciones (para usar con .iloc)
            key5 = df["_dane_norm"].astype(str).str.slice(0, 5)
            dane_index = df.groupby(key5, sort=False).indices
        except Exception:
            dane_index = None

    return df, dane_index


def _get_licencias_indexed(path: str) -> tuple[pd.DataFrame, Optional[dict]]:
    """Devuelve (DF licencias, índice por DANE) cacheado."""
    abs_path = os.path.abspath(path)
    try:
        mtime = float(os.path.getmtime(abs_path))
    except OSError:
        mtime = 0.0
    return _load_licencias_indexed(abs_path, mtime)


@lru_cache(maxsize=8)
def _load_licencias_fast_index(
    abs_path: str, mtime: float
) -> tuple[pd.DataFrame, Optional[dict], Optional[dict]]:
    """Extiende `_load_licencias_indexed` con una estructura rápida por DANE.

    Objetivo: acelerar el matching cuando se solicitan muchos DANEs (p. ej. 62),
    evitando:
      - crear copias de DataFrame por cada llamada
      - recalcular delta_f sobre todo el subconjunto
      - ordenar por score en cada comparación

    Esta función NO cambia la lógica del matching: sólo precomputamos arrays y
    un índice ordenado por frecuencia para poder hacer búsqueda por rango.
    """
    df, dane_index = _load_licencias_indexed(abs_path, mtime)

    # Si no hay índice por DANE o no existen columnas normalizadas, no hay fast path.
    if dane_index is None or "_fc_nom_mhz" not in df.columns:
        return df, dane_index, None

    # Arrays base (view cuando es posible)
    try:
        fc_all = df["_fc_nom_mhz"].to_numpy(dtype=float, copy=False)
    except Exception:
        fc_all = np.asarray(df["_fc_nom_mhz"], dtype=float)

    bw_all = None
    if "_bw_nom_khz" in df.columns:
        try:
            bw_all = df["_bw_nom_khz"].to_numpy(dtype=float, copy=False)
        except Exception:
            bw_all = np.asarray(df["_bw_nom_khz"], dtype=float)

    p_all = None
    if "_p_nom_dbm" in df.columns:
        try:
            p_all = df["_p_nom_dbm"].to_numpy(dtype=float, copy=False)
        except Exception:
            p_all = np.asarray(df["_p_nom_dbm"], dtype=float)

    dane_row_sorted: dict[str, np.ndarray] = {}
    dane_fc_sorted: dict[str, np.ndarray] = {}

    # Precomputar arrays ordenados por fc para cada key5.
    # Nota: almacenamos únicamente filas con fc finita.
    for key5, idxs in dane_index.items():
        try:
            idx_arr = np.asarray(list(idxs), dtype=np.int32)
        except Exception:
            continue
        if idx_arr.size == 0:
            continue

        fc = fc_all[idx_arr]
        m = np.isfinite(fc)
        if not np.any(m):
            continue
        idx_arr = idx_arr[m]
        fc = fc[m]

        # Orden estable por frecuencia (para búsqueda por rango)
        order = np.argsort(fc, kind="mergesort")
        idx_sorted = idx_arr[order]
        fc_sorted = fc[order]

        dane_row_sorted[str(key5)] = idx_sorted
        dane_fc_sorted[str(key5)] = fc_sorted

    fast = {
        "fc_all": fc_all,
        "bw_all": bw_all,
        "p_all": p_all,
        "dane_row_sorted": dane_row_sorted,
        "dane_fc_sorted": dane_fc_sorted,
    }
    return df, dane_index, fast


def _get_licencias_fast_indexed(path: str) -> tuple[pd.DataFrame, Optional[dict], Optional[dict]]:
    """Devuelve (DF licencias, índice por DANE, estructura fast) cacheado."""
    abs_path = os.path.abspath(path)
    try:
        mtime = float(os.path.getmtime(abs_path))
    except OSError:
        mtime = 0.0
    return _load_licencias_fast_index(abs_path, mtime)


def _si_no(x: Any) -> str:
    """Normaliza a 'SI'/'NO' (sin tildes ni caracteres raros)."""
    if x is None:
        return "NO"
    s = str(x).strip().upper()
    # Normalizaciones comunes
    s = (
        s.replace("SÍ", "SI")
        .replace("SÍ", "SI")
        .replace("SÝ", "SI")
        .replace("YES", "SI")
        .replace("TRUE", "SI")
    )
    if s in ("SI", "S", "1"):
        return "SI"
    return "NO"


def _power_to_dbm(p: float, unit: str) -> float:
    """Convierte potencia (varias unidades) a dBm.

    Soporta: dBm, dBW, W, kW, mW, uW (y variantes en texto).
    Si llega "dB" (ambigua), se asume dBm para mantener la impresión en dBm.
    """
    u = _norm_text(unit)
    if not np.isfinite(p):
        return float("nan")

    # ya está en dBm
    if u in ("DBM", "DB", "DBM."):
        return float(p)

    # dBW -> dBm
    if u in ("DBW", "DBW."):
        return float(p) + 30.0

    # potencia lineal -> dBm
    # Normalizamos algunas variantes
    if u in ("MW", "M W", "MILLIWATT", "MILLIWATTS"):
        if p <= 0:
            return float("nan")
        # mW a W: p/1000
        return 10.0 * math.log10(p)  # 10*log10(mW) ya está referido a 1mW

    if u in ("UW", "U W", "MICROWATT", "MICROWATTS"):
        if p <= 0:
            return float("nan")
        # uW -> mW: p/1000
        return 10.0 * math.log10(p) - 30.0

    if u in ("W", "WATTS", "WATT"):
        if p <= 0:
            return float("nan")
        return 10.0 * math.log10(p) + 30.0

    if u in ("KW", "K W", "KILOWATT", "KILOWATTS"):
        if p <= 0:
            return float("nan")
        return 10.0 * math.log10(p * 1000.0) + 30.0

    if u in ("MWATT", "MEGAWATT", "MEGAWATTS"):
        if p <= 0:
            return float("nan")
        return 10.0 * math.log10(p * 1e6) + 30.0

    # si no reconoce, intenta como W si es positiva
    if p > 0:
        return 10.0 * math.log10(p) + 30.0
    return float("nan")


def comparar_parametros(
    f_medida: float,                 # MHz
    bw_medido: float,                # kHz
    p_medida: float,                 # dBm
    ruta_csv: str,
    tolerancia_freq: float = 0.1,    # MHz
    dane_filtro: Optional[str] = None,
    municipio_filtro: Optional[str] = None,  # compatibilidad hacia atrás
) -> Dict[str, Any]:
    """
    Encuentra la licencia que mejor calza por frecuencia (principal),
    opcionalmente filtrando por *codigo_dane* (nuevo) o por municipio (legado).

    Devuelve:
      - Licencia: "SI" o "NO"
      - fc_nominal_MHz, bw_nominal_kHz, p_nominal_dBm
      - delta_f_MHz, delta_bw_kHz, delta_p_dB
    """
    df, dane_index, fast = _get_licencias_fast_indexed(ruta_csv)

    # Validación mínima de columnas esperadas (se hace 1 vez en el cache)
    if not bool(getattr(df, "attrs", {}).get("__schema_ok", False)):
        expected_base = {"frecuencia", "ancho_de_banda", "unidad_ancho_de_banda", "potencia", "unidad_potencia"}
        missing_base = [c for c in expected_base if c not in set(df.columns)]
        if missing_base:
            raise ValueError(
                f"CSV licencias no tiene columnas esperadas. Faltan: {missing_base}. Columnas: {list(df.columns)}"
            )
        has_dane = "codigo_dane" in set(df.columns)
        has_mun = "municipio" in set(df.columns)
        if not (has_dane or has_mun):
            raise ValueError(
                "CSV licencias debe contener columna 'codigo_dane' (nuevo) o 'municipio' (legado). "
                f"Columnas: {list(df.columns)}"
            )

    has_dane = "codigo_dane" in set(df.columns)
    has_mun = "municipio" in set(df.columns)

    df2 = df

    # Filtro por DANE (preferido)
    dane_req = str(dane_filtro).strip() if dane_filtro is not None else ""
    if dane_req:
        if not has_dane:
            raise ValueError("Se recibió dane_filtro pero el CSV no tiene columna 'codigo_dane'.")

        def _norm_dane_str(x: Any) -> str:
            """Normaliza un código DANE a sólo dígitos, sin perder ceros a la izquierda."""
            if x is None:
                return ""
            s = str(x).strip()
            # quita .0 si viene como 11001.0
            if re.fullmatch(r"\d+\.0", s):
                s = s[:-2]
            digits = re.sub(r"\D", "", s)
            if not digits:
                return ""
            # Municipios son 5 dígitos; algunos archivos traen 4 (sin cero inicial)
            if len(digits) < 5:
                digits = digits.zfill(5)
            return digits

        # Fast-normalización común: evita regex cuando ya viene limpio
        if dane_req.isdigit() and len(dane_req) == 5:
            dane_req_n = dane_req
        else:
            dane_req_n = _norm_dane_str(dane_req)

        # Si el usuario pasa el municipio (5 dígitos), acepta también códigos extendidos que empiecen por esos 5.
        # Optimización: cuando hay fast-index (len==5), NO construimos subconjuntos de DataFrame aquí.
        # La selección por frecuencia se hace más abajo en un fast-path O(logN + K).
        if len(dane_req_n) == 5 and fast is not None:
            # No filtrar df2 aquí (evita copias/costes). El fast-path se encarga.
            pass
        elif len(dane_req_n) == 5 and dane_index is not None:
            idxs = dane_index.get(dane_req_n)
            if idxs is None or len(idxs) == 0:
                df2 = df2.iloc[0:0]
            else:
                df2 = df2.iloc[idxs]
        else:
            dane_col = df2["_dane_norm"] if "_dane_norm" in df2.columns else df2["codigo_dane"].apply(_norm_dane_str)
            if len(dane_req_n) == 5:
                df2 = df2[dane_col.astype(str).str.startswith(dane_req_n, na=False)].copy()
            else:
                df2 = df2[dane_col == dane_req_n].copy()

    # Filtro por municipio (legado)
    mun_req = _norm_text(municipio_filtro) if municipio_filtro else ""
    if (not dane_req) and mun_req:
        if not has_mun:
            raise ValueError("Se recibió municipio_filtro pero el CSV no tiene columna 'municipio'.")
        mun_col = df2["_mun_norm"] if "_mun_norm" in df2.columns else df2["municipio"].apply(_norm_text)
        df2 = df2[mun_col == mun_req].copy()
        # si por algún motivo el municipio viene con dobles espacios o variantes,
        # al menos intenta contención suave:
        if df2.empty:
            if "_mun_norm" in df.columns:
                df2 = df[df["_mun_norm"].astype(str).str.contains(mun_req, na=False)].copy()
            else:
                df2 = df[df["municipio"].apply(_norm_text).astype(str).str.contains(mun_req, na=False)].copy()

    # =========================
    # Selección de candidato por frecuencia (fast path cuando hay DANE)
    # =========================
    # Si estamos filtrando por DANE de 5 dígitos y tenemos fast-index, evitamos
    # construir DataFrames intermedios y ordenar por score en cada llamada.
    if dane_req and (fast is not None) and (len(dane_req_n) == 5):
        dane_key = str(dane_req_n)
        idx_sorted = fast["dane_row_sorted"].get(dane_key)
        fc_sorted = fast["dane_fc_sorted"].get(dane_key)
        if idx_sorted is None or fc_sorted is None or len(idx_sorted) == 0:
            return {"Licencia": "NO"}

        f0 = float(f_medida)
        tol = float(tolerancia_freq)
        lo = int(np.searchsorted(fc_sorted, f0 - tol, side="left"))
        hi = int(np.searchsorted(fc_sorted, f0 + tol, side="right"))
        if hi <= lo:
            return {"Licencia": "NO"}

        cand_rows = idx_sorted[lo:hi]
        cand_fc = fc_sorted[lo:hi]
        if cand_rows.size == 0:
            return {"Licencia": "NO"}

        abs_df = np.abs(cand_fc - f0)

        bw_all = fast.get("bw_all")
        p_all = fast.get("p_all")
        bw_nom = bw_all[cand_rows] if bw_all is not None else None
        p_nom = p_all[cand_rows] if p_all is not None else None

        # Score: |delta_f| + 1e-3*|delta_bw| si hay BW finitos.
        score = abs_df
        if bw_nom is not None and np.any(np.isfinite(bw_nom)):
            dbw = np.where(np.isfinite(bw_nom), np.abs(bw_nom - float(bw_medido)), 0.0)
            score = score + 1e-3 * dbw

        # Elegir mínimo; en empate, preferir menor índice original (similar a "primero")
        min_score = float(np.min(score))
        pos = np.where(score == min_score)[0]
        if pos.size == 1:
            k = int(pos[0])
        else:
            # tie-break determinista por menor índice de fila en el DF
            k = int(pos[np.argmin(cand_rows[pos])])

        fc_nominal_MHz = float(cand_fc[k])
        bw_val = float(bw_nom[k]) if (bw_nom is not None and np.isfinite(bw_nom[k])) else None
        p_val = float(p_nom[k]) if (p_nom is not None and np.isfinite(p_nom[k])) else None
        bw_nominal_kHz = bw_val
        p_nominal_dBm = p_val

    else:
        # ----- Ruta fallback (municipio o DANE no indexable) -----
        # Frecuencia nominal (MHz)
        # Ojo: en muchas exportaciones viene como "88,9" (coma decimal) y pd.to_numeric lo vuelve NaN.
        if "_fc_nom_mhz" in df2.columns:
            fc_nom = df2["_fc_nom_mhz"].astype(float)
        else:
            fc_nom = _to_float_series(df2["frecuencia"]).astype(float)
            # Evita mutar el DF cacheado
            df2 = df2.copy()
            df2["_fc_nom_mhz"] = fc_nom

        # Candidatos por frecuencia
        df2 = df2[np.isfinite(df2["_fc_nom_mhz"])]
        if df2.empty:
            return {"Licencia": "NO"}

        # Candidatos por frecuencia (evita mutar el DF cacheado)
        delta_f = df2["_fc_nom_mhz"].astype(float) - float(f_medida)
        dfcand = df2[np.abs(delta_f) <= float(tolerancia_freq)].copy()
        if dfcand.empty:
            return {"Licencia": "NO"}
        dfcand["_delta_f_mhz"] = dfcand["_fc_nom_mhz"].astype(float) - float(f_medida)

        # BW nominal (kHz) (si existe)
        if "_bw_nom_khz" in dfcand.columns:
            bw_nom = dfcand["_bw_nom_khz"].astype(float)
        else:
            units_bw = dfcand["unidad_ancho_de_banda"] if "unidad_ancho_de_banda" in dfcand.columns else None
            bw_nom = _bandwidth_to_khz_series(dfcand["ancho_de_banda"], units_bw)
            dfcand["_bw_nom_khz"] = bw_nom

        # Potencia nominal a dBm (si ya está precalculada en el cache, no recalcular)
        if "_p_nom_dbm" not in dfcand.columns:
            p_nom = _to_float_series(dfcand["potencia"]).astype(float)
            dfcand["_p_nom_dbm"] = [
                _power_to_dbm(float(p), str(u))
                for p, u in zip(p_nom.values, dfcand["unidad_potencia"].values)
            ]

        # Score: prioriza |delta_f| (lo más importante).
        # Si hay empate, usa BW más cercano (si está disponible).
        dfcand["_score"] = np.abs(dfcand["_delta_f_mhz"])
        if np.any(np.isfinite(dfcand["_bw_nom_khz"].values)):
            dfcand["_score"] = dfcand["_score"] + 1e-3 * np.abs(dfcand["_bw_nom_khz"] - float(bw_medido)).fillna(0.0)

        best = dfcand.sort_values("_score", ascending=True).iloc[0]

        fc_nominal_MHz = float(best["_fc_nom_mhz"])
        bw_nominal_kHz = float(best["_bw_nom_khz"]) if np.isfinite(best["_bw_nom_khz"]) else None
        p_nominal_dBm = float(best["_p_nom_dbm"]) if np.isfinite(best["_p_nom_dbm"]) else None

    delta_f_MHz = float(f_medida - fc_nominal_MHz)
    delta_bw_kHz = (float(bw_medido) - bw_nominal_kHz) if bw_nominal_kHz is not None else None
    delta_p_dB = (float(p_medida) - p_nominal_dBm) if p_nominal_dBm is not None else None

    return {
        "Licencia": "SI",
        "fc_nominal_MHz": fc_nominal_MHz,
        "bw_nominal_kHz": bw_nominal_kHz,
        "p_nominal_dBm": p_nominal_dBm,
        "delta_f_MHz": delta_f_MHz,
        "delta_bw_kHz": delta_bw_kHz,
        "delta_p_dB": delta_p_dB,
    }
