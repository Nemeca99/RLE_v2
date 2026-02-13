#!/usr/bin/env python3
"""
RID Invariant Independence Test

Tests ChatGPT's critical validation questions:
1. Are LTP and RSR truly independent dimensions?
2. Is there double-penalization from shared telemetry?
3. Does the degradation surface behave smoothly and predictably?

Test Protocol:
- Hold RLE constant, vary only LTP → observe S_n curvature
- Hold RLE constant, vary only RSR → observe S_n curvature
- Vary two at once → check for interaction effects
- Check for spurious coupling from shared base telemetry

Usage:
    python3 lab/analysis/rid_independence_test.py
"""

import sys
from pathlib import Path
import numpy as np
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / "monitoring"))
from rid_core import RIDCore

# Optional matplotlib import
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Note: matplotlib not available - skipping plot generation")


def test_ltp_independence():
    """
    Test 1: Hold RLE constant, vary only LTP
    
    Checks if LTP is truly independent dimension
    """
    print("=" * 80)
    print("TEST 1: LTP Independence (RLE held constant)")
    print("=" * 80)
    
    rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    
    # Fix utilization to keep RLE roughly constant
    fixed_util = 50.0
    
    # Vary temperature to change LTP (headroom changes)
    # But keep power low to minimize RLE variation
    test_cases = []
    
    for temp in np.linspace(35.0, 83.0, 20):
        # Low power to keep RLE stable
        power = 30.0
        result = rid.compute(fixed_util, temp, power)
        test_cases.append((temp, result.RLE, result.LTP, result.RSR, result.S_n))
    
    print(f"\n{'Temp°C':<8} {'RLE':<8} {'LTP':<8} {'RSR':<8} {'S_n':<8} {'dRLE':<8} {'dLTP':<8} {'dS_n':<8}")
    print("-" * 80)
    
    rle_baseline = test_cases[0][1]
    ltp_baseline = test_cases[0][2]
    sn_baseline = test_cases[0][4]
    
    rle_variation = []
    ltp_variation = []
    sn_variation = []
    
    for temp, rle, ltp, rsr, sn in test_cases:
        d_rle = rle - rle_baseline
        d_ltp = ltp - ltp_baseline
        d_sn = sn - sn_baseline
        
        rle_variation.append(abs(d_rle))
        ltp_variation.append(abs(d_ltp))
        sn_variation.append(abs(d_sn))
        
        print(f"{temp:<8.1f} {rle:<8.3f} {ltp:<8.3f} {rsr:<8.3f} {sn:<8.3f} "
              f"{d_rle:+8.3f} {d_ltp:+8.3f} {d_sn:+8.3f}")
    
    # Analysis
    print("\nAnalysis:")
    print(f"  RLE variation: {max(rle_variation):.4f} (should be small)")
    print(f"  LTP variation: {max(ltp_variation):.4f} (should be large)")
    print(f"  S_n variation: {max(sn_variation):.4f}")
    
    # Check if S_n tracks LTP when RLE is held constant
    if max(rle_variation) < 0.05:  # RLE stayed stable
        print(f"  ✓ RLE held approximately constant (Δ < 0.05)")
        
        # S_n should vary roughly proportionally to LTP
        ltp_range = max(ltp_variation)
        sn_range = max(sn_variation)
        ratio = sn_range / ltp_range if ltp_range > 0 else 0
        
        print(f"  S_n / LTP ratio: {ratio:.3f} (expect ≈ RLE_baseline = {rle_baseline:.3f})")
        
        if abs(ratio - rle_baseline) < 0.1:
            print(f"  ✓ S_n tracks LTP linearly when RLE constant")
        else:
            print(f"  ⚠ Nonlinear coupling detected")
    else:
        print(f"  ⚠ RLE varied too much (Δ = {max(rle_variation):.4f})")
    
    return test_cases


