import os
import csv
import datetime
from rf_validation_metrics import ejecutar_validacion

# ================= CONFIGURACIÓN DE EJECUCIÓN =================
# 1. Nombre de tu archivo subido
RUTA_ARCHIVO = "data_105700000.csv"

# 2. Selecciona el modo descomentando la línea deseada:
MODO_EJECUCION = "MONITOR"  # Solo muestra en pantalla
# MODO_EJECUCION = "MINERIA"  # Guarda en un archivo .csv histórico
# ==============================================================

def procesar():
    if not os.path.exists(RUTA_ARCHIVO):
        print(f"❌ ERROR: No encuentro el archivo '{RUTA_ARCHIVO}' en Colab.")
        print("   -> Arrastra tu archivo a la carpeta de la izquierda.")
        return

    # Ejecutar algoritmo
    resultados = ejecutar_validacion(RUTA_ARCHIVO)

    # ---------------------------------------------------------
    # OPCIÓN A: MONITOR SERIAL (VER EN PANTALLA)
    # ---------------------------------------------------------
    if MODO_EJECUCION == "MONITOR":
        print(f"\n{'='*45}")
        print(f"   🖥️  MONITOR DE CALIDAD DE SEÑAL")
        print(f"{'='*45}")

        if results_validos := resultados.get("valid"):
            m = resultados["metrics"]
            pass_ks = m['ks_passed']
            pass_sim = m['similarity_passed']

            print(f"📂 Archivo analizado: {RUTA_ARCHIVO}")
            print(f"📊 Métricas:")
            print(f"   1. Test K-S (Estadística):  {m['ks_statistic']:.4f}  [{'✅ PASS' if pass_ks else '❌ FAIL'}]")
            print(f"   2. Test Coseno (Forma):     {m['cosine_similarity']:.4f}  [{'✅ PASS' if pass_sim else '❌ FAIL'}]")
            print("-" * 45)

            if resultados['test_passed']:
                print(f"✅ ESTADO FINAL: APROBADO")
                print(f"🔧 CALIBRACIÓN SUGERIDA: Sumar {resultados['calibration_offset_dB']:.2f} dB")
            else:
                print(f"⚠️ ESTADO FINAL: RECHAZADO (Señal sucia o ruido)")
        else:
            print(f"❌ ERROR CRÍTICO: {resultados.get('error')}")
        print(f"{'='*45}\n")

    # ---------------------------------------------------------
    # OPCIÓN B: MINERÍA DE DATOS (GUARDAR EN LOG)
    # ---------------------------------------------------------
    elif MODO_EJECUCION == "MINERIA":
        archivo_log = "mineria_datos_calibracion.csv"
        existe_log = os.path.exists(archivo_log)

        with open(archivo_log, mode='a', newline='') as f:
            writer = csv.writer(f)
            # Crear cabecera si es la primera vez
            if not existe_log:
                writer.writerow(["Fecha", "Archivo", "Valido", "KS_Stat", "Similitud", "Offset_dB", "Error"])

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if results_validos := resultados.get("valid"):
                m = resultados["metrics"]
                writer.writerow([
                    timestamp,
                    RUTA_ARCHIVO,
                    resultados['test_passed'],
                    f"{m['ks_statistic']:.4f}",
                    f"{m['cosine_similarity']:.4f}",
                    f"{resultados['calibration_offset_dB']:.2f}",
                    "None"
                ])
                print(f"💾 [MINERÍA] Registro guardado en '{archivo_log}'")
                print(f"   -> Valido: {resultados['test_passed']} | Offset: {resultados['calibration_offset_dB']:.2f} dB")
            else:
                writer.writerow([timestamp, RUTA_ARCHIVO, False, 0, 0, 0, resultados.get('error')])
                print(f"💾 [MINERÍA] Error registrado en '{archivo_log}'")

# Ejecutar la función
if __name__ == "__main__":
    procesar()