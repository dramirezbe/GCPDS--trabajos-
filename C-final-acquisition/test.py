import cfg
log = cfg.set_logger()
from utils import ZmqPub

import time


# --- Main Execution ---
if __name__ == "__main__":
    
    # Initialize Publisher
    pub = ZmqPub(verbose=True)

    try:
        log.info("Publisher running... Press Ctrl+C to stop.")
        counter = 0
        
        while True:
            # Create a dummy payload
            data = {
                "id": counter,
                "voltage": 3.3 + (counter % 5) * 0.1,
                "msg": "Hello C code"
            }

            # Send to the topic defined in your C main.c
            pub.public_client("DATA_FEED", data)
            log.info(f"Published: {data}")
            
            counter += 1
            time.sleep(1.0) # Send every 1 second

    except KeyboardInterrupt:
        print("\nStopping publisher...")
    finally:
        pub.close()