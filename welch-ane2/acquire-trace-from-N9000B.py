import pyvisa
import numpy as np
import matplotlib.pyplot as plt

# Parámetros
N9000B_IP = '169.254.192.72'
VISA_TIMEOUT_MS = 5000  # 5 segundos
TRACE_CSV_FILE = 'spectrum_trace.csv'

try:
    # Iniciar PyVISA
    rm = pyvisa.ResourceManager('@py')
    inst = rm.open_resource(f'TCPIP::{N9000B_IP}::INSTR')
    inst.timeout = VISA_TIMEOUT_MS

    # Consultar identificación
    print("Conectando al analizador...")
    idn = inst.query('*IDN?')
    print(f"Instrumento conectado: {idn.strip()}")

    # Limpiar errores anteriores
    inst.write('*CLS')

    # Obtener los datos de la traza activa (usualmente TRACE1)
    print("Solicitando datos de traza...")
    inst.write(':FORM ASC')  # Asegura formato ASCII (más simple para pruebas)
    trace_data = inst.query_ascii_values(':TRACe:DATA? TRACE1')

    print(f"Se recibieron {len(trace_data)} puntos de traza.")

    # Guardar en CSV
    np.savetxt(TRACE_CSV_FILE, trace_data, delimiter=',', header='Amplitude (dBm)', comments='')
    print(f"Traza guardada en '{TRACE_CSV_FILE}'")

    # Graficar (opcional)
    plt.plot(trace_data)
    plt.title("Espectro capturado")
    plt.xlabel("Punto de frecuencia")
    plt.ylabel("Amplitud (dBm)")
    plt.grid(True)
    plt.show()

except Exception as e:
    print(f"Error: {e}")

finally:
    if 'inst' in locals():
        inst.close()
        print("Conexión cerrada.")
