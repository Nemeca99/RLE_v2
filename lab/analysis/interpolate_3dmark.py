#!/usr/bin/env python3
"""
Interpolate the 14 screenshot data points into continuous 1 Hz data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

df = pd.read_csv("pc/3dmark_extracted.csv")

# Parse timestamps
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['elapsed_sec'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds()

print(f"Original: {len(df)} data points over {df['elapsed_sec'].max():.1f} seconds")
print(f"Temp range: {df['temp'].min():.1f}°C - {df['temp'].max():.1f}°C")
print(f"FPS range: {df['fps'].min():.1f} - {df['fps'].max():.1f}")

# Create 1 Hz timeline (interpolate)
duration = int(df['elapsed_sec'].max())
timeline = np.arange(0, duration, 1.0)  # 1 Hz

# Interpolate
fps_interp = np.interp(timeline, df['elapsed_sec'], df['fps'])
temp_interp = np.interp(timeline, df['elapsed_sec'], df['temp'])

# Create full sensor data
start_time = df['timestamp'].min()
sensor_data = []

for i, t in enumerate(timeline):
    timestamp = start_time + timedelta(seconds=i)
    
    # Estimate util from FPS
    util_pct = 40 + (fps_interp[i] / 60 * 40)
    
    # Estimate power
    power_w = 3.0 + (util_pct / 100.0 * 7.0)
    
    sensor_data.append({
        'timestamp': timestamp.isoformat() + 'Z',
        'cpu_util_pct': util_pct,
        'cpu_freq_ghz': 2.8,
        'battery_temp_c': temp_interp[i],
        'battery_voltage_v': 4.2,
        'battery_current_a': -power_w / 4.2,
    })

sensor_df = pd.DataFrame(sensor_data)
sensor_df.to_csv("pc/phone_raw_interpolated.csv", index=False)

print(f"\nCreated {len(sensor_df)} samples (1 Hz)")
print(f"Duration: {len(sensor_df)} seconds ({len(sensor_df)/60:.1f} minutes)")
print(f"Saved to pc/phone_raw_interpolated.csv")

# Now convert to RLE
print("\nConverting to RLE...")
from mobile_to_rle import convert
convert("pc/phone_raw_interpolated.csv", "pc/phone_rle_final.csv")
print("Saved to pc/phone_rle_final.csv")

