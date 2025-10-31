#!/usr/bin/env python3
"""
Generate operating envelope visualizations
Plots RLE vs temperature, power, and efficiency maps
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse
from pathlib import Path

def plot_rle_temp_envelope(df, output_dir):
    """Plot RLE vs temperature with envelope zones"""
    
    cpu_df = df[df['device'] == 'cpu'].copy()
    
    # Filter for samples with temperature data
    if 'temp_c' in cpu_df.columns:
        valid = cpu_df['temp_c'].notna()
        
        if valid.sum() > 0:
            plt.figure(figsize=(10, 6))
            temp_data = cpu_df[valid]['temp_c']
            rle_data = cpu_df[valid]['rle_smoothed']
            
            plt.scatter(temp_data, rle_data, alpha=0.5, s=1)
            
            # Annotate zones
            plt.axhline(y=5.0, color='green', linestyle='--', linewidth=2, label='Optimal (>5.0)')
            plt.axhline(y=1.0, color='yellow', linestyle='--', linewidth=2, label='Good (1.0-5.0)')
            plt.axhline(y=0.3, color='red', linestyle='--', linewidth=2, label='Warning (<0.3)')
            
            plt.xlabel('Temperature (°C)', fontsize=12)
            plt.ylabel('RLE', fontsize=12)
            plt.title('RLE vs Temperature - Operating Envelope', fontsize=14, fontweight='bold')
            plt.legend()
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'{output_dir}/rle_temp_envelope.png', dpi=150)
            print(f"✓ Saved: {output_dir}/rle_temp_envelope.png")
            plt.close()
        else:
            print("⚠ No temperature data available")
    else:
        print("⚠ No temperature column in data")

def plot_rle_power_curve(df, output_dir):
    """Plot RLE vs power draw curve"""
    
    cpu_df = df[df['device'] == 'cpu'].copy()
    
    if 'power_w' in cpu_df.columns:
        valid = cpu_df['power_w'].notna()
        
        if valid.sum() > 0:
            plt.figure(figsize=(10, 6))
            power_data = cpu_df[valid]['power_w']
            rle_data = cpu_df[valid]['rle_smoothed']
            
            plt.scatter(power_data, rle_data, alpha=0.5, s=1)
            
            # Find sweet spot
            max_rle_idx = rle_data.idxmax()
            sweet_spot_power = power_data.loc[max_rle_idx]
            sweet_spot_rle = rle_data.loc[max_rle_idx]
            
            plt.axvline(x=sweet_spot_power, color='green', linestyle='--', 
                       linewidth=2, label=f'Peak RLE @ {sweet_spot_power:.1f}W')
            
            plt.xlabel('Power (W)', fontsize=12)
            plt.ylabel('RLE', fontsize=12)
            plt.title(f'RLE vs Power - Peak Efficiency at {sweet_spot_power:.1f}W', 
                     fontsize=14, fontweight='bold')
            plt.legend()
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'{output_dir}/rle_power_curve.png', dpi=150)
            print(f"✓ Saved: {output_dir}/rle_power_curve.png")
            plt.close()
        else:
            print("⚠ No power data available")
    else:
        print("⚠ No power column in data")

def plot_efficiency_map(df, output_dir):
    """Generate 2D efficiency map (util vs power color-coded by RLE)"""
    
    cpu_df = df[df['device'] == 'cpu'].copy()
    
    if 'util_pct' in cpu_df.columns and 'power_w' in cpu_df.columns and 'rle_smoothed' in cpu_df.columns:
        valid = cpu_df['util_pct'].notna() & cpu_df['power_w'].notna() & cpu_df['rle_smoothed'].notna()
        
        if valid.sum() > 0:
            plt.figure(figsize=(12, 8))
            
            util_data = cpu_df[valid]['util_pct']
            power_data = cpu_df[valid]['power_w']
            rle_data = cpu_df[valid]['rle_smoothed']
            
            scatter = plt.scatter(util_data, power_data, c=rle_data, 
                                cmap='RdYlGn', s=2, alpha=0.6)
            plt.colorbar(scatter, label='RLE')
            
            plt.xlabel('Utilization (%)', fontsize=12)
            plt.ylabel('Power (W)', fontsize=12)
            plt.title('Efficiency Map: Bright Green = Optimal Zone', 
                     fontsize=14, fontweight='bold')
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'{output_dir}/efficiency_map.png', dpi=150)
            print(f"✓ Saved: {output_dir}/efficiency_map.png")
            plt.close()
        else:
            print("⚠ Insufficient data for efficiency map")
    else:
        print("⚠ Missing required columns")

def main():
    parser = argparse.ArgumentParser(description="Generate RLE operating envelope plots")
    parser.add_argument("csv", help="Path to CSV file")
    
    args = parser.parse_args()
    
    print("="*70)
    print("GENERATING OPERATING ENVELOPE VISUALIZATIONS")
    print("="*70)
    print(f"Input: {args.csv}")
    
    # Create output directory
    output_dir = Path("sessions/archive/plots")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = pd.read_csv(args.csv)
    
    # Clean data
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.drop_duplicates(subset=['timestamp', 'device'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"\nLoaded {len(df)} samples")
    
    # Generate plots
    plot_rle_temp_envelope(df, output_dir)
    plot_rle_power_curve(df, output_dir)
    plot_efficiency_map(df, output_dir)
    
    print("\n" + "="*70)
    print("VISUALIZATION COMPLETE")
    print("="*70)
    print(f"\nPlots saved to: {output_dir}/")
    print("  - rle_temp_envelope.png")
    print("  - rle_power_curve.png")
    print("  - efficiency_map.png")

if __name__ == "__main__":
    main()

