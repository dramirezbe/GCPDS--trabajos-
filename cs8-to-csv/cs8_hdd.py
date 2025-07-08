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

def recuperar_IQ_de_json_gz(filename):
    with gzip.open(filename, 'rt', encoding='utf-8') as f:
        data_loaded = json.load(f)
    I_recovered = np.array(data_loaded['I'])
    Q_recovered = np.array(data_loaded['Q'])
    return I_recovered, Q_recovered

hdd_path = r'D:\\' # HHD raw data 

folder_list = os.listdir(hdd_path) # List HDD folders

remove_char = 'DATA-'

simple_folder_list = [s.replace(remove_char, "") for s in folder_list]
simple_folder_list = [item for item in simple_folder_list if item not in ignore_folders]

print(simple_folder_list)






"""
final_path = r'D:\\json_gz'
os.makedirs(final_path, exist_ok=True)



for folder in folder_list:
    print("="*50)
    print(folder)
    print("="*50)
    if folder in ignore_folders:
        continue
    else:
        file_list = os.listdir(os.path.join(hdd_path, folder))
        for file in file_list:
            full_file_path = os.path.join(hdd_path, folder, file)
            print("Processing file: ", full_file_path)
            I, Q = cargar_cs8(full_file_path)
            print("IQ extracted")
            convertir_json_gz(I, Q, full_file_path)
            print("JSON gz file created")
            """
