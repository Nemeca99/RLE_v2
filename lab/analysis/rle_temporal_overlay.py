#!/usr/bin/env python3
"""
RLE Temporal Overlay
Plot CPU and GPU RLE on same timeline for comparison
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

def plot_temporal_overlay(df, output_dir):
    """Plot CPU and GPU RLE on same timeline"""
    
    print("="*70)
    print("TEMPORAL OVERLAY ANALYSIS")
    print("="*70)
    
    # Separate devices
    cpu_df = df[df['device'] == 'cpu'].copy()
    gpu_df = df[df['device'] == 'gpu'].copy()
    
    if len(cpu_df) == 0 or len(gpu_df) == 0:
        print("ERROR: Missing device data")
        return
    
    # Parse timestamps
    cpu_df['timestamp'] = pd.to_datetime(cpu_df['timestamp'], utc=True, errors='coerce')
    gpu_df['timestamp'] = pd.to_datetime(gpu_df['timestamp'], utc=True, errors='coerce')
    
    # Sort by time
    cpu_df = cpu_df.sort_values('timestamp').reset_index(drop=True)
    gpu_df = gpu_df.sort_values('timestamp').reset_index(drop=True)
    
    # Create time axis (minutes from start)
    cpu_start = cpu_df['timestamp'].min()
    gpu_start = gpu_df['timestamp'].min()
    start_time = min(cpu_start, gpu_start)
    
    cpu_df['minutes'] = (cpu_df['timestamp'] - start_time).dt.total_seconds() / 60
    gpu_df['minutes'] = (gpu_df['timestamp'] - start_time).dt.total_seconds() / 60
    
    # Create figure
    fig, axes = plt.subplots(4, 1, figsize=(16, 12))
    
    # Plot 1: RLE overlay
    ax1 = axes[0]
    ax1.plot(cpu_df['minutes'], cpu_df['rle_smoothed'], label='CPU RLE', 
             linewidth=0.8, alpha=0.8, color='blue')
    ax1.plot(gpu_df['minutes'], gpu_df['rle_smoothed'], label='GPU RLE', 
             linewidth=0.8, alpha=0.8, color='red')
    ax1.set_xlabel('Time (minutes)', fontsize=11)
    ax1.set_ylabel('RLE', fontsize=11)
    ax1.set_title('RLE Temporal Overlay: CPU vs GPU', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Plot 2: Utilization overlay
    ax2 = axes[1]
    ax2.plot(cpu_df['minutes'], cpu_df['util_pct'], label='CPU Utilization', 
             linewidth=0.8, alpha=0.8, color='blue')
    ax2.plot(gpu_df['minutes'], gpu_df['util_pct'], label='GPU Utilization', 
             linewidth=0.8, alpha=0.8, color='red')
    ax2.set_xlabel('Time (minutes)', fontsize=11)
    ax2.set_ylabel('Utilization (%)', fontsize=11)
    ax2.set_title('Utilization Temporal Overlay', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    # Plot 3: Power overlay
    ax3 = axes[2]
    ax3.plot(cpu_df['minutes'], cpu_df['power_w'], label='CPU Power', 
             linewidth=0.8, alpha=0.8, color='blue')
    ax3.plot(gpu_df['minutes'], gpu_df['power_w'], label='GPU Power', 
             linewidth=0.8, alpha=0.8, color='red')
    ax3.set_xlabel('Time (minutes)', fontsize=11)
    ax3.set_ylabel('Power (W)', fontsize=11)
    ax3.set_title('Power Temporal Overlay', fontsize=13, fontweight='bold')
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # Plot 4: RLE comparison (scatter)
    ax4 = axes[3]
    # Sample for visualization (too many points otherwise)
    sample_cpu = cpu_df.sample(min(1000, len(cpu_df)))
    sample_gpu = gpu_df.sample(min(1000, len(gpu_df)))
    
    ax4.scatter(sample_cpu['minutes'], sample_cpu['rle_smoothed'], 
               label='CPU RLE', alpha=0.5, s=10, color='blue')
    ax4.scatter(sample_gpu['minutes'], sample_gpu['rle_smoothed'], 
               label='GPU RLE', alpha=0.5, s=10, color='red')
    ax4.set_xlabel('Time (minutes)', fontsize=11)
    ax4.set_ylabel('RLE', fontsize=11)
    ax4.set_title('RLE Scatter Overlay', fontsize=13, fontweight='bold')
    ax4.legend()
    ax4.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/rle_temporal_overlay.png', dpi=150)
    print(f"\n✓ Saved: {output_dir}/rle_temporal_overlay.png")
    plt.close()
    
    # Correlation analysis
    print("\n" + "="*70)
    print("CORRELATION ANALYSIS")
    print("="*70)
    
    # Find overlapping samples (within 1 second)
    overlap_count = 0
    cpu_rle_overlap = []
    gpu_rle_overlap = []
    
    for cpu_time in cpu_df['timestamp']:
        gpu_close = gpu_df[abs((gpu_df['timestamp'] - cpu_time).dt.total_seconds()) < 1]
        if len(gpu_close) > 0:
            overlap_count += 1
            cpu_rle_overlap.append(cpu_df[cpu_df['timestamp'] == cpu_time]['rle_smoothed'].values[0])
            gpu_rle_overlap.append(gpu_close.iloc[0]['rle_smoothed'])
    
    print(f"Overlapping samples (within 1s): {overlap_count}")
    
    if len(cpu_rle_overlap) > 10:
        correlation = np.corrcoef(cpu_rle_overlap, gpu_rle_overlap)[0, 1]
        print(f"CPU-GPU RLE correlation: {correlation:.4f}")
        
        if abs(correlation) > 0.7:
            print("→ Strong coupling (GPU and CPU RLE synchronized)")
        elif abs(correlation) > 0.3:
            print("→ Moderate coupling (partial synchronization)")
        else:
            print("→ Weak coupling (independent operation)")
    else:
        print("Insufficient overlap for correlation")

def main():
    parser = argparse.ArgumentParser(description="RLE temporal overlay")
    parser.add_argument("csv", help="Path to CSV file")
    parser.add_argument("--plot", action="store_true", help="Generate visualization")
    
    args = parser.parse_args()
    
    print(f"Loading: {args.csv}")
    df = pd.read_csv(args.csv)
    
    # Clean data
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.drop_duplicates(subset=['timestamp', 'device'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    if args.plot:
        output_dir = Path("sessions/archive/plots")
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_temporal_overlay(df, output_dir)
    else:
        print("Add --plot flag to generate visualizations")
    
    print("\n" + "="*70)
    print("TEMPORAL OVERLAY COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

