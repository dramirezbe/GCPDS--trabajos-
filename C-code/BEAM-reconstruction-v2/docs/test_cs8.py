import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

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


# Cargar el archivo .cs8
file_path = '/home/javastral/Documents/HackF/88108.cs8'
fs = 20000000

IQ_data_raw, I, Q = cargar_cs8(file_path)
#IQ_data_raw = IQ_data_raw[:fs]

f_raw, Pxx_raw = welch_psd_full(IQ_data_raw, fs=fs, segment_length=1024, overlap=0.5)
print("Welch python Done")

# Cargar datos procesados
data = np.loadtxt("psd_output.csv", delimiter=',', skiprows=1)
f_proc = data[:, 0]
Pxx_proc = data[:, 1]

# Desplazar el espectro
f_raw = np.fft.fftshift(f_raw)
Pxx_raw = np.fft.fftshift(Pxx_raw)
#f_proc = np.fft.fftshift(f_proc)
#Pxx_proc = np.fft.fftshift(Pxx_proc)

# Crear subplots
fig, axs = plt.subplots(2, 1, figsize=(10, 8))

# Gráfico para los datos RAW
axs[0].semilogy(f_raw, Pxx_raw)
axs[0].set_title('Densidad espectral de potencia (RAW)')
axs[0].set_xlabel('Frecuencia (Hz)')
axs[0].set_ylabel('Densidad espectral de potencia (dB/Hz)')
axs[0].grid()

# Gráfico para los datos procesados
axs[1].semilogy(f_proc, Pxx_proc)
axs[1].set_title('Densidad espectral de potencia (C - PROCESADO)')
axs[1].set_xlabel('Frecuencia (Hz)')
axs[1].set_ylabel('Densidad espectral de potencia (dB/Hz)')
axs[1].grid()

# Ajustar el espacio entre subplots
plt.tight_layout()
plt.show()