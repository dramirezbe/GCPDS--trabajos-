import pandas as pd
import matplotlib.pyplot as plt

df_C = pd.read_csv("psd_results.csv")

Pxx_C = df_C["Power_dBm"]
f_C = df_C["Frequency_Hz"]

# Use standard plot because data is already in dB (logarithmic)
plt.plot(f_C, Pxx_C)
plt.xlabel("Frequency [Hz]")
plt.ylabel("Power [dBm]")
plt.grid(True)
plt.show()