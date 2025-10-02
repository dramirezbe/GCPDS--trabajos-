import time
import matplotlib.pyplot as plt
import numpy as np
import os
import shutil

def get_cpu_usage_per_thread():
    """Retorna un vector de flotantes con el porcentaje de uso de cada hilo del cpu"""
    try:
        # Primera lectura de /proc/stat
        with open('/proc/stat', 'r') as f:
            lines_initial = f.readlines()

        # Esperar un corto período para medir la diferencia
        time.sleep(0.1) # Puedes ajustar este valor si necesitas mayor precisión o menor latencia

        # Segunda lectura de /proc/stat
        with open('/proc/stat', 'r') as f:
            lines_final = f.readlines()

        cpu_usages = []

        # Procesar cada línea de CPU (cpu0, cpu1, etc.)
        for i in range(len(lines_initial)):
            if lines_initial[i].startswith('cpu'):
                # Si es la línea 'cpu' general, la ignoramos o la tratamos por separado si es necesario.
                # Para este script, nos enfocamos en 'cpuX' para hilos individuales.
                if lines_initial[i].startswith('cpu '):
                    continue

                # Parsear los valores de la línea inicial
                parts_initial = lines_initial[i].split()
                # user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice
                # Los primeros 4 valores son los más importantes para el uso de la CPU.
                # Total ticks = user + nice + system + idle + iowait + irq + softirq + steal
                initial_total = sum(map(int, parts_initial[1:9])) # Suma de user, nice, system, idle, iowait, irq, softirq, steal
                initial_idle = int(parts_initial[4]) # idle time

                # Parsear los valores de la línea final
                parts_final = lines_final[i].split()
                final_total = sum(map(int, parts_final[1:9]))
                final_idle = int(parts_final[4])

                # Calcular la diferencia
                delta_total = final_total - initial_total
                delta_idle = final_idle - initial_idle

                # Evitar división por cero
                if delta_total == 0:
                    cpu_usages.append(0.0)
                    continue

                # Calcular el porcentaje de uso
                # Uso = 100 * (1 - (tiempo_inactivo / tiempo_total))
                usage_percentage = 100.0 * (1.0 - (delta_idle / delta_total))
                cpu_usages.append(round(usage_percentage, 2))

        return cpu_usages

    except FileNotFoundError:
        print("Error: /proc/stat no encontrado. Asegúrate de estar en un sistema Linux basado en /proc.")
        return []
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return []

def get_storage():
    """
    Retorna información sobre el uso de RAM, SWAP y disco duro del sistema.
    Los valores se expresan en megabytes (MB).

    Returns:
        tuple: Una tupla que contiene tres listas:
               - ram_info [uso_ram_mb, capacidad_ram_mb]
               - swap_info [uso_swap_mb, capacidad_swap_mb]
               - disk_info [uso_disco_mb, capacidad_disco_mb]
               Retorna listas vacías si hay un error al obtener la información.
    """
    ram_info = []
    swap_info = []
    disk_info = []

    # --- Obtener información de la RAM y SWAP desde /proc/meminfo ---
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()

        mem_total_kb = 0
        mem_free_kb = 0
        buffers_kb = 0
        cached_kb = 0
        swap_total_kb = 0
        swap_free_kb = 0

        for line in lines:
            if line.startswith('MemTotal:'):
                mem_total_kb = int(line.split()[1])
            elif line.startswith('MemFree:'):
                mem_free_kb = int(line.split()[1])
            elif line.startswith('Buffers:'):
                buffers_kb = int(line.split()[1])
            elif line.startswith('Cached:'):
                cached_kb = int(line.split()[1])
            elif line.startswith('SwapTotal:'):
                swap_total_kb = int(line.split()[1])
            elif line.startswith('SwapFree:'):
                swap_free_kb = int(line.split()[1])

        # RAM
        # Memoria usada = MemTotal - MemFree - Buffers - Cached
        # Buffers y Cached son memoria usada por el sistema pero que puede ser liberada,
        # así que para el "uso real" es mejor restarlos.
        ram_used_kb = mem_total_kb - mem_free_kb - buffers_kb - cached_kb
        ram_info = [round(ram_used_kb / 1024, 2), round(mem_total_kb / 1024, 2)]

        # SWAP
        swap_used_kb = swap_total_kb - swap_free_kb
        swap_info = [round(swap_used_kb / 1024, 2), round(swap_total_kb / 1024, 2)]

    except FileNotFoundError:
        print("Error: /proc/meminfo no encontrado. Asegúrate de estar en un sistema Linux.")
    except Exception as e:
        print(f"Error al leer /proc/meminfo: {e}")

    # --- Obtener información del disco duro desde shutil ---
    try:
        import shutil
        # Usamos '/' para la partición raíz del sistema de archivos
        total_b, used_b, free_b = shutil.disk_usage('/')

        disk_total_mb = round(total_b / (1024 * 1024), 2)
        disk_used_mb = round(used_b / (1024 * 1024), 2)
        disk_info = [disk_used_mb, disk_total_mb]

    except ImportError:
        print("Error: El módulo 'shutil' no está disponible. Esto es inusual en Python estándar.")
    except Exception as e:
        print(f"Error al obtener información del disco: {e}")

    return ram_info, swap_info, disk_info

