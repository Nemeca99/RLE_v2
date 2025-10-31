#!/usr/bin/env python3
"""
Theta Clock Validation & Plots (append-only outputs)

Generates a single-page figure and a small text summary with:
- T0_s vs time, dtheta vs time, theta_index vs time
- F_mu vs power_w (when available)
- log_Gamma vs log(power_w) (when available)
- Histograms: T_sustain_hat; rle_norm vs rle_norm_ms (if ms present)
- Marks theta_gap positions if present

Usage:
  python lab/analysis/theta_plots.py --in sessions/recent/some.csv --outdir sessions/archive/plots

No code changes to monitor required. This script reads existing CSVs.
"""

from __future__ import annotations
import argparse
from pathlib import Path
import csv
import math
from typing import List, Dict, Optional

import matplotlib
matplotlib.use('Agg')  # headless
import matplotlib.pyplot as plt


def read_rows(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open('r', encoding='utf-8', errors='ignore', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def to_float(v: Optional[str]) -> Optional[float]:
    try:
        if v is None: return None
        s = str(v).strip()
        if s == '' or s.lower() == 'none': return None
        return float(s)
    except Exception:
        return None


def ks_test(a: List[float], b: List[float]) -> float:
    a = sorted(x for x in a if math.isfinite(x))
    b = sorted(x for x in b if math.isfinite(x))
    if not a or not b: return float('nan')
    import bisect
    xs = sorted(set(a+b))
    def F(vals, x):
        return bisect.bisect_right(vals, x)/len(vals)
    D = max(abs(F(a,x)-F(b,x)) for x in xs)
    return D


def main() -> None:
    ap = argparse.ArgumentParser(description='Theta clock validation plots')
    ap.add_argument('--in', dest='infile', required=True, help='Input CSV with theta fields (augmenter output)')
    ap.add_argument('--outdir', dest='outdir', default='sessions/archive/plots', help='Output directory for plots')
    args = ap.parse_args()

    in_path = Path(args.infile)
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(in_path)
    if not rows:
        print('No data rows found.')
        return

    # Extract series
    t0s: List[float] = []
    theta_idx: List[float] = []
    tsus_hat: List[float] = []
    theta_gap: List[int] = []
    power_w: List[float] = []
    dthetas: List[float] = []
    rle_norm: List[float] = []
    rle_norm_ms: List[float] = []
    gamma_log: List[float] = []

    prev_ts_val: Optional[float] = None
    for row in rows:
        t0 = to_float(row.get('T0_s'))
        th = to_float(row.get('theta_index'))
        ths = to_float(row.get('T_sustain_hat'))
        gap = row.get('theta_gap')
        pw = to_float(row.get('power_w'))
        rn = to_float(row.get('rle_norm'))
        rn_ms = to_float(row.get('rle_norm_ms'))
        lg = to_float(row.get('log_Gamma'))

        if t0 is not None: t0s.append(t0)
        if th is not None: theta_idx.append(th)
        if ths is not None: tsus_hat.append(ths)
        theta_gap.append(int(str(gap).strip())) if gap is not None and str(gap).strip() != '' else theta_gap.append(0)
        if pw is not None: power_w.append(pw)
        if rn is not None: rle_norm.append(rn)
        if rn_ms is not None: rle_norm_ms.append(rn_ms)
        if lg is not None: gamma_log.append(lg)

    # dtheta estimate from consecutive theta_index
    for x, y in zip(theta_idx, theta_idx[1:]):
        dthetas.append(y - x)

    # Figure
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 3)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(t0s, lw=1.2)
    ax1.set_title('T0_s vs time')
    ax1.set_ylabel('T0_s (s)')

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(dthetas, lw=1.2)
    ax2.set_title('dtheta vs time (Δθ)')
    ax2.set_ylabel('Δθ per tick')

    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(theta_idx, lw=1.2)
    ax3.set_title('theta_index (cumulative)')
    ax3.set_ylabel('θ')

    ax4 = fig.add_subplot(gs[1, 0])
    # Micro-scale scatter
    if power_w and rle_norm:
        # F_mu only present if ms path used
        # Approximate F_mu from rle_raw_ms/rle_raw_ms when available would require raw; here plot log_Gamma behavior
        ax4.scatter(power_w[:len(gamma_log)], gamma_log[:len(power_w)], s=10, alpha=0.6)
        ax4.set_xlabel('power_w')
        ax4.set_ylabel('log_Gamma')
        ax4.set_title('log_Gamma vs power_w')
    else:
        ax4.text(0.1, 0.5, 'No power/log_Gamma data', transform=ax4.transAxes)
        ax4.axis('off')

    ax5 = fig.add_subplot(gs[1, 1])
    if rle_norm and rle_norm_ms:
        ax5.hist(rle_norm, bins=20, alpha=0.6, label='rle_norm')
        ax5.hist(rle_norm_ms, bins=20, alpha=0.6, label='rle_norm_ms')
        ax5.legend()
        ax5.set_title('RLE distributions (core vs ms)')
    else:
        ax5.text(0.1, 0.5, 'No *_ms path present', transform=ax5.transAxes)
        ax5.axis('off')

    ax6 = fig.add_subplot(gs[1, 2])
    ax6.hist([x for x in tsus_hat if math.isfinite(x)], bins=20, alpha=0.8)
    ax6.set_title('Histogram: T_sustain_hat')

    ax7 = fig.add_subplot(gs[2, :])
    ax7.plot(t0s, lw=1.0, label='T0_s')
    # Mark gaps if any
    for i, g in enumerate(theta_gap):
        if g == 1:
            ax7.axvline(i, color='r', alpha=0.2)
    ax7.set_title('T0_s with gap markers (red)')
    ax7.legend(loc='upper right')

    fig.tight_layout()
    out_png = out_dir / f"theta_plots_{in_path.stem}.png"
    fig.savefig(out_png, dpi=120)
    print(f"Wrote plots → {out_png}")

    # Simple text summary
    out_md = out_dir / f"theta_summary_{in_path.stem}.txt"
    with out_md.open('w', encoding='utf-8') as f:
        def mean(xs):
            xs = [x for x in xs if math.isfinite(x)]
            return sum(xs)/len(xs) if xs else float('nan')
        def stdev(xs):
            xs = [x for x in xs if math.isfinite(x)]
            if len(xs) < 2: return 0.0
            m = mean(xs)
            return (sum((x-m)*(x-m) for x in xs)/len(xs))**0.5
        f.write(f"T0_s mean={mean(t0s):.3f} stdev={stdev(t0s):.3f}\n")
        f.write(f"dtheta mean={mean(dthetas):.6f} stdev={stdev(dthetas):.6f}\n")
        f.write(f"theta_index final={theta_idx[-1] if theta_idx else float('nan'):.6f}\n")
        f.write(f"theta_gap count={sum(1 for x in theta_gap if x==1)}\n")
        if gamma_log:
            f.write(f"log_Gamma mean={mean(gamma_log):.3f}\n")
    print(f"Wrote summary → {out_md}")


if __name__ == '__main__':
    main()


