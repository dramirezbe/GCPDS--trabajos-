import numpy as np
from scipy import signal as sig
import matplotlib.pyplot as plt

# Cargar el archivo .cs8
file_path = '/home/javastral/Documents/HackF/88108.cs8'
fs = 20000000

# Cargar el archivo como enteros con signo de 8 bits
def cargar_cs8(filename):
    data = np.fromfile(filename, dtype=np.int8)
    I = data[0::2]  # Muestras pares como parte real
    Q = data[1::2]  # Muestras impares como parte imaginaria
    señal_compleja = I + 1j * Q
    return señal_compleja, I, Q

IQ_data_raw, I, Q = cargar_cs8(file_path)
#IQ_data_raw = IQ_data_raw[:fs]

f_raw, Pxx_raw = sig.welch(IQ_data_raw, fs=fs, nperseg=1024, return_onesided=False)
print("Welch scipy Done")

# Cargar datos procesados
data = np.loadtxt("psd_output.csv", delimiter=',', skiprows=1)
f_proc = data[:, 0]
Pxx_proc = data[:, 1]

# Desplazar el espectro
f_raw = np.fft.fftshift(f_raw)
Pxx_raw = np.fft.fftshift(Pxx_raw)
f_proc = np.fft.fftshift(f_proc)
Pxx_proc = np.fft.fftshift(Pxx_proc)

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