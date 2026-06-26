import SoapySDR
from SoapySDR import SOAPY_SDR_TX, SOAPY_SDR_CF32
import numpy as np

# 1. Generate the 100 kHz Tone (Baseband)
sample_rate = 2e6
t = np.arange(0, sample_rate) / sample_rate
iq_signal = np.exp(1j * 2 * np.pi * 100e3 * t).astype(np.complex64)

# 2. Setup Device & Parameters
# (REMINDER: USE A DUMMY LOAD. Transmitting on 108MHz without authorization is illegal)
sdr = SoapySDR.Device("driver=hackrf")
sdr.setSampleRate(SOAPY_SDR_TX, 0, sample_rate)
sdr.setFrequency(SOAPY_SDR_TX, 0, 108.1e6)
sdr.setGain(SOAPY_SDR_TX, 0, 10) # Keep gain low!

# 3. Setup and Activate TX Stream
tx_stream = sdr.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)
sdr.activateStream(tx_stream)

print("Transmitting...")

try:
    # 4. Transmit Loop
    while True:
        sdr.writeStream(tx_stream, [iq_signal], len(iq_signal))
except KeyboardInterrupt:
    pass
finally:
    # 5. Clean up
    sdr.deactivateStream(tx_stream)
    sdr.closeStream(tx_stream)
    print("Stopped.")