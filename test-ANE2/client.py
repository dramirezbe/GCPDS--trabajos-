import socketio
import time
import numpy as np

# Initialize Client
sio = socketio.Client()

@sio.event
def connect():
    print("I am the Sensor. I have connected to the Server.")

@sio.event
def configure_sensor(config):
    """
    Listens for the 'configure_sensor' event from the server.
    """
    print(f"\n[Command Received] Configuring with: {config}")
    
    # --- SIMULATE DATA ACQUISITION ---
    print("Simulating hardware acquisition...")
    time.sleep(1) # Fake processing time
    
    # Generate fake Power Spectral Density data
    num_points = 1024
    pxx_data = np.random.uniform(-120, -40, num_points).tolist() # Fake dBm values
    
    # Construct the JSON payload
    payload = {
        "timestamp": time.time(),
        "start_freq_hz": config['start_freq_hz'],
        "end_freq_hz": config['end_freq_hz'],
        "Pxx": pxx_data
    }
    
    print("[Transmitting] Sending JSON payload to server...")
    sio.emit('sensor_reading', payload)

@sio.event
def server_ack(data):
    """
    Wait for server confirmation before closing.
    """
    print(f"[Server Response] {data}")
    print("Cycle complete. Disconnecting.")
    sio.disconnect()

@sio.event
def disconnect():
    print("Disconnected from server.")

if __name__ == '__main__':
    try:
        # Connect to localhost server
        sio.connect('http://localhost:5000')
        sio.wait() # Wait for events until disconnect is called
    except Exception as e:
        print(f"Connection failed: {e}")