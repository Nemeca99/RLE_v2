#!/usr/bin/env python3
"""
RID Orthogonality Test - ChatGPT's Critical Diagnostic

Tests if RLE and LTP are truly orthogonal failure modes or the same signal in disguise.

Test Protocol (ChatGPT's suggestion):
1. Efficiency Isolation: Hold thermal constant, vary workload
   → RLE should drop (efficiency penalty)
   → LTP should remain stable (structure unchanged)

2. Structural Isolation: Hold workload constant, vary cooling capacity
   → LTP should drop faster (capacity reduction)
   → RLE should remain more stable (efficiency less affected)

If we can separate them experimentally → orthogonal (feature)
If they always move together → coupled (bug)

Usage:
    python3 lab/analysis/rid_orthogonality_test.py
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "monitoring"))
from rid_core import RIDCore


def test_efficiency_isolation():
    """
    Test A: Efficiency Isolation
    
    Hold temperature constant, vary workload intensity
    
    Expected if orthogonal:
    - RLE drops (workload affects efficiency)
    - LTP stays stable (headroom unchanged)
    
    Expected if coupled:
    - Both drop together
    """
    print("=" * 100)
    print("TEST A: EFFICIENCY ISOLATION (Hold thermal constant, vary workload)")
    print("=" * 100)
    print()
    print("Protocol:")
    print("  - Fix temperature at 60°C (mid-range, ample headroom)")
    print("  - Fix power at 50W (to isolate utilization effects)")
    print("  - Vary utilization from 20% → 95% (workload ramp)")
    print()
    print("Expected if orthogonal:")
    print("  ✓ RLE should drop (efficiency penalty from high util)")
    print("  ✓ LTP should remain stable (headroom unchanged)")
    print()
    
    rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    
    # Fixed thermal state
    fixed_temp = 60.0
    fixed_power = 50.0
    
    # Vary utilization (workload intensity)
    util_range = [20, 30, 40, 50, 60, 70, 80, 90, 95]
    
    print(f"{'Util%':<8} {'RLE':<8} {'LTP':<8} {'RSR':<8} {'S_n':<8} | {'dRLE':<8} {'dLTP':<8} {'Ratio':<10}")
    print("-" * 100)
    
    baseline = None
    results = []
    
    for util in util_range:
        result = rid.compute(util, fixed_temp, fixed_power)
        
        if baseline is None:
            baseline = (result.RLE, result.LTP, result.RSR, result.S_n)
            print(f"{util:<8} {result.RLE:<8.3f} {result.LTP:<8.3f} {result.RSR:<8.3f} {result.S_n:<8.3f} | (baseline)")
        else:
            d_rle = result.RLE - baseline[0]
            d_ltp = result.LTP - baseline[1]
            
            # Ratio of changes (should be >> 1 if RLE drops more than LTP)
            ratio = abs(d_rle) / abs(d_ltp) if abs(d_ltp) > 0.001 else float('inf')
            
            print(f"{util:<8} {result.RLE:<8.3f} {result.LTP:<8.3f} {result.RSR:<8.3f} {result.S_n:<8.3f} | "
                  f"{d_rle:+8.3f} {d_ltp:+8.3f} {ratio:<10.2f}")
        
        results.append((util, result.RLE, result.LTP, result.RSR, result.S_n))
    
    # Analysis
    rle_vals = [r[1] for r in results]
    ltp_vals = [r[2] for r in results]
    
    rle_range = max(rle_vals) - min(rle_vals)
    ltp_range = max(ltp_vals) - min(ltp_vals)
    
    print()
    print("Analysis:")
    print(f"  RLE variation: {rle_range:.3f} (should be large)")
    print(f"  LTP variation: {ltp_range:.3f} (should be small)")
    print(f"  Variation ratio (RLE/LTP): {rle_range/ltp_range if ltp_range > 0.001 else float('inf'):.2f}")
    print()
    
    if ltp_range < 0.05:
        print("  ✅ LTP remained stable (< 0.05 variation)")
        print("  ✅ Thermal isolation successful")
    else:
        print(f"  ⚠️ LTP varied significantly ({ltp_range:.3f})")
        print("  ⚠️ Workload affects structure (unexpected)")
    
    if rle_range > 0.2:
        print("  ✅ RLE responded to workload (> 0.2 variation)")
    else:
        print("  ⚠️ RLE did not respond significantly")
    
    return results


def test_structural_isolation():
    """
    Test B: Structural Isolation
    
    Hold workload constant, artificially reduce cooling capacity
    
    Expected if orthogonal:
    - LTP drops faster (capacity reduction)
    - RLE remains more stable (efficiency less affected)
    
    Expected if coupled:
    - Both drop together proportionally
    """
    print("\n" + "=" * 100)
    print("TEST B: STRUCTURAL ISOLATION (Hold workload constant, vary cooling capacity)")
    print("=" * 100)
    print()
    print("Protocol:")
    print("  - Fix utilization at 60% (moderate workload)")
    print("  - Fix power at 60W")
    print("  - Vary temperature from 45°C → 80°C (simulates reduced cooling)")
    print("  - This mimics loss of cooling capacity while workload stays constant")
    print()
    print("Expected if orthogonal:")
    print("  ✓ LTP should drop faster (headroom reduction)")
    print("  ✓ RLE should remain more stable (efficiency less affected)")
    print()
    
    rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    
    # Fixed workload
    fixed_util = 60.0
    fixed_power = 60.0
    
    # Vary temperature (cooling capacity)
    temp_range = [45, 50, 55, 60, 65, 70, 75, 80]
    
    print(f"{'Temp°C':<8} {'RLE':<8} {'LTP':<8} {'RSR':<8} {'S_n':<8} | {'dRLE':<8} {'dLTP':<8} {'Ratio':<10}")
    print("-" * 100)
    
    baseline = None
    results = []
    
    for temp in temp_range:
        result = rid.compute(fixed_util, temp, fixed_power)
        
        if baseline is None:
            baseline = (result.RLE, result.LTP, result.RSR, result.S_n)
            print(f"{temp:<8} {result.RLE:<8.3f} {result.LTP:<8.3f} {result.RSR:<8.3f} {result.S_n:<8.3f} | (baseline)")
        else:
            d_rle = result.RLE - baseline[0]
            d_ltp = result.LTP - baseline[1]
            
            # Ratio of changes (should be << 1 if LTP drops more than RLE)
            ratio = abs(d_rle) / abs(d_ltp) if abs(d_ltp) > 0.001 else 0.0
            
            print(f"{temp:<8} {result.RLE:<8.3f} {result.LTP:<8.3f} {result.RSR:<8.3f} {result.S_n:<8.3f} | "
                  f"{d_rle:+8.3f} {d_ltp:+8.3f} {ratio:<10.2f}")
        
        results.append((temp, result.RLE, result.LTP, result.RSR, result.S_n))
    
    # Analysis
    rle_vals = [r[1] for r in results]
    ltp_vals = [r[2] for r in results]
    
    rle_range = max(rle_vals) - min(rle_vals)
    ltp_range = max(ltp_vals) - min(ltp_vals)
    
    print()
    print("Analysis:")
    print(f"  RLE variation: {rle_range:.3f}")
    print(f"  LTP variation: {ltp_range:.3f}")
    print(f"  Variation ratio (LTP/RLE): {ltp_range/rle_range if rle_range > 0.001 else float('inf'):.2f}")
    print()
    
    if ltp_range > rle_range:
        print(f"  ✅ LTP dropped faster than RLE (ratio = {ltp_range/rle_range:.2f}x)")
        print("  ✅ Structural degradation exceeds efficiency degradation")
    else:
        print(f"  ⚠️ RLE dropped as much or more than LTP")
        print("  ⚠️ May indicate coupling")
    
    # Check proportionality
    # If coupled, RLE and LTP should track linearly
    # Calculate correlation
    rle_normalized = [(r - min(rle_vals)) / (max(rle_vals) - min(rle_vals)) for r in rle_vals]
    ltp_normalized = [(l - min(ltp_vals)) / (max(ltp_vals) - min(ltp_vals)) for l in ltp_vals]
    
    # Pearson correlation
    n = len(rle_normalized)
    mean_rle = sum(rle_normalized) / n
    mean_ltp = sum(ltp_normalized) / n
    
    cov = sum((rle_normalized[i] - mean_rle) * (ltp_normalized[i] - mean_ltp) for i in range(n))
    std_rle = (sum((r - mean_rle)**2 for r in rle_normalized) / n) ** 0.5
    std_ltp = (sum((l - mean_ltp)**2 for l in ltp_normalized) / n) ** 0.5
    
    correlation = cov / (std_rle * std_ltp) if std_rle * std_ltp > 0 else 0.0
    
    print(f"  Correlation (RLE vs LTP): {correlation:.3f}")
    
    if abs(correlation) > 0.9:
        print("  ⚠️ High correlation (> 0.9) - may be same signal")
    elif abs(correlation) > 0.7:
        print("  ⚠️ Moderate correlation (0.7-0.9) - partial coupling")
    else:
        print("  ✅ Low correlation (< 0.7) - distinct signals")
    
    return results


def test_cross_sensitivity():
    """
    Test C: Cross-Sensitivity Matrix
    
    Check how each input affects each output
    """
    print("\n" + "=" * 100)
    print("TEST C: CROSS-SENSITIVITY MATRIX")
    print("=" * 100)
    print()
    print("Measuring partial derivatives: ∂(output)/∂(input)")
    print()
    
    rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    
    # Baseline state
    base_util = 60.0
    base_temp = 60.0
    base_power = 60.0
    
    # Establish baseline
    base_result = rid.compute(base_util, base_temp, base_power)
    
    # Test partial sensitivities
    delta = 10.0  # 10% change
    
    # ∂RLE/∂util
    result_util = rid.compute(base_util + delta, base_temp, base_power)
    d_rle_util = (result_util.RLE - base_result.RLE) / delta
    d_ltp_util = (result_util.LTP - base_result.LTP) / delta
    
    # ∂RLE/∂temp
    rid_temp = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    result_temp = rid_temp.compute(base_util, base_temp + delta, base_power)
    d_rle_temp = (result_temp.RLE - base_result.RLE) / delta
    d_ltp_temp = (result_temp.LTP - base_result.LTP) / delta
    
    # ∂RLE/∂power
    rid_power = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    result_power = rid_power.compute(base_util, base_temp, base_power + delta)
    d_rle_power = (result_power.RLE - base_result.RLE) / delta
    d_ltp_power = (result_power.LTP - base_result.LTP) / delta
    
    print(f"{'Input':<12} | {'∂RLE/∂input':<15} {'∂LTP/∂input':<15} | {'Ratio':<10}")
    print("-" * 70)
    print(f"{'Utilization':<12} | {d_rle_util:+15.6f} {d_ltp_util:+15.6f} | {abs(d_rle_util/d_ltp_util) if abs(d_ltp_util) > 1e-6 else float('inf'):<10.2f}")
    print(f"{'Temperature':<12} | {d_rle_temp:+15.6f} {d_ltp_temp:+15.6f} | {abs(d_rle_temp/d_ltp_temp) if abs(d_ltp_temp) > 1e-6 else 0.0:<10.2f}")
    print(f"{'Power':<12} | {d_rle_power:+15.6f} {d_ltp_power:+15.6f} | {abs(d_rle_power/d_ltp_power) if abs(d_ltp_power) > 1e-6 else float('inf'):<10.2f}")
    
    print()
    print("Interpretation:")
    print("  - If ∂RLE/∂util >> ∂LTP/∂util → Workload primarily affects efficiency (orthogonal)")
    print("  - If ∂LTP/∂temp >> ∂RLE/∂temp → Temperature primarily affects structure (orthogonal)")
    print("  - If ratios ≈ 1 → Inputs affect both outputs equally (coupled)")


def main():
    print("\n" + "=" * 100)
    print("RID ORTHOGONALITY TEST")
    print("ChatGPT's Critical Diagnostic: Are RLE and LTP the same signal in disguise?")
    print("=" * 100)
    print()
    print("Goal: Prove RLE and LTP are orthogonal failure modes")
    print()
    print("Strategy:")
    print("  1. Efficiency isolation: Vary workload, hold thermal constant")
    print("  2. Structural isolation: Vary cooling, hold workload constant")
    print("  3. Cross-sensitivity: Measure partial derivatives")
    print()
    print("If orthogonal:")
    print("  ✓ Test A: RLE drops, LTP stable")
    print("  ✓ Test B: LTP drops faster than RLE")
    print("  ✓ Test C: Different input sensitivities")
    print()
    print("If coupled (bug):")
    print("  ✗ Both always move together")
    print("  ✗ High correlation (> 0.9)")
    print("  ✗ Same input sensitivities")
    print()
    
    # Run tests
    test_efficiency_isolation()
    test_structural_isolation()
    test_cross_sensitivity()
    
    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    print()
    print("Based on test results:")
    print("  - Review variation ratios")
    print("  - Review correlation coefficients")
    print("  - Review sensitivity matrix")
    print()
    print("If RLE and LTP can be experimentally separated:")
    print("  → Orthogonal (FEATURE)")
    print("  → Double-penalization is legitimate dual failure")
    print("  → 91% gap is physically meaningful")
    print()
    print("If they always move together:")
    print("  → Coupled (BUG)")
    print("  → LTP(T) = g(RLE(T)) - same signal disguised")
    print("  → Need to reformulate LTP without thermal dependence")
    print()


if __name__ == "__main__":
    main()
