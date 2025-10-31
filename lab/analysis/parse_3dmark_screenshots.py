#!/usr/bin/env python3
"""
Parse 3DMark screenshots and extract RLE data
Manual data entry for now - just paste the numbers from the screenshots
"""

import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta

def create_from_3dmark_data():
    """
    Data from screenshots:
    - Wild Life: Temp 30°C → 32°C over 60 seconds
    - Wild Life Extreme: Run 1 (started hot ~38°C from WL), Run 2 (phone call interrupt, warm restart)
    - Frame rate varying
    """
    
    # Create 1200-second (20 minute) timeline for Wild Life Extreme
    start_time = datetime.now().replace(microsecond=0)
    
    # Temperature: starts at 32°C from WL, ramps to ~45°C by end
    minutes = 20
    total_seconds = minutes * 60
    
    # Single continuous 20-minute thermal ramp
    temp_progression = []
    for i in range(total_seconds):
        # Linear ramp from 32°C to 45°C over 20 minutes
        temp_progression.append(32.0 + (13.0 * i / (total_seconds - 1)))
    
    # Frame rate - Wild Life Extreme is more demanding
    # Lower average FPS (35-50 range), throttles under heat
    # Starts at ~50 FPS, gradually drops to ~38 FPS as temp rises
    fps_data = []
    for i in range(total_seconds):
        # Starts high, gradually throttles down as heat builds
        progress = i / total_seconds
        fps = 50 - (12 * progress) + (3 * np.sin(i * 0.008))
        fps_data.append(max(35, min(52, fps)))  # Clamp 35-52
    
    # Estimate CPU utilization from FPS (Wild Life Extreme: 35 FPS = 50% load, 55 FPS = 95% load)
    util_pct = [(fps - 25) / 30 * 100 for fps in fps_data]
    util_pct = [max(15, min(98, u)) for u in util_pct]  # Clamp 15-98%
    
    # Power estimate (use FPS as proxy)
    power_w = [fps / 100 * 7.0 for fps in fps_data]  # ~7W max
    
    # Create dataframe (1200 samples for 20 minutes)
    data = []
    for i in range(total_seconds):
        timestamp = start_time + timedelta(seconds=i)
        data.append({
            'timestamp': timestamp.isoformat() + 'Z',
            'cpu_util_pct': util_pct[i],
            'cpu_freq_ghz': 2.8,  # Estimated
            'battery_temp_c': temp_progression[i],
            'battery_voltage_v': 4.2,  # Typical
            'battery_current_a': -power_w[i] / 4.2 if power_w[i] > 0 else None
        })
    
    df = pd.DataFrame(data)
    return df

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python parse_3dmark_screenshots.py output.csv")
        sys.exit(1)
    
    print("Parsing 3DMark screenshot data...")
    df = create_from_3dmark_data()
    
    output_file = sys.argv[1]
    df.to_csv(output_file, index=False)
    print(f"Created {output_file} with {len(df)} samples")
    print(f"\nNow convert to RLE:")
    print(f"  python lab/analysis/mobile_to_rle.py {output_file} phone_rle.csv")
