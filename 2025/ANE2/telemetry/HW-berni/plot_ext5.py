#plot_ext5.py

from csv_dataclasses import TelemetryParser, TelemetryRecord
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
import logging

def plot_data(records: list[TelemetryRecord]):
    """Extrae las variables de las dataclasses y genera el gráfico."""
    logging.info("Extrayendo vectores y generando la gráfica...")
    
    # Extraemos time_min (X) y v_ext5v (Y), filtrando valores nulos
    t_min = []
    v_ext = []
    
    for r in records: # Fill arrays
        t_min.append(r.time_min)
        v_ext.append(r.voltages.v_ext5v)

    # Creamos la figura
    plt.figure(figsize=(10, 5))
    plt.plot(t_min, v_ext, label="EXT5V_V", color="coral", linewidth=1.5)
    
    # Formateo visual
    plt.title("Voltaje EXT5V a lo largo del tiempo de ejecución")
    plt.xlabel("Tiempo de ejecución (Minutos)")
    plt.ylabel("Voltaje (V)")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.tight_layout()
    
    logging.info("Mostrando ventana del gráfico...")
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Parsea telemetría de RPi5 y grafica una de sus variables."
    )
    parser.add_argument("directory", type=str, help="Ruta a la carpeta o archivo CSV")
    
    args = parser.parse_args()
    input_path = Path(args.directory)

    telemetry_parser = TelemetryParser()

    try:
        # 1. Cargamos TODOS los datos del generador a una lista en memoria.
        # (Para graficar la línea entera, necesitamos la historia completa)
        records_list = list(telemetry_parser.read_directory(input_path))
        
        if not records_list:
            logging.error("El CSV está vacío o no se pudo parsear ninguna fila.")
            return

        # 2. Llamamos a nuestra función de ploteo pasando la lista estructurada
        plot_data(records_list)
            
    except FileNotFoundError:
        logging.error("El archivo o directorio no fue encontrado.")
    except KeyboardInterrupt:
        logging.info("Ejecución interrumpida por el usuario.")

if __name__ == "__main__":
    main()