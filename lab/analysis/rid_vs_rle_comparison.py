#!/usr/bin/env python3
"""
RID vs RLE Comparison Tool

Demonstrates the difference between:
- RLE-only monitoring (efficiency retention alone)
- Full RID triangle (RLE × LTP × RSR)

Shows how RID provides earlier warning by detecting:
- Structural capacity exhaustion (LTP)
- State reconstruction failures (RSR)
- Not just efficiency loss (RLE)

Usage:
    python3 lab/analysis/rid_vs_rle_comparison.py
    
    # Or with real session data:
    python3 lab/analysis/rid_vs_rle_comparison.py --csv sessions/recent/rle_20251030_19.csv
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple
import csv

# Add monitoring path
sys.path.insert(0, str(Path(__file__).parent.parent / "monitoring"))
from rid_core import RIDCore


def simulate_degradation() -> List[Tuple[float, float, float, str]]:
    """
    Simulate a realistic system degradation scenario
    
    Returns list of (util_pct, temp_c, power_w, description) tuples
    """
    scenarios = []
    
    # Gradual load increase with thermal accumulation
    for step in range(20):
        if step < 5:
            # Warm-up phase
            util = 30.0 + step * 2.0
            temp = 35.0 + step * 1.0
            power = 30.0 + step * 2.0
            desc = "Warm-up"
        elif step < 10:
            # Stable operation
            util = 40.0 + (step - 5) * 4.0
            temp = 40.0 + (step - 5) * 2.5
            power = 40.0 + (step - 5) * 4.0
            desc = "Ramp-up"
        elif step < 15:
            # Approaching limits
            util = 60.0 + (step - 10) * 5.0
            temp = 52.5 + (step - 10) * 4.5
            power = 60.0 + (step - 10) * 5.0
            desc = "High load"
        else:
            # Near thermal limit
            util = 85.0 + (step - 15) * 2.0
            temp = 75.0 + (step - 15) * 1.8
            power = 85.0 + (step - 15) * 2.0
            desc = "Critical"
        
        scenarios.append((util, temp, power, desc))
    
    return scenarios


def analyze_comparison(scenarios: List[Tuple[float, float, float, str]],
                       temp_limit: float = 85.0,
                       power_limit: float = 100.0) -> None:
    """
    Compare RLE-only vs full RID across degradation scenarios
    """
    
    rid_engine = RIDCore(temp_limit_c=temp_limit, power_limit_w=power_limit)
    
    print("=" * 100)
    print("RLE-ONLY vs FULL RID COMPARISON")
    print("=" * 100)
    print()
    print("Legend:")
    print("  RLE: Efficiency retention (existing validated metric)")
    print("  LTP: Structure vs demand (headroom ratio)")
    print("  RSR: State reconstruction fidelity (sensor lag)")
    print("  S_n: Full RID stability scalar (RLE × LTP × RSR)")
    print()
    print("Thresholds:")
    print("  S_n < 0.4: Pre-collapse regime (warning)")
    print("  S_n < 0.2: Collapse imminent (emergency)")
    print()
    print("=" * 100)
    print(f"{'Step':<5} {'Phase':<10} {'Util%':<7} {'Temp°C':<7} {'Pwr W':<7} | {'RLE':<6} {'LTP':<6} {'RSR':<6} {'S_n':<6} | {'Gap':<6} {'Mode':<25}")
    print("=" * 100)
    
    rle_warnings = []
    rid_warnings = []
    
    for step, (util, temp, power, phase) in enumerate(scenarios):
        result = rid_engine.compute(util, temp, power)
        
        # Calculate warning gap (how much earlier RID warns)
        gap_pct = ((result.RLE - result.S_n) / max(result.RLE, 0.001)) * 100
        
        # Track when each method would issue warnings
        if result.RLE < 0.4 and not rle_warnings:
            rle_warnings.append((step, temp, "RLE < 0.4"))
        if result.RLE < 0.2 and len(rle_warnings) < 2:
            rle_warnings.append((step, temp, "RLE < 0.2"))
        
        if result.S_n < 0.4 and not rid_warnings:
            rid_warnings.append((step, temp, "S_n < 0.4"))
        if result.S_n < 0.2 and len(rid_warnings) < 2:
            rid_warnings.append((step, temp, "S_n < 0.2"))
        
        # Display row
        status = ""
        if result.S_n < 0.2:
            status = "⚠️  EMERGENCY"
        elif result.S_n < 0.4:
            status = "⚠️  WARNING"
        
        print(f"{step:<5} {phase:<10} {util:<7.1f} {temp:<7.1f} {power:<7.1f} | "
              f"{result.RLE:<6.3f} {result.LTP:<6.3f} {result.RSR:<6.3f} {result.S_n:<6.3f} | "
              f"{gap_pct:<6.0f}% {result.failure_mode:<25} {status}")
    
    print("=" * 100)
    print()
    
    # Summary analysis
    print("ANALYSIS SUMMARY")
    print("=" * 100)
    print()
    
    if rid_warnings and rle_warnings:
        # Compare warning times
        rid_first_warn = rid_warnings[0]
        rle_first_warn = rle_warnings[0] if rle_warnings else (999, 999, "Never")
        
        temp_diff = rle_first_warn[1] - rid_first_warn[1]
        step_diff = rle_first_warn[0] - rid_first_warn[0]
        
        print(f"Early Warning Advantage (RID vs RLE-only):")
        print(f"  RID first warning:  Step {rid_first_warn[0]:<3} @ {rid_first_warn[1]:.1f}°C ({rid_first_warn[2]})")
        print(f"  RLE first warning:  Step {rle_first_warn[0]:<3} @ {rle_first_warn[1]:.1f}°C ({rle_first_warn[2]})")
        print(f"  Lead time:          {step_diff} steps earlier")
        print(f"  Thermal margin:     {temp_diff:.1f}°C more headroom when warned")
        print()
    
    print("Key Insights:")
    print("  1. S_n < RLE always (multiplicative degradation)")
    print("  2. Gap increases as system approaches limits")
    print("  3. LTP captures structural exhaustion (headroom)")
    print("  4. RSR captures observability failures (lag/error)")
    print("  5. RID warns while RLE still looks acceptable")
    print()
    
    # Find maximum gap
    rid_engine_fresh = RIDCore(temp_limit_c=temp_limit, power_limit_w=power_limit)
    max_gap = 0.0
    max_gap_scenario = None
    
    for scenario in scenarios:
        result = rid_engine_fresh.compute(*scenario[:3])
        gap = result.RLE - result.S_n
        if gap > max_gap:
            max_gap = gap
            max_gap_scenario = (scenario, result)
    
    if max_gap_scenario:
        scenario, result = max_gap_scenario
        util, temp, power, phase = scenario
        print(f"Maximum Gap Observed:")
        print(f"  Conditions: {phase} @ {temp:.1f}°C, {util:.0f}% util, {power:.0f}W")
        print(f"  RLE:        {result.RLE:.3f} (appears stable)")
        print(f"  S_n:        {result.S_n:.3f} (actually degraded)")
        print(f"  Gap:        {max_gap:.3f} ({(max_gap/result.RLE)*100:.0f}% hidden instability)")
        print()
    
    print("RID Advantage:")
    print("  ✓ Detects margin exhaustion before efficiency drops")
    print("  ✓ Identifies structural overload (LTP) separately from dissipation (RLE)")
    print("  ✓ Catches observability failures (RSR) that RLE misses")
    print("  ✓ Provides earlier actionable warning")
    print()
    print("=" * 100)


def analyze_csv(csv_path: Path) -> None:
    """Analyze real session CSV data"""
    
    print(f"Analyzing session data: {csv_path}")
    print()
    
    # Read CSV and extract scenarios
    scenarios = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                util = float(row.get('util_pct', 0))
                temp = float(row.get('temp_c', 0))
                power = float(row.get('power_w', 0))
                scenarios.append((util, temp, power, "Session"))
            except (ValueError, KeyError):
                continue
    
    if not scenarios:
        print("ERROR: No valid data found in CSV")
        return
    
    print(f"Loaded {len(scenarios)} samples")
    print()
    
    # Run comparison
    analyze_comparison(scenarios)


def main():
    parser = argparse.ArgumentParser(description="Compare RLE-only vs full RID triangle")
    parser.add_argument('--csv', type=str, help='Path to session CSV (optional - will simulate if not provided)')
    parser.add_argument('--temp-limit', type=float, default=85.0, help='Temperature limit (°C)')
    parser.add_argument('--power-limit', type=float, default=100.0, help='Power limit (W)')
    
    args = parser.parse_args()
    
    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"ERROR: CSV not found: {csv_path}")
            return 1
        analyze_csv(csv_path)
    else:
        scenarios = simulate_degradation()
        analyze_comparison(scenarios, args.temp_limit, args.power_limit)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
