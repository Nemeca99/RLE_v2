#!/usr/bin/env python3
"""
Fix phone RLE with better mobile power estimation
"""

import pandas as pd

# Read raw phone data
df = pd.read_csv('pc/phone_raw.csv')

# Better power model for Snapdragon/Exynos
# Mobile SoCs: 2-4W idle, 6-10W gaming, 12-15W peak
util = df['cpu_util_pct'] / 100.0
power_w = 3.0 + (util * 9.0)  # 3W base + 9W dynamic
df['power_w'] = power_w

# Recompute RLE with correct power
util_vals = util.values
jitter = pd.Series(util_vals).rolling(10).std().fillna(0.0)
stability = 1.0 / (1.0 + jitter * 100)  # Adjust scale
a_load = power_w / 8.0  # Baseline 8W

# Temp rate
temp_c = df['battery_temp_c']
temp_rate = temp_c.diff().clip(lower=0.001)
t_sustain = (50.0 - temp_c) / temp_rate.clip(lower=0.001)
t_sustain = t_sustain.clip(1.0, 600.0)

# RLE
denominator = a_load * (1.0 + 1.0 / t_sustain)
rle_raw = (util * stability) / denominator
rle_smoothed = rle_raw.rolling(5).mean()

# Output
out_df = pd.DataFrame({
    'timestamp': df['timestamp'],
    'device': 'mobile',
    'rle_smoothed': rle_smoothed,
    'rle_raw': rle_raw,
    'temp_c': temp_c,
    'power_w': power_w,
    'util_pct': df['cpu_util_pct'],
    'a_load': a_load,
    't_sustain_s': t_sustain
})

out_df.to_csv('pc/phone_rle_fixed.csv', index=False)
print(f"Fixed phone RLE: {len(out_df)} samples")

# Stats
print(f"\nStats:")
print(f"  RLE range: {rle_smoothed.min():.2f} - {rle_smoothed.max():.2f}")
print(f"  Avg temp: {temp_c.mean():.1f}°C")
print(f"  Temp range: {temp_c.min():.1f}°C - {temp_c.max():.1f}°C")
print(f"  Avg util: {util.mean()*100:.1f}%")
print(f"  Avg power: {power_w.mean():.1f}W")

