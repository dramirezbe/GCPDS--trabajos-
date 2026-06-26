import pandas as pd

filename = 'telemetry-noPCB-20M-1KRBW-FILTERING-6GHZ.csv'
df = pd.read_csv(filename)

# Convert to UTC-5, then remove timezone info
df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('-05:00').dt.tz_localize(None)

df.to_csv(filename, index=False)