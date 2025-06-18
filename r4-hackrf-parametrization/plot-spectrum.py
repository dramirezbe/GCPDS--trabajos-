import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt # Import matplotlib for plotting

def load_signals_from_folder(folder_path):
    """
    Loads frequency and Pxx data from all JSON files in the specified folder.

    Args:
        folder_path (str): The path to the folder containing JSON signal files.

    Returns:
        list: A list of dictionaries, where each dictionary contains 'filename',
              'f' (frequencies), and 'Pxx' (power spectral density) for a signal.
    """
    signals_data = []
    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        if os.path.isfile(filepath) and filename.lower().endswith('.json'):
            try:
                with open(filepath, 'r') as f_obj:
                    data = json.load(f_obj)
                    # Check if 'f' and 'Pxx' keys exist
                    if 'f' in data and 'Pxx' in data:
                        freq = np.array(data['f'])
                        pxx = np.array(data['Pxx'])
                        signals_data.append({'filename': filename, 'f': freq, 'Pxx': pxx})
                    else:
                        print(f"Advertencia: El archivo '{filename}' no contiene las claves 'f' y 'Pxx'. Saltando.")
            except json.JSONDecodeError:
                print(f"Advertencia: El archivo '{filename}' no es un JSON válido. Saltando.")
            except Exception as e:
                print(f"Error al procesar '{filename}': {e}")
    return signals_data

if __name__ == "__main__":
    # Check for correct number of command-line arguments
    if len(sys.argv) != 2:
        print("Uso: python script.py <ruta_a_folder_de_señales>")
        sys.exit(1)

    signals_folder_path = sys.argv[1]

    # Validate if the provided path is a directory
    if not os.path.isdir(signals_folder_path):
        print(f"Error: La ruta '{signals_folder_path}' no es un directorio válido.")
        sys.exit(1)

    print(f"Cargando señales de '{signals_folder_path}'...")
    all_signals = load_signals_from_folder(signals_folder_path)

    if not all_signals:
        print(f"No se encontraron señales válidas (archivos JSON con 'f' y 'Pxx') en '{signals_folder_path}'.")
        sys.exit(0) # Exit gracefully if no signals found

    print(f"Se encontraron {len(all_signals)} señales para graficar.")

    for signal_data in all_signals:
        filename = signal_data['filename']
        f = signal_data['f']
        pxx = signal_data['Pxx']

        plt.figure(figsize=(10, 6))
        plt.plot(f, pxx)
        plt.title(f"Espectro de Potencia: {filename}")
        plt.xlabel("Frecuencia (Hz)")
        plt.ylabel("Densidad Espectral de Potencia (Pxx)")
        plt.grid(True)
        plt.tight_layout() # Adjust layout to prevent labels from overlapping
        plt.show()

        # Ask user to press Enter to show the next plot or exit
        user_input = input(f"Presiona Enter para ver la siguiente señal ('{filename}') o 'q' para salir: ")
        if user_input.lower() == 'q':
            print("Saliendo del programa.")
            break # Exit the loop if user types 'q'

    print("Todas las señales han sido mostradas.")