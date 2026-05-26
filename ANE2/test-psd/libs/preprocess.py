import numpy as np
from scipy import signal
from sklearn.preprocessing import MinMaxScaler

def preprocessSignals(nom_signal, rec_signal):
    """Preprocess two 1D signals for comparison.

    - Resamples both signals to a common length (by default the shorter length)
      using `scipy.signal.resample` (handles arbitrary length ratios).
    - Replaces non-finite values with finite numbers using ``np.nan_to_num``.
    - Scales signals to the range [0, 1] using `sklearn.preprocessing.MinMaxScaler`
      fitted on the nominal (reference) signal so scaling is reversible.

    Returns
    -------
    nom_scaled, rec_scaled, scaler, info
        `nom_scaled` and `rec_scaled` are 1D numpy arrays of the same length.
        `scaler` is the fitted MinMaxScaler (use `scaler.inverse_transform` to
        revert scaling). `info` is a dict with original lengths and target length.
    """
    # Convert to numpy arrays and ensure 1D
    nom = np.asarray(nom_signal).flatten()
    rec = np.asarray(rec_signal).flatten()

    # Replace NaNs / infs with finite numbers (avoid crashes in resampling)
    if not np.isfinite(nom).all():
        nom = np.nan_to_num(nom, nan=0.0, posinf=np.finfo(float).max, neginf=np.finfo(float).min)
    if not np.isfinite(rec).all():
        rec = np.nan_to_num(rec, nan=0.0, posinf=np.finfo(float).max, neginf=np.finfo(float).min)

    len_nom = nom.size
    len_rec = rec.size

    # Choose target length: the shorter of the two by default
    target_len = min(len_nom, len_rec)

    # Resample if needed (handles arbitrary ratios)
    if len_nom != target_len:
        nom_resampled = signal.resample(nom, target_len)
    else:
        nom_resampled = nom.astype(float)

    if len_rec != target_len:
        rec_resampled = signal.resample(rec, target_len)
    else:
        rec_resampled = rec.astype(float)

    # Scale to [0,1] with MinMaxScaler fitted on nominal/reference
    nom_reshaped = nom_resampled.reshape(-1, 1)
    rec_reshaped = rec_resampled.reshape(-1, 1)

    scaler = MinMaxScaler(feature_range=(0, 1))
    # Fit on nominal and transform both; safe if nominal is constant
    nom_scaled = scaler.fit_transform(nom_reshaped).ravel()
    # If scaler would divide by zero (constant signal), transform still returns zeros
    rec_scaled = scaler.transform(rec_reshaped).ravel()

    info = {
        "original_lengths": (len_nom, len_rec),
        "target_length": target_len,
    }

    return nom_scaled, rec_scaled, scaler, info

def mseMaeSpectralDistance(nom_signal, rec_signal):
    """Compute MSE, MAE and a stable spectral-distance-like metric.

    The spectral distance is defined here as 10*log10((MSE + eps) / (MAE + eps)).
    A small epsilon prevents division-by-zero and keeps the metric numerically
    stable. Inputs may be in linear units or dB; the caller should ensure both
    signals use the same units.

    Returns
    -------
    mse, mae, spectral_distance
        Mean squared error, mean absolute error, and the spectral-distance value
        (in dB). If both errors are zero, spectral_distance is 0. If MAE is zero
        but MSE > 0, spectral_distance will be +inf.
    """
    a = np.asarray(nom_signal).flatten().astype(float)
    b = np.asarray(rec_signal).flatten().astype(float)

    if a.size != b.size:
        raise ValueError("nom_signal and rec_signal must have the same length")

    diff = a - b
    mse = np.mean(diff ** 2)
    mae = np.mean(np.abs(diff))

    eps = 1e-12
    if mae == 0.0:
        spectral_distance = 0.0 if mse == 0.0 else float('inf')
    else:
        spectral_distance = 10.0 * np.log10((mse + eps) / (mae + eps))

    return mse, mae, spectral_distance