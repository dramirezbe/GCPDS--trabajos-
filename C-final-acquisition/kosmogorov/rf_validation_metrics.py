import pandas as pd
import numpy as np
from scipy import stats
import os

class RFValidator:
    def __init__(self, umbral_ks=0.20, umbral_similitud=0.90):
        self.ks_threshold = umbral_ks
        self.similarity_threshold = umbral_similitud

    def calcular_calibracion_y_validar(self, csv_path):
        try:
            if not os.path.exists(csv_path):
                return {"valid": False, "error": f"Archivo no encontrado: {csv_path}"}

            df = pd.read_csv(csv_path)

            # Identificación inteligente de columnas
            cols = df.columns
            col_ref = next((c for c in cols if "N9000B" in c or "ref" in c.lower()), None)
            col_dut = next((c for c in cols if "Sensor" in c or "hackrf" in c.lower()), None)

            if not col_ref or not col_dut:
                return {"valid": False, "error": f"Columnas no identificadas. Se requiere referencia y sensor."}

            ref = df[col_ref].dropna().values
            dut = df[col_dut].dropna().values

            if len(ref) == 0 or len(dut) == 0:
                return {"valid": False, "error": "Datos vacíos."}

            min_len = min(len(ref), len(dut))
            ref = ref[:min_len]
            dut = dut[:min_len]

            # 1. OFFSET
            potencia_media_ref = np.mean(ref)
            potencia_media_dut = np.mean(dut)
            offset_calculado = potencia_media_ref - potencia_media_dut

            # 2. NORMALIZACIÓN
            if np.std(ref) == 0 or np.std(dut) == 0:
                 return {"valid": False, "error": "Señal plana (std=0)."}

            ref_norm = (ref - np.mean(ref)) / np.std(ref)
            dut_norm = (dut - np.mean(dut)) / np.std(dut)

            # 3. TEST COSENO
            dot_product = np.dot(ref_norm, dut_norm)
            norm_a = np.linalg.norm(ref_norm)
            norm_b = np.linalg.norm(dut_norm)
            cosine_similarity = dot_product / (norm_a * norm_b) if (norm_a * norm_b) > 0 else 0

            # 4. TEST K-S
            ks_stat, p_value = stats.ks_2samp(ref_norm, dut_norm)

            # 5. DECISIÓN
            ks_pass = ks_stat < self.ks_threshold
            sim_pass = cosine_similarity > self.similarity_threshold
            test_exitoso = ks_pass and sim_pass

            return {
                "valid": True,
                "test_passed": bool(test_exitoso),
                "calibration_offset_dB": float(offset_calculado),
                "metrics": {
                    "ks_statistic": float(ks_stat),
                    "ks_threshold": self.ks_threshold,
                    "ks_passed": bool(ks_pass),
                    "cosine_similarity": float(cosine_similarity),
                    "similarity_threshold": self.similarity_threshold,
                    "similarity_passed": bool(sim_pass)
                }
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

def ejecutar_validacion(csv_path):
    """Wrapper simple para llamar a la clase"""
    validator = RFValidator()
    return validator.calcular_calibracion_y_validar(csv_path)