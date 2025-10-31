#!/usr/bin/env python3
"""
Compute unified vs original drift and low-power jitter metrics.

Usage:
  py -3 lab/analysis/unified_vs_original_stats.py --in path.csv --device phone
"""

from __future__ import annotations
import argparse
import csv
from pathlib import Path
from statistics import pstdev


def to_float(v):
    try:
        if v is None: return None
        s = str(v).strip()
        if s == '' or s.lower() == 'none': return None
        return float(s)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='infile', required=True)
    ap.add_argument('--device', default='phone')
    args = ap.parse_args()

    p = Path(args.infile)
    rle_norm = []
    rle_norm_uni = []
    power = []
    with p.open('r', encoding='utf-8', errors='ignore', newline='') as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            rn = to_float(row.get('rle_norm'))
            ru = to_float(row.get('rle_norm_uni'))
            pw = to_float(row.get('power_w'))
            if rn is not None and ru is not None:
                rle_norm.append(rn)
                rle_norm_uni.append(ru)
                power.append(pw)

    n = len(rle_norm)
    if n == 0:
        print('No rows with rle_norm and rle_norm_uni')
        return

    mean_delta = sum(abs(u - r) for r, u in zip(rle_norm, rle_norm_uni)) / n

    # Low-power jitter (<5W)
    low_r = [r for r, p in zip(rle_norm, power) if p is not None and p < 5.0]
    low_u = [u for u, p in zip(rle_norm_uni, power) if p is not None and p < 5.0]
    jitter_r = pstdev(low_r) if len(low_r) >= 2 else float('nan')
    jitter_u = pstdev(low_u) if len(low_u) >= 2 else float('nan')
    ratio = (jitter_u / jitter_r) if (isinstance(jitter_r, float) and jitter_r > 0 and isinstance(jitter_u, float)) else float('nan')

    print(f"Mean |rle_norm_uni - rle_norm| = {mean_delta:.4f}")
    print(f"Low-power jitter (core) = {jitter_r if jitter_r==jitter_r else float('nan'):.4f}")
    print(f"Low-power jitter (uni)  = {jitter_u if jitter_u==jitter_u else float('nan'):.4f}")
    print(f"Jitter ratio (uni/core) = {ratio if ratio==ratio else float('nan'):.3f}")


if __name__ == '__main__':
    main()


