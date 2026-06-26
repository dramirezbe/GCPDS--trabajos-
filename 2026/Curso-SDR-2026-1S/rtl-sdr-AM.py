import sys
import types
import numpy as np
import scipy.signal as signal
import scipy.io.wavfile as wav

# --- PATCH START: Fix for pyrtlsdr on Python 3.13 ---
# We inject a dummy 'pkg_resources' so the library doesn't crash on import.
# This bypasses the broken version check.
if 'pkg_resources' not in sys.modules:
    dummy_pkg = types.ModuleType('pkg_resources')
    # Mock the 'require' function to return a dummy object with a 'version' attribute
    class DummyDist:
        version = "0.3.0"
    
    def dummy_require(name):
        return [DummyDist()]
    
    dummy_pkg.require = dummy_require
    sys.modules['pkg_resources'] = dummy_pkg
# --- PATCH END ---

# Now we can safely import
from rtlsdr import RtlSdr

# Paste your class here (or import it if in a separate file)
class AMDemodulator:
    def __init__(self, fs_rf, fs_audio):
        self.fs_rf = fs_rf
        self.fs_audio = fs_audio

    def demodulate(self, iq_data):
        # 1. Envelope Detection
        envelope = np.abs(iq_data)
        # 2. DC Offset Removal
        envelope_ac = envelope - np.mean(envelope)
        # 3. Decimation
        num_samples = int(len(envelope_ac) * self.fs_audio / self.fs_rf)
        audio_resampled = signal.resample(envelope_ac, num_samples)
        # 4. LPF
        nyquist = 0.5 * self.fs_audio
        sos = signal.butter(4, 5000 / nyquist, btype='low', output='sos')
        audio_filtered = signal.sosfilt(sos, audio_resampled)
        # 5. Normalize
        max_val = np.max(np.abs(audio_filtered))
        if max_val > 0:
            return audio_filtered / max_val
        return audio_filtered

# --- Main Execution ---
if __name__ == "__main__":
    # Configuration
    FS_RF = 1.024e6       # 1.024 MSps (Standard RTL-SDR rate)
    FS_AUDIO = 48000      # 48 kHz
    FREQ = 105.7e6         
    DURATION = 5          # Seconds to capture

    # 1. Setup SDR
    sdr = RtlSdr()
    sdr.sample_rate = FS_RF
    sdr.center_freq = FREQ
    sdr.gain = 'auto'
    
    # Note: For AM Broadcast (530-1700kHz), you need an RTL-SDR v3
    # and must uncomment the line below to use Direct Sampling (Q-branch).
    # sdr.set_direct_sampling(2) 

    print(f"Streaming {DURATION}s of raw I/Q from {FREQ/1e6} MHz...")

    # 2. Capture Raw I/Q (Reading in one block for simplicity)
    num_samples = int(FS_RF * DURATION)
    samples = sdr.read_samples(num_samples)
    sdr.close()

    # 3. Demodulate
    print("Demodulating...")
    demod = AMDemodulator(FS_RF, FS_AUDIO)
    audio = demod.demodulate(samples)

    # 4. Save to WAV
    # Scale float (-1.0 to 1.0) to int16 for WAV format
    audio_int16 = (audio * 32767).astype(np.int16)
    wav.write("output_am.wav", FS_AUDIO, audio_int16)

    print("Done. Audio saved to 'output_am.wav'")