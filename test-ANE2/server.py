import os
import csv
import json
import datetime
import numpy as np
from flask import Flask, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Configuration ---
sensor_config = {
    "start_freq_hz": 88000000,
    "end_freq_hz": 108000000,
    "resolution_hz": 10000,
    "antenna_port": 1,
    "window": "hamming",
    "overlap": 0.5,
    "sample_rate_hz": 20000000,
    "lna_gain": 0,
    "vga_gain": 0,
    "antenna_amp": False,
    "span_hz": 20000000 
}

OUTPUT_DIR = "sensor_captures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@socketio.on('connect')
def handle_connect():
    print(f"--- Client Connected: {request.sid} ---")
    # Send the first job immediately upon connection
    emit('configure_sensor', sensor_config)

@socketio.on('disconnect')
def handle_disconnect():
    print(f"--- Client Disconnected: {request.sid} ---")

@socketio.on('sensor_reading')
def handle_sensor_reading(data):
    print(f"--- Received Data from {request.sid} ---")
    
    try:
        timestamp_unix = data.get('timestamp')
        start_freq = data.get('start_freq_hz')
        end_freq = data.get('end_freq_hz')
        pxx_values = data.get('Pxx', [])

        if not (timestamp_unix and start_freq and end_freq and pxx_values):
            return

        ts_human = datetime.datetime.fromtimestamp(timestamp_unix).strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"{ts_human}_{start_freq}_{end_freq}.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)

        freqs = np.linspace(start_freq, end_freq, len(pxx_values))

        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Frequency_Hz", "Power_dB"])
            for f, p in zip(freqs, pxx_values):
                writer.writerow([f, p])

        print(f"Saved: {filepath}")
        
        emit('server_ack', {'status': 'saved', 'file': filename})
        
        # === CONTINUOUS LOOP LOGIC ===
        # If you want the slave to immediately start the next scan:
        # emit('configure_sensor', sensor_config) 

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    print("Master Server Running on 0.0.0.0:5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)