from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

from src.processor import process_input


def parse_picos_arg(picos_arg: Optional[str]) -> List[float]:
    """Soporta:
      --picos ""                     -> []
      --picos "91000000,98e6"        -> [91000000.0, 98000000.0]
      --picos "[91000000, 98000000]" -> [91000000.0, 98000000.0]
      --picos (sin valor)            -> []  (nargs='?' + const='')
    """
    if picos_arg is None:
        return []

    s = str(picos_arg).strip()
    if s == "":
        return []

    # Si viene como JSON list string
    if s.startswith("[") and s.endswith("]"):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [float(x) for x in arr]
        except Exception:
            pass

    # CSV por comas
    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    return [float(x) for x in parts]




def parse_danes_arg(danes_arg: Optional[str]) -> List[str]:
    """Soporta:
      --danes ""                    -> []
      --danes "11001,17001"         -> ["11001","17001"]
      --danes "[11001, 17001]"      -> ["11001","17001"]
      --danes (sin valor)           -> []  (nargs='?' + const='')
    """
    if danes_arg is None:
        return []

    s = str(danes_arg).strip()
    if s == "":
        return []

    # JSON list style
    if s.startswith("[") and s.endswith("]"):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                out = []
                for x in arr:
                    xs = str(x).strip()
                    if xs != "":
                        # limpia 11001.0
                        if xs.replace(".", "", 1).isdigit() and "." in xs:
                            try:
                                xs = str(int(float(xs)))
                            except Exception:
                                pass
                        out.append(xs)
                return out
        except Exception:
            pass

    # CSV
    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    out2: List[str] = []
    for p in parts:
        # limpia 11001.0
        if p.replace(".", "", 1).isdigit() and "." in p:
            try:
                p = str(int(float(p)))
            except Exception:
                pass
        out2.append(str(p))
    return out2

def print_full_response(out: Dict[str, Any]) -> None:
    """Imprime salida completa (sin tablas bonitas/pandas).

    - Primero un resumen con claves principales
    - Luego la lista completa de results (si existe)
    """
    print("\n[OK] Respuesta:")

    basic_keys = [
        "mode",
        "cumplimiento",
        "umbral_db",
        "umbral",
        "picos_count",
        "picos",
        "num_emissions",
        "correction_applied",
        "timestamp",
        "mac",
    ]
    for k in basic_keys:
        if k in out:
            print(f"  - {k}: {out[k]}")

    if "results_by_dane" in out and isinstance(out.get("results_by_dane"), dict):
        print("\n[RESULTS POR DANE]:")
        rbd = out["results_by_dane"]
        for dane_k, rows in rbd.items():
            print(f"\n=== DANE {dane_k} ===")
            if not isinstance(rows, list):
                print(rows)
                continue
            for i, row in enumerate(rows, start=1):
                print(f"  [{i:02d}] {row}")
        return

    results = out.get("results", [])
    if not isinstance(results, list):
        print("\n[RESULTS COMPLETOS]:")
        print(results)
        return

    print(f"  - results_count: {len(results)}")
    print("\n[RESULTS COMPLETOS]:")
    for i, row in enumerate(results, start=1):
        print(f"  [{i:02d}] {row}")


