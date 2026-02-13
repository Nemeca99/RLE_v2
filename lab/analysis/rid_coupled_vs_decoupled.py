#!/usr/bin/env python3
"""
RID Coupled vs Decoupled Comparison

ChatGPT's decisive experiment:
"Remove temperature from LTP entirely. Run the same sweep.
If early warning disappears → coupling was physically meaningful.
If early warning remains similar → current coupling is over-amplified."

This tool runs BOTH versions side-by-side and compares:
1. Early warning onset points
2. False positive rates
3. Prediction timing delta
4. Interpretability

Usage:
    python3 lab/analysis/rid_coupled_vs_decoupled.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "monitoring"))
from rid_core_decoupled import RIDCoreDecoupled


def compare_degradation_sweep():
    """
    Run identical degradation scenario through both coupled and decoupled versions
    
    Track:
    - When does each version issue first warning?
    - When does each version declare emergency?
    - How much do the S_n values differ?
    - Does decoupled lose early warning capability?
    """
    print("=" * 100)
    print("COUPLED vs DECOUPLED LTP COMPARISON")
    print("ChatGPT's Decisive Experiment")
    print("=" * 100)
    print()
    print("Test: Remove temperature from LTP entirely")
    print()
    print("Coupled LTP:    structure = (thermal × power × fan)^(1/3)")
    print("Decoupled LTP:  structure = (power × fan)^(1/2)  [NO THERMAL]")
    print()
    print("If early warning disappears → coupling was physically meaningful")
    print("If early warning remains similar → coupling is over-amplified")
    print()
    
    rid = RIDCoreDecoupled(temp_limit_c=85.0, power_limit_w=100.0)
    
    # Degradation scenario: gradual thermal + workload ramp
    scenarios = []
    for step in range(20):
        if step < 5:
            util = 30.0 + step * 2.0
            temp = 35.0 + step * 1.0
            power = 30.0 + step * 2.0
            phase = "Warm-up"
        elif step < 10:
            util = 40.0 + (step - 5) * 4.0
            temp = 40.0 + (step - 5) * 2.5
            power = 40.0 + (step - 5) * 4.0
            phase = "Ramp-up"
        elif step < 15:
            util = 60.0 + (step - 10) * 5.0
            temp = 52.5 + (step - 10) * 4.5
            power = 60.0 + (step - 10) * 5.0
            phase = "High load"
        else:
            util = 85.0 + (step - 15) * 2.0
            temp = 75.0 + (step - 15) * 1.8
            power = 85.0 + (step - 15) * 2.0
            phase = "Critical"
        scenarios.append((step, util, temp, power, phase))
    
    print(f"{'Step':<5} {'Phase':<10} {'Temp°C':<7} {'Util%':<7} | "
          f"{'LTP_c':<8} {'LTP_d':<8} | {'S_c':<8} {'S_d':<8} | {'Delta':<8} {'Status':<30}")
    print("-" * 100)
    
    first_warning_coupled = None
    first_warning_decoupled = None
    first_emergency_coupled = None
    first_emergency_decoupled = None
    
    results = []
    
    for step, util, temp, power, phase in scenarios:
        result = rid.compute(util, temp, power)
        
        # Track first warnings
        if result.pre_collapse_coupled and first_warning_coupled is None:
            first_warning_coupled = (step, temp, result.S_n_coupled)
        if result.pre_collapse_decoupled and first_warning_decoupled is None:
            first_warning_decoupled = (step, temp, result.S_n_decoupled)
        
        if result.S_n_coupled < 0.2 and first_emergency_coupled is None:
            first_emergency_coupled = (step, temp, result.S_n_coupled)
        if result.S_n_decoupled < 0.2 and first_emergency_decoupled is None:
            first_emergency_decoupled = (step, temp, result.S_n_decoupled)
        
        # Status indicator
        status = []
        if result.pre_collapse_coupled:
            status.append("C:WARN" if result.S_n_coupled >= 0.2 else "C:EMERG")
        if result.pre_collapse_decoupled:
            status.append("D:WARN" if result.S_n_decoupled >= 0.2 else "D:EMERG")
        
        status_str = " | ".join(status) if status else ""
        
        print(f"{step:<5} {phase:<10} {temp:<7.1f} {util:<7.0f} | "
              f"{result.LTP_coupled:<8.3f} {result.LTP_decoupled:<8.3f} | "
              f"{result.S_n_coupled:<8.3f} {result.S_n_decoupled:<8.3f} | "
              f"{result.delta_S_n:+8.3f} {status_str:<30}")
        
        results.append((step, temp, util, result.S_n_coupled, result.S_n_decoupled,
                       result.LTP_coupled, result.LTP_decoupled, result.delta_S_n))
    
    print("=" * 100)
    print()
    
    # Analysis
    print("ANALYSIS")
    print("=" * 100)
    print()
    
    # Early warning comparison
    print("1. Early Warning Onset")
    print("-" * 80)
    
    if first_warning_coupled and first_warning_decoupled:
        delta_steps = first_warning_coupled[0] - first_warning_decoupled[0]
        delta_temp = first_warning_coupled[1] - first_warning_decoupled[1]
        
        print(f"  Coupled first warning:    Step {first_warning_coupled[0]:<3} @ {first_warning_coupled[1]:.1f}°C (S_n={first_warning_coupled[2]:.3f})")
        print(f"  Decoupled first warning:  Step {first_warning_decoupled[0]:<3} @ {first_warning_decoupled[1]:.1f}°C (S_n={first_warning_decoupled[2]:.3f})")
        print()
        print(f"  Delta: {delta_steps} steps, {delta_temp:.1f}°C")
        print()
        
        if delta_steps > 2:
            print("  ✅ COUPLED warns significantly earlier")
            print("  → Thermal coupling provides earlier detection")
        elif delta_steps < -2:
            print("  ✅ DECOUPLED warns significantly earlier")
            print("  → Thermal coupling was over-amplifying")
        else:
            print("  ≈ Both warn at similar times")
            print("  → Coupling provides minimal advantage")
    elif first_warning_coupled and not first_warning_decoupled:
        print("  ✅ COUPLED warned, DECOUPLED did not")
        print("  → Thermal coupling is necessary for early warning")
    elif first_warning_decoupled and not first_warning_coupled:
        print("  ⚠️ DECOUPLED warned, COUPLED did not (unexpected)")
    else:
        print("  Neither version issued warnings")
    
    print()
    
    # Emergency comparison
    print("2. Emergency Threshold")
    print("-" * 80)
    
    if first_emergency_coupled and first_emergency_decoupled:
        delta_steps = first_emergency_coupled[0] - first_emergency_decoupled[0]
        delta_temp = first_emergency_coupled[1] - first_emergency_decoupled[1]
        
        print(f"  Coupled emergency:    Step {first_emergency_coupled[0]:<3} @ {first_emergency_coupled[1]:.1f}°C")
        print(f"  Decoupled emergency:  Step {first_emergency_decoupled[0]:<3} @ {first_emergency_decoupled[1]:.1f}°C")
        print()
        print(f"  Delta: {delta_steps} steps, {delta_temp:.1f}°C")
    
    print()
    
    # Delta magnitude analysis
    print("3. S_n Delta Magnitude")
    print("-" * 80)
    
    deltas = [r[7] for r in results]
    max_delta = max(abs(d) for d in deltas)
    avg_delta = sum(abs(d) for d in deltas) / len(deltas)
    
    print(f"  Average |delta|: {avg_delta:.3f}")
    print(f"  Maximum |delta|: {max_delta:.3f}")
    print()
    
    if avg_delta < 0.05:
        print("  ≈ Minimal difference (< 0.05 average)")
        print("  → Thermal coupling provides little value")
    elif avg_delta < 0.15:
        print("  ~ Moderate difference (0.05-0.15 average)")
        print("  → Thermal coupling has measurable effect")
    else:
        print("  ✓ Significant difference (> 0.15 average)")
        print("  → Thermal coupling substantially changes S_n")
    
    print()
    
    # Gap evolution
    print("4. Gap Evolution (Coupled vs Decoupled)")
    print("-" * 80)
    
    low_temp_deltas = [r[7] for r in results if r[1] < 60]
    high_temp_deltas = [r[7] for r in results if r[1] >= 75]
    
    if low_temp_deltas and high_temp_deltas:
        avg_low = sum(abs(d) for d in low_temp_deltas) / len(low_temp_deltas)
        avg_high = sum(abs(d) for d in high_temp_deltas) / len(high_temp_deltas)
        
        print(f"  Low temp (< 60°C):  avg delta = {avg_low:.3f}")
        print(f"  High temp (≥ 75°C): avg delta = {avg_high:.3f}")
        print()
        
        if avg_high > avg_low * 2:
            print("  ✓ Gap increases at high temperature")
            print("  → Thermal coupling amplifies near limits")
        else:
            print("  ≈ Gap remains relatively constant")
    
    print()
    
    # Final verdict
    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    print()
    
    if first_warning_coupled and not first_warning_decoupled:
        print("RESULT: Coupling is NECESSARY")
        print("  - Decoupled version failed to provide early warning")
        print("  - Thermal coupling is physically meaningful")
        print("  - Current implementation should be kept")
    elif first_warning_coupled and first_warning_decoupled:
        delta_steps = abs(first_warning_coupled[0] - first_warning_decoupled[0])
        
        if delta_steps >= 3:
            print("RESULT: Coupling provides SIGNIFICANT advantage")
            print(f"  - Coupled warns {delta_steps} steps earlier")
            print("  - Thermal coupling improves early detection")
            print("  - Current implementation justified")
        else:
            print("RESULT: Coupling provides MARGINAL advantage")
            print(f"  - Coupled warns only {delta_steps} steps earlier")
            print("  - Decoupled performs similarly with cleaner interpretation")
            print("  - Consider simplifying to decoupled version")
    else:
        print("RESULT: Inconclusive")
        print("  - Run on real session data for definitive answer")
    
    print()
    print("Next Step: Test on real CSV logs with known collapse events")
    print()


def main():
    print()
    compare_degradation_sweep()


if __name__ == "__main__":
    main()
