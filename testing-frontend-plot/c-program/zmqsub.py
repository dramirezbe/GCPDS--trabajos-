import zmq
import zmq.asyncio
import json
import logging
import asyncio
import numpy as np
import matplotlib.pyplot as plt
import time
import cfg

# Configure Logging
logging.basicConfig(level=logging.INFO, format='[PY-SERVER] %(message)s')
logger = logging.getLogger(__name__)

class ZmqPub:
    def __init__(self, address=cfg.IPC_CMD_ADDR, verbose=True, log=logger):
        self.verbose = verbose
        self._log = log
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        
        # Python binds to the Command Channel
        try:
            self.socket.bind(address)
            self._log.info(f"Publisher BOUND to {address}")
        except zmq.ZMQError as e:
            self._log.error(f"Could not bind to {address}: {e}")

    def public_client(self, topic: str, payload: dict):
        json_msg = json.dumps(payload)
        full_msg = f"{topic} {json_msg}"
        self.socket.send_string(full_msg)
        if self.verbose:
            self._log.info(f"Sent Command: {json_msg}")

    def close(self):
        self.socket.close()
        self.context.term()

class ZmqSub:
    def __init__(self, topic: str, address=cfg.IPC_DATA_ADDR, verbose=True, log=logger):
        self.verbose = verbose
        self.topic = topic
        self._log = log
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.SUB)
        
        # Python CONNECTS to the Data Channel (Created by C)
        self.socket.connect(address)
        self.socket.subscribe(self.topic.encode('utf-8'))

        self._log.info(f"Subscriber CONNECTED to {address} (Topic: {topic})")

    async def wait_msg(self):
        """Blocks asynchronously until a message arrives"""
        while True:
            full_msg = await self.socket.recv_string()
            try:
                pub_topic, json_msg = full_msg.split(" ", 1)
                if pub_topic == self.topic:
                    if self.verbose:
                        self._log.info(f"Received {len(json_msg)} bytes of JSON data.")
                    return json.loads(json_msg)
            except ValueError:
                self._log.error(f"Malformed message received: {full_msg[:50]}...")

    def close(self):
        self.socket.close()
        self.context.term()

def save_plot(data, filename="psd_output.png"):
    """
    Generates and saves a PSD plot from the JSON data.
    """
    try:
        # 1. Extract Data
        pxx = data["Pxx"]
        start_f = data["start_freq_hz"]
        end_f = data["end_freq_hz"]
        
        num_points = len(pxx)
        
        # 2. Generate Frequency Axis (X-Axis)
        # Create a linear space from Start to End
        freqs = np.linspace(start_f, end_f, num_points)
        
        # Convert to MHz for cleaner plotting
        freqs_mhz = freqs / 1e6
        
        # 3. Plotting
        plt.figure(figsize=(10, 6))
        plt.plot(freqs_mhz, pxx, color='#00aaff', linewidth=1)
        
        plt.title("Power Spectral Density")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Magnitude") # dBm, dBuV, etc.
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        
        # 4. Save
        plt.savefig(filename)
        plt.close()
        logger.info(f"Plot saved to {filename}")
        
    except KeyError as e:
        logger.error(f"Missing key in data for plotting: {e}")
    except Exception as e:
        logger.error(f"Plotting error: {e}")

async def run_server():
    # 1. Initialize Channels
    # Command Channel (Outbound)
    pub = ZmqPub(address=cfg.IPC_CMD_ADDR)
    
    # Data Channel (Inbound) - Topic MUST match C code ("psd_data")
    sub = ZmqSub(topic="psd_data", address=cfg.IPC_DATA_ADDR)

    # Allow ZMQ connections to settle
    await asyncio.sleep(0.5)

    # 2. Define Configuration
    config = {
        "center_freq_hz": 98000000,   # 98 MHz
        "rbw_hz": 10000,              # 10 kHz Res Bandwidth
        "sample_rate_hz": 20000000,   # 20 MSPS
        "span": 20000000,             # Full Span
        "scale": "dBm",               # Units
        "window": "hamming",
        "overlap": 0.5,
        "lna_gain": 0,
        "vga_gain": 0,
        "antenna_amp": False
    }

    print("\n--- [SERVER] Starting Cycle ---")
    
    # 3. Send Command
    pub.public_client("acquire", config)
    
    # 4. Await Response
    logger.info("Waiting for PSD data from C engine...")
    
    # This will block until C finishes acquisition and processing
    data = await sub.wait_msg()
    
    # 5. Process Data
    logger.info(f"Data Received! Processing {len(data['Pxx'])} bins...")
    logger.info(f"Span: {data['start_freq_hz']/1e6:.2f} MHz to {data['end_freq_hz']/1e6:.2f} MHz")
    
    # 6. Save Image
    timestamp = int(time.time())
    save_plot(data, filename=f"psd_{timestamp}.png")
    
    # Cleanup
    pub.close()
    sub.close()
    print("--- [SERVER] Cycle Complete ---\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nStopping server.")