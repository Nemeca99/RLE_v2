#!/usr/bin/env python3
"""
Desktop/Laptop regression check for Micro-Scale addon using a single augmented CSV.

Checks (expect pass on desktop):
- F_mu ~ 1 (report mean, p5, p95)
- Mean absolute delta of rle_norm_ms - rle_norm < 0.02
- Collapse parity implied (same original collapse column)

Usage:
  py -3 lab/analysis/desktop_regression_check.py --in lab/sessions/recent/out_aug.csv
"""

from __future__ import annotations
import argparse
import csv
from pathlib import Path


def to_float(v):
    try:
        if v is None: return None
        s = str(v).strip()
        if s == '' or s.lower() == 'none': return None
        return float(s)
    except Exception:
        return None


def ptiles(vals, ps=(5, 50, 95)):
    if not vals:
        return {p: float('nan') for p in ps}
    xs = sorted(vals)
    n = len(xs)
    out = {}
    for p in ps:
        if n == 1:
            out[p] = xs[0]
        else:
            k = (p/100.0) * (n-1)
            f = int(k)
            c = min(f+1, n-1)
            w = k - f
            out[p] = xs[f]*(1-w) + xs[c]*w
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='infile', required=True, help='Augmented CSV with *_ms columns')
    args = ap.parse_args()

    fmus = []
    deltas = []
    with Path(args.infile).open('r', encoding='utf-8', errors='ignore', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            fm = to_float(row.get('F_mu'))
            rn = to_float(row.get('rle_norm'))
            rn_ms = to_float(row.get('rle_norm_ms'))
            if fm is not None:
                fmus.append(fm)
            if rn is not None and rn_ms is not None:
                deltas.append(abs(rn_ms - rn))

    mean_fmu = sum(fmus)/len(fmus) if fmus else float('nan')
    q = ptiles(fmus, ps=(5, 50, 95)) if fmus else {5: float('nan'), 50: float('nan'), 95: float('nan')}
    mean_delta = sum(deltas)/len(deltas) if deltas else float('nan')

    print(f"F_mu: mean={mean_fmu:.4f} p5={q[5]:.4f} p50={q[50]:.4f} p95={q[95]:.4f}")
    print(f"Mean |rle_norm_ms - rle_norm| = {mean_delta:.4f}")
    if mean_delta < 0.02:
        print("PASS: Mean delta < 0.02")
    else:
        print("FAIL: Mean delta >= 0.02")


if __name__ == '__main__':
    main()


