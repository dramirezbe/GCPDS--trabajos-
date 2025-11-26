import subprocess
import re
import json
import math

# --- CONFIGURATION ---
# ⚠️ IMPORTANT: Change this to your actual wireless interface name.
WIFI_INTERFACE = "wlp0s20f3" 
RADIO_MAP_FILE = "local_radio_map.json"
# --- CONFIGURATION END ---

# --- PART 1: WI-FI SCANNING (Same Linux Code) ---
def scan_wifi(interface):
    """
    Runs 'sudo iwlist <interface> scan' and parses BSSID and RSSI.
    """
    # ... (Keep the scan_wifi function exactly as in the previous script)
    # [Code for subprocess.run and regex parsing goes here]
    # For brevity, assume you copy the complete scan_wifi function here.
    # It must return a list of dictionaries: [{'macAddress': 'BSSID', 'signalStrength': -70}, ...]
    # Placeholder for copied code:
    
    print(f"Scanning Wi-Fi networks on interface **{interface}**...")
    # --- Start Copied Code ---
    try:
        scan_command = ["sudo", "iwlist", interface, "scan"]
        result = subprocess.run(scan_command, capture_output=True, text=True, check=True)
        output = result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Error during scan: {e}")
        return []

    cell_pattern = re.compile(r"Cell \d+ - Address: (([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))")
    signal_pattern = re.compile(r"Signal level=(-?\d+) dBm")
    
    access_points = []
    current_ap = {}
    
    for line in output.splitlines():
        line = line.strip()
        mac_match = cell_pattern.search(line)
        if mac_match:
            if current_ap and 'macAddress' in current_ap and 'signalStrength' in current_ap:
                access_points.append(current_ap)
            current_ap = {"macAddress": mac_match.group(1).upper().replace('-', ':')}
            continue
        signal_match = signal_pattern.search(line)
        if signal_match and current_ap:
            current_ap["signalStrength"] = int(signal_match.group(1))
    
    if current_ap and 'macAddress' in current_ap and 'signalStrength' in current_ap:
        access_points.append(current_ap)
    # --- End Copied Code ---
    return access_points

# --- PART 2: FINGERPRINTING LOGIC ---

def load_radio_map(filename):
    """Loads the manually created location database from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Radio Map file '{filename}' not found. Please create it first.")
        return None
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON format in '{filename}'.")
        return None

def calculate_euclidean_distance(live_rssi_vector, stored_rssi_vector):
    """Calculates the difference between two signal patterns."""
    sum_of_squares = sum([(live_rssi_vector.get(mac, -100) - stored_rssi_vector.get(mac, -100)) ** 2 
                          for mac in set(live_rssi_vector.keys()) | set(stored_rssi_vector.keys())])
    return math.sqrt(sum_of_squares)

def estimate_local_location(live_scan, radio_map):
    """Estimates location by comparing live scan to the radio map."""
    if not radio_map:
        return "Unknown (No Map)", float('inf')

    # Convert live scan to a dictionary for easier lookup: {BSSID: RSSI}
    live_rssi_dict = {ap['macAddress']: ap['signalStrength'] for ap in live_scan}

    min_distance = float('inf')
    best_match_location = "Unknown"
    
    print("\nComparing scan to stored fingerprints...")

    for location, stored_data in radio_map.items():
        # stored_data is already in {BSSID: RSSI} format
        distance = calculate_euclidean_distance(live_rssi_dict, stored_data)
        print(f"  Distance to '{location}': {distance:.2f}")

        if distance < min_distance:
            min_distance = distance
            best_match_location = location
            
    return best_match_location, min_distance

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    # 1. You MUST create this file first based on your local Wi-Fi environment!
    # Example structure for local_radio_map.json:
    # {
    #     "Desk": { "C4:00:2B:FF:8C:13": -65, "11:AA:22:BB:33:CC": -80, "01:23:45:67:89:AB": -75 },
    #     "Kitchen": { "C4:00:2B:FF:8C:13": -85, "11:AA:22:BB:33:CC": -55, "01:23:45:67:89:AB": -90 }
    # }
    
    # For a quick test, you can create a dummy file:
    # with open(RADIO_MAP_FILE, 'w') as f:
    #     json.dump({"Office Desk": {"A1:B2:C3:D4:E5:F6": -50, "B2:C3:D4:E5:F6:A1": -70}, 
    #                "Kitchen Counter": {"A1:B2:C3:D4:E5:F6": -80, "B2:C3:D4:E5:F6:A1": -55}}, f, indent=4)
    # This dummy data needs to be replaced with REAL MACs and RSSIs from your iwlist scan output!
    
    radio_map = load_radio_map(RADIO_MAP_FILE)

    # 2. Perform the live scan
    live_wifi_data = scan_wifi(WIFI_INTERFACE)
    
    if not live_wifi_data:
        print("Exiting due to scan failure or lack of data.")
    elif radio_map:
        # 3. Estimate location using the local map
        estimated_location, confidence = estimate_local_location(live_wifi_data, radio_map)

        # 4. Print results
        print("\n" + "=" * 50)
        print("🏠 **LOCALIZED LOCATION ESTIMATE (Self-Hosted)**")
        print(f"   You are likely near: **{estimated_location}**")
        print(f"   Confidence Score (Distance): {confidence:.2f} (Lower is better)")
        print("\nNote: This only works for the locations stored in your radio map.")
        print("=" * 50)