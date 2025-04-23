import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
from tqdm import tqdm

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


# Parámetros de la señal y su creación
fs = 20000000  # Frecuencia de muestreo
N = 20000000  # Número de puntos de la señal
seg = 1024
t = np.linspace(0, N / fs, N)

# Generación de la señal compleja en formato i + jQ
I = 0.25 * np.sin(2 * np.pi * 1000000 * t) + np.random.normal(0, 0.2, N)  # Componente I
Q = 0.25 * np.sin(2 * np.pi * 2000000 * t) + np.random.normal(0, 0.2, N)   # Componente Q
signal = I + 1j * Q  # Señal compleja

# Estimar la PSD usando la función ajustada de Welch con eliminación de la media
f_adjusted, P_welch_adjusted = welch_psd_full(signal, fs=fs, segment_length=seg, overlap=0, window_type='hamming')

# Estimar la PSD usando la función de Welch de SciPy
f_scipy, P_welch_scipy = welch(signal, fs=fs, nperseg=seg, noverlap=0, window='hamming', return_onesided=False)

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
