#!/usr/bin/env python3
"""
ADB Logger - Collect sensor data from Android via USB
Run this ON YOUR DESKTOP while phone is connected

Usage:
    python lab/monitoring/adb_logger.py --output phone_data.csv --duration 5
"""

import subprocess
import time
import csv
import sys
from datetime import datetime

def check_adb():
    """Check if phone is connected via ADB"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices_output = result.stdout.strip()
        
        if 'List of devices' in devices_output and len(devices_output.splitlines()) > 1:
            print("✓ Phone connected via ADB")
            print(f"  {devices_output}")
            return True
        else:
            print("✗ No device detected.")
            print("\nTo connect wirelessly:")
            print("  1. On phone: Settings → Developer Options")
            print("  2. Enable 'Wireless debugging'")
            print("  3. Tap 'Pair device with pairing code'")
            print("  4. Run: adb pair [IP]:[PORT] [CODE]")
            print("  5. Then: adb connect [IP]:[PORT]")
            return False
    except FileNotFoundError:
        print("✗ ADB not found. Install Android SDK Platform Tools:")
        print("  https://developer.android.com/studio/releases/platform-tools")
        return False

def sample_battery(duration_minutes=5):
    """Sample battery info via dumpsys"""
    output_file = f"phone_battery_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    print(f"Sampling for {duration_minutes} minutes...")
    print("Run 3DMark on your phone NOW!")
    print(f"Output: {output_file}\n")
    
    end_time = time.time() + (duration_minutes * 60)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'temp_c', 'voltage_v', 'current_ma', 'level_pct', 'status'])
        
        sample_count = 0
        
        while time.time() < end_time:
            try:
                result = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'], 
                                      capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0:
                    # Parse output
                    temp_c = None
                    voltage_mv = None
                    current_ma = None
                    level = None
                    status = None
                    
                    for line in result.stdout.splitlines():
                        if 'temperature:' in line:
                            temp_c = int(line.split(':')[1].strip()) / 10.0
                        elif 'voltage:' in line:
                            voltage_mv = int(line.split(':')[1].strip())
                        elif 'charge counter:' in line:
                            # Not current, but related
                            pass
                        elif 'level:' in line:
                            level = int(line.split(':')[1].strip())
                        elif 'status:' in line:
                            status = line.split(':')[1].strip()
                    
                    timestamp = datetime.now().isoformat() + 'Z'
                    writer.writerow([
                        timestamp,
                        f'{temp_c:.2f}' if temp_c else '',
                        f'{voltage_mv/1000:.3f}' if voltage_mv else '',
                        current_ma if current_ma else '',
                        level if level else '',
                        status if status else ''
                    ])
                    
                    if sample_count % 60 == 0:  # Print every 60 seconds
                        print(f"[{sample_count}s] Temp: {temp_c:.1f}°C, Level: {level}%")
                    
                    sample_count += 1
                    
            except Exception as e:
                print(f"Error: {e}")
            
            time.sleep(1.0)
    
    print(f"\n✓ Collected {sample_count} samples")
    print(f"✓ Saved to: {output_file}")
    print(f"\nNow convert to RLE format:")
    print(f"  python lab/analysis/battery_to_rle.py {output_file} phone_rle.csv")
    return output_file

if __name__ == '__main__':
    if not check_adb():
        sys.exit(1)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=5, help='Duration in minutes')
    args = parser.parse_args()
    
    sample_battery(args.duration)

