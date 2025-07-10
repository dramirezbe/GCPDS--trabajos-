import os
import json
import gzip
import numpy as np
import scipy.signal as sig
import matplotlib.pyplot as plt
from tqdm import tqdm

# Cargar el archivo como enteros con signo de 8 bits
def cargar_cs8(filename):
    data = np.fromfile(filename, dtype=np.int8)
    I = data[0::2]  # Muestras pares como parte real
    Q = data[1::2]  # Muestras impares como parte imaginaria
    
    return I, Q

def convertir_json_gz(I, Q, filename):
    with gzip.open(filename, 'wt', encoding='utf-8') as f:
        json.dump({
            'I': I.tolist(),
            'Q': Q.tolist()
        }, f)
    print(f"Compressed JSON file '{filename}' created successfully")
 
def recuperar_IQ_de_json_gz(filename):
    with gzip.open(filename, 'rt', encoding='utf-8') as f:
        data_loaded = json.load(f)
    I_recovered = np.array(data_loaded['I'])
    Q_recovered = np.array(data_loaded['Q'])
    return I_recovered, Q_recovered

def guardar_psd_en_json_gz(f, Pxx, filename):
    """
    Guarda las arrays f y Pxx en un archivo JSON comprimido con gzip.
    """
    # Pxx es una matriz 2x4096, pero f es un array 1x4096. 
    # Para guardarlas en un archivo, ambas deben ser convertidas a lista.
    # Pxx.tolist() ya maneja la conversión de una matriz 2D a una lista de listas.
    with gzip.open(filename, 'wt', encoding='utf-8') as f_gz:
        json.dump({
            'f': f.tolist(),
            'Pxx': Pxx.tolist()
        }, f_gz)
    print(f"Compressed PSD JSON file '{filename}' created successfully")

def welch_psd_full(signal, fs=1.0, segment_length=256, overlap=0.5, window_type='hamming'):
    signal = np.asarray(signal)
    N = len(signal)
    step = int(segment_length * (1 - overlap))

    # Selección y creación de la ventana
    if window_type == 'hamming':
        window = np.hamming(segment_length)
    elif window_type == 'hann':
        window = np.hanning(segment_length)
    elif window_type == 'rectangular':
        window = np.ones(segment_length)
    else:
        raise ValueError("Tipo de ventana no soportado")

    U = np.sum(window ** 2)
    K = (N - segment_length) // step + 1
    P_welch = np.zeros(segment_length)

    # Barra de progreso
    for k in tqdm(range(K), desc="Calculando Welch PSD"):
        start = k * step
        segment = signal[start:start + segment_length] * window

        # Calcular la FFT completa del segmento y obtener PSD
        X_k = np.fft.fft(segment)
        P_k = (1 / (fs * U)) * np.abs(X_k) ** 2

        P_welch += P_k

    P_welch /= K  # Promediar sobre los segmentos
    f = np.fft.fftfreq(segment_length, d=1.0 / fs)

    return f, P_welch

def exec_psd_full(x, fs, segment_length, overlap=0.5, window_type='hammming'):
    f, Pxx = welch_psd_full(x, fs, segment_length, overlap, window_type)

    return np.fft.fftshift(f), np.fft.fftshift(Pxx)

FS = 20e6
NOVERLAP = 0.5
NPERSEG = 4096
WINDOW = 'hamming'

hdd_folder_path = '/home/javastral/HDD-IoT/'
folder_name = "DATA-108-128-USRP"

data_folder_path = os.path.join(hdd_folder_path, folder_name)
project_path = "/home/javastral/GIT/GCPDS--trabajos-/cs8-to-jsongz/"
new_folder_name = "psd-108-128-aislated"
output_folder_path = os.path.join(project_path, new_folder_name)

data_list = os.listdir(data_folder_path)
data_len = len(data_list)


# Create the output folder if it doesn't exist
os.makedirs(output_folder_path, exist_ok=True)

file_counter = 0


for file in os.listdir(data_folder_path):
    print("="*50)
    print(file + " [" + str(file_counter) + "/" + str(data_len) + "]")
    print("="*50)

    file_path = os.path.join(data_folder_path, file)
    print("Processing file: ", file_path)
    try:
        I, Q = cargar_cs8(file_path)
        print("IQ extracted")
        x = I + 1j * Q
        f, Pxx = exec_psd_full(x, FS, NPERSEG, NOVERLAP, WINDOW)
        print("PSD calculated")

        output_filename = os.path.join(output_folder_path, os.path.splitext(file)[0] + '_psd.json.gz')
        guardar_psd_en_json_gz(f, Pxx, output_filename)
        print("PSD JSON gz file created")

    except EOFError:
        print(f"Skipping corrupted file: {file_path} - EOFError: Compressed file ended prematurely.")
    except Exception as e: # Catch any other unexpected errors during processing a file
        print(f"Skipping file due to an unexpected error: {file_path} - Error: {e}")

    file_counter += 1