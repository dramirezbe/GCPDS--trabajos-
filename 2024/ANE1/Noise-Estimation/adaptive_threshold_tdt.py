import os
import re
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as sig

def extract_sample_number(file_name):
    match = re.search(r'sample #(\d+)', file_name)
    if match:
        return int(match.group(1))
    # Return a large number to push files without sample numbers to the end
    return float('inf')

def data_SDR(path_folder):
    # List all files in the folder
    file_list = os.listdir(path_folder)

    # Sort files by sample number
    sorted_file_list = sorted(file_list, key=extract_sample_number)

    # Initialize data matrix based on the sorted file list
    exploration_path = os.path.join(path_folder, sorted_file_list[0])
    data_exploration = np.load(exploration_path)
    
    # Check if the data is complex
    is_complex = np.iscomplexobj(data_exploration)
    
    # Initialize the data matrix with the correct dtype
    data_matrix = np.zeros((len(sorted_file_list), data_exploration.shape[0]), dtype=complex if is_complex else float)

    # Load all files into data_matrix
    for pos, file_name in enumerate(sorted_file_list):
        full_path = os.path.join(path_folder, file_name)
        print(f'file {full_path} Done.')
        data = np.load(full_path)
        #print(f"Loading {file_name} (sample #{extract_sample_number(file_name)}), shape = {data.shape}")
        data_matrix[pos] = data

    print("Data matrix loading complete.")
    return data_matrix

def basic_threshold(Pxx_window, percentage_threshold):
        threshold = np.mean(Pxx_window)
        
        while True:
            points_below_threshold = np.sum(Pxx_window < threshold)
            total_points = len(Pxx_window)

            percentage_below = points_below_threshold / total_points

            if percentage_below < percentage_threshold:
                break

            threshold *= 0.95
        return threshold

def cut_zero_harmonic(cutoff, freq, Pxx):
    bw_smooth = (freq >= -cutoff) & (freq <= cutoff)
    index = np.abs(freq - cutoff).argmin()
    Pxx_value = Pxx[index]
    Pxx[bw_smooth] = Pxx_value

    return Pxx

def estimate_noise_by_windows_adaptive(freq, Pxx, num_splits=100, percentage_threshold=0.1):

    if len(freq) != len(Pxx):
        raise ValueError("freq y Pxx deben tener el mismo tamaño")
    
    # Dividir el espectro en ventanas
    split_size = len(Pxx) // num_splits
    thresholds = np.zeros(len(Pxx))
    
    # Calcular el umbral adaptativo para cada ventana
    for i in range(num_splits):
        start_idx = i * split_size
        if i == num_splits - 1:
            end_idx = len(Pxx)  # Último segmento toma lo que queda
        else:
            end_idx = (i + 1) * split_size
        
        Pxx_window = Pxx[start_idx:end_idx]
        
        # Calcular el umbral adaptativo para esta ventana
        adaptive_threshold = basic_threshold(Pxx_window, percentage_threshold)
        
        # Asignar el umbral calculado a la porción correspondiente del vector threshold
        thresholds[start_idx:end_idx] = adaptive_threshold
    
    return freq, thresholds



folder_path = r'C:\Samples-tdt-Hack-RF'
tdt_matrix = data_SDR(folder_path)
M, N = tdt_matrix.shape
print(f'Matrix shape= ({M},{N})')

cutoff = 1e5
fs_bw = 20e6

# Crear la figura y los subplots, con una distribución apropiada de filas y columnas
fig, axes = plt.subplots(M, 1, figsize=(18, 6 * M))

# Iterar sobre cada fila de tdt_matrix
for i in range(M):
    # Calcular el PSD para la fila i
    freq, Pxx = sig.welch(tdt_matrix[i], fs=fs_bw, nperseg=1024, return_onesided=False)
    
    # Aplicar el filtro de corte para la armónica cero
    Pxx = cut_zero_harmonic(cutoff, freq, Pxx)
    
    # Estimar el umbral adaptativo por ventanas
    freq, threshold = estimate_noise_by_windows_adaptive(freq, Pxx, num_splits=3, percentage_threshold=0.2)
    
    # Ordenar las frecuencias y los valores de Pxx y threshold
    sorted_indices = np.argsort(freq)
    freq = freq[sorted_indices]
    Pxx = Pxx[sorted_indices]
    threshold = threshold[sorted_indices]

    # Graficar en el subplot correspondiente
    axes[i].semilogy(freq, Pxx, label='PSD')
    axes[i].plot(freq, threshold, linestyle='--', label='Adaptive Threshold')
    
    # Añadir título y leyenda a cada subplot
    axes[i].set_title(f'PSD and Threshold for Sample {i}')
    axes[i].legend()

# Ajustar el espaciado entre subplots
plt.tight_layout()
plt.show()