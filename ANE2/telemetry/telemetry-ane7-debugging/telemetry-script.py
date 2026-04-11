import time, datetime, subprocess, signal, os, psutil

running = True
def handle_signal(*args): global running; running = False
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

csv_file = open('telemetry.csv', 'w')
csv_file.write("timestamp,cpu_cores,temp_c,ram_total,ram_used,ram_free,swap_total,swap_used,swap_free,disk_read,disk_write,disk_percent,throttled\n")
psutil.cpu_percent()

for _ in range(600): # 600 seconds = 10 minutes
    if not running: break
    
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cpu = "|".join(map(str, psutil.cpu_percent(percpu=True)))
    
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
        temp = float(f.read().strip()) / 1000.0
        
    mem, swap = psutil.virtual_memory(), psutil.swap_memory()
    disk_io, disk_health = psutil.disk_io_counters(), psutil.disk_usage('/').percent
    throttle = subprocess.check_output(['vcgencmd', 'get_throttled']).decode().strip()
    
    csv_file.write(f"{ts},{cpu},{temp},{mem.total},{mem.used},{mem.free},{swap.total},{swap.used},{swap.free},{disk_io.read_bytes},{disk_io.write_bytes},{disk_health},{throttle}\n")
    csv_file.flush()
    os.fsync(csv_file.fileno())
    time.sleep(1)

csv_file.close()