#!/usr/bin/env python3
"""
Extract data from 3DMark screenshots
User will provide the actual values from the screenshots
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_timeline():
    """
    Timeline from screenshots:
    - Screenshot_20251027_154002: Start
    - Screenshot_20251027_161243 through 161351: Regular intervals
    - Screenshot_20251027_161351: End
    
    That's about 33 minutes total
    But Wild Life Extreme is 20 minutes...
    So there might have been some delays or multiple runs.
    
    Let me create a 20-minute data template.
    """
    
    print("Creating 3DMark data template...")
    print("Please provide the following from your screenshots:")
    print("1. Temperature at different time points")
    print("2. Frame rate (FPS) at different time points")
    print()
    
    # Create a placeholder that user can fill in
    # Based on expected Wild Life Extreme behavior:
    # - Starts cool (~32°C), heats up to ~45-50°C
    # - FPS starts high (~50), drops as it heats up (~35-40)
    
    # Let's create a 20-minute timeline at 1 Hz (1200 samples)
    start_time = datetime(2025, 10, 27, 15, 40, 0)  # 3:40 PM
    duration_seconds = 20 * 60  # 20 minutes
    
    data = []
    for i in range(duration_seconds):
        timestamp = start_time + timedelta(seconds=i)
        
        # Placeholder values - WILL BE REPLACED with actual data
        temp_c = 32.0 + (18.0 * i / duration_seconds)  # Ramp from 32°C to 50°C
        fps = 50.0 - (15.0 * i / duration_seconds)    # Drop from 50 FPS to 35 FPS
        
        # Estimate util from FPS (higher FPS = higher load)
        util_pct = 50 + (fps / 100 * 40)  # Rough estimate
        util_pct = max(15, min(95, util_pct))
        
        # Power estimate
        power_w = 3.0 + (util_pct / 100.0 * 7.0)
        
        data.append({
            'timestamp': timestamp.isoformat() + 'Z',
            'cpu_util_pct': util_pct,
            'cpu_freq_ghz': 2.8,
            'battery_temp_c': temp_c,
            'battery_voltage_v': 4.2,
            'battery_current_a': -power_w / 4.2,
        })
    
    df = pd.DataFrame(data)
    
    print(f"Created template with {len(df)} samples")
    print("NOTE: These are PLACEHOLDER values")
    print()
    print("To fill in actual data, run this script with --interactive mode")
    print("or manually edit the CSV with values from screenshots.")
    
    return df

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='../pc/phone_raw_actual.csv', help='Output CSV file')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode to enter data')
    args = parser.parse_args()
    
    if args.interactive:
        print("Interactive mode - enter data from screenshots")
        print("TODO: Implement interactive data entry")
    else:
        df = create_timeline()
        df.to_csv(args.output, index=False)
        print(f"Saved template to: {args.output}")
        print("\nNow you can:")
        print("1. Open the CSV and fill in actual temp/FPS values")
        print("2. OR describe the screenshots to me and I'll update the script")
        print()
        print("Once filled, convert to RLE:")
        print(f"  python mobile_to_rle.py {args.output} phone_rle_actual.csv")

