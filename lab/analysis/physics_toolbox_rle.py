#!/usr/bin/env python3
"""
Physics Toolbox Sensor Suite → RLE Converter

Reads CSV exported from Physics Toolbox Sensor Suite (Android)
and converts it to RLE format compatible with rle_comprehensive_timeline.py

This lets you use your paid sensor suite instead of building custom Android app.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

def compute_rle_from_physics_toolbox(csv_path, output_path):
    """
    Convert Physics Toolbox CSV to RLE-compatible format.
    
    Expected Physics Toolbox columns (may vary by export type):
    - Time, CPU Usage, CPU Frequency, Battery Temp, Battery Voltage, Battery Current
    - Or similar variants
    
    Outputs RLE-compatible CSV with:
    - timestamp, device, rle_smoothed, rle_raw, rle_norm, E_th, E_pw, etc.
    """
    
    # Read Physics Toolbox CSV
    df = pd.read_csv(csv_path)
    
    # Detect column names (Physics Toolbox uses varying names)
    time_col = None
    cpu_util_col = None
    cpu_freq_col = None
    batt_temp_col = None
    batt_volt_col = None
    batt_curr_col = None
    
    # Fuzzy matching for column names
    for col in df.columns:
        col_lower = col.lower()
        if 'time' in col_lower or 'timestamp' in col_lower:
            time_col = col
        elif 'cpu' in col_lower and 'usage' in col_lower or 'utilization' in col_lower:
            cpu_util_col = col
        elif 'cpu' in col_lower and 'freq' in col_lower or 'frequency' in col_lower:
            cpu_freq_col = col
        elif 'battery' in col_lower and 'temp' in col_lower:
            batt_temp_col = col
        elif 'battery' in col_lower and ('volt' in col_lower or 'voltage' in col_lower):
            batt_volt_col = col
        elif 'battery' in col_lower and ('curr' in col_lower or 'current' in col_lower):
            batt_curr_col = col
    
    # Report what we found
    print(f"Found columns:")
    print(f"  Time: {time_col}")
    print(f"  CPU Util: {cpu_util_col}")
    print(f"  CPU Freq: {cpu_freq_col}")
    print(f"  Battery Temp: {batt_temp_col}")
    print(f"  Battery Voltage: {batt_volt_col}")
    print(f"  Battery Current: {batt_curr_col}")
    print()
    
    if not cpu_util_col or not batt_temp_col:
        print("ERROR: Missing required columns (CPU usage and battery temp)")
        print(f"Available columns: {list(df.columns)}")
        return False
    
    # Compute derived metrics
    # 1. Parse timestamps
    if time_col:
        try:
            df['timestamp'] = pd.to_datetime(df[time_col])
        except:
            # If parsing fails, create synthetic timestamps
            df['timestamp'] = pd.date_range(start='2025-01-01', periods=len(df), freq='1s')
    else:
        df['timestamp'] = pd.date_range(start='2025-01-01', periods=len(df), freq='1s')
    
    # 2. CPU utilization (%)
    util_pct = df[cpu_util_col].fillna(0.0) * 100  # Convert to percentage if needed
    
    # 3. Battery temperature (°C)
    temp_c = df[batt_temp_col].fillna(method='ffill').fillna(40.0)  # Default 40°C
    
    # 4. Power estimate (W)
    power_w = None
    if batt_volt_col and batt_curr_col:
        voltage = df[batt_volt_col].fillna(3.8)  # Default voltage
        current = df[batt_curr_col].fillna(0.0)  # mA or A
        # Physics Toolbox might use mA, convert to A if needed
        if df[batt_curr_col].abs().max() > 10:  # Probably in mA
            current = current / 1000.0
        power_w = voltage * current.abs()
    
    # 5. CPU frequency (GHz)
    cpu_freq_ghz = None
    if cpu_freq_col:
        freq_hz = df[cpu_freq_col].fillna(2.4e9)  # Default big core freq
        # Convert Hz to GHz
        cpu_freq_ghz = freq_hz / 1e9
    else:
        cpu_freq_ghz = pd.Series(2.4, index=df.index)  # Default
    
    # Compute RLE components
    # This is the same computation as hardware_monitor.py
    
    # 6. Stability (inverse of jitter in utilization)
    util_rolling = util_pct.rolling(window=10, min_periods=5)
    jitter = util_rolling.std().fillna(0.0)
    stability = 1.0 / (1.0 + jitter)
    
    # 7. Load factor (α)
    if power_w is not None:
        rated_power = 8.0  # S24 baseline gaming power
        a_load = power_w / rated_power
    else:
        # Fallback: estimate from CPU utilization
        a_load = util_pct / 100.0 * 1.2
    
    # 8. Sustainability time (τ)
    # Rate of temperature change
    temp_diff = temp_c.diff().fillna(0.0)  # dT/dt ≈ dT (since dt=1s)
    temp_rate = temp_diff.clip(lower=0.01)  # Avoid division by zero
    
    # Time until thermal limit
    temp_limit = 80.0  # Mobile SoC thermal limit
    t_sustain = (temp_limit - temp_c) / temp_rate
    t_sustain = t_sustain.clip(lower=1.0, upper=600.0)
    
    # 9. Raw RLE
    util = util_pct / 100.0
    denominator = a_load * (1.0 + 1.0 / t_sustain)
    rle_raw = (util * stability) / denominator
    
    # 10. Smoothed RLE (5-sample rolling average)
    rle_smoothed = rle_raw.rolling(window=5, min_periods=1).mean()
    
    # 11. Normalized RLE (0-1 range)
    # Same normalization as hardware_monitor.py
    rle_norm = (rle_smoothed / 4.0).clip(0.0, 1.0)  # Rough normalization
    
    # 12. Split efficiency components
    E_th = stability / (1.0 + 1.0 / t_sustain)
    E_pw = util / a_load
    
    # 13. Rolling peak (for collapse detection)
    rolling_peak = rle_smoothed.expanding().max()
    
    # 14. Collapse detection
    collapse_threshold = 0.65 * rolling_peak
    is_collapsed = (rle_smoothed < collapse_threshold).astype(int)
    
    # 15. Alerts
    alerts = []
    for idx in df.index:
        alert_list = []
        if temp_c.iloc[idx] > 50:
            alert_list.append("BATTERY_TEMP_HIGH")
        if a_load.iloc[idx] > 1.1:
            alert_list.append("POWER_LIMIT")
        alerts.append("|".join(alert_list) if alert_list else "")
    
    # 16. Cycles per joule (optional)
    cycles_per_joule = None
    if power_w is not None:
        # cycles_per_joule = (freq_GHz * 1e9 cycles/sec) / (power_W joules/sec)
        cycles_per_joule = (cpu_freq_ghz * 1e9) / power_w
        # Handle division by zero
        cycles_per_joule = cycles_per_joule.replace([np.inf, -np.inf], np.nan)
    
    # Create output DataFrame
    output_df = pd.DataFrame({
        'timestamp': df['timestamp'],
        'device': 'mobile',
        'rle_smoothed': rle_smoothed,
        'rle_raw': rle_raw,
        'rle_norm': rle_norm,
        'E_th': E_th,
        'E_pw': E_pw,
        'temp_c': temp_c,
        'vram_temp_c': '',
        'power_w': power_w if power_w is not None else '',
        'util_pct': util_pct,
        'a_load': a_load,
        't_sustain_s': t_sustain,
        'fan_pct': '',
        'rolling_peak': rolling_peak,
        'collapse': is_collapsed,
        'alerts': alerts,
        'cpu_freq_ghz': cpu_freq_ghz,
        'cycles_per_joule': cycles_per_joule if cycles_per_joule is not None else ''
    })
    
    # Format timestamp as ISO UTC
    output_df['timestamp'] = output_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    # Write output CSV
    output_df.to_csv(output_path, index=False)
    
    # Print summary
    print(f"Converted {len(df)} samples to RLE format")
    print(f"Output: {output_path}")
    print(f"\nSummary statistics:")
    print(f"  Mean RLE (smoothed): {rle_smoothed.mean():.4f}")
    print(f"  Peak temperature: {temp_c.max():.1f}°C")
    print(f"  Collapse events: {is_collapsed.sum()} ({100*is_collapsed.sum()/len(df):.1f}%)")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python physics_toolbox_rle.py <physics_toolbox_csv> [output_csv]")
        print()
        print("Converts Physics Toolbox Sensor Suite CSV to RLE-compatible format.")
        print("Then analyze with: python rle_comprehensive_timeline.py <output_csv>")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else input_csv.replace('.csv', '_rle.csv')
    
    print(f"Converting Physics Toolbox CSV to RLE format...")
    print(f"Input: {input_csv}")
    print(f"Output: {output_csv}")
    print()
    
    success = compute_rle_from_physics_toolbox(input_csv, output_csv)
    
    if success:
        print()
        print("Next steps:")
        print(f"  python rle_comprehensive_timeline.py {output_csv}")

if __name__ == "__main__":
    main()

