import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
from tqdm import tqdm

def welch_psd_full(signal, fs=1.0, segment_length=256, overlap=0.5):
    signal = np.asarray(signal)
    N = len(signal)
    step = int(segment_length * (1 - overlap))

    window = np.hamming(segment_length)

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

# Cargar el archivo como enteros con signo de 8 bits
def cargar_cs8(filename):
    data = np.fromfile(filename, dtype=np.int8)
    I = data[0::2]  # Muestras pares como parte real
    Q = data[1::2]  # Muestras impares como parte imaginaria
    señal_compleja = I + 1j * Q
    return señal_compleja, I, Q


IQ_data_raw, I, Q = cargar_cs8(file_path)
#IQ_data_raw = IQ_data_raw[:fs]

print("IQ_dat_raw shape=", IQ_data_raw.shape)

# Estimar la PSD usando la función ajustada de Welch con eliminación de la media
f_adjusted, P_welch_adjusted = welch_psd_full(IQ_data_raw, fs=fs, segment_length=10224, overlap=0)

# Estimar la PSD usando la función de Welch de SciPy
f_scipy, P_welch_scipy = welch(IQ_data_raw, fs=fs, nperseg=1024, noverlap=0, window='hamming', return_onesided=False)

# Ajuste para visualizar espectro completo
f_adjusted = np.fft.fftshift(f_adjusted)
P_welch_adjusted = np.fft.fftshift(P_welch_adjusted)
f_scipy = np.fft.fftshift(f_scipy)
P_welch_scipy = np.fft.fftshift(P_welch_scipy)

# Graficar los resultados
plt.figure(figsize=(10, 6))
plt.semilogy(f_adjusted, P_welch_adjusted, label='Adjusted Welch (Mean Removed)', linestyle='-', alpha=0.7)
plt.semilogy(f_scipy, P_welch_scipy, label='SciPy Welch (Mean Removed)', linestyle='--', alpha=0.7)
plt.title('Comparación de la estimación de la PSD usando Welch (Media Removida)')
plt.xlabel('Frecuencia [Hz]')
plt.ylabel('Densidad espectral de potencia [V^2/Hz]')
plt.legend()
plt.grid(True)
plt.show()



