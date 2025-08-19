import uhd
import numpy as np
import time

def transmit_white_noise(center_freq, sample_rate, tx_gain, duration_seconds=60):
    """
    Transmite ruido blanco con una USRP.

    Args:
        center_freq (float): Frecuencia central de transmisión en Hz.
        sample_rate (float): Tasa de muestreo en Hz.
        tx_gain (float): Ganancia de transmisión en dB.
        duration_seconds (float): Duración de la transmisión en segundos.
                                  (0 para transmisión continua hasta interrupción manual)
    """
    print(f"Intentando inicializar USRP en {center_freq/1e6} MHz con {sample_rate/1e6} MS/s y {tx_gain} dB TX gain...")

    # Crear un transmisor USRP
    try:
        usrp = uhd.usrp.MultiUSRP("")
    except Exception as e:
        print(f"Error al inicializar USRP: {e}")
        print("Asegúrate de que la USRP esté conectada y los drivers instalados correctamente.")
        return


    usrp.set_tx_rate(sample_rate, 0)
    usrp.set_tx_gain(tx_gain, 0)

    # Configurar el stream para transmisión
    st_args = uhd.usrp.StreamArgs("fc32", "sc16") # Formato de complejo flotante 32-bit, muestra corta 16-bit
    st_args.channels = [0]
    tx_streamer = usrp.get_tx_stream(st_args)

    # Preparar metadatos de transmisión
    tx_metadata = uhd.types.TXMetadata()
    tx_metadata.start_of_burst = True
    tx_metadata.end_of_burst = False
    tx_metadata.has_time_spec = False # No especificamos tiempo absoluto de inicio, se envía inmediatamente

    # Tamaño del buffer de transmisión (número de muestras por bloque)
    # Un tamaño más grande puede ser más eficiente, pero consume más memoria
    num_samps_per_buff = tx_streamer.get_max_num_samps()
    print(f"Tamaño máximo de muestras por buffer: {num_samps_per_buff}")

    # Generar un buffer de ruido blanco complejo
    # np.random.randn() genera muestras de una distribución normal estándar (media 0, varianza 1)
    # Se genera para las partes real e imaginaria
    noise_buffer = (np.random.randn(num_samps_per_buff) + 1j * np.random.randn(num_samps_per_buff)).astype(np.complex64)

    # Normalizar el ruido para asegurar que no haya clipping excesivo
    # Un buen punto de partida es normalizar por la raíz de 2 (para ruido complejo I/Q)
    noise_buffer /= np.sqrt(2.0)
    
    print("Iniciando transmisión de ruido blanco... Presiona Ctrl+C para detener.")

    start_time = time.time()
    try:
        while True:
            # Enviar el buffer de ruido
            # Aquí 'uhd.types.TimeSpec(0.1)' puede usarse para un retraso, pero lo ignoramos
            # ya que tx_metadata.has_time_spec = False
            tx_streamer.send(noise_buffer, tx_metadata)
            
            # Si se especificó una duración, verificar si ha transcurrido
            if duration_seconds > 0 and (time.time() - start_time) >= duration_seconds:
                print(f"Transmisión completada después de {duration_seconds} segundos.")
                break
            
            # Pequeña pausa para no sobrecargar la CPU, aunque la transmisión es continua
            time.sleep(0.01) 

    except KeyboardInterrupt:
        print("\nTransmisión detenida por el usuario.")
    except Exception as e:
        print(f"Un error ocurrió durante la transmisión: {e}")
    finally:
        # Asegurarse de enviar el final de la ráfaga
        tx_metadata.end_of_burst = True
        tx_streamer.send(np.zeros(num_samps_per_buff, dtype=np.complex64), tx_metadata)
        print("Fin de ráfaga enviado.")
        del tx_streamer
        del usrp # Esto ayuda a liberar los recursos de la USRP

# --- Configuración de Parámetros ---
if __name__ == "__main__":
    # Asegúrate de que estos valores sean apropiados para tu USRP y el entorno regulatorio.
    # ¡Siempre verifica las regulaciones de RF locales antes de transmitir!
    
    CENTER_FREQUENCY = 98e6  # Ejemplo: 915 MHz (banda ISM en algunas regiones)
    SAMPLE_RATE = 5e6         # Ejemplo: 5 MSps (5 millones de muestras por segundo)
    TX_GAIN = 10              # Ejemplo: 10 dB (ajusta según sea necesario, empieza bajo)
    TRANSMISSION_DURATION = 0 # 0 para continuo, o un número en segundos para una duración fija

    transmit_white_noise(CENTER_FREQUENCY, SAMPLE_RATE, TX_GAIN, TRANSMISSION_DURATION)