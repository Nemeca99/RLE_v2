#!/usr/bin/env python3
"""
Analyze CPU ramp stress test results
Computes efficiency curves and thermal decay metrics
"""

import pandas as pd
import argparse
import sys
from pathlib import Path

def analyze_ramp_test(csv_path):
    """Full analysis of ramp stress test"""
    
    print("="*70)
    print("CPU RAMP TEST ANALYSIS")
    print("="*70)
    print(f"File: {csv_path.name}")
    
    # Load data
    df = pd.read_csv(csv_path)
    
    # Clean data
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.drop_duplicates(subset=['timestamp', 'device'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Basic stats
    print(f"\nTotal Samples: {len(df)}")
    # Account for dual-device logging (CPU + GPU per second)
    actual_duration_min = (len(df) / 2) / 60 if len(df) > 0 else 0
    actual_duration_hr = actual_duration_min / 60
    print(f"Duration: {actual_duration_min:.1f} minutes ({actual_duration_hr:.2f} hours)")
    
    # CPU data only
    cpu_df = df[df['device'] == 'cpu'].copy()
    print(f"CPU Samples: {len(cpu_df)}")
    
    if len(cpu_df) == 0:
        print("ERROR: No CPU data found!")
        return
    
    # Target load steps
    load_steps = {
        17: (10, 25),
        33: (28, 38),
        50: (45, 55),
        67: (62, 72),
        83: (78, 88),
        100: (95, 105)
    }
    
    print("\n" + "="*70)
    print("EFFICIENCY CURVE BY LOAD STEP")
    print("="*70)
    print(f"{'Load%':<10} {'Mean RLE':<12} {'Mean Temp':<12} {'Mean Power':<12} {'Collapse Rate':<15} {'t_sustain':<12}")
    print("-"*70)
    
    summary_data = []
    
    for target, (low, high) in load_steps.items():
        # Filter to samples near this load
        mask = (cpu_df['util_pct'] >= low) & (cpu_df['util_pct'] <= high)
        subset = cpu_df[mask]
        
        if len(subset) > 0:
            mean_rle = subset['rle_smoothed'].mean()
            mean_temp = subset['temp_c'].mean() if pd.notna(subset['temp_c'].iloc[0]) else 0
            mean_power = subset['power_w'].mean() if 'power_w' in subset.columns else 0
            collapse_rate = subset['collapse'].sum() / len(subset) * 100
            mean_tsustain = subset['t_sustain_s'].mean()
            
            print(f"{target:<10} {mean_rle:<12.4f} {mean_temp:<12.1f} {mean_power:<12.1f} {collapse_rate:<15.1f} {mean_tsustain:<12.1f}")
            
            summary_data.append({
                'load': target,
                'mean_rle': mean_rle,
                'mean_temp': mean_temp,
                'mean_power': mean_power,
                'collapse_rate': collapse_rate,
                'mean_tsustain': mean_tsustain,
                'samples': len(subset)
            })
    
    # Compare early vs late
    print("\n" + "="*70)
    print("EFFICIENCY DECAY ANALYSIS (Early vs Late)")
    print("="*70)
    
    # First 10 minutes
    first_10min = cpu_df.head(600)  # 600 samples at 1 Hz
    
    # Last 10 minutes
    last_10min = cpu_df.tail(600)
    
    print("\nComparing first 10 minutes vs last 10 minutes:")
    print("-"*70)
    print(f"{'Load Step':<12} {'Early RLE':<12} {'Late RLE':<12} {'Change':<12} {'% Decay':<12}")
    print("-"*70)
    
    for target, (low, high) in load_steps.items():
        # Early samples
        early_mask = (first_10min['util_pct'] >= low) & (first_10min['util_pct'] <= high)
        early_data = first_10min[early_mask]
        
        # Late samples
        late_mask = (last_10min['util_pct'] >= low) & (last_10min['util_pct'] <= high)
        late_data = last_10min[late_mask]
        
        if len(early_data) > 0 and len(late_data) > 0:
            early_rle = early_data['rle_smoothed'].mean()
            late_rle = late_data['rle_smoothed'].mean()
            change = late_rle - early_rle
            pct_decay = (change / early_rle) * 100
            
            print(f"{target:<12} {early_rle:<12.4f} {late_rle:<12.4f} {change:<12.4f} {pct_decay:<12.1f}%")
    
    # Overall session health
    print("\n" + "="*70)
    print("OVERALL SESSION HEALTH")
    print("="*70)
    
    max_temp = cpu_df['temp_c'].max() if pd.notna(cpu_df['temp_c'].iloc[0]) else None
    mean_rle = cpu_df['rle_smoothed'].mean()
    max_rle = cpu_df['rle_smoothed'].max()
    collapse_count = cpu_df['collapse'].sum()
    collapse_pct = (collapse_count / len(cpu_df)) * 100
    
    print(f"Mean RLE: {mean_rle:.4f}")
    print(f"Max RLE: {max_rle:.4f}")
    print(f"Collapse Count: {collapse_count} ({collapse_pct:.1f}% of samples)")
    
    if max_temp:
        print(f"Max Temp: {max_temp:.1f}°C")
    
    mean_a_load = cpu_df['a_load'].mean() if 'a_load' in cpu_df.columns else None
    if mean_a_load:
        print(f"Mean a_load: {mean_a_load:.3f}")
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    # Find sweet spot (highest RLE)
    best_load = max(summary_data, key=lambda x: x['mean_rle'])
    print(f"Efficiency Sweet Spot: {best_load['load']}% load")
    print(f"  Mean RLE: {best_load['mean_rle']:.4f}")
    print(f"  Mean Temp: {best_load['mean_temp']:.1f}°C")
    
    # Check for problematic collapse
    high_collapse = [x for x in summary_data if x['collapse_rate'] > 10]
    if high_collapse:
        print(f"\nHigh Collapse Rates (>10%):")
        for item in high_collapse:
            print(f"  {item['load']}% load: {item['collapse_rate']:.1f}%")
    
    # Check RLE decay
    if len(summary_data) >= 6:
        # Compare first and last load steps
        if summary_data[-1]['mean_rle'] < summary_data[0]['mean_rle'] * 0.9:
            print(f"\nWarning: Significant RLE decay detected!")
            print(f"  Low load ({summary_data[0]['load']}%): RLE = {summary_data[0]['mean_rle']:.4f}")
            print(f"  High load ({summary_data[-1]['load']}%): RLE = {summary_data[-1]['mean_rle']:.4f}")
    
    print("\n" + "="*70)
    print("SUCCESS!")
    print("="*70)
    print("Archive this CSV:")
    print(f"  mv {csv_path.name} ../archive/cpu_ramp_8h_baseline.csv")
    print("\nThis dataset is your baseline reference for all future tests.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze CPU ramp stress test")
    parser.add_argument("csv", help="Path to ramp test CSV")
    
    args = parser.parse_args()
    
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        sys.exit(1)
    
    analyze_ramp_test(csv_path)

