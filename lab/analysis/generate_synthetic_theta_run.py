#!/usr/bin/env python3
"""
Generate a synthetic 1-hour CSV (fast, not real-time) to exercise θ-clock and micro-scale.

Outputs: sessions/recent/synth_hour.csv
Includes occasional dt gaps and quantized temperature segments.
"""
import csv
from pathlib import Path
from datetime import datetime, timedelta
import random

OUT = Path('sessions/recent/synth_hour.csv')

random.seed(42)
start = datetime(2025, 10, 31, 0, 0, 0)
rows = []

# Build 3600 samples nominally at 1 Hz, with a few injected gaps
current = start
util = 35.0
power = 30.0
temp = 45.0

# Gaps at indices
gap_indices = {600: 8.0, 1800: 5.0}  # seconds to skip
quantize_segments = range(2400, 2700)  # quantized temp here

for i in range(3600):
    # Simulate simple workload pattern
    if 300 <= i < 1200:
        util = min(90.0, util + 0.2)
        power = min(120.0, power + 0.3)
    elif 1200 <= i < 1800:
        util = max(50.0, util - 0.1)
        power = max(60.0, power - 0.15)
    elif 1800 <= i < 2400:
        util = min(85.0, util + 0.15)
        power = min(110.0, power + 0.2)
    else:
        util = max(30.0, util - 0.1)
        power = max(25.0, power - 0.1)

    # Temperature rises slowly with power, then breathes
    temp += 0.02 + 0.0005 * power + 0.02 * (1 if (i//200)%2==0 else -1)
    if i in quantize_segments:
        # Quantize to 0.5 C to test F_s
        temp = round(temp * 2.0) / 2.0

    ts_iso = current.replace(tzinfo=None).isoformat() + 'Z'
    rows.append([ts_iso, 'cpu', f"{util:.2f}", f"{temp:.2f}", f"{power:.2f}"])

    # Advance time; inject occasional gap
    step = 1.0
    if i in gap_indices:
        step = gap_indices[i]
    current += timedelta(seconds=step)

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['timestamp','device','util_pct','temp_c','power_w'])
    w.writerows(rows)

print(f"Wrote synthetic 1-hour CSV → {OUT}")
