from pathlib import Path
import json
import shutil
import requests
import argparse
from typing import Tuple, List, Any

from campaignAPI.data_request import DataRequest
from api_dane_from_coords_via_tunnel import full_example_dane_tunnel

dr = DataRequest(base_url="https://rsm.ane.gov.co:12443/api")

campIds = {'CAMP-275': 275}
#nodeIds = [1,2,3,4,5,7,9]
nodeIds = [3]

#Bogota
lat, lon = 4.6775, -74.0541

WORK_FOLDER = Path("camp_signals")
DEFAULT_THRES = 0
DEFAULT_DELTA_FC = 100
DEFAULT_DELTA_BW = 10
MIN_VALID_FREQ_HZ = 1_000_000
MIN_VALID_PXX_LEN = 256

BASE_API = "127.0.0.1"
BASE_EP = "analyze"

JEISSON_PORT = 8000
OSCAR_PORT = 8001
JEISSON_URL = f"http://{BASE_API}:{JEISSON_PORT}/{BASE_EP}"

DEFAULT_RESPONSES_FOLDER_NAME = "responses_jeisson_api_compliance"

def _safe_name(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(" ", "_")


def _normalize_pxx_values(pxx_raw):
    if hasattr(pxx_raw, "tolist"):
        return pxx_raw.tolist()
    return list(pxx_raw)


def _row_is_valid_signal(row):
    try:
        pxx = _normalize_pxx_values(row["pxx"])
    except Exception as exc:
        return False, f"pxx inválido: {exc}"

    if len(pxx) < MIN_VALID_PXX_LEN:
        return False, f"pxx demasiado corto ({len(pxx)} < {MIN_VALID_PXX_LEN})"

    invalid_freq_fields = []
    for key, value in row.items():
        if not str(key).endswith("freq_hz") or value is None:
            continue
        try:
            freq_hz = float(value)
        except (TypeError, ValueError):
            invalid_freq_fields.append(f"{key}={value!r}")
            continue
        if freq_hz < MIN_VALID_FREQ_HZ:
            invalid_freq_fields.append(f"{key}={freq_hz}")

    if invalid_freq_fields:
        return False, (
            f"frecuencias menores a {MIN_VALID_FREQ_HZ} Hz: "
            + ", ".join(invalid_freq_fields)
        )

    return True, pxx


def _build_payload_from_row(row, dane_codes, umbral_db=DEFAULT_THRES,
                            delta_fc_khz=DEFAULT_DELTA_FC,
                            delta_bw_khz=DEFAULT_DELTA_BW,
                            cumplimiento=True):
    is_valid, pxx_or_reason = _row_is_valid_signal(row)
    if not is_valid:
        raise ValueError(pxx_or_reason)

    pxx = pxx_or_reason

    if cumplimiento:
        return {
                "frame": {
                    "Pxx": pxx,
                    "start_freq_hz": int(row["start_freq_hz"]),
                    "end_freq_hz": int(row["end_freq_hz"]),
                },
                "cumplimiento": 1,
                "dane": dane_codes[0],
                "danes": dane_codes,
                "picos": [],
                "umbral_db": umbral_db,
                "delta_fc_khz": delta_fc_khz,
                "delta_bw_khz": delta_bw_khz,
                }
    else:
        return {
                "frame": {
                    "Pxx": pxx,
                    "start_freq_hz": int(row["start_freq_hz"]),
                    "end_freq_hz": int(row["end_freq_hz"]),
                },
                "cumplimiento": 0,
                "umbral_db": umbral_db,
                "delta_fc_khz": delta_fc_khz,
                "delta_bw_khz": delta_bw_khz,
                }


def downloadCampaignsData(campaign_ids, node_ids, dane_codes,
                          work_folder=WORK_FOLDER,
                          umbral_db=DEFAULT_THRES,
                          delta_fc_khz=DEFAULT_DELTA_FC,
                          delta_bw_khz=DEFAULT_DELTA_BW):

    df_full = dr.load_campaigns_and_nodes(campaigns=campaign_ids, node_ids=node_ids)

    for campaign_name, data_nodes in df_full.items():
        for node_name, df_node in data_nodes.items():

            if df_node is None or df_node.empty:
                print(f"Sin datos para {campaign_name} - {node_name}")
                continue

            for row_idx, row in df_node.iterrows():
                try:
                    is_valid, reason = _row_is_valid_signal(row)
                    if not is_valid:
                        print(
                            f"Se omite row {row_idx} de {campaign_name}/{node_name}: {reason}"
                        )
                        continue

                    payload = _build_payload_from_row(
                        row,
                        dane_codes=dane_codes,
                        umbral_db=umbral_db,
                        delta_fc_khz=delta_fc_khz,
                        delta_bw_khz=delta_bw_khz,
                        cumplimiento=True,
                    )

                    signal_name = row.get("signal_name", f"signal_{row_idx}")

                    file_name = (
                        f"{_safe_name(campaign_name)}_"
                        f"{_safe_name(node_name)}_"
                        f"{_safe_name(signal_name)}_"
                        f"row_{row_idx}.json"
                    )

                    file_path = work_folder / file_name

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False)

                    print(f"JSON guardado en: {file_path}")

                except KeyError as e:
                    print(f"Falta columna esperada en row {row_idx} de {campaign_name}/{node_name}: {e}")
                except Exception as e:
                    print(f"Error procesando row {row_idx} de {campaign_name}/{node_name}: {e}")

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

