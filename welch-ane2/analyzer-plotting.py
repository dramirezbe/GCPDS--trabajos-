import pandas as pd
import matplotlib.pyplot as plt

# Replace this with the path to your CSV or text file
file_path = '/run/media/javastral/JAVASTRAL/Trace_0002.csv'

# Step 1: Read the file and extract the DATA section
with open(file_path, 'r') as file:
    lines = file.readlines()

# Find the index where DATA starts
data_index = next(i for i, line in enumerate(lines) if line.strip() == 'DATA')

# Extract data lines (frequency, dBm)
data_lines = lines[data_index + 1:]
data = [line.strip().split(',') for line in data_lines if line.strip()]
data = [(float(freq), float(dbm)) for freq, dbm in data]

# Step 2: Convert to DataFrame for easy plotting
df = pd.DataFrame(data, columns=['Frequency (Hz)', 'Power (dBm)'])

print(df['Frequency (Hz)'].shape)
print(df['Power (dBm)'].shape)

# Step 3: Plot the data
plt.figure(figsize=(12, 6))
plt.plot(df['Frequency (Hz)'], df['Power (dBm)'], linewidth=1)
plt.title('Spectrum Analyzer Trace')
plt.xlabel('Frequency (Hz)')
plt.ylabel('Power (dBm)')
plt.grid(True)
plt.tight_layout()

plt.savefig("spectrum_plot.png")  # Save the figure to a file
print("Plot saved as 'spectrum_plot.png'")