import requests
import time
import numpy as np

MAC_ADDRESS = "d0:65:78:9c:dd:d0"
BASE_URL = "http://0.0.0.0:8005"

payload_count = 0
stations = []

while True:
    try:
        config = requests.get(f"{BASE_URL}/{MAC_ADDRESS}/realtime", timeout=5).json()
        
        fs = config.get("sample_rate_hz", 0) or 1e6
        rbw = config.get("rbw_hz", 0) or 1e3
        fc = config.get("center_freq_hz", 0) or 100e6
        lna = config.get("lna_gain", 0)
        vga = config.get("vga_gain", 0)
        window = config.get("window", "hamming")
        
        win_factors = {"hamming": 1.3, "hann": 1.5, "flattop": 3.77}
        factor = win_factors.get(window, 1.0)
        
        n_bins = int((factor * fs) / rbw)
        noise_level = -23 + lna + vga
        pxx = np.random.normal(noise_level, 2.0, n_bins)
        
        if payload_count % 10 == 0 or not stations:
            num_stations = np.random.randint(3, 8)
            stations = [(np.random.uniform(0.05, 0.95), np.random.uniform(30.0, 60.0)) for _ in range(num_stations)]
            print(f"--- Frequencies changed! Generated {num_stations} new stations ---")

        bw_pct = 0.01 
        half_bw = max(1, int(n_bins * bw_pct / 2))

        for rel_pos, base_power in stations:
            idx = int(rel_pos * n_bins)
            current_power = base_power + np.random.uniform(-5.0, 5.0) 
            
            for i in range(-half_bw, half_bw + 1):
                target_idx = idx + i
                if 0 <= target_idx < n_bins:
                    pxx[target_idx] += current_power * (1 - abs(i) / (half_bw + 1))
        
        payload = {
            "mac": MAC_ADDRESS,
            "Pxx": pxx.tolist(),
            "start_freq_hz": int(fc - (fs / 2)),
            "end_freq_hz": int(fc + (fs / 2)),
            "timestamp": int(time.time())
        }
        
        requests.post(f"{BASE_URL}/data", json=payload, timeout=5)
        print(f"Payload {payload_count}: Sent {n_bins} points. Center: {fc}Hz.")
        
        payload_count += 1

    except requests.exceptions.RequestException:
        print("Endpoint not found or unreachable. Retrying...")
    
    time.sleep(2)