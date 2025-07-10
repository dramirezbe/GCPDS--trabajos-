import uhd
import numpy as np
import sys # Import the sys module to access command-line arguments


# Check if a command-line argument for center_user_freq is provided
if len(sys.argv) < 2:
    print("Usage: python3 USRP_Tx.py <center_user_freq>")
    print("Example: python3 USRP_Tx.py 98")
    sys.exit(1) # Exit if no argument is provided

try:
    # Get the center_user_freq from the command-line argument
    center_user_freq = int(sys.argv[1])
    # Gain
    gain = int(sys.argv[2])
except ValueError:
    print("Error: center_user_freq must be an integer.")
    sys.exit(1) # Exit if the argument is not a valid integer

# Initialize USRP device
# Ensure your USRP device is connected and recognized by UHD
try:
    usrp = uhd.usrp.MultiUSRP("type=b200")
except RuntimeError as e:
    print(f"Error initializing USRP: {e}")
    print("Please ensure your USRP is connected and UHD drivers are installed correctly.")
    sys.exit(1)

# Duration for the transmission in seconds
duration_min = 10
duration = duration_min * 60 # 10 minutes

# Calculate the center frequency in Hz
center_freq = center_user_freq * 1e6 # Convert MHz to Hz]

# Sample rate in samples per second
sample_rate = 201e3

# Create a random signal
# Using 0.8 for amplitude to stay within typical DAC limits and avoid saturation
samples = 0.8 * np.random.normal(0, 1, 1024)

print(f"Attempting to transmit at {center_user_freq} MHz with sample rate {sample_rate/1e3} kHz and gain {gain} dB.")
print(f"Signal duration: {duration_min} minutes.")

# Send the waveform
try:
    # The send_waveform function typically requires the following arguments:
    # (samples, duration, center_freq, sample_rate, channel_list, gain)
    # Assuming channel 0 for transmission
    usrp.send_waveform(samples, duration, center_freq, sample_rate, [0], gain)
    print("Waveform transmission started successfully.")
except uhd.libpyuhd.exceptions.UHDError as e:
    print(f"UHD Error during transmission: {e}")
    print("Possible issues: USRP not configured correctly, frequency out of range, or gain too high.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("Script finished.")