def test_rsr_independence():
    """
    Test 2: Hold RLE constant, vary only RSR
    
    Checks if RSR is truly independent dimension
    """
    print("\n" + "=" * 80)
    print("TEST 2: RSR Independence (RLE held constant)")
    print("=" * 80)
    
    rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0, rsr_window_n=20)
    
    # Create scenario where RSR varies but RLE doesn't
    # By introducing noisy utilization patterns
    
    test_cases = []
    base_util = 50.0
    base_temp = 50.0
    base_power = 50.0
    
    # First, establish baseline with smooth data
    for i in range(10):
        result = rid.compute(base_util, base_temp, base_power)
    
    baseline_result = result
    
    print(f"\n{'Step':<6} {'Noise':<8} {'RLE':<8} {'LTP':<8} {'RSR':<8} {'S_n':<8} {'dRSR':<8} {'dS_n':<8}")
    print("-" * 80)
    
    # Now introduce noise to create reconstruction error (affects RSR)
    noise_levels = np.linspace(0, 15, 20)
    
    for noise_amp in noise_levels:
        # Add noise to utilization (affects RSR via reconstruction error)
        noisy_util = base_util + np.random.uniform(-noise_amp, noise_amp)
        noisy_util = max(0, min(100, noisy_util))
        
        result = rid.compute(noisy_util, base_temp, base_power)
        
        d_rsr = result.RSR - baseline_result.RSR
        d_sn = result.S_n - baseline_result.S_n
        
        test_cases.append((noise_amp, result.RLE, result.LTP, result.RSR, result.S_n))
        
        print(f"{int(noise_amp):<6} {noise_amp:<8.1f} {result.RLE:<8.3f} {result.LTP:<8.3f} "
              f"{result.RSR:<8.3f} {result.S_n:<8.3f} {d_rsr:+8.3f} {d_sn:+8.3f}")
    
    # Analysis
    rle_vals = [x[1] for x in test_cases]
    rsr_vals = [x[3] for x in test_cases]
    sn_vals = [x[4] for x in test_cases]
    
    rle_var = max(rle_vals) - min(rle_vals)
    rsr_var = max(rsr_vals) - min(rsr_vals)
    sn_var = max(sn_vals) - min(sn_vals)
    
    print("\nAnalysis:")
    print(f"  RLE variation: {rle_var:.4f}")
    print(f"  RSR variation: {rsr_var:.4f}")
    print(f"  S_n variation: {sn_var:.4f}")
    
    if rsr_var > 0.1:
        print(f"  ✓ RSR varied with noise injection")
        
        # Check if variation is smooth
        rsr_diffs = [abs(rsr_vals[i+1] - rsr_vals[i]) for i in range(len(rsr_vals)-1)]
        max_jump = max(rsr_diffs)
        avg_jump = sum(rsr_diffs) / len(rsr_diffs)
        
        print(f"  RSR smoothness: avg step = {avg_jump:.4f}, max step = {max_jump:.4f}")
        
        if max_jump < 0.2:
            print(f"  ✓ RSR degradation is smooth (no discontinuities)")
        else:
            print(f"  ⚠ RSR has discontinuities")
    
    return test_cases


def test_shared_telemetry_coupling():
    """
    Test 3: Check for double-penalization from shared telemetry
    
    Examines if LTP and RSR share base signals that create spurious coupling
    """
    print("\n" + "=" * 80)
    print("TEST 3: Shared Telemetry Analysis")
    print("=" * 80)
    
    print("\nBase Telemetry Used:")
    print("-" * 80)
    print("RLE inputs: util_pct, temp_c, power_w")
    print("LTP inputs: temp_c, power_w, fan_speed_pct")
    print("RSR inputs: util_pct, temp_c, power_w")
    print()
    print("Shared signals:")
    print("  - temp_c: Used by RLE, LTP, RSR")
    print("  - power_w: Used by RLE, LTP, RSR")
    print("  - util_pct: Used by RLE, RSR")
    print()
    
    # Test: Does temperature affect all three invariants?
    rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    
    print("Temperature Coupling Test:")
    print(f"{'Temp°C':<8} {'RLE':<8} {'LTP':<8} {'RSR':<8} | {'RLE_chg':<10} {'LTP_chg':<10} {'RSR_chg':<10}")
    print("-" * 80)
    
    baseline = None
    for temp in [40, 50, 60, 70, 80]:
        result = rid.compute(util_pct=50.0, temp_c=temp, power_w=50.0)
        
        if baseline is None:
            baseline = (result.RLE, result.LTP, result.RSR)
            print(f"{temp:<8} {result.RLE:<8.3f} {result.LTP:<8.3f} {result.RSR:<8.3f} | (baseline)")
        else:
            rle_chg = ((result.RLE - baseline[0]) / baseline[0]) * 100
            ltp_chg = ((result.LTP - baseline[1]) / baseline[1]) * 100
            rsr_chg = ((result.RSR - baseline[2]) / baseline[2]) * 100
            
            print(f"{temp:<8} {result.RLE:<8.3f} {result.LTP:<8.3f} {result.RSR:<8.3f} | "
                  f"{rle_chg:+9.1f}% {ltp_chg:+9.1f}% {rsr_chg:+9.1f}%")
    
    print("\nInterpretation:")
    print("  - If all three change together → shared telemetry coupling")
    print("  - If LTP changes independently → headroom calculation is distinct")
    print("  - If RSR stays constant → reconstruction error is independent")


