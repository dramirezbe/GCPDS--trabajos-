import pyvisa
import numpy as np
import matplotlib.pyplot as plt

# Parámetros
N9000B_IP = '169.254.192.72'
VISA_TIMEOUT_MS = 5000  # 5 segundos

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

    inst.write(':FREQ:CENT 785e6') 
    inst.write(':FREQ:SPAN 70e6')       
    inst.write(':BAND:RES 680e3')        

    # Obtener los datos de la traza activa
    print("Solicitando datos de traza...")
    inst.write(':FORM ASC')  # Asegura formato ASCII (más simple para pruebas)
    trace_data = inst.query_ascii_values(':TRACe:DATA? TRACE1')
    print("Traza adquirida...")

    sort_trace = np.sort(np.array(trace_data))

    noise_floor = sort_trace[0] + 2.5  #Sum 3dB to minimum peak

    print("Noise floor: ", noise_floor)

    signal_array = []
    noise_array = []
    signal_indices = []
    noise_indices = []

    for i, power in enumerate(trace_data):
        if power >= noise_floor:
            signal_array.append(power)
            signal_indices.append(i) # Store index for plotting
        else:
            noise_array.append(power)
            noise_indices.append(i) # Store index for plotting

    signal_array = np.array(signal_array)
    noise_array = np.array(noise_array)

    # La fórmula es P_watts = 10^((P_dBm - 30) / 10)
    def dbm_to_watts(dbm_value):
        return 10**((dbm_value - 30) / 10)

    # 2. Convertir los arrays de señal y ruido de dBm a Watts
    signal_watts = [dbm_to_watts(p) for p in signal_array]
    noise_watts = [dbm_to_watts(p) for p in noise_array]

    # Convertir a numpy arrays para facilitar las sumas
    signal_watts = np.array(signal_watts)
    noise_watts = np.array(noise_watts)

    total_signal_power_watts = np.sum(signal_watts)
    total_noise_power_watts = np.sum(noise_watts)

        # 4. Calcular el SNR
    # Asegúrate de que la potencia de ruido no sea cero para evitar división por cero
    if total_noise_power_watts > 0:
        snr_linear = total_signal_power_watts / total_noise_power_watts
        snr_db = 10 * np.log10(snr_linear)

        print(f"\nSNR (Lineal): {snr_linear:.2f}")
        print(f"SNR (dB): {snr_db:.2f} dB")
    else:
        print("\nNo se puede calcular el SNR: La potencia total de ruido es cero o negativa.")
        print("Esto puede ocurrir si el 'noise_array' está vacío o si todos los puntos fueron clasificados como señal.")

    
    plt.plot(trace_data, label='Traza Completa')
    #plt.plot(signal_indices, signal_array, '--', color='blue', label='Señal')
    #plt.plot(noise_indices, noise_array, '--', color='green', label='Ruido')

    plt.axhline(y=noise_floor, color='r', linestyle='--', label=f'Umbral de Ruido ({noise_floor:.2f} dBm)')
    plt.title("Espectro Capturado: Señal vs. Ruido")
    plt.xlabel("Punto de Frecuencia")
    plt.ylabel("Amplitud (dBm)")
    plt.grid(True)
    plt.legend() # Show the labels
    plt.show()

except Exception as e:
    print(f"Error: {e}")

finally:
    if 'inst' in locals():
        inst.close()
        print("Conexión cerrada.")