import pandas as pd
import matplotlib.pyplot as plt

# Leer el archivo CSV
data = pd.read_csv("fft_output.csv")

# Graficar la FFT
plt.figure(figsize=(10, 5))
plt.plot(data["frecuencia"], data["magnitud"])
plt.title("Espectro de Frecuencia (FFT)")
plt.xlabel("Frecuencia (Hz)")
plt.ylabel("Magnitud")
plt.grid(True)
plt.show()