#!/usr/bin/env python3
"""
Offline CSV augmentation tool for Micro-Scale addon

Appends F_mu, F_q, F_s, F_p and rle_*_ms columns without modifying existing columns.
Wraps RLE core engine to ensure identical factor computation.

Usage:
  python lab/monitoring/apply_micro_scale.py \
    --in lab/sessions/recent/ANY_SESSION.csv \
    --out out_aug.csv \
    --sensor-lsb 0.2 \
    --power-knee 3.0
"""

from __future__ import annotations
import argparse
from pathlib import Path

# Local import resilient to script execution
try:
    # If running as a module
    from .rle_core import augment_csv
except Exception:
    # If executed directly: adjust import path to project root
    import sys
    from pathlib import Path as _P
    _root = _P(__file__).resolve().parents[2]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from lab.monitoring.rle_core import augment_csv


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Append Micro-Scale factors and *_ms columns to an existing CSV")
    p.add_argument('--in', dest='infile', type=str, required=True, help='Input CSV path')
    p.add_argument('--out', dest='outfile', type=str, required=True, help='Output CSV path')
    p.add_argument('--rated-power', dest='rated_power', type=float, default=100.0, help='Baseline/rated power for A_load normalization (W)')
    p.add_argument('--temp-limit', dest='temp_limit', type=float, default=85.0, help='Thermal limit (°C) used by T_sustain')
    p.add_argument('--sensor-lsb', dest='sensor_lsb', type=float, default=0.1, help='Temperature sensor LSB (°C per tick) for micro-scale correction')
    p.add_argument('--power-knee', dest='power_knee', type=float, default=3.0, help='Low-power granularity knee (W) for micro-scale correction')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_path = Path(args.infile)
    out_path = Path(args.outfile)
    augment_csv(in_path, out_path,
                rated_power_w=args.rated_power,
                temp_limit_c=args.temp_limit,
                enable_micro_scale=True,
                sensor_temp_lsb_c=args.sensor_lsb,
                low_power_knee_w=args.power_knee)
    print(f"Wrote micro-scale augmented CSV → {out_path}")
    print(f"Micro-scale addon: sensor_lsb={args.sensor_lsb}°C, power_knee={args.power_knee}W")


if __name__ == '__main__':
    main()


