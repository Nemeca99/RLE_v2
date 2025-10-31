#!/usr/bin/env python3
"""
Mobile Sensor Reader for RLE
Works on Android via Termux or Pydroid3

Just run this on your phone to collect sensor data.
"""

import subprocess
import sys
from datetime import datetime
import csv
import time

def get_cpu_usage():
    """Read /proc/stat for CPU utilization"""
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
            parts = line.split()
            if len(parts) < 5:
                return 0.0
            
            user = int(parts[1])
            nice = int(parts[2])
            system = int(parts[3])
            idle = int(parts[4])
            iowait = int(parts[5]) if len(parts) > 5 else 0
            irq = int(parts[6]) if len(parts) > 6 else 0
            softirq = int(parts[7]) if len(parts) > 7 else 0
            
            total = user + nice + system + idle + iowait + irq + softirq
            active = user + nice + system + iowait + irq + softirq
            
            return (active / max(total, 1)) * 100.0
    except:
        return 0.0

def get_cpu_freq():
    """Read CPU frequency in GHz"""
    max_freq = 0.0
    for i in range(8):
        try:
            with open(f'/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq', 'r') as f:
                freq_hz = int(f.readline().strip())
                freq_ghz = freq_hz / 1e9
                if freq_ghz > max_freq:
                    max_freq = freq_ghz
        except:
            pass
    return max_freq if max_freq > 0 else 2.4

def get_battery_temp():
    """Try to get battery temperature in Celsius"""
    temp_milli_c = None
    try:
        result = subprocess.run(['dumpsys', 'battery'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if 'temperature' in line.lower():
                temp_milli_c = int(line.split(':')[1].strip()) / 10.0  # Convert to Celsius
                break
    except:
        pass
    return temp_milli_c

def get_battery_voltage():
    """Get battery voltage in V"""
    try:
        result = subprocess.run(['dumpsys', 'battery'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if 'voltage' in line.lower():
                voltage_mv = int(line.split(':')[1].strip())
                return voltage_mv / 1000.0
    except:
        pass
    return None

def get_battery_current():
    """Get battery current in A (negative = discharging)"""
    try:
        result = subprocess.run(['dumpsys', 'battery'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if 'current' in line.lower():
                current_ma = int(line.split(':')[1].strip())
                return current_ma / 1000.0  # Convert mA to A
    except:
        pass
    return None

def sample_loop(output_file, duration_minutes=5):
    """Sample sensors and write to CSV"""
    import os
    
    # Use Downloads folder so you can find it
    if not '/' in output_file:
        download_path = os.path.join(os.path.expanduser('~'), 'Download')
        if not os.path.exists(download_path):
            download_path = '/sdcard/Download'
        output_file = os.path.join(download_path, output_file)
    
    print(f"Sampling for {duration_minutes} minutes...")
    print(f"Saving to: {output_file}")
    print("Run 3DMark now!")
    
    end_time = time.time() + (duration_minutes * 60)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp', 'cpu_util_pct', 'cpu_freq_ghz',
            'battery_temp_c', 'battery_voltage_v', 'battery_current_a'
        ])
        
        while time.time() < end_time:
            timestamp = datetime.now().isoformat() + 'Z'
            cpu_util = get_cpu_usage()
            cpu_freq = get_cpu_freq()
            battery_temp = get_battery_temp()
            battery_voltage = get_battery_voltage()
            battery_current = get_battery_current()
            
            writer.writerow([
                timestamp, f'{cpu_util:.2f}', f'{cpu_freq:.3f}',
                f'{battery_temp:.2f}' if battery_temp else '',
                f'{battery_voltage:.3f}' if battery_voltage else '',
                f'{battery_current:.3f}' if battery_current else ''
            ])
            
            print(f"Sample: CPU {cpu_util:.1f}% @ {cpu_freq:.2f}GHz, Temp: {battery_temp:.1f}°C" if battery_temp else f"Sample: CPU {cpu_util:.1f}% @ {cpu_freq:.2f}GHz")
            time.sleep(1.0)  # 1 Hz sampling
    
    print(f"\nDone! Data saved to: {output_file}")
    print(f"Transfer to desktop and run:")
    print(f"  python lab/analysis/mobile_to_rle.py {output_file} phone_rle.csv")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=5, help='Sampling duration in minutes')
    parser.add_argument('--output', default='mobile_sensors.csv')
    args = parser.parse_args()
    
    sample_loop(args.output, args.duration)

