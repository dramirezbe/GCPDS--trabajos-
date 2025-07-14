import uhd
import numpy as np
import sys # Import the sys module to access command-line arguments
# Check if command-line arguments for center_user_freq and gain are provided
if len(sys.argv) < 3:
    print("Usage: python3 USRP_Tx.py <center_user_freq_MHz> <gain_dB>")
    print("Example: python3 USRP_Tx.py 98 20")
    sys.exit(1) # Exit if arguments are not provided

try:
    # Get the center_user_freq and gain from the command-line arguments
    center_user_freq_MHz = float(sys.argv[1]) # Use float for potentially non-integer frequencies
    gain_dB = int(sys.argv[2])
except ValueError:
    print("Error: center_user_freq_MHz must be a number and gain_dB must be an integer.")
    sys.exit(1) # Exit if arguments are not valid

# Initialize USRP device
try:
    usrp = uhd.usrp.MultiUSRP("type=b200")
except RuntimeError as e:
    print(f"Error initializing USRP: {e}")
    print("Please ensure your USRP is connected and UHD drivers are installed correctly.")
    sys.exit(1)

# Duration for the transmission in seconds
duration_min = 10
transmission_duration_seconds = duration_min * 60 # 10 minutes

# Calculate the center frequency in Hz
center_freq_Hz = center_user_freq_MHz * 1e6 # Convert MHz to Hz

# Sample rate in samples per second. This dictates your bandwidth.
# Ensure this is appropriate for your USRP and the frequencies you want to generate.
# 201e3 Hz (201 kHz) is relatively small. If you want widely spaced peaks, consider higher.
# For the example, let's keep it but be aware of its implications.
sample_rate = 201e3

# --- Generate Signal with Four Peaks and Noise ---
# Number of samples for one 'burst' or period of the signal.
# We'll create a waveform that repeats for the duration of the transmission.
# A longer NFFT like 4096 or 8192 helps in resolving peaks in the PSD.
num_samples_per_burst = 4096 # Good for FFT resolution, power of 2

# Time vector for one burst
time_per_burst = np.linspace(0, num_samples_per_burst / sample_rate, num_samples_per_burst, endpoint=False)

# Frequencies for the four peaks (relative to baseband 0 Hz)
# These frequencies must be within Nyquist frequency (sample_rate / 2).
# For sample_rate = 201e3, Nyquist is 100.5 kHz.
# Let's choose frequencies that can be clearly seen within this range,
# mimicking the relative spacing of your example image.
# If you want to place them higher in the spectrum, increase sample_rate.
peak_frequencies_Hz = [
    5e3,    # 5 kHz
    15e3,   # 15 kHz
    40e3,   # 40 kHz
    80e3    # 80 kHz
]

# Amplitudes for the peaks
peak_amplitudes = [
    0.7,  # Highest peak
    0.5,
    0.3,
    0.6   # Second highest peak
]

# Generate the signal for the peaks (sum of sine waves)
signal_peaks = np.zeros(num_samples_per_burst, dtype=np.complex64) # Use complex for baseband
for freq, amp in zip(peak_frequencies_Hz, peak_amplitudes):
    # For real signals centered at baseband, you typically use np.sin.
    # For complex baseband (which USRPs usually expect), you'd use complex exponentials.
    # Since UHD's send_waveform usually expects complex I/Q, we'll generate complex.
    signal_peaks += amp * np.exp(1j * 2 * np.pi * freq * time_per_burst)

# --- Add Noise ---
# Adjust noise_amplitude to control the SNR. Higher amplitude means more noise, lower SNR.
# The noise will have the same power regardless of the peaks, allowing you to see the "true SNR".
noise_amplitude = 0.15 # Example: Adjust this value to control the noise floor level
noise = noise_amplitude * (np.random.randn(num_samples_per_burst) + 1j * np.random.randn(num_samples_per_burst)) # Complex Gaussian noise

# Combine signal and noise
# Normalize the signal to prevent saturation, especially when adding strong peaks and noise.
# The `send_waveform` function often expects values typically between -1 and 1.
combined_signal_burst = (signal_peaks + noise)
# Find the maximum absolute value to normalize to prevent clipping
max_val = np.max(np.abs(combined_signal_burst))
if max_val > 0:
    combined_signal_burst /= max_val
# Scale down slightly to ensure it's within range, e.g., 0.8 as in original example
combined_signal_burst *= 0.8


# Repeat the burst for the entire transmission duration if needed,
# though `send_waveform` often handles continuous transmission of a shorter buffer.
# For simplicity and to match the original structure, we'll assume `send_waveform`
# can repeatedly transmit this `combined_signal_burst`.
samples_to_transmit = combined_signal_burst

print(f"Attempting to transmit at {center_user_freq_MHz} MHz with sample rate {sample_rate/1e3} kHz and gain {gain_dB} dB.")
print(f"Signal duration: {duration_min} minutes.")
print(f"Generated signal with {len(samples_to_transmit)} complex samples per burst.")



# Send the waveform
try:
    # The send_waveform function typically requires the following arguments:
    # (samples, duration, center_freq, sample_rate, channel_list, gain)
    # Assuming channel 0 for transmission
    usrp.send_waveform(samples_to_transmit, transmission_duration_seconds, center_freq_Hz, sample_rate, [0], gain_dB)
    print("Waveform transmission started successfully.")
except uhd.libpyuhd.exceptions.UHDError as e:
    print(f"UHD Error during transmission: {e}")
    print("Possible issues: USRP not configured correctly, frequency out of range, or gain too high.")
    sys.exit(1) # Exit on UHD error
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1) # Exit on other errors

print("Script finished.")