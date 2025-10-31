#!/usr/bin/env python3
"""
RLE Time Derivative Analysis
Sanity check: Compute dRLE/dt to verify thermal saturation behavior
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import glob

def load_rle_data(csv_file):
    """Load RLE data"""
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def compute_derivative(df, device='cpu'):
    """Compute dRLE/dt for specified device"""
    device_df = df[df['device'] == device].copy()
    device_df = device_df.sort_values('timestamp').reset_index(drop=True)
    
    # Compute time differences
    device_df['time_elapsed'] = (device_df['timestamp'] - device_df['timestamp'].iloc[0]).dt.total_seconds()
    
    # Compute dRLE/dt
    device_df['dRLE_dt'] = np.gradient(device_df['rle_smoothed'], device_df['time_elapsed'])
    
    return device_df

def analyze_saturation_behavior(df_cpu, df_gpu, output_file="rle_time_derivative_analysis.png"):
    """Analyze if RLE derivative flattens over time (thermal saturation)"""
    
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.patch.set_facecolor('white')
    
    # Panel 1: RLE over time
    ax1 = axes[0, 0]
    ax1.plot(df_cpu['time_elapsed'], df_cpu['rle_smoothed'], 'b-', linewidth=2, label='CPU RLE')
    ax1.plot(df_gpu['time_elapsed'], df_gpu['rle_smoothed'], 'r-', linewidth=2, label='GPU RLE')
    ax1.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax1.set_title('RLE vs Time', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: dRLE/dt over time
    ax2 = axes[0, 1]
    ax2.plot(df_cpu['time_elapsed'], df_cpu['dRLE_dt'], 'b-', linewidth=2, label='CPU dRLE/dt')
    ax2.plot(df_gpu['time_elapsed'], df_gpu['dRLE_dt'], 'r-', linewidth=2, label='GPU dRLE/dt')
    ax2.axhline(0, color='gray', linestyle='--', alpha=0.5, label='Zero')
    ax2.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('dRLE/dt', fontsize=12, fontweight='bold')
    ax2.set_title('RLE Derivative vs Time', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Temperature over time
    ax3 = axes[1, 0]
    ax3.plot(df_cpu['time_elapsed'], df_cpu['temp_c'], 'b-', linewidth=2, label='CPU Temp')
    ax3.plot(df_gpu['time_elapsed'], df_gpu['temp_c'], 'r-', linewidth=2, label='GPU Temp')
    ax3.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Temperature (°C)', fontsize=12, fontweight='bold')
    ax3.set_title('Temperature vs Time', fontsize=14, fontweight='bold')
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    
    # Panel 4: Collapse events
    ax4 = axes[1, 1]
    cpu_collapse_mask = df_cpu['collapse'] == 1
    gpu_collapse_mask = df_gpu['collapse'] == 1
    ax4.scatter(df_cpu[cpu_collapse_mask]['time_elapsed'], 
                df_cpu[cpu_collapse_mask]['rle_smoothed'],
                color='blue', s=100, zorder=5, label='CPU Collapses', marker='x')
    ax4.scatter(df_gpu[gpu_collapse_mask]['time_elapsed'],
                df_gpu[gpu_collapse_mask]['rle_smoothed'],
                color='red', s=100, zorder=5, label='GPU Collapses', marker='x')
    ax4.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax4.set_title('Collapse Events over Time', fontsize=14, fontweight='bold')
    ax4.legend(loc='upper right')
    ax4.grid(True, alpha=0.3)
    
    # Panel 5: Running std of dRLE/dt (saturation check)
    ax5 = axes[2, 0]
    window = 10  # 10-sample window
    df_cpu['dRLE_dt_std'] = df_cpu['dRLE_dt'].rolling(window=window, center=True).std()
    df_gpu['dRLE_dt_std'] = df_gpu['dRLE_dt'].rolling(window=window, center=True).std()
    ax5.plot(df_cpu['time_elapsed'], df_cpu['dRLE_dt_std'], 'b-', linewidth=2, label='CPU Std(dRLE/dt)')
    ax5.plot(df_gpu['time_elapsed'], df_gpu['dRLE_dt_std'], 'r-', linewidth=2, label='GPU Std(dRLE/dt)')
    ax5.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Std(dRLE/dt)', fontsize=12, fontweight='bold')
    ax5.set_title('RLE Derivative Stability (Saturation Check)', fontsize=14, fontweight='bold')
    ax5.legend(loc='upper right')
    ax5.grid(True, alpha=0.3)
    
    # Panel 6: Power vs RLE
    ax6 = axes[2, 1]
    ax6.scatter(df_cpu['power_w'], df_cpu['rle_smoothed'], color='blue', alpha=0.6, label='CPU', s=50)
    ax6.scatter(df_gpu['power_w'], df_gpu['rle_smoothed'], color='red', alpha=0.6, label='GPU', s=50)
    ax6.set_xlabel('Power (W)', fontsize=12, fontweight='bold')
    ax6.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax6.set_title('Power vs RLE', fontsize=14, fontweight='bold')
    ax6.legend(loc='upper right')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Derivative analysis saved: {output_file}")

def main():
    """Main analysis"""
    print("="*70)
    print("RLE TIME DERIVATIVE ANALYSIS")
    print("="*70)
    print("Sanity check: Verify thermal saturation behavior")
    print()
    
    # Find most recent RLE file
    csv_files = sorted(Path("sessions/recent").glob("rle_enhanced_*.csv"), 
                      key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not csv_files:
        print("[ERROR] No RLE data found")
        return
    
    csv_file = csv_files[0]
    print(f"[INFO] Loading: {csv_file}")
    
    df = load_rle_data(csv_file)
    print(f"[SUCCESS] Loaded {len(df)} samples")
    
    # Compute derivatives
    df_cpu = compute_derivative(df, 'cpu')
    df_gpu = compute_derivative(df, 'gpu')
    
    # Analysis
    print("\n" + "="*70)
    print("DERIVATIVE ANALYSIS")
    print("="*70)
    
    cpu_mean_dRLE = df_cpu['dRLE_dt'].abs().mean()
    gpu_mean_dRLE = df_gpu['dRLE_dt'].abs().mean()
    
    print(f"\nCPU dRLE/dt:")
    print(f"  Mean absolute value: {cpu_mean_dRLE:.6f}")
    print(f"  Std: {df_cpu['dRLE_dt'].std():.6f}")
    print(f"  Range: [{df_cpu['dRLE_dt'].min():.6f}, {df_cpu['dRLE_dt'].max():.6f}]")
    
    print(f"\nGPU dRLE/dt:")
    print(f"  Mean absolute value: {gpu_mean_dRLE:.6f}")
    print(f"  Std: {df_gpu['dRLE_dt'].std():.6f}")
    print(f"  Range: [{df_gpu['dRLE_dt'].min():.6f}, {df_gpu['dRLE_dt'].max():.6f}]")
    
    # Saturation check
    window = 10
    cpu_late_std = df_cpu['dRLE_dt'].rolling(window=window, center=True).std().tail(10).mean()
    gpu_late_std = df_gpu['dRLE_dt'].rolling(window=window, center=True).std().tail(10).mean()
    
    print(f"\nSaturation Analysis (last 10 samples):")
    print(f"  CPU std(dRLE/dt): {cpu_late_std:.6f}")
    print(f"  GPU std(dRLE/dt): {gpu_late_std:.6f}")
    
    if cpu_late_std < 0.001 and gpu_late_std < 0.001:
        print("\n✅ RLE derivative flattened → thermal saturation confirmed")
    else:
        print("\n⚠️  RLE still changing → residual load modulation present")
    
    # Generate visualization
    analyze_saturation_behavior(df_cpu, df_gpu)
    
    print("\n" + "="*70)
    print("DERIVATIVE ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