def get_cpu_temperature():
    """
    Obtiene la temperatura de la CPU del sistema en grados Celsius.
    Funciona en sistemas Linux que exponen la temperatura a través de /sys/class/thermal/.
    (Típicamente efectivo en Raspberry Pi y muchos otros sistemas Linux).

    Returns:
        float: La temperatura de la CPU en grados Celsius, o None si no se puede leer.
    """

    temp_file_path = '/sys/class/thermal/thermal_zone0/temp'
    try:
        # La ruta más común para la temperatura de la CPU
        with open(temp_file_path, 'r') as f:
            # Lee el valor, que es un entero en milésimas de grado Celsius
            temperature_raw = int(f.read().strip())
            # Convierte a grados Celsius
            temperature_celsius = temperature_raw / 1000.0
            return temperature_celsius
    except FileNotFoundError:
        print(f"Advertencia: El archivo de temperatura '{temp_file_path}' no fue encontrado.")
        print("Esto es normal si tu sistema no expone la temperatura de esta manera.")
        print("En Raspberry Pi, también puedes intentar 'vcgencmd measure_temp' via subprocess.")
        return None
    except ValueError:
        print(f"Advertencia: No se pudo convertir el valor de temperatura de '{temp_file_path}' a número.")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado al leer la temperatura: {e}")
        return None

