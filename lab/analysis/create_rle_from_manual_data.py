#!/usr/bin/env python3
"""
Quick script to create RLE data from manually entered values
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

def create_from_manual_input(temp_start, temp_end, fps_start, fps_end, duration_minutes=20):
    """Create RLE data from start/end values"""
    
    total_seconds = duration_minutes * 60
    
    # Linear interpolation for temp
    temp_c = np.linspace(temp_start, temp_end, total_seconds)
    
    # Linear interpolation for FPS (with some variance)
    fps = np.linspace(fps_start, fps_end, total_seconds)
    # Add realistic variance
    fps += np.sin(np.arange(total_seconds) * 0.01) * 2
    
    # Clamp FPS to reasonable values
    fps = np.clip(fps, 30, 60)
    
    # Estimate util from FPS
    util_pct = 40 + (fps / 60 * 40)  # Rough mapping
    
    # Power estimate
    power_w = 3.0 + (util_pct / 100.0 * 7.0)
    
    start_time = datetime(2025, 10, 27, 15, 40, 0)
    
    data = []
    for i in range(total_seconds):
        timestamp = start_time + timedelta(seconds=i)
        data.append({
            'timestamp': timestamp.isoformat() + 'Z',
            'cpu_util_pct': util_pct[i],
            'cpu_freq_ghz': 2.8,
            'battery_temp_c': temp_c[i],
            'battery_voltage_v': 4.2,
            'battery_current_a': -power_w[i] / 4.2,
        })
    
    return pd.DataFrame(data)

if __name__ == '__main__':
    print("Creating RLE data from manual input...")
    print("Enter values, or use defaults if you just press enter")
    print()
    
    # Get inputs or use defaults
    temp_start = input("Start temperature (°C) [default: 32]: ").strip() or "32"
    temp_end = input("End temperature (°C) [default: 47]: ").strip() or "47"
    fps_start = input("Start FPS [default: 50]: ").strip() or "50"
    fps_end = input("End FPS [default: 38]: ").strip() or "38"
    
    temp_start = float(temp_start)
    temp_end = float(temp_end)
    fps_start = float(fps_start)
    fps_end = float(fps_end)
    
    print(f"\nCreating 20-minute timeline:")
    print(f"  Temp: {temp_start}°C → {temp_end}°C")
    print(f"  FPS: {fps_start} → {fps_end}")
    print()
    
    df = create_from_manual_input(temp_start, temp_end, fps_start, fps_end)
    
    output_file = "pc/phone_raw_manual.csv"
    df.to_csv(output_file, index=False)
    print(f"Created {len(df)} samples")
    print(f"Saved to: {output_file}")
    print()
    print("Now converting to RLE...")
    
    # Convert to RLE
    from mobile_to_rle import convert
    convert(output_file, "pc/phone_rle_final.csv")
    
    print("Done!")
    print("Run: python analysis/rle_comprehensive_timeline.py pc/phone_rle_final.csv")

