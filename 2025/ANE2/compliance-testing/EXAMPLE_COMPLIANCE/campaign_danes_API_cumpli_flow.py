from pathlib import Path
import json
import shutil
import requests
import argparse
from typing import Optional

nodeIds = [1,2,3,4,5,6,7,8,9,10]

#Bogota
lat, lon = 4.6775, -74.0541

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CAMPAIGN_NUMBER = 275
DEFAULT_THRES = None
DEFAULT_DELTA_FC_KHZ = 100
DEFAULT_DELTA_BW_KHZ = 10
MIN_VALID_FREQ_HZ = 1_000_000
MIN_VALID_PXX_LEN = 256

BASE_API = "127.0.0.1"
BASE_EP = "analyze"

JEISSON_PORT = 8000
OSCAR_PORT = 8001
JEISSON_URL = f"http://{BASE_API}:{JEISSON_PORT}/{BASE_EP}"

def _safe_name(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(" ", "_")


def _campaign_folder_name(campaign_number: int, suffix: str) -> str:
    return f"camp-{campaign_number}-{suffix}"


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
                            delta_fc_khz=DEFAULT_DELTA_FC_KHZ,
                            delta_bw_khz=DEFAULT_DELTA_BW_KHZ,
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
                          data_request,
                          work_folder,
                          umbral_db=DEFAULT_THRES,
                          delta_fc_khz=DEFAULT_DELTA_FC_KHZ,
                          delta_bw_khz=DEFAULT_DELTA_BW_KHZ):

    df_full = data_request.load_campaigns_and_nodes(
        campaigns=campaign_ids,
        node_ids=node_ids,
    )

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
        type=Path,
        help=(
            "Nombre o ruta de la carpeta donde se guardarán las respuestas JSON. "
            "Por defecto usa camp-<n>-responses."
        ),
    )
    parser.add_argument(
        "--signals-folder",
        type=Path,
        help=(
            "Nombre o ruta de la carpeta donde se guardarán las señales generadas. "
            "Por defecto usa camp-<n>-signals."
        ),
    )
    parser.add_argument(
        "-n",
        "--campaign-number",
        "--number-camp",
        dest="campaign_number",
        type=int,
        default=DEFAULT_CAMPAIGN_NUMBER,
        help=f"Número de campaña a procesar (default: {DEFAULT_CAMPAIGN_NUMBER})."
    )
    return parser.parse_args()


def _resolve_output_folder(folder_arg: Optional[Path], default_name: str) -> Path:
    if folder_arg is None:
        return BASE_DIR / default_name

    return folder_arg.expanduser().resolve()


def main():
    args = _parse_args()

    from campaignAPI.data_request import DataRequest
    from api_dane_from_coords_via_tunnel import full_example_dane_tunnel

    nameCamp = f"CAMP-{args.campaign_number}"
    campIds = {nameCamp: args.campaign_number}
    work_folder = _resolve_output_folder(
        args.signals_folder,
        _campaign_folder_name(args.campaign_number, "signals"),
    )
    responses_folder = _resolve_output_folder(
        args.responses_folder,
        _campaign_folder_name(args.campaign_number, "responses"),
    )

    print(f"Signals will be saved in: {work_folder.resolve()}")
    responses_folder.mkdir(parents=True, exist_ok=True)
    print(f"Responses from API will be saved in: {responses_folder.resolve()}")

    if work_folder.exists() and work_folder.is_dir():
        shutil.rmtree(work_folder)

    work_folder.mkdir(parents=True, exist_ok=True)

    data_request = DataRequest(base_url="https://rsm.ane.gov.co:12443/api")
    dane_codes = full_example_dane_tunnel(lat, lon)
    downloadCampaignsData(
        dane_codes=dane_codes,
        campaign_ids=campIds,
        node_ids=nodeIds,
        data_request=data_request,
        work_folder=work_folder,
    )

    json_files = sorted(work_folder.glob("*.json"))
    if not json_files:
        print("No .json files found in this directory.")
        return {}
    
    for file_path in json_files:
        print()
        print()
        print(f"--- File: {file_path.name} ---")
        ready_payload = load_json_file(str(file_path), verbose=True)

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