def print_progress_bar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 50, fill = '█', print_end = "\r"):
    """
    Call in a loop to create a terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = print_end)
    # Print New Line on Complete
    if iteration == total: 
        print()

# --- Parámetros de recolección de datos ---
duration = 60 * 30 # Duración en segundos
sampling_interval = 1 # Muestreo cada 1 segundo
num_samples = int(duration / sampling_interval)

# --- Listas para almacenar los datos ---
timestamps = []
cpu_plot_data = []
ram_plot_data = []
swap_plot_data = []
disk_plot_data = []
temp_plot_data = []

print(f"Comenzando la recolección de datos por {duration} segundos...")
start_time = time.time()

for i in range(num_samples):
    current_time = time.time() - start_time
    timestamps.append(current_time)

    cpu_usage = get_cpu_usage_per_thread()
    ram_usage, swap_usage, disk_usage = get_storage()
    cpu_temp = get_cpu_temperature()

    cpu_plot_data.append(cpu_usage)
    ram_plot_data.append(ram_usage)
    swap_plot_data.append(swap_usage)
    disk_plot_data.append(disk_usage)
    temp_plot_data.append(cpu_temp)

    # Actualizar la barra de progreso
    elapsed_time = time.time() - start_time
    print_progress_bar(i + 1, num_samples, prefix = 'Progreso:', suffix = f'Completado - Tiempo transcurrido: {elapsed_time:.1f}s', length = 50)
    
    time_to_wait = sampling_interval - (time.time() - (start_time + (i + 1) * sampling_interval))
    if time_to_wait > 0:
        time.sleep(time_to_wait)

print("Recolección de datos finalizada.")

# --- Preparar datos para graficar ---

if cpu_plot_data:
    max_threads = max(len(threads) for threads in cpu_plot_data) if cpu_plot_data else 0
    padded_cpu_data = [
        sample + [0.0] * (max_threads - len(sample))
        for sample in cpu_plot_data
    ]
    cpu_usage_per_thread_series = list(map(list, zip(*padded_cpu_data)))

ram_used = [r[0] for r in ram_plot_data if r]
ram_total = [r[1] for r in ram_plot_data if r]
swap_used = [s[0] for s in swap_plot_data if s]
swap_total = [s[1] for s in swap_plot_data if s]
disk_used = [d[0] for d in disk_plot_data if d]
disk_total = [d[1] for d in disk_plot_data if d]

# --- Directorio de salida ---
output_dir = "outputs"
os.makedirs(output_dir, exist_ok=True)

# --- Graficar los datos ---

# Gráfica de Uso de CPU por Hilo
if cpu_plot_data and cpu_usage_per_thread_series:
    plt.figure(figsize=(12, 6))
    for i, thread_data in enumerate(cpu_usage_per_thread_series):
        plt.plot(timestamps, thread_data, label=f'CPU Core {i}', alpha=0.7)

    cpu_usage_average = np.mean(cpu_usage_per_thread_series, axis=0)
    plt.plot(timestamps, cpu_usage_average, label='CPU Promedio', color='black', linewidth=3)

    plt.xlabel('Tiempo (segundos)')
    plt.ylabel('Uso de CPU (%)')
    plt.title('Uso de CPU por Hilo a lo largo del Tiempo')
    plt.ylim(0, 100)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'cpu_usage.jpg'), dpi=300)
    plt.close()

# Gráfica de Uso de RAM
if ram_used and ram_total:
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, ram_used, label='RAM Usada (MB)', color='blue')
    
    plt.xlabel('Tiempo (segundos)')
    plt.ylabel('Memoria (MB)')
    
    # Get the maximum RAM total from the collected data
    max_ram_total = max(ram_total) if ram_total else 0
    plt.title(f'Uso de RAM a lo largo del Tiempo (Total: {max_ram_total:.2f} MB)')
    
    plt.grid(True)
    plt.ylim(0, max_ram_total * 1.05) # Set ylim from 0 to max total RAM with a little buffer
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'ram_usage.jpg'), dpi=300)
    plt.close()

# Gráfica de Uso de SWAP
if swap_used and swap_total:
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, swap_used, label='SWAP Usado (MB)', color='orange')
    
    plt.xlabel('Tiempo (segundos)')
    plt.ylabel('Memoria (MB)')

    # Get the maximum SWAP total from the collected data
    max_swap_total = max(swap_total) if swap_total else 0
    plt.title(f'Uso de SWAP a lo largo del Tiempo (Total: {max_swap_total:.2f} MB)')
    
    plt.grid(True)
    plt.ylim(0, max_swap_total * 1.05) # Set ylim from 0 to max total SWAP with a little buffer
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'swap_usage.jpg'), dpi=300)
    plt.close()

# Gráfica de Uso de Disco
if disk_used and disk_total:
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, disk_used, label='Disco Usado (MB)', color='green')
    
    plt.xlabel('Tiempo (segundos)')
    plt.ylabel('Espacio (MB)')

    # Get the maximum Disk total from the collected data
    max_disk_total = max(disk_total) if disk_total else 0
    plt.title(f'Uso de Disco a lo largo del Tiempo (Total: {max_disk_total:.2f} MB)')
    
    plt.grid(True)
    plt.ylim(0, max_disk_total * 1.05) # Set ylim from 0 to max total Disk with a little buffer
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'disk_usage.jpg'), dpi=300)
    plt.close()

# Gráfica de Temperatura de CPU
if temp_plot_data and any(t is not None for t in temp_plot_data):
    valid_timestamps_temp = [timestamps[i] for i, temp in enumerate(temp_plot_data) if temp is not None]
    valid_temp_data = [temp for temp in temp_plot_data if temp is not None]

    if valid_temp_data:
        plt.figure(figsize=(12, 6))
        plt.plot(valid_timestamps_temp, valid_temp_data, label='Temperatura CPU (°C)', color='red')
        plt.xlabel('Tiempo (segundos)')
        plt.ylabel('Temperatura (°C)')
        plt.title('Temperatura de CPU a lo largo del Tiempo')
        plt.grid(True)
        min_temp = min(valid_temp_data) if valid_temp_data else 0
        max_temp = max(valid_temp_data) if valid_temp_data else 100
        plt.ylim(min_temp * 0.9, max_temp * 1.1)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'cpu_temperature.jpg'), dpi=300)
        plt.close()

print(f"Gráficas de rendimiento guardadas en la carpeta '{output_dir}/' en formato JPEG.")