#!/usr/bin/env python3
"""
Convert mobile sensor CSV to RLE format
"""

import pandas as pd
import sys

def convert(infile, outfile):
    df = pd.read_csv(infile)
    
    # Compute RLE
    util_pct = df['cpu_util_pct']
    temp_c = pd.to_numeric(df['battery_temp_c'], errors='coerce').fillna(40.0)
    freq_ghz = df['cpu_freq_ghz']
    
    # Power estimate
    voltage = pd.to_numeric(df['battery_voltage_v'], errors='coerce')
    current = pd.to_numeric(df['battery_current_a'], errors='coerce')
    power_w = None
    if voltage.notna().any() and current.notna().any():
        power_w = (voltage * current.abs()).fillna(0.0)
    else:
        # Mobile SoC: 3W idle, 4-10W typical load
        # Base 3W + dynamic 7W at 100% util
        power_w = 3.0 + (util_pct / 100.0 * 7.0)
    
    # RLE computation
    util = util_pct / 100.0
    jitter = util_pct.rolling(10).std().fillna(0.0)
    stability = 1.0 / (1.0 + jitter)
    
    # Load factor (mobile baseline: 5W)
    a_load = power_w / 5.0  # Baseline 5W for mobile SoC
    
    # Sustainability
    temp_rate = temp_c.diff().clip(lower=0.01)
    t_sustain = (80.0 - temp_c) / temp_rate.clip(lower=0.01)
    t_sustain = t_sustain.clip(1.0, 600.0)
    
    # RLE
    denominator = a_load * (1.0 + 1.0 / t_sustain)
    rle_raw = (util * stability) / denominator
    rle_smoothed = rle_raw.rolling(5).mean()
    rle_norm = (rle_smoothed / 4.0).clip(0.0, 1.0)
    
    # Efficiency components
    E_th = stability / (1.0 + 1.0 / t_sustain)
    E_pw = util / a_load
    
    # Collapse detection
    rolling_peak = rle_smoothed.expanding().max()
    collapse = (rle_smoothed < 0.65 * rolling_peak).astype(int)
    
    # Alerts
    alerts = []
    for idx in df.index:
        alert = []
        if temp_c.iloc[idx] > 50:
            alert.append("BATTERY_TEMP_HIGH")
        if a_load.iloc[idx] > 1.1:
            alert.append("POWER_LIMIT")
        alerts.append("|".join(alert))
    
    # Output
    out_df = pd.DataFrame({
        'timestamp': df['timestamp'],
        'device': 'mobile',
        'rle_smoothed': rle_smoothed,
        'rle_raw': rle_raw,
        'rle_norm': rle_norm,
        'E_th': E_th,
        'E_pw': E_pw,
        'temp_c': temp_c,
        'vram_temp_c': '',
        'power_w': power_w,
        'util_pct': util_pct,
        'a_load': a_load,
        't_sustain_s': t_sustain,
        'fan_pct': '',
        'rolling_peak': rolling_peak,
        'collapse': collapse,
        'alerts': alerts,
        'cpu_freq_ghz': freq_ghz,
        'cycles_per_joule': (freq_ghz * 1e9 / power_w) if power_w.notna().any() else ''
    })
    
    out_df.to_csv(outfile, index=False)
    print(f"Converted {len(df)} samples")
    print(f"Saved to: {outfile}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python mobile_to_rle.py input.csv output.csv")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])

