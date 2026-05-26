from dataclasses import asdict
import asyncio
import csv
import json
from pathlib import Path

import numpy as np

import cfg
from functions import AcquireDual
from libs.instrument import KeysightHandler
from libs.preprocess import mseMaeSpectralDistance, preprocessSignals
from utils import ZmqPairController, ServerRealtimeConfig

log = cfg.set_logger()

#intrument parameters
IP_INST = "192.168.0.100"
TIMEOUT_INST_MS = 5000

#radio parameters
CENTER_FREQ_HZ = int(98e6)
SAMPLE_RATE_HZ = int(20e6)
RBW_HZ = int(10e3)
WINDOW = "hamming"
OVERLAP = 0.5
LNA_GAIN = 30
VGA_GAIN = 20
ANTENNA_AMP = True
ANTENNA_PORT = 1

#experiment 
METH0DS_PSD_TEST = ["pfb", "welch"]
NUM_REALIZATIONS = 10

#save experiment data
DATA_DIR = Path("./data_results")

CSV_FIELDNAMES = [
    "method",
    "realization",
    "nominal_signal",
    "received_signal",
    "nominal_length",
    "received_length",
    "target_length",
    "mse",
    "mae",
    "spectral_distance",
]


def write_csv_row(csv_path: Path, row: dict):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0

    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


async def get_rec_sig(method_psd):
    config_obj_sig = asdict(
            ServerRealtimeConfig(
                method_psd=method_psd,
                center_freq_hz=CENTER_FREQ_HZ,
                sample_rate_hz=SAMPLE_RATE_HZ,
                rbw_hz=RBW_HZ,
                window=WINDOW,
                overlap=OVERLAP,
                lna_gain=LNA_GAIN,
                vga_gain=VGA_GAIN,
                antenna_amp=ANTENNA_AMP,
                antenna_port=ANTENNA_PORT,
                ppm_error=0,
                cooldown_request=0.1
            )
        )

    controller = ZmqPairController(addr=cfg.IPC_ADDR, is_server=True, verbose=False)
    async with controller as zmq_ctrl:
        acquirer = AcquireDual(controller=zmq_ctrl, log=log)

        dsp_payload = await acquirer.get_corrected_data(config_obj_sig)
        if dsp_payload is None:
            log.error("Failed to get DSP payload from engine")
            return
        rec_sig = dsp_payload.get("Pxx", None)

        return rec_sig


async def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for method in METH0DS_PSD_TEST:
        log.info(f"----------Testing method: {method}----------")
        data_filename = DATA_DIR / (
            f"psd_{method}_CF{CENTER_FREQ_HZ}Hz_SR{SAMPLE_RATE_HZ}Hz_RBW{RBW_HZ}Hz_"
            f"{WINDOW}_overlap{OVERLAP}_LNA{LNA_GAIN}dB_VGA{VGA_GAIN}dB_"
            f"ANT{ANTENNA_AMP}_port{ANTENNA_PORT}.csv"
        )
  
        async with KeysightHandler(ip=IP_INST, timeout_ms=TIMEOUT_INST_MS) as inst:
            info_inst = await inst.get_info()
            print(f"Instrument info: {info_inst}")

            #Press Intro to continue
            input("Press Enter to continue...")
            await inst.clear_errors()

            for i in range(NUM_REALIZATIONS):
                log.info(f"Realization {i+1}/{NUM_REALIZATIONS}")
                input("Press Enter to continue...")

                log.info("[INST]getting trace CF={CENTER_FREQ_HZ}Hz, SPAN={SAMPLE_RATE_HZ}Hz")
                nom_sig = await inst.get_trace(center_freq_hz=float(CENTER_FREQ_HZ), span_hz=float(SAMPLE_RATE_HZ))
                if nom_sig is not None:
                    log.info(f"Received nominal signal of length: {len(nom_sig)}")
                else:
                    log.error("Failed to receive nominal signal")
                    continue

                log.info("[RADIO]getting signal CF={CENTER_FREQ_HZ}Hz, SR={SAMPLE_RATE_HZ}Hz, RBW={RBW_HZ}Hz, WINDOW={WINDOW}, OVERLAP={OVERLAP}, LNA_GAIN={LNA_GAIN}dB, VGA_GAIN={VGA_GAIN}dB, ANTENNA_AMP={ANTENNA_AMP}, ANTENNA_PORT={ANTENNA_PORT}")
                rec_sig = await get_rec_sig(method)
                if rec_sig is not None:
                    log.info(f"Received signal of length: {len(rec_sig)}")
                else:
                    log.error("Failed to receive signal")
                    continue

                #preprocess
                nom_sig, rec_sig, _, info = preprocessSignals(nom_sig, rec_sig)
                mse, mae, spectral_distance = mseMaeSpectralDistance(nom_sig, rec_sig)

                log.info(
                    f"Preprocessed signals to target length: {info['target_length']} "
                    f"(original lengths: {info['original_lengths']})"
                )

                write_csv_row(
                    data_filename,
                    {
                        "method": method,
                        "realization": i + 1,
                        "nominal_signal": json.dumps(np.asarray(nom_sig).tolist()),
                        "received_signal": json.dumps(np.asarray(rec_sig).tolist()),
                        "nominal_length": int(info["original_lengths"][0]),
                        "received_length": int(info["original_lengths"][1]),
                        "target_length": int(info["target_length"]),
                        "mse": float(mse),
                        "mae": float(mae),
                        "spectral_distance": float(spectral_distance),
                    },
                )

if __name__ == "__main__":
    asyncio.run(main())