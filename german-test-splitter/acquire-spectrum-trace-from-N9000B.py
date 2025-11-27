import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import time
import os

# Parámetros
N9000B_IP = '10.42.0.41'
VISA_TIMEOUT_MS = 5000  # 5 segundos
OUTPUT_DIR = 'spectrum_data'
# Lista de 5 frecuencias centrales (ejemplos en Hz)
CENTER_FREQUENCIES = [100.0e6, 105.7e6, 110.0e6, 115.5e6, 120.0e6]
WAIT_TIME_BETWEEN_COMMANDS = 0.5  # Tiempo de espera entre comandos de cambio de frecuencia

# Crear directorio de salida si no existe
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Directorio de salida creado: '{OUTPUT_DIR}'")

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
    
    # Asegura formato ASCII (más simple para pruebas y PyVISA)
    inst.write(':FORM ASC')

    print(f"Iniciando captura de {len(CENTER_FREQUENCIES)} trazas...")

    # Bucle para 5 capturas en diferentes frecuencias
    for i, freq in enumerate(CENTER_FREQUENCIES):
        # 1. Configurar la frecuencia central
        print(f"\n--- Captura {i+1}/{len(CENTER_FREQUENCIES)}: Configurando {freq/1e6:.1f} MHz ---")
        inst.write(f':SENSe:FREQuency:CENTer {freq}')
        time.sleep(WAIT_TIME_BETWEEN_COMMANDS) # Espera 0.5s entre comandos

        # 2. Obtener los datos de la traza activa (usualmente TRACE1)
        print("Solicitando datos de traza...")
        # Usamos :READ? en lugar de :TRACe:DATA? para asegurar una nueva adquisición si el modo es "single"
        # y forzar un barrido. Si el modo es "cont" ambos funcionan. Mantenemos el comando original.
        trace_data = inst.query_ascii_values(':TRACe:DATA? TRACE1')

        print(f"Se recibieron {len(trace_data)} puntos de traza.")

        # Nombres de archivos
        base_name = f'spectrum_trace_{i+1}_{int(freq/1e6)}MHz'
        csv_file = os.path.join(OUTPUT_DIR, f'{base_name}.csv')
        png_file = os.path.join(OUTPUT_DIR, f'{base_name}.png')

        # 3. Guardar en CSV
        np.savetxt(csv_file, trace_data, delimiter=',', header='Amplitude (dBm)', comments='')
        print(f"Traza guardada en '{csv_file}'")

        # 4. Graficar y guardar como PNG
        plt.figure(figsize=(10, 6)) # Crea una nueva figura para cada plot
        plt.plot(trace_data)
        plt.title(f"Espectro capturado - Frecuencia Central: {freq/1e6:.1f} MHz")
        # Nota: Sin configurar el rango de frecuencia, el eje X es solo el índice del punto
        plt.xlabel("Punto de frecuencia") 
        plt.ylabel("Amplitud (dBm)")
        plt.grid(True)
        
        plt.savefig(png_file)
        print(f"Gráfico guardado en '{png_file}'")
        plt.close() # Cierra la figura para liberar memoria
        
    print("\nProceso de captura finalizado.")

    # Mostrar la última figura generada (Opcional: puedes comentar esto si solo quieres guardarlas)
    # Reabrir y mostrar la última figura para que el usuario vea el resultado
    print(f"Mostrando el último gráfico generado: {png_file}")
    img = plt.imread(png_file)
    plt.imshow(img)
    plt.axis('off')
    plt.show()


except Exception as e:
    print(f"\nError: {e}")
    # Si el analizador no proporciona el número de puntos de frecuencia (SPAN/RBW/etc.), 
    # el eje X del gráfico seguirá siendo el índice.
    print("\nVERIFICAR: Asegúrate de que el analizador de espectro esté encendido, accesible en la red, y que PyVISA esté configurado correctamente para la comunicación TCPIP.")

finally:
    if 'inst' in locals() and inst.resource_info.open_count > 0:
        inst.close()
        print("Conexión cerrada.")