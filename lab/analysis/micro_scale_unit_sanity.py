#!/usr/bin/env python3
"""
Micro-Scale addon unit sanity (no hardware)

Checks:
- F_mu(power) monotonic increasing over 0→100 W
- F_mu → 1 for desktop-like power (>50 W)
- F_mu << 1 for phone-like power (<5 W) and rises with power

Outputs plot to sessions/archive/plots/micro_scale_unit.png
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Tuple

import math
import random
import matplotlib.pyplot as plt

from lab.monitoring.rle_core import RLECore


def generate_temp_history(base_c: float, power_w: float, n: int = 8) -> List[float]:
    """
    Create a synthetic temperature history where jitter increases mildly with power.
    This allows F_s to naturally rise toward 1 at higher power while staying small at low power.
    """
    # Jitter amplitude: small at low power, larger at high power
    jitter = 0.02 + 0.003 * power_w  # ~0.17°C at 50W, ~0.32°C at 100W
    hist = []
    t = base_c
    for _ in range(max(n, 5)):
        t += random.uniform(-jitter, jitter)
        hist.append(t)
    return hist


def sweep_fmu(sensor_lsb: float, power_range: Tuple[float, float, int]) -> Tuple[List[float], List[float]]:
    p_lo, p_hi, steps = power_range
    powers = [p_lo + (p_hi - p_lo) * i / (steps - 1) for i in range(steps)]
    core = RLECore(enable_micro_scale=True, sensor_temp_lsb_c=sensor_lsb)
    fmus: List[float] = []
    for p in powers:
        # Refresh synthetic temp history per sample
        core.temp_hist = generate_temp_history(base_c=40.0, power_w=p, n=8)
        F_mu, _, _, _ = core._compute_micro_scale_factor(power_w=p, temp_c=core.temp_hist[-1], dt_s=1.0)
        fmus.append(F_mu)
    return powers, fmus


def assert_monotonic_increasing(values: List[float]) -> None:
    for i in range(1, len(values)):
        if values[i] + 1e-9 < values[i-1]:
            raise AssertionError("F_mu is not monotonically increasing with power")


def main() -> None:
    random.seed(42)
    out_dir = Path('lab/sessions/archive/plots')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / 'micro_scale_unit.png'

    sensor_lsbs = [0.1, 0.2, 0.5]
    power_range = (0.0, 100.0, 201)

    plt.figure(figsize=(8, 5))
    for lsb in sensor_lsbs:
        powers, fmus = sweep_fmu(lsb, power_range)
        # Assertions
        assert_monotonic_increasing(fmus)
        # Convergence check at >50W
        high_idx = [i for i, p in enumerate(powers) if p >= 50.0]
        if high_idx:
            hi_vals = [fmus[i] for i in high_idx]
            if (1.0 - min(hi_vals)) > 0.05:
                raise AssertionError("F_mu does not approach 1 above 50W within 0.05 tolerance")
        # Low-power behavior (<5W)
        low_idx = [i for i, p in enumerate(powers) if p <= 5.0]
        if low_idx:
            lo_vals = [fmus[i] for i in low_idx]
            if not (max(lo_vals) < 0.9 and min(lo_vals) < max(lo_vals)):
                raise AssertionError("F_mu should be well below 1 and rising under 5W")
        # Plot
        plt.plot(powers, fmus, label=f"sensor_lsb={lsb}")

    plt.title('Micro-Scale F_mu vs Power (unit sanity)')
    plt.xlabel('Power (W)')
    plt.ylabel('F_mu')
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png)
    print(f"Saved unit sanity plot → {out_png}")


if __name__ == '__main__':
    main()


