from __future__ import annotations

import argparse
import math
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from flask import Flask, request, jsonify

from src.processor import process_input

app = Flask(__name__)

# Inicializar configuración desde variables de entorno al arrancar
# (necesario para gunicorn, que no llama a main())
app.config["DEFAULT_LIC_CSV"] = os.environ.get("ANE_LIC_CSV", "").strip() or None
app.config["DEFAULT_CORR_CSV"] = os.environ.get("ANE_CORR_CSV", "").strip() or None
app.config["ALLOW_JSON_PATH"] = os.environ.get("ANE_ALLOW_JSON_PATH", "").lower() in ("1", "true", "yes")
app.config["VERBOSE_LOGS"] = os.environ.get("ANE_VERBOSE_LOGS", "1").lower() not in ("0", "false", "no")

# ---------------------------
# Helpers
# ---------------------------

META_KEYS = {
    "frame", "json_path", "cumplimiento", "picos", "lic", "corr", "dane", "danes", "municipio", "umbral_db", "delta_fc_khz", "delta_bw_khz"
}

def parse_umbral_db(value: Any) -> Optional[float]:
    """Parsea umbral_db (dB sobre el piso de ruido)."""
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if not math.isfinite(v):
        return None
    return float(v)


def parse_delta_fc_khz(value: Any) -> Optional[float]:
    """Parsea delta_fc_khz (tolerancia de matching por FC en kHz)."""
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if not math.isfinite(v):
        return None
    if v < 0.0:
        v = 0.0
    return float(v)

def parse_delta_bw_khz(value: Any) -> Optional[float]:
    """Parsea delta_bw_khz (tolerancia de cumplimiento BW en kHz)."""
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if not math.isfinite(v):
        return None
    return float(v)

def parse_picos_arg(picos_arg: Optional[Union[str, List[Any]]]) -> List[float]:
    if picos_arg is None:
        return []
    if isinstance(picos_arg, list):
        out: List[float] = []
        for x in picos_arg:
            try:
                out.append(float(x))
            except Exception:
                pass
        return out

    s = str(picos_arg).strip()
    if s == "":
        return []

    # JSON list style: "[92.86, 95.9]"
    if s.startswith("[") and s.endswith("]"):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [float(x) for x in arr]
        except Exception:
            pass

    # CSV style: "92.86,95.9"
    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    out2: List[float] = []
    for p in parts:
        try:
            out2.append(float(p))
        except Exception:
            pass
    return out2


def parse_danes_arg(danes_arg: Optional[Union[str, List[Any]]]) -> List[str]:
    """Parsea lista de DANEs desde:
      - lista JSON: ["11001","17001"]
      - string CSV: "11001,17001"
      - string JSON list: "[11001,17001]"
    """
    if danes_arg is None:
        return []

    if isinstance(danes_arg, list):
        out: List[str] = []
        for x in danes_arg:
            nd = normalize_dane(x)
            if nd is not None:
                out.append(nd)
        return out

    s = str(danes_arg).strip()
    if s == "":
        return []

    if s.startswith("[") and s.endswith("]"):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                out: List[str] = []
                for x in arr:
                    nd = normalize_dane(x)
                    if nd is not None:
                        out.append(nd)
                return out
        except Exception:
            pass

    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    out2: List[str] = []
    for p in parts:
        nd = normalize_dane(p)
        if nd is not None:
            out2.append(nd)
    return out2

def normalize_dane(d: Optional[Any]) -> Optional[str]:
    if d is None:
        return None
    s = str(d).strip()
    if s == "":
        return None
    # Si llega como "11001.0" por conversiones, lo limpiamos
    if s.replace(".", "", 1).isdigit() and "." in s:
        try:
            s2 = str(int(float(s)))
            return s2
        except Exception:
            return s
    return s

def is_wrapper_object(body: Any) -> bool:
    """Wrapper: dict que contiene metadatos (cumplimiento/dane/picos/etc)."""
    if not isinstance(body, dict):
        return False
    return any(k in body for k in META_KEYS)

