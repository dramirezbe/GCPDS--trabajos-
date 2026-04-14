#csv_dataclasses.py
import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Dict

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ==========================================
# 1. DEFINICIÓN DE ESTRUCTURAS (DATACLASSES)
# ==========================================

@dataclass
class Clocks:
    arm: Optional[float]
    core: Optional[float]
    h264: Optional[float]
    isp: Optional[float]
    v3d: Optional[float]
    uart: Optional[float]
    pwm: Optional[float]
    emmc: Optional[float]
    pixel: Optional[float]
    vec: Optional[float]
    hdmi: Optional[float]
    dpi: Optional[float]

@dataclass
class Voltages:
    core: Optional[float]
    sdram_c: Optional[float]
    sdram_i: Optional[float]
    sdram_p: Optional[float]
    v_3v7_wl_sw: Optional[float]
    v_3v3_sys: Optional[float]
    v_1v8_sys: Optional[float]
    v_ddr_vdd2: Optional[float]
    v_ddr_vddq: Optional[float]
    v_1v1_sys: Optional[float]
    v_0v8_sw: Optional[float]
    v_vdd_core: Optional[float]
    v_3v3_dac: Optional[float]
    v_3v3_adc: Optional[float]
    v_0v8_aon: Optional[float]
    v_hdmi: Optional[float]
    v_ext5v: Optional[float]
    v_batt: Optional[float]

@dataclass
class Currents:
    i_3v7_wl_sw: Optional[float]
    i_3v3_sys: Optional[float]
    i_1v8_sys: Optional[float]
    i_ddr_vdd2: Optional[float]
    i_ddr_vddq: Optional[float]
    i_1v1_sys: Optional[float]
    i_0v8_sw: Optional[float]
    i_vdd_core: Optional[float]
    i_3v3_dac: Optional[float]
    i_3v3_adc: Optional[float]
    i_0v8_aon: Optional[float]
    i_hdmi: Optional[float]

@dataclass
class SystemStatus:
    throttle_hex: str
    uv: str
    arm_freq_cap: str
    cur_throttle: str
    soft_temp_limit: str
    uv_occured: str
    arm_freq_cap_occured: str
    throttle_occured: str
    soft_temp_limit_occured: str
    readmr_registers: Dict[str, Optional[float]]

@dataclass
class TelemetryRecord:
    timestamp: datetime
    time_sec: float  # NUEVO: Tiempo transcurrido en segundos desde el inicio
    time_min: float
    cpu_percent: Optional[float]
    arm_temp: Optional[float]
    clocks: Clocks
    voltages: Voltages
    currents: Currents
    status: SystemStatus


# ==========================================
# 2. LOGICA DE PARSEO Y MANEJO
# ==========================================

