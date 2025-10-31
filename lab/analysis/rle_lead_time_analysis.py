#!/usr/bin/env python3
"""
RLE Lead-Time Analysis
Quantifies the temporal advantage: RLE predicts collapse before hardware responds
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

def analyze_lead_time(df, device='cpu'):
    """Find RLE drop before frequency wobble/collapse"""
    
    device_df = df[df['device'] == device].copy()
    if len(device_df) == 0:
        return None
    
    # Parse timestamps
    device_df['timestamp'] = pd.to_datetime(device_df['timestamp'], utc=True, errors='coerce')
    device_df['seconds'] = (device_df['timestamp'] - device_df['timestamp'].min()).dt.total_seconds()
    
    # Smooth RLE for trend detection
    device_df['rle_smooth'] = device_df['rle_smoothed'].rolling(window=10, center=True).mean()
    device_df['rle_slope'] = device_df['rle_smooth'].diff()
    
    # Find major RLE drops (>20% from peak)
    rle_peak = device_df['rle_smoothed'].max()
    rle_drops = device_df[device_df['rle_smoothed'] < 0.8 * rle_peak]
    
    if len(rle_drops) == 0:
        return None
    
    first_drop_time = rle_drops['seconds'].min()
    
    # Look for hardware response
    # Check for frequency changes (if cpu_freq_ghz exists)
    frequency_events = None
    if 'cpu_freq_ghz' in device_df.columns:
        device_df['freq_smooth'] = device_df['cpu_freq_ghz'].rolling(window=10, center=True).mean()
        device_df['freq_slope'] = device_df['freq_smooth'].diff()
        
        # Find frequency drops (>50 MHz)
        freq_drops = device_df[device_df['freq_slope'] < -0.05]
        if len(freq_drops) > 0:
            first_freq_event = freq_drops[freq_drops['seconds'] > first_drop_time]['seconds'].min()
            if pd.notna(first_freq_event):
                frequency_events = first_freq_event
    
    # Check for collapse flags
    collapse_events = None
    if 'collapse' in device_df.columns:
        collapse_col = pd.to_numeric(device_df['collapse'], errors='coerce').fillna(0)
        collapses = device_df[collapse_col > 0]
        if len(collapses) > 0:
            first_collapse = collapses[collapses['seconds'] > first_drop_time]['seconds'].min()
            if pd.notna(first_collapse):
                collapse_events = first_collapse
    
    # Calculate lead times
    lead_times = {}
    
    if frequency_events:
        lead_times['frequency'] = frequency_events - first_drop_time
    
    if collapse_events:
        lead_times['collapse'] = collapse_events - first_drop_time
    
    result = {
        'device': device,
        'first_drop_time': first_drop_time,
        'rle_at_drop': device_df[device_df['seconds'] == first_drop_time]['rle_smoothed'].values[0] if len(device_df[device_df['seconds'] == first_drop_time]) > 0 else None,
        'frequency_event': frequency_events,
        'collapse_event': collapse_events,
        'lead_times': lead_times
    }
    
    return result

def plot_lead_time_analysis(df, results, output_dir):
    """Plot RLE drop with hardware response markers"""
    
    if results is None:
        print("No lead-time events detected")
        return
    
    device = results['device']
    device_df = df[df['device'] == device].copy()
    
    # Parse timestamps
    device_df['timestamp'] = pd.to_datetime(device_df['timestamp'], utc=True, errors='coerce')
    device_df['seconds'] = (device_df['timestamp'] - device_df['timestamp'].min()).dt.total_seconds()
    
    # Focus on the event window (±5 minutes around first drop)
    first_drop = results['first_drop_time']
    window_start = max(0, first_drop - 300)
    window_end = first_drop + 300
    
    window_df = device_df[(device_df['seconds'] >= window_start) & (device_df['seconds'] <= window_end)].copy()
    
    fig, axes = plt.subplots(4, 1, figsize=(14, 10))
    
    # Panel 1: RLE with drop marker
    ax1 = axes[0]
    ax1.plot(window_df['seconds'], window_df['rle_smoothed'], label='RLE', linewidth=1.5, color='blue')
    ax1.axvline(first_drop, color='red', linestyle='--', linewidth=2, label=f'RLE Drop (t={first_drop:.0f}s)')
    ax1.set_ylabel('RLE', fontsize=11)
    ax1.set_title(f'{device.upper()} Lead-Time Analysis: RLE Predicts Hardware Response', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Panel 2: Frequency response (if available)
    if 'cpu_freq_ghz' in window_df.columns:
        ax2 = axes[1]
        ax2.plot(window_df['seconds'], window_df['cpu_freq_ghz'], label='CPU Frequency', linewidth=1.5, color='green')
        if results['frequency_event']:
            ax2.axvline(results['frequency_event'], color='orange', linestyle='--', linewidth=2, 
                       label=f'Frequency Response (t={results["frequency_event"]:.0f}s)')
            lead_time = results['lead_times'].get('frequency', 0)
            ax2.text(results['frequency_event'], ax2.get_ylim()[1]*0.95, 
                    f'Lead-time: {lead_time:.1f}s', ha='right', fontsize=10, 
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
        ax2.set_ylabel('Frequency (GHz)', fontsize=11)
        ax2.set_title('Hardware Response (Governor Intervention)', fontsize=12)
        ax2.legend()
        ax2.grid(alpha=0.3)
    
    # Panel 3: Power
    ax3 = axes[2]
    ax3.plot(window_df['seconds'], window_df['power_w'], label='Power', linewidth=1.5, color='purple')
    ax3.axvline(first_drop, color='red', linestyle='--', linewidth=2)
    ax3.set_ylabel('Power (W)', fontsize=11)
    ax3.set_title('Power Consumption', fontsize=12)
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # Panel 4: Temperature
    ax4 = axes[3]
    ax4.plot(window_df['seconds'], window_df['temp_c'], label='Temperature', linewidth=1.5, color='darkred')
    ax4.axvline(first_drop, color='red', linestyle='--', linewidth=2)
    ax4.set_xlabel('Time (seconds)', fontsize=11)
    ax4.set_ylabel('Temperature (°C)', fontsize=11)
    ax4.set_title('Thermal Response', fontsize=12)
    ax4.legend()
    ax4.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/rle_lead_time_{device}.png', dpi=200, bbox_inches='tight')
    print(f"\nSaved: {output_dir}/rle_lead_time_{device}.png")
    plt.close()
    
    # Print summary
    print("\n" + "="*70)
    print(f"LEAD-TIME ANALYSIS: {device.upper()}")
    print("="*70)
    print(f"RLE Drop Time: {first_drop:.1f}s")
    print(f"RLE at Drop: {results['rle_at_drop']:.3f}")
    
    for event_type, lead_time in results['lead_times'].items():
        print(f"\n{event_type.upper()} Response:")
        print(f"  Event Time: {results[f'{event_type}_event']:.1f}s")
        print(f"  Lead-Time: {lead_time:.3f}s")
        if lead_time > 0:
            print(f"  → RLE predicts {lead_time:.3f}s EARLY")
        else:
            print(f"  → No predictive advantage")
    
    print("\n" + "="*70)

def main():
    parser = argparse.ArgumentParser(description="RLE lead-time analysis")
    parser.add_argument("csv", help="CSV session file")
    parser.add_argument("--device", default="cpu", help="Device to analyze (cpu/gpu)")
    parser.add_argument("--plot", action="store_true", help="Generate visualization")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("RLE LEAD-TIME ANALYSIS")
    print("="*70)
    
    df = pd.read_csv(args.csv)
    
    # Analyze lead-time
    results = analyze_lead_time(df, device=args.device)
    
    # Generate visualization
    if args.plot and results:
        output_dir = Path("sessions/archive/plots")
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_lead_time_analysis(df, results, output_dir)
    
    print("\nAnalysis complete")

if __name__ == "__main__":
    main()

