#!/usr/bin/env python3
"""
Adaptive Control Curve
Dynamically targets optimal power levels by adjusting utilization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

def compute_control_curve(df, target_power=15.0):
    """
    Generate adaptive control curve to target specific power level
    
    Logic:
    - Measure current power draw
    - Adjust utilization to hit target power
    - Build function: util_adjust = f(current_power, target_power)
    """
    
    print("="*70)
    print("ADAPTIVE CONTROL CURVE")
    print("="*70)
    print(f"Target power: {target_power}W")
    
    cpu_df = df[df['device'] == 'cpu'].copy()
    
    if 'power_w' not in cpu_df.columns or 'util_pct' not in cpu_df.columns:
        print("ERROR: Required columns (power_w, util_pct) not found")
        return
    
    # Filter valid data
    valid = cpu_df['power_w'].notna() & cpu_df['util_pct'].notna() & (cpu_df['power_w'] > 0) & (cpu_df['util_pct'] > 0)
    valid_df = cpu_df[valid].copy()
    
    print(f"\nValid samples: {len(valid_df)}")
    
    # Compute power-to-util ratio
    valid_df['power_per_util'] = valid_df['power_w'] / valid_df['util_pct']
    valid_df['target_util'] = target_power / valid_df['power_per_util']
    
    # Estimate required utilization adjustment
    valid_df['util_adjustment'] = valid_df['target_util'] - valid_df['util_pct']
    
    # Build control function: linear fit of power vs utilization
    from scipy import stats
    
    X = valid_df['util_pct'].values.reshape(-1, 1)
    y = valid_df['power_w'].values
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(valid_df['util_pct'], valid_df['power_w'])
    
    print(f"\nPower vs Utilization Model:")
    print(f"  Power(W) = {slope:.4f} × Util(%) + {intercept:.4f}")
    print(f"  R² = {r_value**2:.4f}")
    print(f"  Std error: {std_err:.4f}")
    
    # Inverse function: what util needed for target power?
    target_util = (target_power - intercept) / slope if slope != 0 else 0
    
    print(f"\n{'='*70}")
    print("CONTROL PARAMETERS")
    print(f"{'='*70}")
    print(f"Target power: {target_power}W")
    print(f"Required utilization: {target_util:.1f}%")
    print(f"Average power/unit: {valid_df['power_per_util'].mean():.4f} W/%")
    print(f"Control function: util_target = (power_target - {intercept:.4f}) / {slope:.4f}")
    
    # Analyze current operation
    mean_power = valid_df['power_w'].mean()
    mean_util = valid_df['util_pct'].mean()
    
    print(f"\n{'='*70}")
    print("CURRENT OPERATION")
    print(f"{'='*70}")
    print(f"Mean power: {mean_power:.1f}W")
    print(f"Mean utilization: {mean_util:.1f}%")
    print(f"Power deviation: {mean_power - target_power:.1f}W")
    
    if abs(mean_power - target_power) < 1.0:
        print("\n✓ Currently operating near target")
    elif mean_power > target_power:
        power_reduction = mean_power - target_power
        util_reduction = power_reduction / slope if slope != 0 else 0
        print(f"\n⚠ Operating {power_reduction:.1f}W above target")
        print(f"  Reduce utilization by ~{util_reduction:.1f}% to reach {target_power}W")
    else:
        power_increase = target_power - mean_power
        util_increase = power_increase / slope if slope != 0 else 0
        print(f"\n→ Operating {power_increase:.1f}W below target")
        print(f"  Increase utilization by ~{util_increase:.1f}% to reach {target_power}W")
    
    return valid_df, slope, intercept

def plot_control_curve(df, slope, intercept, target_power, output_dir):
    """Visualize the control curve"""
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Power vs Utilization with target
    ax1 = axes[0]
    
    valid = df['power_w'].notna() & df['util_pct'].notna()
    ax1.scatter(df.loc[valid, 'util_pct'], df.loc[valid, 'power_w'], 
                alpha=0.3, s=1, label='Actual data')
    
    # Plot fitted line
    util_range = np.linspace(df['util_pct'].min(), df['util_pct'].max(), 100)
    power_range = slope * util_range + intercept
    ax1.plot(util_range, power_range, 'r-', linewidth=2, label='Fitted model')
    
    # Plot target power line
    ax1.axhline(y=target_power, color='green', linestyle='--', linewidth=2, label=f'Target: {target_power}W')
    
    # Calculate and mark target utilization
    target_util = (target_power - intercept) / slope if slope != 0 else 0
    ax1.axvline(x=target_util, color='green', linestyle=':', linewidth=2, alpha=0.7)
    ax1.scatter([target_util], [target_power], color='green', s=100, zorder=10, 
                label=f'Target point: {target_util:.1f}% @ {target_power}W')
    
    ax1.set_xlabel('Utilization (%)', fontsize=12)
    ax1.set_ylabel('Power (W)', fontsize=12)
    ax1.set_title('Adaptive Control Curve: Power vs Utilization', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Plot 2: Utilization adjustment needed
    ax2 = axes[1]
    
    valid = df['util_adjustment'].notna()
    ax2.scatter(df.loc[valid, 'util_pct'], df.loc[valid, 'util_adjustment'], 
                alpha=0.3, s=1, label='Utilization adjustment needed', color='purple')
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax2.axhline(y=-5, color='orange', linestyle='--', linewidth=1, label='±5% zone', alpha=0.7)
    ax2.axhline(y=5, color='orange', linestyle='--', linewidth=1, alpha=0.7)
    
    ax2.set_xlabel('Current Utilization (%)', fontsize=12)
    ax2.set_ylabel('Adjustment Needed (%)', fontsize=12)
    ax2.set_title(f'Required Adjustment to Reach {target_power}W', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/adaptive_control_curve.png', dpi=150)
    print(f"\n✓ Saved: {output_dir}/adaptive_control_curve.png")
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Generate adaptive control curve for power targeting")
    parser.add_argument("csv", help="Path to CSV file")
    parser.add_argument("--target-power", type=float, default=15.0, help="Target power in watts (default: 15.0)")
    parser.add_argument("--plot", action="store_true", help="Generate visualization plots")
    
    args = parser.parse_args()
    
    print(f"Loading: {args.csv}")
    df = pd.read_csv(args.csv)
    
    # Clean data
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.drop_duplicates(subset=['timestamp', 'device'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Compute control curve
    result_df, slope, intercept = compute_control_curve(df, args.target_power)
    
    # Generate plots
    if args.plot:
        output_dir = Path("sessions/archive/plots")
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_control_curve(result_df, slope, intercept, args.target_power, output_dir)
    
    print("\n" + "="*70)
    print("ADAPTIVE CONTROL COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