def test_interaction_effects():
    """
    Test 4: Vary two invariants at once
    
    Checks for nonlinear interaction effects
    """
    print("\n" + "=" * 80)
    print("TEST 4: Interaction Effects (Vary LTP + RSR together)")
    print("=" * 80)
    
    rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    
    # Create grid: temperature (affects LTP) × noise (affects RSR)
    temps = [45, 60, 75]
    noise_levels = [0, 5, 10]
    
    print(f"\n{'Temp':<6} {'Noise':<7} | {'RLE':<8} {'LTP':<8} {'RSR':<8} {'S_n':<8} | {'Expected':<10} {'Actual':<10} {'Error':<10}")
    print("-" * 100)
    
    # Establish baseline
    baseline_rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    baseline = baseline_rid.compute(50.0, 45.0, 50.0)
    
    for temp in temps:
        for noise in noise_levels:
            # Reset RID for clean test
            test_rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
            
            # Warm up with baseline
            for _ in range(10):
                test_rid.compute(50.0, 45.0, 50.0)
            
            # Apply temperature change (LTP) and noise (RSR)
            noisy_util = 50.0 + np.random.uniform(-noise, noise)
            result = test_rid.compute(noisy_util, temp, 50.0)
            
            # Expected S_n if purely multiplicative (no interaction)
            expected = result.RLE * result.LTP * result.RSR
            actual = result.S_n
            error = abs(expected - actual)
            
            print(f"{temp:<6} {noise:<7} | {result.RLE:<8.3f} {result.LTP:<8.3f} {result.RSR:<8.3f} "
                  f"{result.S_n:<8.3f} | {expected:<10.6f} {actual:<10.6f} {error:<10.6f}")
    
    print("\nInterpretation:")
    print("  - Error ≈ 0: Pure multiplicative (no interaction)")
    print("  - Error > 0.01: Nonlinear coupling between invariants")


def plot_degradation_surface():
    """
    Generate 2D surface plot of S_n as function of LTP and RSR
    """
    if not HAS_MATPLOTLIB:
        print("\n" + "=" * 80)
        print("Skipping plot generation (matplotlib not available)")
        print("=" * 80)
        return None
    
    print("\n" + "=" * 80)
    print("Generating degradation surface plot...")
    print("=" * 80)
    
    # Create grid of LTP × RSR values
    ltp_range = np.linspace(0.2, 1.0, 30)
    rsr_range = np.linspace(0.5, 1.0, 30)
    
    LTP, RSR = np.meshgrid(ltp_range, rsr_range)
    
    # Assume RLE = 0.5 (held constant)
    RLE = 0.5
    S_n = RLE * LTP * RSR
    
    # Create plot
    fig = plt.figure(figsize=(12, 5))
    
    # 3D surface
    ax1 = fig.add_subplot(121, projection='3d')
    surf = ax1.plot_surface(LTP, RSR, S_n, cmap='viridis', alpha=0.8)
    ax1.set_xlabel('LTP (Structure)')
    ax1.set_ylabel('RSR (Fidelity)')
    ax1.set_zlabel('S_n (Stability)')
    ax1.set_title('RID Degradation Surface (RLE=0.5)')
    fig.colorbar(surf, ax=ax1, shrink=0.5)
    
    # 2D contour
    ax2 = fig.add_subplot(122)
    contour = ax2.contourf(LTP, RSR, S_n, levels=20, cmap='viridis')
    ax2.set_xlabel('LTP (Structure)')
    ax2.set_ylabel('RSR (Fidelity)')
    ax2.set_title('RID Stability Contours (RLE=0.5)')
    fig.colorbar(contour, ax=ax2)
    
    # Add key threshold lines
    ax2.contour(LTP, RSR, S_n, levels=[0.2, 0.4], colors='red', linewidths=2, linestyles='--')
    ax2.text(0.3, 0.95, 'Pre-collapse (S_n=0.4)', color='red')
    ax2.text(0.25, 0.75, 'Emergency (S_n=0.2)', color='red')
    
    plt.tight_layout()
    output_path = Path('/workspace/lab/sessions/archive/plots/rid_degradation_surface.png')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved: {output_path}")
    
    return output_path


def main():
    print("\n" + "=" * 80)
    print("RID INVARIANT INDEPENDENCE TEST")
    print("Validating ChatGPT's Technical Concerns")
    print("=" * 80)
    print()
    print("Testing:")
    print("  1. LTP independence when RLE held constant")
    print("  2. RSR independence when RLE held constant")
    print("  3. Shared telemetry coupling analysis")
    print("  4. Interaction effects between invariants")
    print("  5. Degradation surface smoothness")
    print()
    
    # Run tests
    test_ltp_independence()
    test_rsr_independence()
    test_shared_telemetry_coupling()
    test_interaction_effects()
    plot_degradation_surface()
    
    print("\n" + "=" * 80)
    print("FINAL ASSESSMENT")
    print("=" * 80)
    print()
    print("Key Questions:")
    print("  1. Are LTP and RSR normalized consistently? → Check test output")
    print("  2. Are they independent dimensions? → Check coupling analysis")
    print("  3. Avoiding double-penalization? → Check shared telemetry test")
    print("  4. Is degradation surface smooth? → Check plot + interaction test")
    print()
    print("Next step: Review results and refine normalization if needed.")
    print()


if __name__ == "__main__":
    main()
