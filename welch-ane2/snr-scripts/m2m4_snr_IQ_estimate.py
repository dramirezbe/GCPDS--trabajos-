import numpy as np
import os
import scipy.signal as sig
import matplotlib.pyplot as plt


def m2m4_snr_estimator(i_vector, q_vector):
    """
    Estimates the Signal-to-Noise Ratio (SNR) using the M2M4 algorithm for complex signals.

    This function combines in-phase (I) and quadrature (Q) components to form a complex signal,
    then calculates the second and fourth order moments, and finally uses these moments
    to estimate the SNR.

    Args:
        i_vector (numpy.ndarray or list): A 1D array or list of in-phase components.
        q_vector (numpy.ndarray or list): A 1D array or list of quadrature components.

    Returns:
        float: The estimated SNR in decibels (dB). Returns NaN if the calculation is invalid
               (e.g., due to negative values under the square root).
    """
    i_vector = np.asarray(i_vector)
    q_vector = np.asarray(q_vector)

    if i_vector.shape != q_vector.shape:
        raise ValueError("I and Q vectors must have the same shape.")
    if i_vector.ndim > 1:
        raise ValueError("I and Q vectors must be 1-dimensional.")

    # 1. Combine I and Q vectors to form the complex signal y
    y = i_vector + 1j * q_vector

    # Calculate the squared magnitude of the complex signal
    abs_y_squared = np.abs(y)**2

    # 2. Calculate the second moment (M2)
    m2 = np.mean(abs_y_squared)

    # 3. Calculate the fourth moment (M4)
    m4 = np.mean(abs_y_squared**2)

    # 4. Apply the M2M4 formula
    # S = sqrt(2*M2^2 - M4)
    # N = M2 - S
    # SNR = S/N

    # Ensure the term inside the square root is non-negative
    discriminant = 2 * m2**2 - m4
    if discriminant < 0:
        # print("Warning: Discriminant for M2M4 is negative. Returning NaN.")
        return np.nan # Or handle as an error, indicating invalid input/estimation conditions

    estimated_signal_power_s = np.sqrt(discriminant)
    estimated_noise_power_n = m2 - estimated_signal_power_s

    # Avoid division by zero for noise power
    if estimated_noise_power_n <= 0:
        if estimated_signal_power_s > 0:
            return np.inf  # Very high SNR if noise is zero or negative
        else:
            return np.nan # Undefined if both signal and noise are zero/negative

    snr_linear = estimated_signal_power_s / estimated_noise_power_n

    # 5. Convert the SNR to dB
    snr_db = 10 * np.log10(snr_linear)

    return snr_db


# Cargar el archivo como enteros con signo de 8 bits
def cargar_cs8(filename):
    data = np.fromfile(filename, dtype=np.int8)
    I = data[0::2]  # Muestras pares como parte real
    Q = data[1::2]  # Muestras impares como parte imaginaria
    
    return I, Q