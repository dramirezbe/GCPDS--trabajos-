import pyvisa
import time

# --- Configuration ---
N9000B_IP = '169.254.192.72'
VISA_TIMEOUT_MS = 5000  # 5 seconds timeout for commands

# --- Initialize Resource Manager ---
# Use '@py' to explicitly use the PyVISA-py backend.
# If you have Keysight's VISA library installed, you might just use rm = pyvisa.ResourceManager()
# but for Linux, @py is generally more straightforward.
try:
    rm = pyvisa.ResourceManager('@py')
    print("PyVISA Resource Manager initialized successfully.")
except Exception as e:
    print(f"Error initializing PyVISA Resource Manager: {e}")
    print("Ensure 'pyvisa' and 'pyvisa-py' are installed.")
    exit()

# --- Connect to the Instrument ---
# For Keysight LXI/VXI-11, the common resource string is TCPIP::IP_ADDRESS::INSTR
# If this doesn't work, try TCPIP::IP_ADDRESS::5025::SOCKET for raw socket.
resource_string = f'TCPIP::{N9000B_IP}::INSTR'
# resource_string = f'TCPIP::{N9000B_IP}::5025::SOCKET' # Uncomment this line if the INSTR method fails

print(f"\nAttempting to connect to: {resource_string}")
inst = None
try:
    inst = rm.open_resource(resource_string)
    inst.timeout = VISA_TIMEOUT_MS # Set the timeout for the connection
    print(f"Successfully connected to {N9000B_IP}")

    # --- Query Instrument Identification ---
    idn = inst.query('*IDN?')
    print(f"Instrument ID: {idn.strip()}") # .strip() removes whitespace/newline characters

    # --- Send SCPI Commands ---
    print("\nSending SCPI commands...")

    # *CLS: Clear Status Command - Clears the instrument's status registers. Good practice before a sequence.
    inst.write('*CLS')
    print("Sent *CLS")

    # *RST: Reset Command - Resets the instrument to its factory default state.
    # Be careful with this, as it will clear all current settings on the analyzer.
    # inst.write('*RST')
    # print("Sent *RST")
    # time.sleep(1) # Give the instrument a moment to reset

    # Set Frequency Center and Span
    inst.write(':SENSe:FREQuency:CENTer 1GHz') # Set center frequency to 1 GHz
    print("Set center frequency to 1 GHz")
    inst.write(':SENSe:FREQuency:SPAN 100MHz') # Set span to 100 MHz
    print("Set span to 100 MHz")

    # Query current Center Frequency
    current_center_freq = inst.query(':SENSe:FREQuency:CENTer?')
    print(f"Current Center Frequency: {float(current_center_freq)} Hz")

    # Set Reference Level
    inst.write(':DISPlay:WINDow:TRACe:Y:RLEVel 0DBM') # Set reference level to 0 dBm
    print("Set reference level to 0 dBm")
    current_ref_level = inst.query(':DISPlay:WINDow:TRACe:Y:RLEVel?')
    print(f"Current Reference Level: {float(current_ref_level)} dBm")

    # Take a single sweep and wait for it to complete
    # INITiate:CONTinuous OFF sets single sweep mode
    inst.write(':INITiate:CONTinuous OFF')
    # INITiate:IMMediate triggers a single sweep
    inst.write(':INITiate:IMMediate')
    # *OPC? queries for operation complete (returns 1 when previous operations are done)
    inst.query('*OPC?') # This will block until the sweep is complete
    print("Single sweep completed.")

    # Get trace data (example: TRACE1 data)
    # The format of trace data (ASCII, REAL, etc.) and the command might vary.
    # Refer to your N9000B programming guide for the exact trace data query.
    # Example: Fetches trace data as ASCII values
    # trace_data_str = inst.query(':TRACe:DATA? TRACE1')
    # print(f"Raw Trace Data (first 100 chars): {trace_data_str[:100]}...")

    # If you expect binary data (faster for large traces), you'd use query_binary_values:
    # Example for binary data (assuming IEEE 488.2 format with a definite length header)
    # trace_data_values = inst.query_binary_values(':TRACe:DATA? TRACE1', datatype='f', is_big_endian=False)
    # print(f"Trace Data points (first 10): {trace_data_values[:10]}")
    # print(f"Number of trace points: {len(trace_data_values)}")

    # Trigger a screenshot
    # Check your N9000B manual for screenshot commands.
    # Example for saving to internal drive (path might vary)
    # inst.write(':HCOPy:SDUMp:DATA? ALL') # Query screenshot data
    # raw_image_data = inst.read_raw()
    # with open('screenshot.png', 'wb') as f:
    #     f.write(raw_image_data)
    # print("Screenshot saved as screenshot.png")


    print("\nDone sending commands.")

except pyvisa.errors.VisaIOError as e:
    print(f"VISA I/O Error: {e}")
    print("Possible causes:")
    print(f" - Is the N9000B CXA at IP {N9000B_IP} and powered on?")
    print(" - Is the Ethernet cable securely connected?")
    print(" - Double-check the IP configuration on your Arch Linux machine.")
    print(" - Is the correct PyVISA resource string being used (INSTR vs SOCKET, correct port)?")
    print(" - Has the instrument entered an error state?")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

finally:
    if inst:
        inst.close()
        print("Connection closed.")