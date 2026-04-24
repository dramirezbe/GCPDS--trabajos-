import numpy as np
from scipy.signal import savgol_filter

def smooth_psd(x, window_length=21, polyorder=2):
    """
    Suaviza la PSD preservando forma espectral.
    """
    x = np.asarray(x, dtype=float)


    window_length = min(window_length, len(x))
    if window_length % 2 == 0:
        window_length -= 1
    if window_length < polyorder + 2:
        window_length = polyorder + 2
        if window_length % 2 == 0:
            window_length += 1
    if window_length >= len(x):
        window_length = len(x) - 1 if len(x) % 2 == 0 else len(x)
    if window_length < 3:
        return x.copy()

    return savgol_filter(x, window_length=window_length, polyorder=polyorder)





def estimate_local_trend(window_y: np.ndarray):
    """
    Estima la tendencia local de una ventana usando regresión lineal simple.

    Retorna:
        slope_db_per_bin : pendiente local en dB/bin
        level_db         : nivel robusto local (mediana)
    """
    y = np.asarray(window_y, dtype=float)

    if y.size == 0:
        return 0.0, np.nan
    if y.size == 1:
        return 0.0, float(y[0])

    x = np.arange(y.size, dtype=float)
    x = x - np.mean(x)
    y_centered = y - np.mean(y)

    denom = np.dot(x, x)
    if denom <= 0:
        slope = 0.0
    else:
        slope = float(np.dot(x, y_centered) / denom)

    level = float(np.median(y))
    return slope, level

def find_local_minima_indices(y: np.ndarray):
    """
    Encuentra mínimos locales simples en un vector 1D.
    Retorna índices relativos al vector de entrada.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)

    if n < 3:
        return []

    minima = []
    for i in range(1, n - 1):
        if (y[i] <= y[i - 1] and y[i] < y[i + 1]) or (y[i] < y[i - 1] and y[i] <= y[i + 1]):
            minima.append(i)

    return minima
