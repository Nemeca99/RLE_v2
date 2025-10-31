#!/usr/bin/env python3
"""
Collapse Threshold Detector
Predicts imminent instability using rolling RLE variance
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

def detect_imminent_collapse(df, window_size=30, variance_threshold=0.5, rle_drop_threshold=-0.1):
    """
    Detect imminent collapse using rolling variance and RLE drop
    
    Logic:
    - Large variance in RLE → instability indicators
    - RLE drop below rolling mean → loss of efficiency
    - Both together → imminent collapse
    """
    
    print("="*70)
    print("COLLAPSE THRESHOLD DETECTOR")
    print("="*70)
    
    cpu_df = df[df['device'] == 'cpu'].copy()
    
    if 'rle_smoothed' not in cpu_df.columns:
        print("ERROR: No RLE data available")
        return df
    
    # Compute rolling statistics
    cpu_df['rle_rolling_mean'] = cpu_df['rle_smoothed'].rolling(window=window_size, center=True).mean()
    cpu_df['rle_rolling_std'] = cpu_df['rle_smoothed'].rolling(window=window_size, center=True).std()
    cpu_df['rle_rolling_var'] = cpu_df['rle_rolling_std'] ** 2
    
    # Detect variance spikes
    cpu_df['high_variance'] = cpu_df['rle_rolling_var'] > variance_threshold
    
    # Detect RLE drops
    cpu_df['rle_drop'] = cpu_df['rle_smoothed'] - cpu_df['rle_rolling_mean']
    cpu_df['large_drop'] = cpu_df['rle_drop'] < rle_drop_threshold
    
    # Imminent collapse = high variance AND large drop
    cpu_df['imminent_collapse'] = cpu_df['high_variance'] & cpu_df['large_drop']
    
    # Count warnings
    warning_count = cpu_df['imminent_collapse'].sum()
    total_samples = len(cpu_df)
    
    print(f"\nAnalysis window: {window_size} samples")
    print(f"Variance threshold: >{variance_threshold}")
    print(f"RLE drop threshold: <{rle_drop_threshold}")
    
    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Total samples: {total_samples}")
    print(f"Imminent collapse warnings: {warning_count} ({warning_count/total_samples*100:.2f}%)")
    
    if warning_count > 0:
        print("\n⚠ WARNING: Instability indicators detected!")
        print(f"  - Large variance in RLE ({cpu_df['rle_rolling_var'].max():.4f})")
        print(f"  - Significant RLE drops detected")
        print("  - System approaching thermal/power limits")
        
        # Analyze warning periods
        warning_periods = []
        in_warning = False
        start_idx = None
        
        for idx, row in cpu_df.iterrows():
            if row['imminent_collapse'] and not in_warning:
                in_warning = True
                start_idx = idx
            elif not row['imminent_collapse'] and in_warning:
                in_warning = False
                warning_periods.append((start_idx, idx - 1))
        
        if in_warning:
            warning_periods.append((start_idx, len(cpu_df) - 1))
        
        print(f"\nDetected {len(warning_periods)} warning periods:")
        for i, (start, end) in enumerate(warning_periods[:5], 1):
            period_samples = cpu_df.loc[start:end]
            print(f"\nPeriod {i}:")
            print(f"  Duration: {len(period_samples)}s")
            print(f"  Mean RLE: {period_samples['rle_smoothed'].mean():.4f}")
            print(f"  Mean variance: {period_samples['rle_rolling_var'].mean():.4f}")
            
            if 'power_w' in period_samples.columns:
                print(f"  Mean power: {period_samples['power_w'].mean():.1f}W")
            
            if 'util_pct' in period_samples.columns:
                print(f"  Mean util: {period_samples['util_pct'].mean():.1f}%")
    else:
        print("\n✓ No imminent collapse warnings")
        print("  System maintained stable operation")
    
    return cpu_df

def plot_collapse_predictions(cpu_df, output_dir):
    """Visualize collapse predictions"""
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # Plot 1: RLE with warnings
    ax1 = axes[0]
    ax1.plot(cpu_df.index, cpu_df['rle_smoothed'], alpha=0.5, label='RLE', linewidth=0.5)
    
    warnings = cpu_df[cpu_df['imminent_collapse']]
    if len(warnings) > 0:
        ax1.scatter(warnings.index, warnings['rle_smoothed'], 
                   color='red', s=10, alpha=0.7, label='Imminent Collapse Warnings', zorder=5)
    
    ax1.set_ylabel('RLE', fontsize=11)
    ax1.set_title('RLE with Collapse Threshold Warnings', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Plot 2: Rolling variance
    ax2 = axes[1]
    ax2.plot(cpu_df.index, cpu_df['rle_rolling_var'], color='orange', linewidth=0.5)
    ax2.axhline(y=0.5, color='red', linestyle='--', linewidth=1, label='Threshold')
    ax2.set_ylabel('RLE Variance', fontsize=11)
    ax2.set_title('Rolling Variance', fontsize=13)
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    # Plot 3: Power (if available)
    ax3 = axes[2]
    if 'power_w' in cpu_df.columns:
        ax3.plot(cpu_df.index, cpu_df['power_w'], alpha=0.5, color='green', linewidth=0.5)
        ax3.set_ylabel('Power (W)', fontsize=11)
        ax3.set_title('Power Draw', fontsize=13)
        ax3.grid(alpha=0.3)
    
    ax3.set_xlabel('Sample Index', fontsize=11)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/collapse_predictions.png', dpi=150)
    print(f"\n✓ Saved: {output_dir}/collapse_predictions.png")
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Detect imminent collapse using variance analysis")
    parser.add_argument("csv", help="Path to CSV file")
    parser.add_argument("--window", type=int, default=30, help="Rolling window size (default: 30)")
    parser.add_argument("--variance-threshold", type=float, default=0.5, help="Variance threshold (default: 0.5)")
    parser.add_argument("--drop-threshold", type=float, default=-0.1, help="RLE drop threshold (default: -0.1)")
    parser.add_argument("--plot", action="store_true", help="Generate visualization plots")
    
    args = parser.parse_args()
    
    print(f"Loading: {args.csv}")
    df = pd.read_csv(args.csv)
    
    # Clean data
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.drop_duplicates(subset=['timestamp', 'device'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Run detection
    result_df = detect_imminent_collapse(df, args.window, args.variance_threshold, args.drop_threshold)
    
    # Generate plots
    if args.plot:
        output_dir = Path("sessions/archive/plots")
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_collapse_predictions(result_df, output_dir)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

