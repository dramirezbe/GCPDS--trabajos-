import os
import sys
import json
import numpy as np
import pandas as pd
from scipy import stats
from scipy.interpolate import interp1d

def load_signals_from_folder(folder_path):
    """
    Carga señales espectrales (freq, Pxx) de archivos JSON en una carpeta.
    Retorna una lista de diccionarios, donde cada dict es una señal { 'freq': [...], 'Pxx': [...] }.
    """
    signals = []
    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    # Verificar si las claves 'freq' y 'Pxx' existen
                    if 'freq' in data and 'Pxx' in data:
                        freq = np.array(data['freq'])
                        pxx = np.array(data['Pxx'])
                        if len(freq) == len(pxx) and len(freq) > 0:
                            signals.append({'freq': freq, 'Pxx': pxx})
                        else:
                            print(f"Advertencia: Archivo '{filename}' en '{folder_path}' tiene datos inconsistentes o vacíos. Saltando.")
                    else:
                        print(f"Advertencia: Archivo '{filename}' en '{folder_path}' no contiene las claves 'freq' o 'Pxx'. Saltando.")
            except json.JSONDecodeError:
                print(f"Advertencia: Archivo '{filename}' en '{folder_path}' no es un JSON válido. Saltando.")
            except Exception as e:
                print(f"Error al procesar '{filename}' en '{folder_path}': {e}. Saltando.")
    return signals

def interpolate_signals(signals, common_freq_points):
    """
    Interpola las señales Pxx a un conjunto común de puntos de frecuencia.
    """
    interpolated_pxx_list = []
    for sig in signals:
        freq = sig['freq']
        pxx = sig['Pxx']
        # Usar interpolación lineal para Pxx.
        # Asegurarse de que los puntos de interpolación estén dentro del rango de freq original.
        interp_func = interp1d(freq, pxx, kind='linear', bounds_error=False, fill_value="extrapolate")
        interpolated_pxx = interp_func(common_freq_points)
        # Asegurarse de que no haya NaNs si extrapolate no se usó o si los puntos están fuera de rango
        # Podrías querer rellenar NaNs con 0 o la media, dependiendo del contexto.
        interpolated_pxx_list.append(interpolated_pxx)
    return interpolated_pxx_list


def extract_metrics(freq_points, pxx_data):
    """
    Extrae métricas clave de una señal de potencia espectral (Pxx).
    """
    metrics = {}

    # 1. Potencia Total
    # Aproximación de la integral usando la regla del trapecio
    metrics['total_power'] = np.trapz(pxx_data, freq_points)

    # 2. Pico de Potencia y Frecuencia del Pico
    max_pxx_idx = np.argmax(pxx_data)
    metrics['peak_power'] = pxx_data[max_pxx_idx]
    metrics['peak_frequency'] = freq_points[max_pxx_idx]

    # 3. Frecuencia Central (Centroid Frequency)
    # ponderada por la potencia
    if metrics['total_power'] > 0:
        metrics['centroid_frequency'] = np.sum(freq_points * pxx_data) / metrics['total_power']
    else:
        metrics['centroid_frequency'] = 0.0 # O NaN, si prefieres

    # 4. Ancho de Banda Ocupado (99%) - Simplificado
    # Esto es una aproximación y requiere que Pxx sea no-negativo.
    # Necesitaríamos sortear y luego encontrar los percentiles.
    # Una implementación más robusta de OBW requeriría una distribución de probabilidad acumulativa.
    # Para simplicidad, podríamos tomar el rango de frecuencias donde la Pxx es significativa.
    # O, calcular el rango de freqs que contienen el 99% de la potencia
    
    # Para una aproximación más sencilla del "ancho de banda efectivo" o dispersión
    # Podríamos usar la varianza ponderada de la frecuencia
    if metrics['total_power'] > 0:
        mean_freq = metrics['centroid_frequency']
        variance_freq = np.sum((freq_points - mean_freq)**2 * pxx_data) / metrics['total_power']
        metrics['rms_bandwidth'] = np.sqrt(variance_freq)
    else:
        metrics['rms_bandwidth'] = 0.0

    return metrics

