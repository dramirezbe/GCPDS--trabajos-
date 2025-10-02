import pyhackrf2
import pyvisa
import numpy as np
import sys
import threading
from queue import Queue

# Params
N9000B_IP = '169.254.192.72'
VISA_TIMEOUT_MS = 5000
TRACE_CSV_FILE = 'n9000bTrace_and_HackrfRx.csv'


if len(sys.argv) < 3:
    print("Usage: python n9000b-HackRF-Samples.py <center_user_freq_MHz> <samples_MHz>")
    print("Example: python3 n9000b-HackRF-Samples.py 98 20")
    sys.exit(1) # Exit if arguments are not provided

try:
    # Get user params
    USER_CENTER_FREQ = float(sys.argv[1])
    USER_SAMPLE_RATE = float(sys.argv[2])
except ValueError:
    print("Error: center_user_freq_MHz must be a number and Samples must be an integer.")
    sys.exit(1) # Exit if arguments are not valid

CENTER_FREQ_MHZ = USER_CENTER_FREQ * 1e6
SAMPLE_RATE_MHZ = USER_SAMPLE_RATE * 1e6

def acquire_trace_n9000b(inst):
    print("Init n9000b...")
    trace_data = inst.query_ascii_values(':TRACe:DATA? TRACE1')
    trace_data =np.array(trace_data)
    print("Done n9000b...")
    return trace_data

def acquire_rx_hackrf(hackrf, sample_rate):
    print("Init HackRF...")
    # It's good practice to start RX explicitly before reading samples if not continuous
    hackrf.start_rx() 
    rx_data = hackrf.read_samples(sample_rate) # Assuming sample_rate is the number of samples to read
    hackrf.stop_rx() # Stop RX after acquiring
    rx_data = np.array(rx_data)
    print("Done HackRF...")
    return rx_data

# Helper functions for threading to pass results via Queue
def _thread_acquire_n9000b(inst, q):
    try:
        data = acquire_trace_n9000b(inst)
        q.put(('n9000b', data))
    except Exception as e:
        q.put(('n9000b_error', e))

def _thread_acquire_hackrf(hackrf, sample_rate, q):
    try:
        data = acquire_rx_hackrf(hackrf, sample_rate)
        q.put(('hackrf', data))
    except Exception as e:
        q.put(('hackrf_error', e))


def main():
    rm = None
    inst = None
    hackrf = None
    n9000b_connected = False
    hackrf_connected = False

    try:
        # Init PyVISA
        rm = pyvisa.ResourceManager('@py')
        inst = rm.open_resource(f'TCPIP::{N9000B_IP}::INSTR')
        inst.timeout = VISA_TIMEOUT_MS

        # Consult id n9000b
        print("Connecting n9000b...")
        idn = inst.query('*IDN?')
        print(f"Instrument connected: {idn.strip()}")

        inst.write(':FORM ASC')
        print("n9000b Configured...")
        # Clear last error logs
        inst.write('*CLS')
        n9000b_connected = True
    
    except Exception as e:
        print(f"Error Configuring n9000b: {e}")

    try:
        hackrf = pyhackrf2.HackRF()
        hackrf.sample_rate = SAMPLE_RATE_MHZ
        hackrf.center_freq = CENTER_FREQ_MHZ
        print("HackRF Configured...")
        hackrf_connected = True

    except Exception as e:
        print(f"Error configuring HackRF: {e}")
        if hackrf: # Ensure we try to close HackRF even if initial config fails
            try:
                hackrf.close()
            except Exception as close_e:
                print(f"Error closing HackRF during initial configuration error: {close_e}")

    """---------------REQUEST RX FROM BOTH AT THE SAME TIME---------------"""
    print("---------------------------Init Acquisition---------------------------")
    
    if n9000b_connected and hackrf_connected:
        result_queue = Queue()

        # Create and start threads
        n9000b_thread = threading.Thread(target=_thread_acquire_n9000b, args=(inst, result_queue))
        hackrf_thread = threading.Thread(target=_thread_acquire_hackrf, args=(hackrf, SAMPLE_RATE_MHZ, result_queue)) # Pass SAMPLE_RATE_MHZ as number of samples

        n9000b_thread.start()
        hackrf_thread.start()

        # Wait for both threads to complete
        n9000b_thread.join()
        hackrf_thread.join()

        # Retrieve results
        n9000b_trace = None
        hackrf_rx_data = None
        acquisition_errors = []

        while not result_queue.empty():
            source, data = result_queue.get()
            if source == 'n9000b':
                n9000b_trace = data
            elif source == 'hackrf':
                hackrf_rx_data = data
            else: # Handle errors put into the queue
                acquisition_errors.append(f"Error from {source.replace('_error', '')}: {data}")
        
        if acquisition_errors:
            for error_msg in acquisition_errors:
                print(error_msg)

        if n9000b_trace is not None and hackrf_rx_data is not None:
            print("\n¡Ambas muestras adquiridas con hilos!")
            print(f"Forma de la traza del N9000B: {n9000b_trace.shape}")
            print(f"Forma de las muestras del HackRF: {hackrf_rx_data.shape}")

            # Prepare data for CSV saving
            # Convert complex HackRF data to magnitude for simpler CSV storage
            # Or you could save I and Q as separate columns (hackrf_rx_data.real, hackrf_rx_data.imag)
            hackrf_magnitude = np.abs(hackrf_rx_data)
            
            # Ensure consistent length for CSV columns by padding the shorter array
            max_len = max(len(n9000b_trace), len(hackrf_magnitude))
            
            combined_data = np.full((max_len, 2), np.nan) # Initialize with NaN for empty spots
            
            combined_data[:len(n9000b_trace), 0] = n9000b_trace
            combined_data[:len(hackrf_magnitude), 1] = hackrf_magnitude

            try:
                np.savetxt(TRACE_CSV_FILE, combined_data, delimiter=',', header='N9000B_Trace_dBm,HackRF_RX_Magnitude', comments='')
                print(f"Datos guardados en {TRACE_CSV_FILE}")
            except Exception as e:
                print(f"Error al guardar datos en CSV: {e}")
        else:
            print("No se pudieron adquirir ambas muestras correctamente.")
    else:
        print("No se puede iniciar la adquisición concurrente sin ambos dispositivos configurados.")

    # Cleanup: close connections
    if hackrf_connected:
        try:
            hackrf.close()
            print("HackRF cerrado.")
        except Exception as e:
            print(f"Error al cerrar HackRF: {e}")
    if n9000b_connected:
        try:
            inst.close()
            rm.close()
            print("N9000B y Resource Manager cerrados.")
        except Exception as e:
            print(f"Error al cerrar N9000B: {e}")

if __name__ == "__main__":
    main()