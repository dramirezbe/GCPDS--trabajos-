import SoapySDR
# Instanciar mediante string con el driver y el serial explícito
sdr = SoapySDR.Device("driver=uhd,serial=32CABF3")

sdr.setMasterClockRate(61.44e6)

# Configuración RX
sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, 61.44e6)
sdr.setBandwidth(SoapySDR.SOAPY_SDR_RX, 0, 56e6)
sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, 2.4e9)
sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, 76.0)

# Streams
rx = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CF32)

sdr.activateStream(rx)

try:
    while True: pass
except KeyboardInterrupt:
    sdr.deactivateStream(rx)