def load_json_file(file_path: str, verbose: bool = True) -> dict:
    """Lee un archivo JSON para usarlo en una request"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    def _vprint(message: str) -> None:
        if verbose:
            print(message)

    frame = data.get("frame", {})
    psd = frame.get("Pxx", [])
    _vprint(f"PSD length: {len(psd)}")
    start_freq = frame.get("start_freq_hz")
    _vprint(f"Start freq: {start_freq} Hz")
    end_freq = frame.get("end_freq_hz")
    _vprint(f"End freq: {end_freq} Hz")
    cumplimiento = str(data.get("cumplimiento")) == "1"
    _vprint(f"Cumplimiento: {cumplimiento}")

    return data


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Descarga señales de campaña, las envía a una API /analyze y guarda las respuestas JSON."
    )
    parser.add_argument(
        "--responses-folder",
        default=DEFAULT_RESPONSES_FOLDER_NAME,
        help=(
            "Nombre o ruta de la carpeta donde se guardarán las respuestas JSON "
            f"(default: {DEFAULT_RESPONSES_FOLDER_NAME})."
        ),
    )
    return parser.parse_args()


def _resolve_responses_folder(folder_arg: str) -> Path:
    folder = Path(folder_arg).expanduser()
    if not folder.is_absolute():
        folder = Path(__file__).resolve().parent / folder
    return folder


def main():
    args = _parse_args()
    responses_folder = _resolve_responses_folder(args.responses_folder)
    responses_folder.mkdir(parents=True, exist_ok=True)
    print(f"Responses from JEISSON API will be saved in: {responses_folder.resolve()}")

    if WORK_FOLDER.exists() and WORK_FOLDER.is_dir():
        shutil.rmtree(WORK_FOLDER)

    WORK_FOLDER.mkdir(parents=True, exist_ok=True)

    dane_codes = full_example_dane_tunnel(lat, lon)
    downloadCampaignsData(
        dane_codes=dane_codes,
        campaign_ids=campIds,
        node_ids=nodeIds,
    )

    json_files = list(WORK_FOLDER.glob("*.json"))
    if not json_files:
        print("No .json files found in this directory.")
        return {}
    
    for file_path in json_files:
        print()
        print()
        print(f"--- File: {file_path.name} ---")
        ready_payload = load_json_file(str(file_path), verbose=True)

        api_dict = None

        try:
            api_response = _post_to_jeisson_api(ready_payload)
            print("JEISSON API response received.", flush=True)
            #print(json.dumps(api_response, indent=2, ensure_ascii=False))

            # ---- SAVE PRETTY JSON ----
            output_file = responses_folder / f"{file_path.stem}_response.json"

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(api_response, f, indent=2, ensure_ascii=False)

            print(f"Saved response to: {output_file}")
        except requests.RequestException as e:
            print(f"\nError sending payload to JEISSON API: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en la ejecución principal: {e}")
    finally:
        # Elimina la carpeta después de procesar
        #WORK_FOLDER.rmdir()
        pass
