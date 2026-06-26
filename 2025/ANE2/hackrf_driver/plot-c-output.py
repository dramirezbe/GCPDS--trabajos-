import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

c_output = pd.read_csv("/home/javastral/GIT/GCPDS--trabajos-/ANE2/hackrf_driver/Samples/output.csv")

f_c = np.array(c_output['Frequency_Hz'].values)
Pxx_c = np.array(c_output['PSD'].values)

plt.figure(figsize=(20, 10))
plt.semilogy(f_c, Pxx_c)
plt.xlabel('Frequency (Hz)')
plt.ylabel('PSD (dB/Hz)')
plt.title('Power Spectral Density (C Output)')
plt.grid()
plt.show()