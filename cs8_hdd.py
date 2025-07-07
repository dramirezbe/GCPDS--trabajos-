import numpy as np
from scipy import signal as sig
import matplotlib.pyplot as plt
import os

# Cargar el archivo como enteros con signo de 8 bits
def cargar_cs8(filename):
    data = np.fromfile(filename, dtype=np.int8)
    I = data[0::2]  # Muestras pares como parte real
    Q = data[1::2]  # Muestras impares como parte imaginaria
    señal_compleja = I + 1j * Q
    return señal_compleja, I, Q

# Define the HDD path. Using a raw string (r'...') or forward slashes is recommended for paths.
# Or, ensure backslashes are escaped (e.g., 'D:\\').
hdd_path = r'D:\\' # Using a raw string for Windows paths is good practice

# Construct the full folder path
folder_path = os.path.join(hdd_path, 'DATA-580-600-USRP')

# Check if the folder exists before trying to list its contents
if os.path.exists(folder_path):
    print("Listing Dir in: ", folder_path)
    files_name = os.listdir(folder_path)

    print(f"Files found in '{folder_path}':")
    for file_name in files_name:
        print(file_name)
else:
    print(f"Error: The folder '{folder_path}' does not exist.")


full_file_path = os.path.join(folder_path, files_name[0])

print("\nStarting signal processing Full file path = ", full_file_path)

signal, I, Q = cargar_cs8(full_file_path)

# Estimar la PSD usando la función de Welch de SciPy
f_scipy, P_welch_scipy = sig.welch(signal, 20000000, nperseg=1024, noverlap=0, window='hamming', return_onesided=False)

plt.plot(f_scipy, P_welch_scipy)
plt.show()