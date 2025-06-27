# from libs import exec_psd_full, cargar_cs8
import os
import numpy as np
import matplotlib.pyplot as plt

import os
from tqdm import tqdm

TO_MHZ = 1000000

FS = 20000000
LOW_FREQ = 88 * TO_MHZ
CENTER_FREQ = 98 * TO_MHZ
HIGH_FREQ = 108 * TO_MHZ
BANDWIDTH = (HIGH_FREQ - LOW_FREQ) * TO_MHZ
SEG = 4096
OVERLAP = 0.5
WINDOW = 'hamming'

base_path = 'Samples-sdr'


# Cargar el archivo como enteros con signo de 8 bits
def cargar_cs8(filename):
    data = np.fromfile(filename, dtype=np.int8)
    I = data[0::2]  # Muestras pares como parte real
    Q = data[1::2]  # Muestras impares como parte imaginaria
    señal_compleja = I + 1j * Q
    return señal_compleja, I, Q

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


# raw_sig, I, Q = cargar_cs8(os.path.join(base_path,str(0)))
# Estimar la PSD usando la función ajustada de Welch con eliminación de la media

def exec_psd_full(x, fs, segment_length, overlap=0.5, window_type='hammming'):
    f, Pxx = welch_psd_full(x, fs, segment_length, overlap, window_type)

    return np.fft.fftshift(f), np.fft.fftshift(Pxx)





raw_sig, I, Q = cargar_cs8(os.path.join(base_path,"captura_88.5MHz_20MSps.cs8"))
# Estimar la PSD usando la función ajustada de Welch con eliminación de la media

_, Pxx = exec_psd_full(raw_sig, FS, SEG, OVERLAP, WINDOW)

f = np.linspace(LOW_FREQ/TO_MHZ,HIGH_FREQ/TO_MHZ, len(Pxx))


plt.semilogy(f, Pxx)
plt.show()