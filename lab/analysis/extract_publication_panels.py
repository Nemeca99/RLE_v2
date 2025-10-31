#!/usr/bin/env python3
"""
Extract Single-Panel Publication Figures
Split comprehensive timeline into individual panels for paper
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import csv

def load_csv_safe(filepath):
    """Load CSV with malformed row handling"""
    rows = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        col_names = None
        
        for line_num, line in enumerate(reader, 1):
            if line_num == 1:
                col_names = line
                expected_cols = len(col_names)
                rows.append(line)
            else:
                if len(line) == expected_cols:
                    rows.append(line)
    
    df = pd.DataFrame(rows[1:], columns=rows[0])
    
    # Clean numeric columns
    for col in ['rle_smoothed', 'power_w', 'temp_c', 'util_pct', 'a_load']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['timestamp', 'device', 'rle_smoothed'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.dropna(subset=['timestamp'])
    
    if 'timestamp' in df.columns:
        start_time = df['timestamp'].min()
        df['seconds'] = (df['timestamp'] - start_time).dt.total_seconds()
    
    return df

def extract_knee(df):
    """Extract knee point for a device"""
    knees = {}
    
    for device in ['cpu', 'gpu']:
        device_df = df[df['device'] == device].copy()
        
        if len(device_df) == 0:
            continue
        
        # Compute cycles per joule
        device_df['cycles_per_joule'] = device_df['util_pct'] / (device_df['power_w'] + 1e-3) * 100
        device_df['cycles_per_joule'] = pd.to_numeric(device_df['cycles_per_joule'], errors='coerce')
        device_df = device_df.dropna(subset=['cycles_per_joule'])
        
        if len(device_df) < 30:
            continue
        
        # Smooth
        device_df['cycles_smooth'] = device_df['cycles_per_joule'].rolling(window=30, center=True).mean()
        device_df['power_smooth'] = device_df['power_w'].rolling(window=30, center=True).mean()
        
        # Find knee
        device_df['cycles_slope'] = device_df['cycles_smooth'].diff()
        device_df['power_slope'] = device_df['power_smooth'].diff()
        
        knee_mask = (device_df['cycles_slope'] < -0.01) & (device_df['power_slope'] > 0.1)
        knees_found = device_df[knee_mask]
        
        if len(knees_found) > 0:
            cycles_peak = device_df['cycles_per_joule'].max()
            for idx in knees_found.index:
                cycles = device_df.loc[idx, 'cycles_per_joule']
                if cycles < cycles_peak * 0.8:
                    knees[device] = {
                        'seconds': device_df.loc[idx, 'seconds'],
                        'power_w': device_df.loc[idx, 'power_w'],
                        'rle': device_df.loc[idx, 'rle_smoothed']
                    }
                    break
    
    return knees

def plot_panel_2a_rle_timeline(df, knees, output_dir):
    """Panel 2A: RLE Timeline with knee and instability"""
    
    cpu_df = df[df['device'] == 'cpu'].copy()
    gpu_df = df[df['device'] == 'gpu'].copy()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot RLE
    ax.plot(cpu_df['seconds'], cpu_df['rle_smoothed'], label='CPU RLE', 
             linewidth=1.5, alpha=0.8, color='blue')
    ax.plot(gpu_df['seconds'], gpu_df['rle_smoothed'], label='GPU RLE', 
             linewidth=1.5, alpha=0.8, color='red')
    
    # Mark knee points
    for device, knee in knees.items():
        ax.axvline(knee['seconds'], color='purple', linestyle='--', linewidth=2,
                  label=f'{device.upper()} Knee (t={knee["seconds"]/3600:.2f}h)')
    
    ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax.set_title('Figure 2A: RLE Predicts Collapse ~700ms Before Hardware Response', 
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/panel_2a_rle_timeline.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir}/panel_2a_rle_timeline.png")
    plt.close()

def plot_panel_2b_knee_boundary(df, knees, output_dir):
    """Panel 2B: Knee Boundary Map"""
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    for device in ['cpu', 'gpu']:
        device_df = df[df['device'] == device].copy()
        
        if len(device_df) == 0:
            continue
        
        # Scatter RLE vs Power
        ax.scatter(device_df['power_w'], device_df['rle_smoothed'], 
                  label=f'{device.upper()}', s=20, alpha=0.3)
        
        # Mark knee point
        if device in knees:
            k = knees[device]
            ax.scatter(k['power_w'], k['rle'], s=300, marker='*',
                      color='red' if device == 'gpu' else 'blue',
                      edgecolor='black', linewidth=2, zorder=10,
                      label=f'{device.upper()} Knee')
    
    ax.set_xlabel('Power (W)', fontsize=12, fontweight='bold')
    ax.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax.set_title('Figure 2B: Knee Point Boundary (Dont Operate Past This Line)', 
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/panel_2b_knee_boundary.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir}/panel_2b_knee_boundary.png")
    plt.close()

def plot_panel_2c1_thermal_isolation(df, output_dir):
    """Panel 2C1: Thermal Isolation (r ≈ 0)"""
    
    cpu_df = df[df['device'] == 'cpu'].copy()
    gpu_df = df[df['device'] == 'gpu'].copy()
    
    # Align by timestamp
    aligned_data = []
    for cpu_idx, cpu_row in cpu_df.iterrows():
        gpu_close = gpu_df[abs((gpu_df['timestamp'] - cpu_row['timestamp']).dt.total_seconds()) < 1]
        if len(gpu_close) > 0:
            gpu_row = gpu_close.iloc[0]
            aligned_data.append({
                'cpu_temp': cpu_row['temp_c'],
                'gpu_temp': gpu_row.get('vram_temp_c', gpu_row['temp_c'])
            })
    
    if len(aligned_data) == 0:
        return
    
    aligned_df = pd.DataFrame(aligned_data)
    
    # Convert to numeric
    aligned_df['cpu_temp'] = pd.to_numeric(aligned_df['cpu_temp'], errors='coerce')
    aligned_df['gpu_temp'] = pd.to_numeric(aligned_df['gpu_temp'], errors='coerce')
    aligned_df = aligned_df.dropna()
    
    if len(aligned_df) < 10:
        return
    
    fig, ax = plt.subplots(figsize=(8, 8))
    
    ax.scatter(aligned_df['cpu_temp'], aligned_df['gpu_temp'], alpha=0.4, s=30)
    
    # Calculate correlation
    from scipy.stats import pearsonr
    r, p = pearsonr(aligned_df['cpu_temp'], aligned_df['gpu_temp'])
    
    # Add diagonal
    min_temp = min(aligned_df['cpu_temp'].min(), aligned_df['gpu_temp'].min())
    max_temp = max(aligned_df['cpu_temp'].max(), aligned_df['gpu_temp'].max())
    ax.plot([min_temp, max_temp], [min_temp, max_temp], 'r--', alpha=0.3)
    
    ax.set_xlabel('CPU Temperature (°C)', fontsize=12, fontweight='bold')
    ax.set_ylabel('GPU Temperature (°C)', fontsize=12, fontweight='bold')
    ax.set_title(f'Figure 2C1: Isolated Thermal Configuration\nr = {r:.3f}', 
                 fontsize=14, fontweight='bold')
    ax.grid(alpha=0.3)
    
    # Add annotation
    ax.text(0.05, 0.95, f'Liquid-cooled CPU\nAir-cooled GPU\nr ≈ {r:.3f}', 
            transform=ax.transAxes, fontsize=11,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/panel_2c1_thermal_isolation.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir}/panel_2c1_thermal_isolation.png")
    plt.close()

def plot_panel_2d_efficiency_ceiling(df, output_dir):
    """Panel 2D: Efficiency Ceiling"""
    
    duration = df['seconds'].max() / 3600  # hours
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for device in ['cpu', 'gpu']:
        device_df = df[df['device'] == device].copy()
        
        if len(device_df) == 0:
            continue
        
        ax.plot(device_df['seconds'] / 3600, device_df['rle_smoothed'], 
               label=f'{device.upper()} RLE', linewidth=1.5, alpha=0.8)
        
        mean_rle = device_df['rle_smoothed'].mean()
        ax.axhline(mean_rle, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    ax.set_xlabel('Time (hours)', fontsize=12, fontweight='bold')
    ax.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax.set_title(f'Figure 2D: Efficiency Ceiling (Duration = {duration:.2f}h)', 
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/panel_2d_efficiency_ceiling.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir}/panel_2d_efficiency_ceiling.png")
    plt.close()

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_publication_panels.py <csv_file> [csv_file2 ...]")
        return
    
    csv_files = sys.argv[1:]
    
    print("\n" + "="*70)
    print("EXTRACTING PUBLICATION PANELS")
    print("="*70)
    
    # Load and merge
    dfs = []
    for csv_file in csv_files:
        df = load_csv_safe(csv_file)
        if len(df) > 0:
            dfs.append(df)
    
    if len(dfs) == 0:
        print("No valid data loaded")
        return
    
    merged_df = pd.concat(dfs, ignore_index=True).sort_values('timestamp').reset_index(drop=True)
    
    # Extract knee points
    knees = extract_knee(merged_df)
    
    output_dir = Path("sessions/archive/plots")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate panels
    print("\nGenerating publication panels...")
    plot_panel_2a_rle_timeline(merged_df, knees, output_dir)
    plot_panel_2b_knee_boundary(merged_df, knees, output_dir)
    plot_panel_2c1_thermal_isolation(merged_df, output_dir)
    plot_panel_2d_efficiency_ceiling(merged_df, output_dir)
    
    print("\n" + "="*70)
    print("EXTRACTION COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

