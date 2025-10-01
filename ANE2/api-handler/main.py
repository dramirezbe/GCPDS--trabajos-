import schedule
import time
import json
from Modules import status_rpi

def check_system_status():
    """
    This is the job function that schedule will run.
    It calls the module to get the status and then prints it.
    """
    print("Checking system status...")
    
    # Get the JSON string from our module.
    status_json = status_rpi.get_rpi_status()
    
    if status_json:
        try:
            # You can optionally parse the JSON into a Python dictionary
            # to work with the data more easily.
            status_data = json.loads(status_json)
            print("Successfully retrieved status:")
            print(f"  - CPU Temp: {status_data.get('cpu_temp')}°C")
            print(f"  - RAM Used: {status_data.get('ram_used')}%")
            print(f"  - Disk Free: {status_data.get('disk_free')}")
            print("-" * 20)
        except json.JSONDecodeError:
            print("Error: Received invalid JSON from C library.")
            print(f"Raw string: {status_json}")
    else:
        print("Failed to retrieve system status.")

# --- Scheduling the Task ---
print("Starting status monitoring application.")

# Schedule the 'check_system_status' job to run every 5 minutes.
# You have many options, like .seconds, .minutes, .hours, .days, etc.
schedule.every(5).minutes.do(check_system_status)

# For testing, you might want to run it more frequently:
# schedule.every(10).seconds.do(check_system_status)

# --- Main Loop ---
# This loop runs forever, checking if a scheduled task is due to run.
try:
    # Run the job once immediately at the start.
    check_system_status()
    
    while True:
        # This function checks if any jobs are pending and runs them.
        schedule.run_pending()
        # Sleep for a short duration to prevent the CPU from running at 100%.
        time.sleep(1)
except KeyboardInterrupt:
    print("\nProgram stopped by user.")