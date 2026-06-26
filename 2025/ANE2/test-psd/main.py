# main.py
"""
Instrument vs radio signal comparison experiment.
- Using proffesional Keysight instrument to acquire nominal sppectrum signal (reference)
- scalate z-score shape-focused metrics
- save results in CSV for later analysis and plotting
"""

DEVELOPMENT = False

from dataclasses import asdict
import asyncio
from pathlib import Path
import csv
import json
import numpy as np

import cfg
from functions import AcquireDual

if DEVELOPMENT:
    from libs.instrument_dummy import KeysightHandler
else:
    from libs.instrument import KeysightHandler
    
from libs.preprocess import preprocessSignalsForShape, computeSignalMetrics
from utils import ZmqPairController, ServerRealtimeConfig

log = cfg.set_logger()

#intrument parameters
IP_INST = "10.42.0.41"
TIMEOUT_INST_MS = 5000

#radio parameters
CENTER_FREQ_HZ = int(98e6)
SAMPLE_RATE_HZ = int(20e6)
RBW_HZ = int(10e3)
WINDOW = "hamming"
OVERLAP = 0.5
LNA_GAIN = 0
VGA_GAIN = 0
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
    "frequency_hz",
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
    log.info(f"DATETIME:{cfg.human_readable(ts_ms=cfg.get_time_ms())} - Starting experiment with {NUM_REALIZATIONS} realizations for each method: {METH0DS_PSD_TEST}")

    for method in METH0DS_PSD_TEST:
        log.info(f"----------Testing method: {method}----------")
        data_filename = DATA_DIR / (
            f"{cfg.human_readable(ts_ms=cfg.get_time_ms())}_{method}_CF{CENTER_FREQ_HZ/1e6}MHz_SP{SAMPLE_RATE_HZ/1e6}MHz_RBW{RBW_HZ/1e3}kHz_"
            f"{WINDOW}_overlap{OVERLAP}_LNA{LNA_GAIN}dB_VGA{VGA_GAIN}dB_"
            f"ANT{ANTENNA_AMP}_port{ANTENNA_PORT}.csv"
        )
  
        async with KeysightHandler(ip=IP_INST, timeout_ms=TIMEOUT_INST_MS) as inst:
            info_inst = await inst.get_info()
            print(f"Instrument info: {info_inst}")

            #Press Intro to continue
            input("Press Enter to continue...")
            await inst.clear_errors()
            await inst.config_params(center_freq_hz=float(CENTER_FREQ_HZ), span_hz=float(SAMPLE_RATE_HZ))

            log.info("Waiting for instrument to apply settings...")
            await asyncio.sleep(1)  # allow some time for the instrument to apply settings

            for i in range(NUM_REALIZATIONS):
                log.info(f"Realization {i+1}/{NUM_REALIZATIONS}")
                #input("Press Enter to continue...")

                log.info(f"[INST]getting trace CF={CENTER_FREQ_HZ/1e6}MHz, SPAN={SAMPLE_RATE_HZ/1e6}MHz")
                nom_sig = await inst.get_trace()
                if nom_sig is not None:
                    log.info(f"Received nominal signal of length: {len(nom_sig)}")
                else:
                    log.error("Failed to receive nominal signal")
                    continue

                frequency_hz = np.linspace(
                    CENTER_FREQ_HZ - SAMPLE_RATE_HZ / 2.0,
                    CENTER_FREQ_HZ + SAMPLE_RATE_HZ / 2.0,
                    len(nom_sig),
                    dtype=float,
                )

                log.info(f"[RADIO]getting signal CF={CENTER_FREQ_HZ/1e6}MHz, SR={SAMPLE_RATE_HZ/1e6}MHz, RBW={RBW_HZ/1e3}kHz, WINDOW={WINDOW}, OVERLAP={OVERLAP}, LNA_GAIN={LNA_GAIN}dB, VGA_GAIN={VGA_GAIN}dB, ANTENNA_AMP={ANTENNA_AMP}, ANTENNA_PORT={ANTENNA_PORT}")
                rec_sig = await get_rec_sig(method)
                if rec_sig is not None:
                    log.info(f"Received signal of length: {len(rec_sig)}")
                else:
                    log.error("Failed to receive signal")
                    continue

                # Preprocess using shape-focused functions
                nom_len_orig = len(nom_sig)
                rec_len_orig = len(rec_sig)

                nom_scaled, rec_scaled, metadata = preprocessSignalsForShape(nom_sig, rec_sig)
                metrics = computeSignalMetrics(nom_scaled, rec_scaled)

                mse = metrics.get("meanSquaredError")
                mae = metrics.get("meanAbsoluteError")
                spectral_distance = metrics.get("spectralDistanceDb")

                log.info(
                    f"Preprocessed signals to target length: {metadata.get('sampleCount')} "
                    f"(original lengths: ({nom_len_orig}, {rec_len_orig}))"
                )

                write_csv_row(
                    data_filename,
                    {
                        "method": method,
                        "realization": i + 1,
                        "frequency_hz": json.dumps(np.asarray(frequency_hz).tolist()),
                        "nominal_signal": json.dumps(np.asarray(nom_scaled).tolist()),
                        "received_signal": json.dumps(np.asarray(rec_scaled).tolist()),
                        "nominal_length": int(nom_len_orig),
                        "received_length": int(rec_len_orig),
                        "target_length": int(metadata.get("sampleCount")),
                        "mse": float(mse),
                        "mae": float(mae),
                        "spectral_distance": float(spectral_distance),
                    },
                )

if __name__ == "__main__":
    asyncio.run(main())