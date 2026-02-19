import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Define your files here
files = {
    '8M': 'telemetry-8Mfs-1MRBW.csv',
    '20M First': 'telemetry-20M-1KRBW-FILTERING-6GHZ.csv',
    '20M Second': 'telemetry-20M-1KRBW-FILTERING-6GHZ-(2).csv',
    'noPCB': 'telemetry-noPCB-20M-1KRBW-FILTERING-6GHZ.csv'
}

fig, axes = plt.subplots(3, 4, figsize=(24, 18))

for col, (label, file) in enumerate(files.items()):
    df = pd.read_csv(file, parse_dates=['timestamp']).set_index('timestamp')
    
    elapsed = df.index - df.index[0]
    df.index = elapsed.map(lambda x: f"{int(x.total_seconds() // 60):02d}:{int(x.total_seconds() % 60):02d}")
    
    cores = df['cpu_cores'].str.split('|', expand=True).astype(float)
    df['throttled'] = df['throttled'].apply(lambda x: int(x.split('=')[1], 16))

    # Row 0: Temp & Throttled
    df['temp_c'].plot(ax=axes[0, col], color='red')
    ax2 = axes[0, col].twinx()
    df['throttled'].plot(ax=ax2, color='blue')
    axes[0, col].set_title(f'{label}: Temp & Throttled')

    # Row 1: RAM & Swap
    df['ram_used'].plot(ax=axes[1, col], color='green')
    ax3 = axes[1, col].twinx()
    df['swap_used'].plot(ax=ax3, color='orange')
    axes[1, col].set_title(f'{label}: RAM & Swap')

    # Row 2: CPU Heatmap
    sns.heatmap(cores.T, ax=axes[2, col], cmap='viridis', cbar=False, xticklabels=max(1, len(cores)//6))
    axes[2, col].set_title(f'{label}: CPU Heatmap')

# Rotate all x-axis labels by 45 degrees
for ax in axes.flat:
    ax.tick_params(axis='x', rotation=45)

# Force extra space between subplots
plt.tight_layout()
plt.subplots_adjust(hspace=0.5, wspace=0.3) 
plt.show()