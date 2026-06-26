import subprocess
import sys
import struct
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal as sig

def capture_sample(freq:float, sample_rate:float, filepath:str):
    """
    Captures a radio signal using hackrf_transfer and saves it to a file.
    
    Args:
        freq (float): The center frequency in Hz.
        fs (float): The sample rate in Hz, in this case bw filter too.
        filepath (str): The path to the output file.
    """
    fs = str(int(sample_rate))
    f = str(freq)

    # We create the command as a list of strings
    command = [
        "hackrf_transfer",
        "-f", f,
        "-s", fs,
        "-b", fs,
        "-r", filepath,
        "-n", fs,
        "-l", "0",#Gain RX LNA
        "-g", "0",#Gain RX VGA
        "-a", "0",#Amplifier False
    ]

    print(f"Executing command: {' '.join(command)}")
    print("-" * 20)

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Print the standard output and standard error
        print("Standard Output:")
        print(process.stdout)
        
        print("Standard Error:")
        print(process.stderr)
        
    except FileNotFoundError:
        print(f"Error: 'hackrf_transfer' not found. Is it installed and in your system's PATH?", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}.", file=sys.stderr)
        print("Standard Output:\n", e.stdout, file=sys.stderr)
        print("Standard Error:\n", e.stderr, file=sys.stderr)
        sys.exit(1)

def load_cs8(filename):
    "Load binary .cs8 file data in IQ vectors"
    I = []
    Q = []
    
    with open(filename, 'rb') as f:
        data = f.read()
    
   
    for i in range(0, len(data), 2):
        real_part, imag_part = struct.unpack('bb', data[i:i+2])
        I.append(real_part)
        Q.append(imag_part)
        
    return I, Q

# --- Main script ---
cwd = os.getcwd()
output_filename = os.path.join(cwd, "Samples/output.cs8")

# Capture the signal
print("--- Starting HackRF Capture ---")
freq = 98e6
sample_rate = 20e6
capture_sample(freq, sample_rate, output_filename)
print("--- Capture Complete ---")

# Load and process the captured data
print("\n--- Starting Data Processing ---")
I, Q = load_cs8(output_filename)

# Create a complex signal
signal = np.array(I) + 1j * np.array(Q)
print(f"Signal shape: {signal.shape}")

# Perform Welch's spectral analysis
print("Performing Welch's method for Power Spectral Density...")
f, Pxx = sig.welch(signal, fs=sample_rate, nperseg=4096, noverlap=2048, window='hamming', return_onesided=False)
f = np.fft.fftshift(f)
Pxx = np.fft.fftshift(Pxx)
print("Welch's analysis done.")

# Plot the results
plt.figure(figsize=(12, 6))
plt.semilogy(f, Pxx)
plt.title("Welch's Power Spectral Density Estimate")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Power/Frequency (dB/Hz)")
plt.grid(True)
plt.show()

print("--- Script Finished ---")