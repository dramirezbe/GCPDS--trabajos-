import json
import gzip
import numpy as np
import os


def parse_psd_json_gz(filename):
    with gzip.open(filename, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    f = np.array(data['f'])
    Pxx = np.array(data['Pxx'])
    return f, Pxx


folder_path = "/home/javastral/GIT/GCPDS--trabajos-/cs8-to-jsongz/psd-108-128-aislated"
file_list = os.listdir(folder_path)

data_num = len(file_list)
file_counter = 0

x_len = 4096
y_len = data_num

Pxx_aislated = np.zeros((x_len, y_len))

freq_left = None
freq_right = None
freq_step = None


for file in file_list:
    file_path = os.path.join(folder_path, file)
    print(f"\nProcessing file: {file_path}")

    if freq_left is None or freq_right is None or freq_step is None:  #Save freq first time
        f, Pxx = parse_psd_json_gz(file_path)
        freq_left = np.min(f)
        freq_right = np.max(f)
        freq_step = f[1] - f[0]

    else:
        _, Pxx = parse_psd_json_gz(file_path)

    Pxx_aislated[:, file_counter] = Pxx
    file_counter += 1

f_construct = np.arange(freq_left, freq_right + freq_step, freq_step)

print(f_construct.shape)
print(Pxx_aislated.shape)