def main() -> int:
    ap = argparse.ArgumentParser()

    ap.add_argument("--json", dest="json_path", type=str, default=None, help="Ruta a JSON de entrada (frame).")
    ap.add_argument("--frame", dest="frame_inline", type=str, default=None, help="JSON inline (string).")

    # IMPORTANTE: nargs='?' + const='' permite:
    #   --picos ""  y también --picos (sin valor)
    ap.add_argument(
        "--picos",
        dest="picos",
        nargs="?",
        const="",
        default=None,
        help="Lista de picos. Ej: '91000000,98011000' o '[]'.",
    )
    ap.add_argument("--cumplimiento", dest="cumplimiento", type=int, default=0, help="0/1.")

    ap.add_argument("--corr", dest="corr", type=str, default=None, help="CSV de corrección (opcional).")
    ap.add_argument("--lic", dest="lic", type=str, default=None, help="CSV licencias (opcional).")
    ap.add_argument("--dane", dest="dane", type=str, default=None, help="Filtro codigo_dane (recomendado). Ej: 11001")
    ap.add_argument("--danes", dest="danes", nargs="?", const="", default=None, help="Lista de DANEs. Ej: \"11001,17001\" o \"[11001,17001]\". Si se usa, tiene prioridad sobre --dane")
    ap.add_argument("--municipio", dest="municipio", type=str, default=None, help="Filtro municipio (legacy). Si el valor es numerico, se interpreta como DANE.")

    # Umbral configurable (dB sobre el piso de ruido) para decidir emisión/no emisión.
    # Ej: 3, 5, 10 ... Si NO se pasa, se usa el comportamiento histórico.
    ap.add_argument(
        "--umbral_db",
        "--threshold_db",
        dest="umbral_db",
        type=float,
        default=None,
        help="Umbral de detección en dB sobre el piso de ruido (ej: 3, 5).",
    )

    # Tolerancia de matching por frecuencia central (kHz). Default: 100 kHz.
    ap.add_argument(
        "--delta_fc_khz",
        dest="delta_fc_khz",
        type=float,
        default=None,
        help="Tolerancia de matching por FC en kHz (default: 100). Ej: 50, 100, 200.",
    )
    # Tolerancia de cumplimiento para ancho de banda (kHz). Default: 10 kHz.
    ap.add_argument(
        "--delta_bw_khz",
        dest="delta_bw_khz",
        type=float,
        default=None,
        help="Tolerancia de cumplimiento BW en kHz (default: 10). Ej: 0, 5, 10, 25.",
    )


    args = ap.parse_args()

    if not args.json_path and not args.frame_inline:
        raise SystemExit("Debes pasar --json RUTA o --frame JSON_INLINE.")

    # Cargar frame_json
    if args.json_path:
        with open(args.json_path, "r", encoding="utf-8") as f:
            frame_json = json.load(f)
    else:
        frame_json = json.loads(args.frame_inline)

    picos_list = parse_picos_arg(args.picos)
    payload = [frame_json, picos_list, int(args.cumplimiento)]

    # Importante:
    # Si el usuario pide --cumplimiento 0 y NO pasa --picos,
    # el modo es "all_emissions" (solo detección/medición).
    # En ese modo se ignora --lic para evitar que se mezclen
    # comparaciones de licencias (que el usuario asocia a "cumplimiento").
    # Para matching de licencias usa: --picos ... o --cumplimiento 1.
    licencia_csv_path = args.lic
    if int(args.cumplimiento) == 0 and (picos_list is None or len(picos_list) == 0):
        licencia_csv_path = None

    # Prefer nuevo filtro por codigo_dane. Si te pasan un "municipio" numérico
    # (p.ej. 11001), lo interpretamos como DANE por compatibilidad.
    dane_filtro = args.dane
    municipio_filtro = args.municipio
    danes_list = parse_danes_arg(getattr(args, "danes", None))
    if len(danes_list) > 0:
        # Si llegan varios, priorizamos el vector sobre --dane
        dane_filtro = None
    if dane_filtro is None and municipio_filtro is not None:
        m = str(municipio_filtro).strip()
        if m.isdigit():
            dane_filtro = m
            municipio_filtro = None

    out = process_input(
        payload,
        corr_csv_path=args.corr,
        licencia_csv_path=licencia_csv_path,
        dane_filtro=dane_filtro,
        danes_filtro=(danes_list if len(danes_list) > 0 else None),
        municipio_filtro=municipio_filtro,
        umbral_db=args.umbral_db,
        delta_fc_khz=getattr(args, "delta_fc_khz", None),
        delta_bw_khz=getattr(args, "delta_bw_khz", None),
    )

    print_full_response(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
