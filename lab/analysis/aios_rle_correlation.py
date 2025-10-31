#!/usr/bin/env python3
"""
AIOS-RLE Correlation Analysis
Analyzes correlation between AIOS core activity and thermal efficiency
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob
import os
from datetime import datetime

def load_experiment_data():
    """Load RLE and AIOS bridge data from most recent experiment"""
    
    # Find most recent RLE data
    rle_files = glob.glob("sessions/recent/rle_enhanced_*.csv")
    if not rle_files:
        print("[ERROR] No RLE data found")
        return None, None
    
    latest_rle = max(rle_files, key=os.path.getctime)
    print(f"[INFO] Loading RLE data: {latest_rle}")
    
    # Find most recent AIOS bridge data
    bridge_files = glob.glob("sessions/recent/aios_rle_bridge_*.csv")
    if not bridge_files:
        print("[ERROR] No AIOS bridge data found")
        return None, None
    
    latest_bridge = max(bridge_files, key=os.path.getctime)
    print(f"[INFO] Loading AIOS data: {latest_bridge}")
    
    # Load data
    rle_data = pd.read_csv(latest_rle)
    bridge_data = pd.read_csv(latest_bridge)
    
    return rle_data, bridge_data

def merge_data(rle_data, bridge_data):
    """Merge RLE and AIOS data by timestamp"""
    
    # Convert timestamps to datetime
    rle_data['timestamp'] = pd.to_datetime(rle_data['timestamp'])
    bridge_data['timestamp'] = pd.to_datetime(bridge_data['timestamp'])
    
    # Merge on timestamp (with 1-second tolerance)
    merged = pd.merge_asof(
        rle_data.sort_values('timestamp'),
        bridge_data.sort_values('timestamp'),
        on='timestamp',
        direction='nearest',
        tolerance=pd.Timedelta(seconds=1)
    )
    
    print(f"[INFO] Merged {len(merged)} samples")
    return merged

def calculate_correlations(merged_data):
    """Calculate correlation matrix between AIOS and thermal metrics"""
    
    # Select relevant columns
    correlation_cols = [
        'aios_processes', 'aios_cpu_percent', 'aios_memory_mb', 'active_cores',
        'rle_smoothed', 'temp_c', 'power_w', 'util_pct', 'collapse'
    ]
    
    # Filter to available columns
    available_cols = [col for col in correlation_cols if col in merged_data.columns]
    correlation_data = merged_data[available_cols]
    
    # Calculate correlation matrix
    correlation_matrix = correlation_data.corr()
    
    return correlation_matrix

def create_correlation_plot(merged_data, output_file="aios_rle_correlation.png"):
    """Create multi-panel correlation visualization"""
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.patch.set_facecolor('white')
    
    # Panel 1: AIOS Activity vs RLE
    ax1 = axes[0, 0]
    if 'active_cores' in merged_data.columns and 'rle_smoothed' in merged_data.columns:
        ax1.scatter(merged_data['active_cores'], merged_data['rle_smoothed'], 
                   alpha=0.6, s=20)
        ax1.set_xlabel('Active AIOS Cores')
        ax1.set_ylabel('RLE (Smoothed)')
        ax1.set_title('AIOS Core Activity vs Thermal Efficiency')
        ax1.grid(True, alpha=0.3)
    
    # Panel 2: AIOS CPU vs Temperature
    ax2 = axes[0, 1]
    if 'aios_cpu_percent' in merged_data.columns and 'temp_c' in merged_data.columns:
        ax2.scatter(merged_data['aios_cpu_percent'], merged_data['temp_c'], 
                   alpha=0.6, s=20, color='orange')
        ax2.set_xlabel('AIOS CPU Usage (%)')
        ax2.set_ylabel('Temperature (°C)')
        ax2.set_title('AIOS CPU Usage vs Temperature')
        ax2.grid(True, alpha=0.3)
    
    # Panel 3: Time series - AIOS Activity
    ax3 = axes[1, 0]
    if 'timestamp' in merged_data.columns and 'active_cores' in merged_data.columns:
        ax3.plot(merged_data['timestamp'], merged_data['active_cores'], 
                linewidth=2, label='Active Cores')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Active Cores')
        ax3.set_title('AIOS Core Activity Over Time')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    
    # Panel 4: Time series - RLE
    ax4 = axes[1, 1]
    if 'timestamp' in merged_data.columns and 'rle_smoothed' in merged_data.columns:
        ax4.plot(merged_data['timestamp'], merged_data['rle_smoothed'], 
                linewidth=2, color='purple', label='RLE')
        ax4.set_xlabel('Time')
        ax4.set_ylabel('RLE')
        ax4.set_title('Thermal Efficiency Over Time')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Correlation plot saved: {output_file}")

def analyze_workload_signatures(merged_data):
    """Analyze thermal signatures by AIOS workload state"""
    
    print("\n" + "="*60)
    print("AIOS WORKLOAD THERMAL SIGNATURES")
    print("="*60)
    
    if 'active_cores' not in merged_data.columns:
        print("[ERROR] No active_cores data available")
        return
    
    # Define workload states
    idle_mask = merged_data['active_cores'] == 0
    single_core_mask = merged_data['active_cores'] == 1
    multi_core_mask = merged_data['active_cores'] > 1
    
    workload_states = [
        ('Idle', idle_mask),
        ('Single Core', single_core_mask),
        ('Multi-Core', multi_core_mask)
    ]
    
    for state_name, mask in workload_states:
        if not mask.any():
            continue
            
        state_data = merged_data[mask]
        print(f"\n{state_name} State ({len(state_data)} samples):")
        
        if 'rle_smoothed' in state_data.columns:
            rle_mean = state_data['rle_smoothed'].mean()
            rle_std = state_data['rle_smoothed'].std()
            print(f"  RLE: {rle_mean:.3f} ± {rle_std:.3f}")
        
        if 'temp_c' in state_data.columns:
            temp_mean = state_data['temp_c'].mean()
            temp_std = state_data['temp_c'].std()
            print(f"  Temperature: {temp_mean:.1f}°C ± {temp_std:.1f}°C")
        
        if 'aios_cpu_percent' in state_data.columns:
            cpu_mean = state_data['aios_cpu_percent'].mean()
            cpu_std = state_data['aios_cpu_percent'].std()
            print(f"  AIOS CPU: {cpu_mean:.1f}% ± {cpu_std:.1f}%")
        
        if 'collapse' in state_data.columns:
            collapse_rate = state_data['collapse'].mean() * 100
            print(f"  Collapse Rate: {collapse_rate:.1f}%")

def main():
    """Main analysis entry point"""
    
    print("="*70)
    print("AIOS-RLE CORRELATION ANALYSIS")
    print("="*70)
    print("Analyzing correlation between AIOS core activity and thermal efficiency\n")
    
    # Load data
    rle_data, bridge_data = load_experiment_data()
    if rle_data is None or bridge_data is None:
        print("[FAILED] Could not load experiment data")
        return
    
    # Merge data
    merged_data = merge_data(rle_data, bridge_data)
    if merged_data.empty:
        print("[FAILED] Could not merge data")
        return
    
    # Calculate correlations
    correlation_matrix = calculate_correlations(merged_data)
    
    print("\nCorrelation Matrix:")
    print(correlation_matrix.round(3))
    
    # Create visualization
    create_correlation_plot(merged_data)
    
    # Analyze workload signatures
    analyze_workload_signatures(merged_data)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("Files generated:")
    print("• aios_rle_correlation.png - Multi-panel correlation plot")
    print()
    print("Key findings:")
    print("• Check correlation matrix for AIOS-thermal relationships")
    print("• Review workload signatures for thermal fingerprinting")
    print("• Examine time series plots for temporal patterns")

if __name__ == "__main__":
    main()