def run_anova(group1_data, group2_data, metric_name):
    """
    Ejecuta ANOVA para una métrica dada entre dos grupos.
    Retorna el estadístico F, el valor p y una conclusión.
    """
    f_stat, p_value = stats.f_oneway(group1_data, group2_data)
    conclusion = ""
    if p_value < 0.05:
        conclusion = "Diferencia estadísticamente significativa"
    else:
        conclusion = "No hay diferencia estadísticamente significativa"
    return f_stat, p_value, conclusion

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python script.py <ruta_a_device_folder1> <ruta_a_device_folder2>")
        sys.exit(1)

    path_device1 = sys.argv[1]
    path_device2 = sys.argv[2]

    # Validar que las rutas son directorios existentes
    if not os.path.isdir(path_device1):
        print(f"Error: La ruta '{path_device1}' no es un directorio válido o no existe.")
        sys.exit(1)
    if not os.path.isdir(path_device2):
        print(f"Error: La ruta '{path_device2}' no es un directorio válido o no existe.")
        sys.exit(1)

    print(f"Cargando señales de '{path_device1}'...")
    signals_device1 = load_signals_from_folder(path_device1)
    print(f"Cargando señales de '{path_device2}'...")
    signals_device2 = load_signals_from_folder(path_device2)

    if not signals_device1:
        print(f"No se encontraron señales válidas en '{path_device1}'.")
        sys.exit(1)
    if not signals_device2:
        print(f"No se encontraron señales válidas en '{path_device2}'.")
        sys.exit(1)

    # --- Paso de Normalización/Interpolación ---
    # Encontrar un conjunto común de puntos de frecuencia para todas las señales
    # Esto es crucial si las señales tienen diferentes rangos o resoluciones de frecuencia.
    # Para simplificar, usaremos los puntos de la primera señal de device1 como referencia.
    # Una solución más robusta sería encontrar el min_freq, max_freq global y un número fijo de puntos.
    
    # Tomamos la primera señal para definir el rango de frecuencias de referencia
    # Si las señales tienen rangos muy diferentes, esta parte necesita ser más sofisticada
    reference_freq_points = signals_device1[0]['freq']
    print(f"\nNormalizando señales a {len(reference_freq_points)} puntos de frecuencia de referencia...")
    
    interpolated_pxx_device1 = interpolate_signals(signals_device1, reference_freq_points)
    interpolated_pxx_device2 = interpolate_signals(signals_device2, reference_freq_points)

    # --- Extracción de Métricas ---
    all_metrics_data = []

    for i, pxx_data in enumerate(interpolated_pxx_device1):
        metrics = extract_metrics(reference_freq_points, pxx_data)
        metrics['device'] = 'device1'
        all_metrics_data.append(metrics)

    for i, pxx_data in enumerate(interpolated_pxx_device2):
        metrics = extract_metrics(reference_freq_points, pxx_data)
        metrics['device'] = 'device2'
        all_metrics_data.append(metrics)

    df_metrics = pd.DataFrame(all_metrics_data)

    print("\n--- Métricas Promedio por Dispositivo ---")
    print(df_metrics.groupby('device').mean().round(4))
    print("-" * 50)

    print("\n--- Resultados de ANOVA ---")
    # Realizar ANOVA para cada métrica
    anova_results = []
    
    # Obtener la lista de métricas a analizar (excluyendo 'device')
    metrics_to_analyze = [col for col in df_metrics.columns if col != 'device']

    for metric in metrics_to_analyze:
        group1_data = df_metrics[df_metrics['device'] == 'device1'][metric]
        group2_data = df_metrics[df_metrics['device'] == 'device2'][metric]

        f_stat, p_value, conclusion = run_anova(group1_data, group2_data, metric)
        anova_results.append({
            'Métrica': metric,
            'F-Statistic': round(f_stat, 4),
            'P-Value': round(p_value, 4),
            'Conclusión': conclusion
        })
    
    df_anova = pd.DataFrame(anova_results)
    print(df_anova.to_string(index=False)) # Imprime la tabla sin el índice de Pandas
    print("-" * 50)

    print("\nAnálisis completado. ¡Espero que estos resultados te sean útiles!")