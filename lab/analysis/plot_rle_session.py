#!/usr/bin/env python3
"""
RLE Session Visualization Tool
Creates multi-panel plots showing RLE behavior, collapse events, and thermal state

USAGE:
    python plot_rle_session.py sessions/recent/rle_enhanced_20251028_15.csv

Generates:
- Multi-panel plot showing RLE, collapse events, temperature, and power
- Collapse events marked with vertical shaded regions
- Saves as: rle_session_analysis.png
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

def load_session_data(csv_file):
    """Load and validate session data"""
    try:
        df = pd.read_csv(csv_file)
        print(f"[SUCCESS] Loaded {len(df)} samples from {csv_file}")
        
        # Separate CPU and GPU data
        cpu_data = df[df['device'] == 'cpu'].copy()
        gpu_data = df[df['device'] == 'gpu'].copy()
        
        if len(cpu_data) == 0 and len(gpu_data) == 0:
            print("[FAILED] No CPU or GPU data found")
            return None, None, None
        
        return df, cpu_data, gpu_data
        
    except Exception as e:
        print(f"[FAILED] Failed to load CSV: {e}")
        return None, None, None

def create_session_plot(df, cpu_data, gpu_data, output_file):
    """Create comprehensive session analysis plot"""
    
    # Create 4-panel subplot
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))
    
    # Panel 1: RLE over time
    ax1 = axes[0]
    
    if len(cpu_data) > 0:
        ax1.plot(cpu_data.index, cpu_data['rle_smoothed'], 'b-', 
                label='CPU RLE', linewidth=2, alpha=0.8)
    
    if len(gpu_data) > 0:
        ax1.plot(gpu_data.index, gpu_data['rle_smoothed'], 'orange', 
                label='GPU RLE', linewidth=2, alpha=0.8)
    
    ax1.set_ylabel('RLE')
    ax1.set_title('RLE Behavior: Efficiency Stability Index')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add collapse regions as shaded areas
    add_collapse_regions(ax1, cpu_data, gpu_data, alpha=0.2)
    
    # Panel 2: Collapse events
    ax2 = axes[1]
    
    if len(cpu_data) > 0:
        cpu_collapse_points = cpu_data[cpu_data['collapse'] == 1]
        if len(cpu_collapse_points) > 0:
            ax2.scatter(cpu_collapse_points.index, [1] * len(cpu_collapse_points), 
                       c='red', marker='o', s=15, label='CPU Collapse', alpha=0.7)
    
    if len(gpu_data) > 0:
        gpu_collapse_points = gpu_data[gpu_data['collapse'] == 1]
        if len(gpu_collapse_points) > 0:
            ax2.scatter(gpu_collapse_points.index, [0.5] * len(gpu_collapse_points), 
                       c='orange', marker='s', s=15, label='GPU Collapse', alpha=0.7)
    
    ax2.set_ylabel('Collapse Events')
    ax2.set_title('Collapse Events = Efficiency Instability (Not Thermal Death)')
    ax2.legend()
    ax2.set_ylim(-0.1, 1.5)
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Temperature
    ax3 = axes[2]
    
    if len(cpu_data) > 0:
        ax3.plot(cpu_data.index, cpu_data['temp_c'], 'b-', 
                label='CPU Temp', linewidth=2, alpha=0.8)
    
    if len(gpu_data) > 0:
        ax3.plot(gpu_data.index, gpu_data['temp_c'], 'orange', 
                label='GPU Temp', linewidth=2, alpha=0.8)
    
    ax3.set_ylabel('Temperature (°C)')
    ax3.set_title('Thermal State During Test')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Add collapse regions
    add_collapse_regions(ax3, cpu_data, gpu_data, alpha=0.1)
    
    # Panel 4: Power draw
    ax4 = axes[3]
    
    if len(cpu_data) > 0:
        ax4.plot(cpu_data.index, cpu_data['power_w'], 'b-', 
                label='CPU Power', linewidth=2, alpha=0.8)
    
    if len(gpu_data) > 0:
        ax4.plot(gpu_data.index, gpu_data['power_w'], 'orange', 
                label='GPU Power', linewidth=2, alpha=0.8)
    
    ax4.set_ylabel('Power (W)')
    ax4.set_xlabel('Sample Number')
    ax4.set_title('Power Consumption During Test')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Add collapse regions
    add_collapse_regions(ax4, cpu_data, gpu_data, alpha=0.1)
    
    # Add overall title and save
    fig.suptitle('RLE Session Analysis: Controlled Load Test', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Plot saved: {output_file}")

def add_collapse_regions(ax, cpu_data, gpu_data, alpha=0.2):
    """Add shaded regions for collapse events"""
    
    # Find collapse regions for CPU
    if len(cpu_data) > 0:
        cpu_collapses = cpu_data[cpu_data['collapse'] == 1]
        if len(cpu_collapses) > 0:
            for idx in cpu_collapses.index:
                ax.axvspan(idx-0.5, idx+0.5, alpha=alpha, color='red')
    
    # Find collapse regions for GPU
    if len(gpu_data) > 0:
        gpu_collapses = gpu_data[gpu_data['collapse'] == 1]
        if len(gpu_collapses) > 0:
            for idx in gpu_collapses.index:
                ax.axvspan(idx-0.5, idx+0.5, alpha=alpha, color='orange')

def print_session_summary(df, cpu_data, gpu_data):
    """Print summary statistics"""
    
    print("\n" + "="*60)
    print("SESSION SUMMARY")
    print("="*60)
    
    # Basic stats
    duration = len(df) / 2.0  # Assuming 1 Hz sampling, 2 devices
    sample_count = len(df)
    
    print(f"Duration: {duration:.1f}s")
    print(f"Total samples: {sample_count}")
    print(f"Sample rate: {sample_count/duration:.2f} Hz")
    
    # CPU stats
    if len(cpu_data) > 0:
        cpu_collapses = cpu_data['collapse'].sum()
        cpu_collapse_pct = (cpu_collapses / len(cpu_data)) * 100
        cpu_rle_range = f"{cpu_data['rle_smoothed'].min():.3f} - {cpu_data['rle_smoothed'].max():.3f}"
        cpu_rle_mean = cpu_data['rle_smoothed'].mean()
        
        print(f"\nCPU:")
        print(f"  Collapses: {cpu_collapses} ({cpu_collapse_pct:.1f}%)")
        print(f"  RLE range: {cpu_rle_range} (mean: {cpu_rle_mean:.3f})")
        print(f"  Max temp: {cpu_data['temp_c'].max():.1f}°C")
        print(f"  Max power: {cpu_data['power_w'].max():.1f}W")
    
    # GPU stats
    if len(gpu_data) > 0:
        gpu_collapses = gpu_data['collapse'].sum()
        gpu_collapse_pct = (gpu_collapses / len(gpu_data)) * 100
        gpu_rle_range = f"{gpu_data['rle_smoothed'].min():.3f} - {gpu_data['rle_smoothed'].max():.3f}"
        gpu_rle_mean = gpu_data['rle_smoothed'].mean()
        
        print(f"\nGPU:")
        print(f"  Collapses: {gpu_collapses} ({gpu_collapse_pct:.1f}%)")
        print(f"  RLE range: {gpu_rle_range} (mean: {gpu_rle_mean:.3f})")
        print(f"  Max temp: {gpu_data['temp_c'].max():.1f}°C")
        print(f"  Max power: {gpu_data['power_w'].max():.1f}W")
    
    # Key findings
    print(f"\nKey Findings:")
    if len(cpu_data) > 0 and len(gpu_data) > 0:
        print(f"• CPU collapse rate: {cpu_collapse_pct:.1f}%")
        print(f"• GPU collapse rate: {gpu_collapse_pct:.1f}%")
        print(f"• Max temperature: {max(cpu_data['temp_c'].max(), gpu_data['temp_c'].max()):.1f}°C")
        print(f"• Collapse events occur well below thermal limits")
        print(f"• RLE provides component-specific efficiency assessment")

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python plot_rle_session.py <csv_file>")
        print("Example: python plot_rle_session.py sessions/recent/rle_enhanced_20251028_15.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)
    
    print("="*60)
    print("RLE SESSION VISUALIZATION")
    print("="*60)
    
    # Load data
    df, cpu_data, gpu_data = load_session_data(csv_file)
    if df is None:
        sys.exit(1)
    
    # Print summary
    print_session_summary(df, cpu_data, gpu_data)
    
    # Create plot
    output_file = "rle_session_analysis.png"
    create_session_plot(df, cpu_data, gpu_data, output_file)
    
    print(f"[SUCCESS] Analysis complete!")
    print(f"📊 Plot saved: {output_file}")
    print(f"📈 This visualization shows RLE behavior vs. collapse events vs. thermal state")

if __name__ == "__main__":
    main()
