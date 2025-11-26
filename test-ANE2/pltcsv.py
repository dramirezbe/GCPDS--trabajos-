import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('sensor_captures/2025-11-25_19-25-16_88000000_108000000.csv')
freq = df['Frequency_Hz']
psd = df['Power_dB']

plt.plot(freq, psd)
plt.show()