class TelemetryParser:
    def __init__(self):
        # Variable de estado para guardar el T=0 del experimento
        self._first_timestamp: Optional[datetime] = None

    @staticmethod
    def _safe_float(value: str) -> Optional[float]:
        if not value or value.strip() == "":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _parse_row(self, row: Dict[str, str]) -> TelemetryRecord:
        dt_format = "%Y-%m-%d %H:%M:%S"
        timestamp_str = row.get("timestamp", "").split(".")[0] 
        try:
            timestamp = datetime.strptime(timestamp_str, dt_format)
        except ValueError:
            timestamp = datetime.min

        # Lógica para calcular time_sec
        if self._first_timestamp is None and timestamp != datetime.min:
            self._first_timestamp = timestamp
        
        # Si por alguna razón la fecha falló, el delta es 0, si no, calculamos segundos reales
        if self._first_timestamp:
            time_sec = (timestamp - self._first_timestamp).total_seconds()
        else:
            time_sec = 0.0

        clocks = Clocks(
            arm=self._safe_float(row.get("arm_mhz", "")),
            core=self._safe_float(row.get("core_mhz", "")),
            h264=self._safe_float(row.get("h264_mhz", "")),
            isp=self._safe_float(row.get("isp_mhz", "")),
            v3d=self._safe_float(row.get("v3d_mhz", "")),
            uart=self._safe_float(row.get("uart_mhz", "")),
            pwm=self._safe_float(row.get("pwm_mhz", "")),
            emmc=self._safe_float(row.get("emmc_mhz", "")),
            pixel=self._safe_float(row.get("pixel_mhz", "")),
            vec=self._safe_float(row.get("vec_mhz", "")),
            hdmi=self._safe_float(row.get("hdmi_mhz", "")),
            dpi=self._safe_float(row.get("dpi_mhz", ""))
        )

        voltages = Voltages(
            core=self._safe_float(row.get("core_volt", "")),
            sdram_c=self._safe_float(row.get("sdram_c_volt", "")),
            sdram_i=self._safe_float(row.get("sdram_i_volt", "")),
            sdram_p=self._safe_float(row.get("sdram_p_volt", "")),
            v_3v7_wl_sw=self._safe_float(row.get("3V7_WL_SW_V", "")),
            v_3v3_sys=self._safe_float(row.get("3V3_SYS_V", "")),
            v_1v8_sys=self._safe_float(row.get("1V8_SYS_V", "")),
            v_ddr_vdd2=self._safe_float(row.get("DDR_VDD2_V", "")),
            v_ddr_vddq=self._safe_float(row.get("DDR_VDDQ_V", "")),
            v_1v1_sys=self._safe_float(row.get("1V1_SYS_V", "")),
            v_0v8_sw=self._safe_float(row.get("0V8_SW_V", "")),
            v_vdd_core=self._safe_float(row.get("VDD_CORE_V", "")),
            v_3v3_dac=self._safe_float(row.get("3V3_DAC_V", "")),
            v_3v3_adc=self._safe_float(row.get("3V3_ADC_V", "")),
            v_0v8_aon=self._safe_float(row.get("0V8_AON_V", "")),
            v_hdmi=self._safe_float(row.get("HDMI_V", "")),
            v_ext5v=self._safe_float(row.get("EXT5V_V", "")),
            v_batt=self._safe_float(row.get("BATT_V", ""))
        )

        currents = Currents(
            i_3v7_wl_sw=self._safe_float(row.get("3V7_WL_SW_A", "")),
            i_3v3_sys=self._safe_float(row.get("3V3_SYS_A", "")),
            i_1v8_sys=self._safe_float(row.get("1V8_SYS_A", "")),
            i_ddr_vdd2=self._safe_float(row.get("DDR_VDD2_A", "")),
            i_ddr_vddq=self._safe_float(row.get("DDR_VDDQ_A", "")),
            i_1v1_sys=self._safe_float(row.get("1V1_SYS_A", "")),
            i_0v8_sw=self._safe_float(row.get("0V8_SW_A", "")),
            i_vdd_core=self._safe_float(row.get("VDD_CORE_A", "")),
            i_3v3_dac=self._safe_float(row.get("3V3_DAC_A", "")),
            i_3v3_adc=self._safe_float(row.get("3V3_ADC_A", "")),
            i_0v8_aon=self._safe_float(row.get("0V8_AON_A", "")),
            i_hdmi=self._safe_float(row.get("HDMI_A", ""))
        )

        status = SystemStatus(
            throttle_hex=row.get("throttle_hex", "").strip(),
            uv=row.get("UV", "").strip(),
            arm_freq_cap=row.get("ArmFreqCap", "").strip(),
            cur_throttle=row.get("CurThrottle", "").strip(),
            soft_temp_limit=row.get("SoftTempLimit", "").strip(),
            uv_occured=row.get("UV_occured", "").strip(),
            arm_freq_cap_occured=row.get("ArmFreqCap_occured", "").strip(),
            throttle_occured=row.get("Throttle_occured", "").strip(),
            soft_temp_limit_occured=row.get("SoftTempLimit_occured", "").strip(),
            readmr_registers={
                "readmr_4": self._safe_float(row.get("readmr_4", "")),
                "readmr_5": self._safe_float(row.get("readmr_5", "")),
                "readmr_6": self._safe_float(row.get("readmr_6", "")),
                "readmr_8": self._safe_float(row.get("readmr_8", ""))
            }
        )

        return TelemetryRecord(
            timestamp=timestamp,
            time_sec=time_sec,
            time_min=time_sec / 60.0,
            cpu_percent=self._safe_float(row.get("cpu_percent", "")),
            arm_temp=self._safe_float(row.get("arm_temp", "")),
            clocks=clocks,
            voltages=voltages,
            currents=currents,
            status=status
        )

    def read_directory(self, input_path: Path, filename: str = "ALL_PERIPH_MID_PETITION.csv") -> Iterator[TelemetryRecord]:
        
        if input_path.is_file():
            target_file = input_path
        else:
            target_file = input_path / filename

        if not target_file.exists():
            logging.error(f"No se encontró el archivo en: {target_file}")
            raise FileNotFoundError(f"Archivo no encontrado: {target_file}")

        logging.info(f"Procesando telemetría desde: {target_file}")
        
        # Reseteamos el contador inicial cada vez que leemos un archivo nuevo
        self._first_timestamp = None
        
        with open(target_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for line_num, row in enumerate(reader, start=2):
                try:
                    yield self._parse_row(row)
                except Exception as e:
                    logging.warning(f"Error parseando la línea {line_num}: {e}. Fila omitida.")