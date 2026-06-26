import os
import csv
import json
import datetime
import numpy as np
from flask import Flask, request
from flask_socketio import SocketIO, emit
import matplotlib.pyplot as plt

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
    "antenna_amp": True,
    "span_hz": 20000000,
    "scale": "dBm"
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
        filename = f"{ts_human}_{start_freq}_{end_freq}.png"

        plt.plot(pxx_values)
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Power (dB)')
        plt.title(f"Power Spectral Density - {ts_human}")
        plt.savefig(f"{OUTPUT_DIR}/{filename}")
        plt.close()

        emit('server_ack', {'status': 'saved'})
        
        # === CONTINUOUS LOOP LOGIC ===
        # If you want the slave to immediately start the next scan:
        # emit('configure_sensor', sensor_config) 

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    print("Master Server Running on 0.0.0.0:5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)