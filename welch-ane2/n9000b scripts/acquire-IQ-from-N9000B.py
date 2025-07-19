import pyvisa as visa
import numpy as np
import time
import sys # For graceful exit
import matplotlib.pyplot as plt # Import for plotting
import time
from scipy.io import savemat


# --- Configuration Parameters ---
INST_IP = '169.254.192.72'
VISA_ADDRESS = f"TCPIP0::{INST_IP}::inst0::INSTR"

TIMEOUT_MS = 10000 # Timeout in milliseconds
CENTER_FREQ = 1e9 # 1 GHz
ANALYSIS_BANDWIDTH = 10e6 # 10 MHz (standard)
RECORD_LENGTH = 100000 # Number of IQ sample pairs (adjust as needed, max 5M/4M)
INPUT_ATTENUATION = 10 # dB

# --- Error Check Function ---
def check_instrument_errors(instrument):
    """Queries the instrument for errors and prints them."""
    errors = []
    while True:
        error_response = instrument.query("SYST:ERR?").strip()
        error_code, error_message = error_response.split(',', 1)
        if int(error_code) == 0:
            break
        errors.append(f"Error #: {error_code}, Description: {error_message}")
        print(f"Instrument Error: {error_response}")
    return errors

# --- Main Acquisition Script ---
if __name__ == "__main__":
    rm = None
    instrument = None
    try:
        # Establish VISA connection
        rm = visa.ResourceManager()
        instrument = rm.open_resource(VISA_ADDRESS)
        instrument.timeout = TIMEOUT_MS
        instrument.write("*CLS") # Clear instrument status [18, 19]
        print(f"Connected to: {instrument.query('*IDN?')}") # Query IDN [18]
        check_instrument_errors(instrument)

        # Instrument Setup for IQ Data Acquisition
        instrument.write("*RST") # Reset instrument to default settings [19]
        check_instrument_errors(instrument)

        instrument.write(":INSTrument:SELect BASIC") # Select IQ Analyzer mode [3]
        # Alternative: instrument.write(":INSTrument:NSELect 8")
        check_instrument_errors(instrument)

        instrument.write(f":FREQuency:CENTer {CENTER_FREQ}") # Set center frequency [3, 19]
        check_instrument_errors(instrument)

        instrument.write(f":FREQuency:SPAN {ANALYSIS_BANDWIDTH}") # Set span [3]
        check_instrument_errors(instrument)

        instrument.write(f":BANDwidth:DIGital:IF:BWIDth {ANALYSIS_BANDWIDTH}") # Set analysis bandwidth [3]
        check_instrument_errors(instrument)

        instrument.write(f":SWEep:DATA:POINts {RECORD_LENGTH}") # Set record length [3]
        check_instrument_errors(instrument)

        instrument.write(f":INPut:ATTenuation {INPUT_ATTENUATION} dB") # Set input attenuation [3, 26]
        # Optional: instrument.write(":ADJust:ATTenuation:CLIPPing:MINimum") # Auto-adjust attenuation [3, 26]
        check_instrument_errors(instrument)

        # Configure Binary Data Transfer
        instrument.write(":FORMat:DATA REAL,32") # Set data format to 32-bit floating point
        instrument.write(":FORMat:BORDer SWAP") # Set byte order to swapped (little-endian) for PC compatibility [20]
        check_instrument_errors(instrument)

        # Initiating IQ Data Capture
        instrument.write(":INITiate:CONTinuous OFF") # Stop continuous acquisition [18, 19]
        instrument.write(":ACQuire:FCAPture:IMMediate") # Initiate fast capture [3]
        instrument.query("*OPC?") # Wait for operation complete [18, 19]
        check_instrument_errors(instrument)

        # Read IQ Data
        print("Fetching IQ data...")
        iq_data_raw = instrument.query_binary_values("FETCh:SPECtrum? 0", datatype='f', is_big_endian=False) [3]
        print(f"Acquired {len(iq_data_raw)} raw data points.")

        # Separate I and Q Components (data is interleaved)
        inphase = iq_data_raw[0::2]
        quadrature = iq_data_raw[1::2]
        iq_complex = inphase + 1j * quadrature
        print(f"Separated into {len(iq_complex)} complex IQ sample pairs.")

        # Post-Acquisition Data Handling and Saving
        # Save to CSV
        data_to_save_csv = np.column_stack((iq_complex.real, iq_complex.imag))
        np.savetxt("iq_data.csv", data_to_save_csv, delimiter=",", header="I,Q", comments="")
        print("IQ data saved to iq_data.csv")

        # Save to.mat
        mdic = {"iq_data": iq_complex}
        savemat("iq_data.mat", mdic)
        print("IQ data saved to iq_data.mat")

        # Save to.dat (interleaved binary float dump)
        interleaved_iq_dat = np.empty((iq_complex.size * 2,), dtype=iq_complex.real.dtype)
        interleaved_iq_dat[0::2] = iq_complex.real
        interleaved_iq_dat[1::2] = iq_complex.imag
        interleaved_iq_dat.tofile("iq_data.dat")
        print("IQ data saved to iq_data.dat")

    except visa.errors.VisaIOError as e:
        print(f"VISA communication error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if instrument:
            instrument.close()
            print("Instrument connection closed.")
        if rm:
            rm.close()
            print("Resource Manager closed.")