def load_frame_from_json_path(json_path: str) -> Any:
    p = Path(json_path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def get_defaults() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Defaults del servidor (se setean al arrancar).
    - default_lic_csv: ruta CSV licencias
    - default_corr_csv: ruta CSV correcciones
    - allow_json_path: permitir que el cliente mande json_path (NO recomendado en prod)
    """
    return (
        app.config.get("DEFAULT_LIC_CSV"),
        app.config.get("DEFAULT_CORR_CSV"),
        bool(app.config.get("ALLOW_JSON_PATH", False)),
    )


def _server_log(message: str) -> None:
    if not bool(app.config.get("VERBOSE_LOGS", True)):
        return
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"\033[95m[SERVER {stamp}]\033[0m"
    print(f"{prefix} {message}", flush=True)


def _safe_len(value: Any) -> int:
    try:
        return len(value)
    except Exception:
        return 0


def _frame_summary(frame_json: Any) -> str:
    if not isinstance(frame_json, dict):
        return f"frame_type={type(frame_json).__name__}"

    pxx = frame_json.get("Pxx", frame_json.get("pxx", []))
    pxx_len = _safe_len(pxx)
    start = frame_json.get("start_freq_hz", frame_json.get("f_start_hz", None))
    end = frame_json.get("end_freq_hz", frame_json.get("f_stop_hz", None))
    timestamp = frame_json.get("timestamp", None)
    return (
        f"pxx_len={pxx_len} "
        f"start_freq_hz={start} "
        f"end_freq_hz={end} "
        f"timestamp={timestamp}"
    )


def _meta_summary(meta: Dict[str, Any]) -> str:
    picos = parse_picos_arg(meta.get("picos", None))
    danes = parse_danes_arg(meta.get("danes", None))
    dane = normalize_dane(meta.get("dane", None))
    municipio = meta.get("municipio", None)
    try:
        cumplimiento = int(meta.get("cumplimiento", 0))
    except Exception:
        cumplimiento = 0

    mode = "peaks" if len(picos) > 0 else ("compliance" if cumplimiento == 1 else "all_emissions")
    return (
        f"mode={mode} "
        f"cumplimiento={cumplimiento} "
        f"picos_count={len(picos)} "
        f"dane={dane} "
        f"danes_count={len(danes)} "
        f"municipio={municipio} "
        f"umbral_db={meta.get('umbral_db', None)} "
        f"delta_fc_khz={meta.get('delta_fc_khz', None)} "
        f"delta_bw_khz={meta.get('delta_bw_khz', None)}"
    )


def _result_summary(out: Any) -> str:
    if not isinstance(out, dict):
        return f"result_type={type(out).__name__}"

    results = out.get("results", [])
    rbd = out.get("results_by_dane", {})
    return (
        f"mode={out.get('mode', None)} "
        f"num_emissions={out.get('num_emissions', None)} "
        f"results_len={_safe_len(results)} "
        f"results_by_dane={_safe_len(rbd)} "
        f"umbral={out.get('umbral', None)} "
        f"error={out.get('error', None)}"
    )


# ---------------------------
# Routes
# ---------------------------

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/analyze")
def analyze():
    """
    Recomendado (modo ANE/sensores):
    {
      "frame": { ...JSON COMPLETO DE MEDICIÓN... },
      "cumplimiento": 1,
      "dane": "11001",
      "danes": ["11001", "17001"],
      "picos": [92.86, 95.9]    // opcional
    }

    Compatibilidad local (NO recomendado en prod):
    {
      "json_path": "C:\\ruta\\archivo.json",
      "cumplimiento": 1,
      "dane": "11001"
    }
    -> solo si el servidor se arrancó con --allow-json-path
    """
    try:
        t0 = time.perf_counter()
        body = request.get_json(force=True, silent=False)

        default_lic_csv, default_corr_csv, allow_json_path = get_defaults()

        # 1) Determinar frame + meta
        frame_json: Any
        meta: Dict[str, Any]

        if is_wrapper_object(body) and isinstance(body, dict) and "frame" in body:
            meta = body
            frame_json = body["frame"]

        elif is_wrapper_object(body) and isinstance(body, dict) and "json_path" in body:
            if not allow_json_path:
                return jsonify({
                    "error": "Por seguridad, este servidor no permite 'json_path'. Envía el JSON completo en 'frame'."
                }), 400
            meta = body
            frame_json = load_frame_from_json_path(str(body["json_path"]))

        else:
            # Si mandan el JSON "crudo" (solo frame), aceptamos,
            # y leemos metadatos desde query params.
            frame_json = body
            meta = {
                "cumplimiento": request.args.get("cumplimiento", 0),
                "picos": request.args.get("picos", None),
                "dane": request.args.get("dane", None),
                "danes": request.args.get("danes", None),
                "municipio": request.args.get("municipio", None),
                "umbral_db": request.args.get("umbral_db", None),
                "delta_fc_khz": request.args.get("delta_fc_khz", None),
                "lic": request.args.get("lic", None),
                "corr": request.args.get("corr", None),
            }

        _server_log(
            f"POST /analyze remote={request.remote_addr} "
            f"content_length={request.content_length} "
            f"{_meta_summary(meta)} "
            f"{_frame_summary(frame_json)}"
        )

        # 2) Meta params
        try:
            cumplimiento = int(meta.get("cumplimiento", 0))
        except Exception:
            cumplimiento = 0

        picos_list = parse_picos_arg(meta.get("picos", None))
        umbral_db = parse_umbral_db(meta.get("umbral_db", None))
        delta_fc_khz = parse_delta_fc_khz(meta.get("delta_fc_khz", None))
        delta_bw_khz = parse_delta_bw_khz(meta.get("delta_bw_khz", None))

        # rutas: si no vienen, usar defaults del servidor
        corr_csv_path = meta.get("corr", None) or default_corr_csv
        lic_csv_path  = meta.get("lic", None)  or default_lic_csv

        # compatibilidad municipio/dane
        dane_filtro = normalize_dane(meta.get("dane", None))
        danes_list = parse_danes_arg(meta.get("danes", None))
        if len(danes_list) > 0:
            dane_filtro = None
        municipio_filtro = meta.get("municipio", None)

        # Si mandan municipio y no dane, y municipio es numérico => tratar como dane
        if len(danes_list) == 0 and dane_filtro is None and municipio_filtro is not None:
            m = str(municipio_filtro).strip()
            if m.isdigit():
                dane_filtro = m
                municipio_filtro = None

        # 3) Regla: all_emissions (cumplimiento=0 y sin picos) => ignorar licencias
        if cumplimiento == 0 and len(picos_list) == 0:
            lic_csv_path = None

        # 4) Construir payload como espera process_input()
        payload = [frame_json, picos_list, cumplimiento]

        out = process_input(
            payload,
            corr_csv_path=corr_csv_path,
            licencia_csv_path=lic_csv_path,
            dane_filtro=dane_filtro,
            danes_filtro=(danes_list if len(danes_list) > 0 else None),
            municipio_filtro=municipio_filtro,
            umbral_db=umbral_db,
            delta_fc_khz=delta_fc_khz,
            delta_bw_khz=delta_bw_khz,
            debug=bool(app.config.get("RETURN_DEBUG", False)),
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        _server_log(
            f"POST /analyze completed in {elapsed_ms:.1f} ms | "
            f"{_result_summary(out)}"
        )

        return jsonify(out)

    except Exception as e:
        _server_log(f"POST /analyze failed: {type(e).__name__}: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/analyze_batch")
def analyze_batch():
    """
    Procesa múltiples frames en una sola llamada HTTP.

    Body JSON:
    {
      "frames": [
        { ...mismo payload que /analyze... },
        ...
      ],
      "max_workers": 8   // opcional, default 8
    }

    Respuesta:
    {
      "results": [ <resultado /analyze para frame 0>, <resultado frame 1>, ... ]
    }
    Los resultados mantienen el mismo orden que los frames de entrada.
    """
    try:
        t0 = time.perf_counter()
        body = request.get_json(force=True, silent=False)
        if not isinstance(body, dict) or "frames" not in body:
            return jsonify({"error": "El body debe ser {frames: [...], max_workers?: int}"}), 400

        frames_input: List[Any] = body["frames"]
        if not isinstance(frames_input, list) or len(frames_input) == 0:
            return jsonify({"error": "'frames' debe ser una lista no vacía"}), 400

        max_workers: int = int(body.get("max_workers", 8))
        if max_workers < 1:
            max_workers = 1
        if max_workers > 32:
            max_workers = 32

        _server_log(
            f"POST /analyze_batch remote={request.remote_addr} "
            f"frames={len(frames_input)} max_workers={max_workers}"
        )

        default_lic_csv, default_corr_csv, allow_json_path = get_defaults()

        def _process_one(idx: int, frame_body: Any) -> Tuple[int, Any]:
            """Procesa un frame individual con la misma lógica que /analyze."""
            try:
                if not isinstance(frame_body, dict):
                    return idx, {"error": "El frame debe ser un dict"}

                meta = frame_body
                frame_json = frame_body.get("frame", frame_body)

                if "frame" in frame_body:
                    frame_json = frame_body["frame"]
                else:
                    frame_json = frame_body

                _server_log(
                    f"POST /analyze_batch frame[{idx}] "
                    f"{_meta_summary(meta)} "
                    f"{_frame_summary(frame_json)}"
                )

                try:
                    cumplimiento = int(meta.get("cumplimiento", 0))
                except Exception:
                    cumplimiento = 0

                picos_list = parse_picos_arg(meta.get("picos", None))
                umbral_db = parse_umbral_db(meta.get("umbral_db", None))
                delta_fc_khz = parse_delta_fc_khz(meta.get("delta_fc_khz", None))
                delta_bw_khz = parse_delta_bw_khz(meta.get("delta_bw_khz", None))

                corr_csv_path = meta.get("corr", None) or default_corr_csv
                lic_csv_path  = meta.get("lic", None) or default_lic_csv

                dane_filtro = normalize_dane(meta.get("dane", None))
                danes_list = parse_danes_arg(meta.get("danes", None))
                if len(danes_list) > 0:
                    dane_filtro = None
                municipio_filtro = meta.get("municipio", None)

                if len(danes_list) == 0 and dane_filtro is None and municipio_filtro is not None:
                    m = str(municipio_filtro).strip()
                    if m.isdigit():
                        dane_filtro = m
                        municipio_filtro = None

                if cumplimiento == 0 and len(picos_list) == 0:
                    lic_csv_path = None

                payload = [frame_json, picos_list, cumplimiento]

                out = process_input(
                    payload,
                    corr_csv_path=corr_csv_path,
                    licencia_csv_path=lic_csv_path,
                    dane_filtro=dane_filtro,
                    danes_filtro=(danes_list if len(danes_list) > 0 else None),
                    municipio_filtro=municipio_filtro,
                    umbral_db=umbral_db,
                    delta_fc_khz=delta_fc_khz,
                    delta_bw_khz=delta_bw_khz,
                    debug=bool(app.config.get("RETURN_DEBUG", False)),
                )
                _server_log(f"POST /analyze_batch frame[{idx}] completed | {_result_summary(out)}")
                return idx, out
            except Exception as e:
                _server_log(f"POST /analyze_batch frame[{idx}] failed: {type(e).__name__}: {e}")
                return idx, {"error": str(e)}

        results: List[Any] = [None] * len(frames_input)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process_one, i, frame): i
                for i, frame in enumerate(frames_input)
            }
            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        ok_count = sum(1 for r in results if isinstance(r, dict) and "error" not in r)
        err_count = sum(1 for r in results if isinstance(r, dict) and "error" in r)
        _server_log(
            f"POST /analyze_batch completed in {elapsed_ms:.1f} ms | "
            f"frames={len(results)} ok={ok_count} error={err_count}"
        )

        return jsonify({"results": results})

    except Exception as e:
        _server_log(f"POST /analyze_batch failed: {type(e).__name__}: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------
# Entrypoint
# ---------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", type=str, default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Incluye el bloque debug en la respuesta JSON con los vectores internos del processor.",
    )

    # Defaults del servidor (para no mandarlos en cada request)
    ap.add_argument(
        "--lic-default",
        type=str,
        default=os.environ.get("ANE_LIC_CSV", ""),
        help="Ruta default del CSV de licencias (o env ANE_LIC_CSV).",
    )
    ap.add_argument(
        "--corr-default",
        type=str,
        default=os.environ.get("ANE_CORR_CSV", ""),
        help="Ruta default del CSV de correcciones (o env ANE_CORR_CSV).",
    )

    # Seguridad: por defecto NO permitimos que el cliente envíe rutas del servidor
    ap.add_argument(
        "--allow-json-path",
        action="store_true",
        help="(Solo dev) Permite que el cliente mande json_path. NO usar en prod.",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce logs del servidor y deja solo los mensajes básicos de Flask.",
    )

    args = ap.parse_args()

    app.config["DEFAULT_LIC_CSV"] = args.lic_default.strip() or None
    app.config["DEFAULT_CORR_CSV"] = args.corr_default.strip() or None
    app.config["ALLOW_JSON_PATH"] = bool(args.allow_json_path)
    app.config["VERBOSE_LOGS"] = not bool(args.quiet)
    app.config["RETURN_DEBUG"] = bool(args.debug)

    print(f"[SERVER] http://{args.host}:{args.port}")
    if app.config["DEFAULT_LIC_CSV"]:
        print(f"[SERVER] DEFAULT_LIC_CSV = {app.config['DEFAULT_LIC_CSV']}")
    if app.config["DEFAULT_CORR_CSV"]:
        print(f"[SERVER] DEFAULT_CORR_CSV = {app.config['DEFAULT_CORR_CSV']}")
    print(f"[SERVER] allow_json_path = {app.config['ALLOW_JSON_PATH']}")
    print(f"[SERVER] verbose_logs = {app.config['VERBOSE_LOGS']}")
    print(f"[SERVER] return_debug = {app.config['RETURN_DEBUG']}")

    app.run(host=args.host, port=args.port, debug=False, threaded=True)

if __name__ == "__main__":
    main()
