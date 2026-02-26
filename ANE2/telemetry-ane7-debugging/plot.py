import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load and parse data
df = pd.read_csv('telemetry-ANE3-20M-1kRBW-6G.csv', parse_dates=['timestamp'])
df.set_index('timestamp', inplace=True)

# Process CPU cores
cores = df['cpu_cores'].str.split('|', expand=True).astype(float)
df['cpu_avg'] = cores.mean(axis=1)

# Process throttled state
df['throttled'] = df['throttled'].apply(lambda x: int(x.split('=')[1], 16))

# Calculate disk write rate
df['disk_write_rate'] = df['disk_write'].diff()

# Set up the figure
plt.figure(figsize=(15, 12))

# 1. Temp vs Throttled
ax1 = plt.subplot(3, 2, 1)
df['temp_c'].plot(ax=ax1, color='red', label='Temp (C)')
ax2 = ax1.twinx()
df['throttled'].plot(ax=ax2, color='blue', label='Throttled')
ax1.set_title('Temp vs Throttled State')

# 2. CPU Load vs Temp
plt.subplot(3, 2, 2)
plt.scatter(df['temp_c'], df['cpu_avg'])
plt.xlabel('Temp (C)')
plt.ylabel('Avg CPU Load')
plt.title('CPU Load vs Temp')

# 3. Disk Write vs Temp
plt.subplot(3, 2, 3)
plt.scatter(df['temp_c'], df['disk_write'])
plt.xlabel('Temp (C)')
plt.ylabel('Disk Write (Bytes)')
plt.title('Disk Write vs Temp')

# 4. RAM Used vs Time
plt.subplot(3, 2, 4)
df['ram_used'].plot()
plt.title('RAM Used vs Time')
plt.ylabel('RAM Used (Bytes)')

# 5. Per-Core CPU Heatmap
plt.subplot(3, 2, 5)
sns.heatmap(cores.T, cmap='viridis', cbar_kws={'label': 'CPU Load'})
plt.title('Per-Core CPU Heatmap')
plt.ylabel('Core Index')
plt.xlabel('Time (Sample Index)')

# 6. Disk Write Rate
plt.subplot(3, 2, 6)
df['disk_write_rate'].plot()
plt.title('Disk Write Rate')
plt.ylabel('Bytes / Sample')

plt.tight_layout()
plt.show()