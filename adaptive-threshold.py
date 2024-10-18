import os
import re
import numpy as np

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
        data = np.load(full_path)
        #print(f"Loading {file_name} (sample #{extract_sample_number(file_name)}), shape = {data.shape}")
        data_matrix[pos] = data

    print("Data matrix loading complete.")
    return data_matrix

class AdaptiveThreshold:
    def __init__(self, frecuencia, Pxx):
        self.frecuencia = frecuencia
        self.Pxx = Pxx

    @staticmethod
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
    
    def window_threshold(self, num_splits, percentage_threshold):
        N = len(self.Pxx)
        window_size = N // num_splits
        thresholds = []

        for i in range(num_splits):
            lim_inf = i * window_size
            lim_sup = min((i + 1) * window_size, N)
            
            window_Pxx = self.Pxx[lim_inf:lim_sup]
            threshold = self.basic_threshold(window_Pxx, percentage_threshold)
            
            # Guardar un solo umbral por ventana
            thresholds.append(threshold)

        return np.array(thresholds)