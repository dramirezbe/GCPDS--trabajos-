import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Define your files here
files = {
    'ANE9 old-version': 'ANE9-old-version.csv',
    'ANE2 new-version': 'ANE2-new-version.csv'
}

# --- STEP 1: LOAD AND TRUNCATE DATA ---
loaded_dfs = {}
for label, file in files.items():
    df = pd.read_csv(file, parse_dates=['timestamp']).set_index('timestamp')
    loaded_dfs[label] = df

# Normalizator: Find the shortest length
min_len = min(len(df) for df in loaded_dfs.values())

# Process and store normalized data
processed_data = {}
for label, df in loaded_dfs.items():
    temp_df = df.iloc[:min_len].copy()
    
    # Standardize X-axis to "MM:SS" elapsed time
    elapsed = temp_df.index - temp_df.index[0]
    temp_df.index = elapsed.map(lambda x: f"{int(x.total_seconds() // 60):02d}:{int(x.total_seconds() % 60):02d}")
    
    # Process CPU cores and Throttled hex values
    temp_df['cores_data'] = temp_df['cpu_cores'].str.split('|', expand=False)
    temp_df['throttled_val'] = temp_df['throttled'].apply(lambda x: int(x.split('=')[1], 16))
    
    processed_data[label] = temp_df

# --- STEP 2: PLOTTING ---
fig = plt.figure(figsize=(20, 22))

# Define the grid: 3 rows, 2 columns
# Row 0 & 1 will span both columns. Row 2 will be split.
ax_temp = plt.subplot2grid((3, 2), (0, 0), colspan=2)
ax_ram = plt.subplot2grid((3, 2), (1, 0), colspan=2)
ax_heat1 = plt.subplot2grid((3, 2), (2, 0))
ax_heat2 = plt.subplot2grid((3, 2), (2, 1))

# --- ROW 0: COMBINED TEMP & THROTTLED ---
ax_throttled = ax_temp.twinx()
colors = {'ANE9 old-version': ('red', 'blue'), 'ANE2 new-version': ('orange', 'cyan')}

for label, df in processed_data.items():
    t_color, th_color = colors[label]
    df['temp_c'].plot(ax=ax_temp, color=t_color, label=f'{label} Temp', linewidth=2)
    df['throttled_val'].plot(ax=ax_throttled, color=th_color, label=f'{label} Throttled', linestyle='--')

ax_temp.set_title(f"Comparison: Temperature and Throttling (First {min_len} samples)", fontsize=16)
ax_temp.set_ylabel("Temperature (°C)")
ax_throttled.set_ylabel("Throttled (Hex Val)")
ax_temp.legend(loc='upper left')
ax_throttled.legend(loc='upper right')

# --- ROW 1: COMBINED RAM ---
for label, df in processed_data.items():
    df['ram_used'].plot(ax=ax_ram, label=f'{label} RAM')

ax_ram.set_title("Comparison: RAM Usage", fontsize=16)
ax_ram.set_ylabel("RAM Used")
ax_ram.legend()

# --- ROW 2: ISOLATED CPU HEATMAPS ---
for i, (label, df) in enumerate(processed_data.items()):
    # Reconstruct the core matrix from the stored list
    cores_matrix = pd.DataFrame(df['cores_data'].tolist()).astype(float)
    target_ax = ax_heat1 if i == 0 else ax_heat2
    
    sns.heatmap(cores_matrix.T, ax=target_ax, cmap='viridis', cbar=True, 
                xticklabels=max(1, len(cores_matrix)//8))
    target_ax.set_title(f"CPU Heatmap: {label}")
    target_ax.tick_params(axis='x', rotation=45)

# Final formatting
plt.tight_layout()
plt.subplots_adjust(hspace=0.3)
plt.show()