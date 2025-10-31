#!/usr/bin/env python3
"""
Micro-Scale A/B quantitative checks

Usage:
  python lab/analysis/micro_scale_ab_stats.py --off path/phone_off.csv --on path/phone_on.csv --device phone

Outputs a markdown report with:
- Collapse rate comparison
- corr(F_mu, power_w) on ON run
- KS-test on low-power (<5W) OFF rle_norm vs ON rle_norm_ms; high-power (>=5W) parity
"""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import Tuple

import csv
import math


def read_rows(path: Path):
    with path.open('r', encoding='utf-8', errors='ignore', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def to_float(v):
    try:
        if v is None: return None
        s = str(v).strip()
        if s == '' or s.lower() == 'none': return None
        return float(s)
    except Exception:
        return None


def pearson_corr(xs, ys) -> float:
    xs = [x for x in xs]
    ys = [y for y in ys]
    n = min(len(xs), len(ys))
    if n == 0:
        return float('nan')
    xs = xs[:n]; ys = ys[:n]
    mx = sum(xs)/n; my = sum(ys)/n
    num = sum((x-mx)*(y-my) for x,y in zip(xs, ys))
    denx = math.sqrt(sum((x-mx)**2 for x in xs))
    deny = math.sqrt(sum((y-my)**2 for y in ys))
    if denx == 0 or deny == 0:
        return float('nan')
    return num/(denx*deny)


def ecdf(vals):
    vals = sorted(vals)
    n = len(vals)
    def F(x):
        import bisect
        return bisect.bisect_right(vals, x)/n
    return F


def ks_test(a, b) -> Tuple[float, float]:
    """Return (D, p_approx). p-value approximation via asymptotic formula."""
    import math
    if len(a) == 0 or len(b) == 0:
        return float('nan'), float('nan')
    Fa = ecdf(a); Fb = ecdf(b)
    xs = sorted(set(a+b))
    D = max(abs(Fa(x)-Fb(x)) for x in xs)
    n1 = len(a); n2 = len(b)
    ne = n1*n2/(n1+n2)
    # Asymptotic p-value (Massey 1951)
    lam = (math.sqrt(ne) + 0.12 + 0.11/math.sqrt(ne)) * D
    # Smirnov approximation
    p = 2*sum((-1)**(k-1)*math.exp(-2*(lam**2)*(k**2)) for k in range(1, 101))
    p = max(0.0, min(1.0, p))
    return D, p


def load_series(path: Path):
    power = []
    rle_norm = []
    rle_norm_ms = []
    collapse = []
    fmu = []
    for row in read_rows(path):
        pw = to_float(row.get('power_w'))
        rn = to_float(row.get('rle_norm'))
        rn_ms = to_float(row.get('rle_norm_ms'))
        col = row.get('collapse')
        col_i = 0
        try:
            col_i = int(str(col).strip()) if col is not None and str(col).strip() != '' else 0
        except Exception:
            col_i = 0
        fm = to_float(row.get('F_mu'))
        if pw is not None:
            power.append(pw)
        if rn is not None:
            rle_norm.append(rn)
        if rn_ms is not None:
            rle_norm_ms.append(rn_ms)
        collapse.append(col_i)
        if fm is not None:
            fmu.append(fm)
    return power, rle_norm, rle_norm_ms, collapse, fmu


def main():
    ap = argparse.ArgumentParser(description='A/B stats for Micro-Scale addon')
    ap.add_argument('--off', required=True, help='OFF CSV path')
    ap.add_argument('--on', required=True, help='ON CSV path (with micro-scale columns)')
    ap.add_argument('--device', default='phone', help='Device label for report')
    args = ap.parse_args()

    off_p, off_rn, _, off_col, _ = load_series(Path(args.off))
    on_p, on_rn, on_rn_ms, on_col, on_fmu = load_series(Path(args.on))

    # Collapse rates
    off_collapse_rate = (sum(off_col) / max(len(off_col), 1)) * 100.0
    on_collapse_rate = (sum(on_col) / max(len(on_col), 1)) * 100.0

    # Correlation on ON run
    corr_fmu_power = pearson_corr(on_fmu, [p for p in on_p[:len(on_fmu)]]) if on_fmu else float('nan')

    # Low/high power slices
    def slice_vals(pows, vals, low=True):
        out = []
        for p, v in zip(pows, vals):
            if v is None: continue
            if low and p is not None and p < 5.0:
                out.append(v)
            if not low and p is not None and p >= 5.0:
                out.append(v)
        return out

    off_low = slice_vals(off_p, off_rn, low=True)
    on_low = slice_vals(on_p, on_rn_ms if on_rn_ms else on_rn, low=True)
    off_high = slice_vals(off_p, off_rn, low=False)
    on_high = slice_vals(on_p, on_rn_ms if on_rn_ms else on_rn, low=False)

    D_low, p_low = ks_test(off_low, on_low)
    D_high, p_high = ks_test(off_high, on_high)

    # Report
    report_dir = Path('lab/sessions/archive/reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    out_md = report_dir / 'ab_micro_scale_report.md'
    with out_md.open('w', encoding='utf-8') as f:
        f.write(f"# Micro-Scale A/B Report ({args.device})\n\n")
        f.write("## Collapse Rates\n")
        f.write(f"- OFF collapse rate: {off_collapse_rate:.2f}%\n")
        f.write(f"- ON  collapse rate: {on_collapse_rate:.2f}%\n\n")
        f.write("## Correlation (ON run)\n")
        f.write(f"- corr(F_mu, power_w) = {corr_fmu_power:.3f}\n\n")
        f.write("## KS-Test (RLE_norm)\n")
        f.write(f"- Low power <5W: D={D_low:.3f}, p≈{p_low:.3f}\n")
        f.write(f"- High power ≥5W: D={D_high:.3f}, p≈{p_high:.3f}\n\n")
        f.write("Notes: ON uses rle_norm_ms when available; falls back to rle_norm.\n")
    print(f"Wrote A/B report → {out_md}")


if __name__ == '__main__':
    main()


