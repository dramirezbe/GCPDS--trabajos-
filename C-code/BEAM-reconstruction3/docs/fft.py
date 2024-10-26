import numpy as np
import matplotlib.pyplot as plt


DFT16 = np.exp(-2j * np.pi * np.arange(16) * np.arange(16)[:, None] / 16)  # faster
FACTOR = {N: np.exp(-2j * np.pi * np.arange(N / 2) / N) for N in np.array([1024 // 32, 1024 // 16, 1024 // 8, 1024 // 4, 1024 // 2,
                                                                           1024,
                                                                           1024 * 2, 1024 * 4, 1024 * 8, 1024 * 16, 1024 * 32, 1024 * 64, 1024 * 128])}

def _dft(a, axis, forward):
    f = np.moveaxis(a, axis, -1)[..., None]
    N = f.shape[-2]
    DFT = np.exp((-1)**forward * 2j * np.pi * np.arange(N) * np.arange(N)[:, None] / N)
    result = np.moveaxis((DFT @ f)[..., -1], -1, axis)
    return result if forward else result / N

def _fft(a, axis, forward):
    N_min = 16
    N = a.shape[axis]
    # check dimension
    if N & (N - 1) != 0:
        raise ValueError("size of input must be a power of 2")
    # return using dft if dimension is small
    if N <= N_min:
        return _dft(a, axis, forward)
    # if not:
    x = np.moveaxis(a, axis, -1)  # move axis to end
    # split
    DFT16_ = DFT16 if forward else np.conjugate(DFT16)
    X = DFT16_ @ x.reshape((*x.shape[:-1], N_min, -1))
    # combine
    while X.shape[-2] < N:
        X_even = X[..., :X.shape[-1] // 2]
        X_odd = X[..., X.shape[-1] // 2:]
        factor = FACTOR[2 * X.shape[-2]][..., None]
        factor_ = factor if forward else np.conjugate(factor)
        t = factor_ * X_odd
        X = np.concatenate((X_even + t, X_even - t), axis=-2)
    result = np.moveaxis(X[..., -1], -1, axis)
    return result if forward else result / N

def fft(a, axis=-1):
    return _fft(a, axis, True)


# Parámetros de la señal
fs = 1000  # frecuencia de muestreo
t = np.arange(0, 1, 1/fs)  # vector de tiempo de 1 segundo
f1, f2 = 50, 120  # dos frecuencias de las senoidales
signal = np.sin(2 * np.pi * f1 * t) + 0.5 * np.sin(2 * np.pi * f2 * t)  # suma de senoidales

# Zero-padding para que la longitud sea una potencia de 2
next_pow2 = 2**int(np.ceil(np.log2(len(signal))))  # Siguiente potencia de 2
signal = np.pad(signal, (0, next_pow2 - len(signal)), mode='constant')


# FFT con numpy
fft_numpy = np.fft.fft(signal)
freqs = np.fft.fftfreq(len(signal), 1/fs)

# Magnitud y fase
magnitude_numpy = np.abs(fft_numpy)
phase_numpy = np.angle(fft_numpy)

# Implementación from scratch
fft_scratch = fft(signal)

# Magnitud y fase
magnitude_scratch = np.abs(fft_scratch)
phase_scratch = np.angle(fft_scratch)



# Graficar Magnitud y Fase para numpy y scratch

plt.figure(figsize=(14, 8))

# Magnitud - numpy
plt.subplot(2, 2, 1)
plt.plot(freqs[:len(freqs)//2], magnitude_numpy[:len(magnitude_numpy)//2])
plt.title('Magnitud (FFT numpy)')
plt.xlabel('Frecuencia [Hz]')
plt.ylabel('Magnitud')

# Fase - numpy
plt.subplot(2, 2, 2)
plt.plot(freqs[:len(freqs)//2], phase_numpy[:len(phase_numpy)//2])
plt.title('Fase (FFT numpy)')
plt.xlabel('Frecuencia [Hz]')
plt.ylabel('Fase [radianes]')

# Magnitud - scratch
plt.subplot(2, 2, 3)
plt.plot(freqs[:len(freqs)//2], magnitude_scratch[:len(magnitude_scratch)//2])
plt.title('Magnitud (FFT from scratch)')
plt.xlabel('Frecuencia [Hz]')
plt.ylabel('Magnitud')

# Fase - scratch
plt.subplot(2, 2, 4)
plt.plot(freqs[:len(freqs)//2], phase_scratch[:len(phase_scratch)//2])
plt.title('Fase (FFT from scratch)')
plt.xlabel('Frecuencia [Hz]')
plt.ylabel('Fase [radianes]')

plt.tight_layout()
plt.show()