import numpy as np
import os
import json
import gzip

ignore_folders = ['System Volume Information', '$RECYCLE.BIN']

# Cargar el archivo como enteros con signo de 8 bits
def cargar_cs8(filename):
    data = np.fromfile(filename, dtype=np.int8)
    I = data[0::2]  # Muestras pares como parte real
    Q = data[1::2]  # Muestras impares como parte imaginaria
    
    return I, Q

def convertir_json_gz(I, Q, filename):
    with gzip.open(filename, 'wt', encoding='utf-8') as f:
        json.dump({
            'I': I.tolist(),
            'Q': Q.tolist()
        }, f)
    print(f"Compressed JSON file '{filename}' created successfully")

"""
def recuperar_IQ_de_json_gz(filename):
    with gzip.open(filename, 'rt', encoding='utf-8') as f:
        data_loaded = json.load(f)
    I_recovered = np.array(data_loaded['I'])
    Q_recovered = np.array(data_loaded['Q'])
    return I_recovered, Q_recovered"""

hdd_path = r'D:\\' # HHD raw data 

folder_list = os.listdir(hdd_path) # List HDD folders

remove_char = 'DATA-'
simple_folder_list = [s.replace(remove_char, "") for s in folder_list]
simple_folder_list = [item for item in simple_folder_list if item not in ignore_folders] # Folders to create

clean_folder_list = [item for item in folder_list if item not in ignore_folders] # Folders to process



final_folder_char = 'jsongz-'
"""
file_list = os.listdir(os.path.join(hdd_path, folder))
        for file in file_list:
            full_file_path = os.path.join(hdd_path, folder, file)
            print("Processing file: ", full_file_path)
            I, Q = cargar_cs8(full_file_path)
            print("IQ extracted")
            convertir_json_gz(I, Q, full_file_path)
            print("JSON gz file created")"""

folder_len = len(simple_folder_list)
folder_counter = 0

for idx, folder in enumerate(clean_folder_list):
    print("="*50)
    print(folder + " [" + str(folder_counter) + "/" + str(folder_len) + "]")
    print("="*50)

    current_folder_path = os.path.join(hdd_path, folder) #cs8
    current_file_list = os.listdir(current_folder_path)

    # Create final folder to store jsongz
    
    final_folder_name = final_folder_char + simple_folder_list[idx]
    final_folder_path = os.path.join(hdd_path, final_folder_name) #jsongz
    os.makedirs(final_folder_path, exist_ok=True)
    print(f"{final_folder_path} created")

    for current_file in current_file_list:
        current_file_path = os.path.join(current_folder_path, current_file) #cs8
        print("Processing file: ", current_file_path)
        I, Q = cargar_cs8(current_file_path)
        print("IQ extracted")

        final_file_path = os.path.join(final_folder_path, current_file) #jsongz
        convertir_json_gz(I, Q, final_file_path)
        print("JSON gz file created")


    folder_counter += 1


