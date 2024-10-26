import numpy as np

try:
    data = np.loadtxt("IQ_data.csv", delimiter=",")
    I = data[:, 0]  # Primera columna
    Q = data[:, 1]  # Segunda columna
    print("Datos cargados correctamente.")
    print("I:", I[:10])  # Muestra las primeras 10 muestras
    print("Q:", Q[:10])
except Exception as e:
    print("Error al cargar los datos:", e)
