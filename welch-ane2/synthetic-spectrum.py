import numpy as np
import matplotlib.pyplot as plt

def generate_synthetic_spectrum(num_bins=1024, signal_freq_bin=200, signal_power_db=10, noise_floor_db=-20):
    """
    Generates a synthetic power spectrum with a signal peak and a noise floor.

    Args:
        num_bins (int): Number of frequency bins in the spectrum.
        signal_freq_bin (int): The frequency bin where the signal peak is located.
        signal_power_db (float): Power of the signal peak in dB.
        noise_floor_db (float): Power of the noise floor in dB.

    Returns:
        np.ndarray: The power spectrum in linear scale.
    """
    # Convert dB to linear power
    signal_power_linear = 10**(signal_power_db / 10)
    noise_floor_linear = 10**(noise_floor_db / 10)

    # Initialize spectrum with noise floor
    spectrum = np.full(num_bins, noise_floor_linear)

    # Add a signal peak (e.g., a Gaussian shape)
    # For simplicity, let's just add a strong value at the signal bin
    spectrum[signal_freq_bin] += signal_power_linear

    # Add some random fluctuations to the noise floor for realism
    # This simulates measurement noise on the spectrum itself
    spectrum += np.random.normal(0, noise_floor_linear * 0.1, num_bins)
    spectrum[spectrum < 0] = 1e-10 # Ensure no negative power

    return spectrum

# Generate a sample spectrum
sample_spectrum = generate_synthetic_spectrum()

# Plot the spectrum (in dB for better visualization)
plt.figure(figsize=(10, 5))
plt.plot(10 * np.log10(sample_spectrum))
plt.title('Synthetic Power Spectrum (dB)')
plt.xlabel('Frequency Bin')
plt.ylabel('Power (dB)')
plt.grid(True)
plt.show()