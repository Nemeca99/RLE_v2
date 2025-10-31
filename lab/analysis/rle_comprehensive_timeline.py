#!/usr/bin/env python3
"""
RLE Comprehensive Timeline Analysis
Merges multiple sessions, overlays all metrics, marks instability windows, extracts efficiency knee.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import argparse
from pathlib import Path

def load_and_clean_csv(filepath):
    """Load CSV with error handling for malformed rows"""
    print(f"Loading: {filepath}")
    
    rows_before = 0
    rows_after = 0
    
    try:
        # Try reading line by line to handle malformed rows
        import csv
        
        rows = []
        col_names = None
        expected_cols = None
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            line_num = 0
            
            for line in reader:
                line_num += 1
                
                if line_num == 1:
                    # Header row
                    col_names = line
                    expected_cols = len(col_names)
                    rows.append(line)
                else:
                    # Data row - skip if column count doesn't match
                    if len(line) == expected_cols:
                        rows.append(line)
                    # Silently skip malformed lines (too many to report individually)
        
        if col_names is None:
            print(f"  Error: Could not read header")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(rows[1:], columns=rows[0])
        
        rows_before = len(df)
        
        # Clean malformed rows (any row with NaN in critical columns)
        required_cols = ['timestamp', 'device', 'rle_smoothed']
        df = df.dropna(subset=required_cols)
        
        # Remove rows where critical numeric columns are non-numeric
        for col in ['rle_smoothed', 'power_w', 'temp_c', 'util_pct', 'a_load']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop any remaining NaN in critical metrics
        df = df.dropna(subset=['rle_smoothed'])
        rows_after = len(df)
        
        print(f"  Rows: {rows_before} -> {rows_after} (dropped {rows_before - rows_after} malformed)")
        
    except Exception as e:
        print(f"  Error loading {filepath}: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return df

def merge_sessions(csv_files):
    """Load and merge multiple session files into unified timeline"""
    
    print("="*70)
    print("LOADING AND MERGING SESSIONS")
    print("="*70)
    
    all_dfs = []
    
    for filepath in csv_files:
        df = load_and_clean_csv(filepath)
        if df is not None and len(df) > 0:
            all_dfs.append(df)
    
    if len(all_dfs) == 0:
        print("ERROR: No valid data loaded")
        return None
    
    # Concatenate all dataframes
    merged_df = pd.concat(all_dfs, ignore_index=True)
    
    # Parse timestamps
    merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'], utc=True, errors='coerce')
    merged_df = merged_df.dropna(subset=['timestamp'])
    
    # Sort by timestamp
    merged_df = merged_df.sort_values('timestamp').reset_index(drop=True)
    
    # Create unified timeline (seconds from start)
    start_time = merged_df['timestamp'].min()
    merged_df['seconds'] = (merged_df['timestamp'] - start_time).dt.total_seconds()
    
    print(f"\nMerged {len(all_dfs)} session(s)")
    print(f"Total samples: {len(merged_df)}")
    print(f"Duration: {merged_df['seconds'].max() / 3600:.2f} hours")
    print(f"Start: {start_time}")
    print(f"End: {merged_df['timestamp'].max()}")
    
    return merged_df

def identify_instability_windows(df):
    """Mark periods where collapse or alerts are present"""
    
    instability = {
        'cpu': [],
        'gpu': []
    }
    
    for device in ['cpu', 'gpu']:
        device_df = df[df['device'] == device].copy()
        
        if len(device_df) == 0:
            continue
        
        # Detect instability periods
        collapse_active = False
        collapse_start = None
        alerts_active = False
        alerts_start = None
        
        for idx, row in device_df.iterrows():
            seconds = row['seconds']
            
            # Check collapse flag (handle as numeric)
            collapse_val = row.get('collapse', 0)
            try:
                collapse_val = float(collapse_val) if pd.notna(collapse_val) else 0
            except (ValueError, TypeError):
                collapse_val = 0
            is_collapse = collapse_val > 0
            
            # Check alerts
            alerts = row.get('alerts', '')
            has_alerts = pd.notna(alerts) and alerts != '' and str(alerts).strip() != ''
            
            # Collapse tracking
            if is_collapse:
                if not collapse_active:
                    collapse_active = True
                    collapse_start = seconds
            else:
                if collapse_active:
                    instability[device].append(('collapse', collapse_start, seconds))
                    collapse_active = False
            if collapse_active and idx == len(device_df) - 1:
                # Still active at end
                instability[device].append(('collapse', collapse_start, seconds))
            
            # Alerts tracking
            if has_alerts:
                if not alerts_active:
                    alerts_active = True
                    alerts_start = seconds
            else:
                if alerts_active:
                    instability[device].append(('alerts', alerts_start, seconds))
                    alerts_active = False
            if alerts_active and idx == len(device_df) - 1:
                instability[device].append(('alerts', alerts_start, seconds))
    
    return instability

def extract_efficiency_knee(df):
    """Find the point where cycles_per_joule falls off while power keeps climbing"""
    
    print("\n" + "="*70)
    print("EXTRACTING EFFICIENCY KNEE")
    print("="*70)
    
    knees = {}
    
    for device in ['cpu', 'gpu']:
        device_df = df[df['device'] == device].copy()
        
        if len(device_df) == 0:
            continue
        
        # Need cycles_per_joule or can compute it
        if 'cycles_per_joule' not in device_df.columns:
            # Compute from util and power
            device_df['cycles_per_joule'] = device_df['util_pct'] / (device_df['power_w'] + 1e-3) * 100
        
        # Convert to numeric, handle strings
        device_df['cycles_per_joule'] = pd.to_numeric(device_df['cycles_per_joule'], errors='coerce')
        device_df['power_w'] = pd.to_numeric(device_df['power_w'], errors='coerce')
        
        # Remove any remaining NaN
        device_df = device_df.dropna(subset=['cycles_per_joule', 'power_w'])
        
        if len(device_df) == 0:
            continue
        
        # Smooth the signal
        device_df['cycles_smooth'] = device_df['cycles_per_joule'].rolling(window=30, center=True).mean()
        device_df['power_smooth'] = device_df['power_w'].rolling(window=30, center=True).mean()
        
        # Find region where cycles is falling while power is rising
        device_df['cycles_slope'] = device_df['cycles_smooth'].diff()
        device_df['power_slope'] = device_df['power_smooth'].diff()
        
        # Knee: negative cycles slope AND positive power slope
        knee_mask = (device_df['cycles_slope'] < -0.01) & (device_df['power_slope'] > 0.1)
        knee_indices = device_df[knee_mask].index
        
        if len(knee_indices) > 0:
            # Find first major knee (where efficiency drops significantly)
            for idx in knee_indices:
                seconds = device_df.loc[idx, 'seconds']
                cycles = device_df.loc[idx, 'cycles_per_joule']
                power = device_df.loc[idx, 'power_w']
                
                # Check if this is a significant drop (>20% from peak)
                cycles_peak = device_df['cycles_per_joule'].max()
                if cycles < cycles_peak * 0.8:
                    knees[device] = {
                        'seconds': seconds,
                        'cycles_per_joule': cycles,
                        'power_w': power,
                        'rle': device_df.loc[idx, 'rle_smoothed']
                    }
                    break
        
        if device in knees:
            k = knees[device]
            print(f"\n{device.upper()} Knee:")
            print(f"  Time: {k['seconds']:.0f}s ({k['seconds']/3600:.2f}h)")
            print(f"  Cycles/Joule: {k['cycles_per_joule']:.2f}")
            print(f"  Power: {k['power_w']:.1f}W")
            print(f"  RLE: {k['rle']:.2f}")
        else:
            print(f"\n{device.upper()}: No knee detected (stable operation)")
    
    return knees

def plot_comprehensive_timeline(df, instability, knees, output_dir):
    """Generate comprehensive multi-panel timeline visualization"""
    
    print("\n" + "="*70)
    print("GENERATING VISUALIZATION")
    print("="*70)
    
    # Separate devices
    cpu_df = df[df['device'] == 'cpu'].copy()
    gpu_df = df[df['device'] == 'gpu'].copy()
    
    if len(cpu_df) == 0 or len(gpu_df) == 0:
        print("ERROR: Missing device data")
        return
    
    # Create figure with multiple subplots
    fig = plt.figure(figsize=(20, 16))
    gs = fig.add_gridspec(6, 2, hspace=0.3, wspace=0.3)
    
    # Helper to plot instability windows
    def add_instability_patches(ax, device, color='red', alpha=0.15):
        if device not in instability:
            return
        for event_type, start, end in instability[device]:
            if event_type == 'collapse':
                rect = mpatches.Rectangle((start, ax.get_ylim()[0]), end-start, 
                                         ax.get_ylim()[1] - ax.get_ylim()[0],
                                         facecolor=color, alpha=alpha, edgecolor=None)
                ax.add_patch(rect)
            elif event_type == 'alerts':
                rect = mpatches.Rectangle((start, ax.get_ylim()[0]), end-start, 
                                         ax.get_ylim()[1] - ax.get_ylim()[0],
                                         facecolor='orange', alpha=alpha*0.5, edgecolor=None)
                ax.add_patch(rect)
    
    # Helper to mark knee points
    def mark_knee(ax, device):
        if device in knees:
            k = knees[device]
            ax.axvline(k['seconds'], color='purple', linestyle='--', linewidth=2, 
                      label=f"Knee ({k['seconds']/3600:.1f}h)")
            ax.legend()
    
    # Row 0: RLE Overlay
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(cpu_df['seconds'], cpu_df['rle_smoothed'], label='CPU RLE', 
             linewidth=1.2, alpha=0.8, color='blue')
    ax1.plot(gpu_df['seconds'], gpu_df['rle_smoothed'], label='GPU RLE', 
             linewidth=1.2, alpha=0.8, color='red')
    add_instability_patches(ax1, 'cpu', 'blue', 0.1)
    add_instability_patches(ax1, 'gpu', 'red', 0.1)
    mark_knee(ax1, 'cpu')
    mark_knee(ax1, 'gpu')
    ax1.set_xlabel('Time (seconds)', fontsize=10)
    ax1.set_ylabel('RLE', fontsize=10)
    ax1.set_title('RLE Timeline Overlay with Instability Windows', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Row 1: Temperature overlay
    ax2 = fig.add_subplot(gs[1, :])
    ax2.plot(cpu_df['seconds'], cpu_df['temp_c'], label='CPU Temp (°C)', 
             linewidth=1.0, alpha=0.8, color='blue')
    ax2.plot(gpu_df['seconds'], gpu_df.get('vram_temp_c', gpu_df['temp_c']), 
             label='GPU VRAM Temp (°C)', linewidth=1.0, alpha=0.8, color='red')
    add_instability_patches(ax2, 'cpu', 'blue', 0.1)
    add_instability_patches(ax2, 'gpu', 'red', 0.1)
    mark_knee(ax2, 'cpu')
    mark_knee(ax2, 'gpu')
    ax2.set_xlabel('Time (seconds)', fontsize=10)
    ax2.set_ylabel('Temperature (°C)', fontsize=10)
    ax2.set_title('Temperature Timeline', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    # Row 2: Power overlay
    ax3 = fig.add_subplot(gs[2, :])
    ax3.plot(cpu_df['seconds'], cpu_df['power_w'], label='CPU Power (W)', 
             linewidth=1.0, alpha=0.8, color='blue')
    ax3.plot(gpu_df['seconds'], gpu_df['power_w'], label='GPU Power (W)', 
             linewidth=1.0, alpha=0.8, color='red')
    add_instability_patches(ax3, 'cpu', 'blue', 0.1)
    add_instability_patches(ax3, 'gpu', 'red', 0.1)
    mark_knee(ax3, 'cpu')
    mark_knee(ax3, 'gpu')
    ax3.set_xlabel('Time (seconds)', fontsize=10)
    ax3.set_ylabel('Power (W)', fontsize=10)
    ax3.set_title('Power Timeline', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # Row 3: cycles_per_joule
    if 'cycles_per_joule' in cpu_df.columns or 'cycles_per_joule' in gpu_df.columns:
        ax4 = fig.add_subplot(gs[3, :])
        
        # Compute if missing
        if 'cycles_per_joule' not in cpu_df.columns:
            cpu_df['cycles_per_joule'] = cpu_df['util_pct'] / (cpu_df['power_w'] + 1e-3) * 100
        if 'cycles_per_joule' not in gpu_df.columns:
            gpu_df['cycles_per_joule'] = gpu_df['util_pct'] / (gpu_df['power_w'] + 1e-3) * 100
        
        # Convert to numeric
        cpu_df['cycles_per_joule'] = pd.to_numeric(cpu_df['cycles_per_joule'], errors='coerce')
        gpu_df['cycles_per_joule'] = pd.to_numeric(gpu_df['cycles_per_joule'], errors='coerce')
        
        # Filter out NaN
        cpu_df = cpu_df.dropna(subset=['cycles_per_joule'])
        gpu_df = gpu_df.dropna(subset=['cycles_per_joule'])
        
        ax4.plot(cpu_df['seconds'], cpu_df['cycles_per_joule'], label='CPU Cycles/Joule', 
                 linewidth=1.0, alpha=0.8, color='blue')
        ax4.plot(gpu_df['seconds'], gpu_df['cycles_per_joule'], label='GPU Cycles/Joule', 
                 linewidth=1.0, alpha=0.8, color='red')
        add_instability_patches(ax4, 'cpu', 'blue', 0.1)
        add_instability_patches(ax4, 'gpu', 'red', 0.1)
        mark_knee(ax4, 'cpu')
        mark_knee(ax4, 'gpu')
        ax4.set_xlabel('Time (seconds)', fontsize=10)
        ax4.set_ylabel('Cycles per Joule', fontsize=10)
        ax4.set_title('Efficiency Timeline (Cycles per Joule)', fontsize=12, fontweight='bold')
        ax4.legend()
        ax4.grid(alpha=0.3)
    
    # Row 4: CPU frequency (if available)
    if 'cpu_freq_ghz' in cpu_df.columns:
        ax5 = fig.add_subplot(gs[4, :])
        ax5.plot(cpu_df['seconds'], cpu_df['cpu_freq_ghz'], label='CPU Freq (GHz)', 
                 linewidth=1.0, alpha=0.8, color='blue')
        add_instability_patches(ax5, 'cpu', 'blue', 0.1)
        mark_knee(ax5, 'cpu')
        ax5.set_xlabel('Time (seconds)', fontsize=10)
        ax5.set_ylabel('CPU Frequency (GHz)', fontsize=10)
        ax5.set_title('CPU Clock Behavior', fontsize=12, fontweight='bold')
        ax5.legend()
        ax5.grid(alpha=0.3)
    
    # Row 5: RLE vs Time (scatter to show density)
    ax6 = fig.add_subplot(gs[5, 0])
    ax6.scatter(cpu_df['seconds'], cpu_df['rle_smoothed'], s=1, alpha=0.3, color='blue', label='CPU')
    ax6.scatter(gpu_df['seconds'], gpu_df['rle_smoothed'], s=1, alpha=0.3, color='red', label='GPU')
    add_instability_patches(ax6, 'cpu', 'blue', 0.1)
    add_instability_patches(ax6, 'gpu', 'red', 0.1)
    ax6.set_xlabel('Time (seconds)', fontsize=10)
    ax6.set_ylabel('RLE', fontsize=10)
    ax6.set_title('RLE Scatter (Full Dataset)', fontsize=12, fontweight='bold')
    ax6.legend()
    ax6.grid(alpha=0.3)
    
    # RLE efficiency curve
    ax7 = fig.add_subplot(gs[5, 1])
    ax7.scatter(cpu_df['power_w'], cpu_df['rle_smoothed'], s=1, alpha=0.3, color='blue', label='CPU')
    ax7.scatter(gpu_df['power_w'], gpu_df['rle_smoothed'], s=1, alpha=0.3, color='red', label='GPU')
    if 'cpu' in knees:
        ax7.scatter(knees['cpu']['power_w'], knees['cpu']['rle'], 
                   s=200, color='purple', marker='*', edgecolor='black', 
                   linewidth=1, label='CPU Knee', zorder=10)
    if 'gpu' in knees:
        ax7.scatter(knees['gpu']['power_w'], knees['gpu']['rle'], 
                   s=200, color='magenta', marker='*', edgecolor='black', 
                   linewidth=1, label='GPU Knee', zorder=10)
    ax7.set_xlabel('Power (W)', fontsize=10)
    ax7.set_ylabel('RLE', fontsize=10)
    ax7.set_title('RLE vs Power (Efficiency Map)', fontsize=12, fontweight='bold')
    ax7.legend()
    ax7.grid(alpha=0.3)
    
    plt.savefig(f'{output_dir}/rle_comprehensive_timeline.png', dpi=200, bbox_inches='tight')
    print(f"\nSaved: {output_dir}/rle_comprehensive_timeline.png")
    plt.close()

def print_analysis_summary(df, instability, knees):
    """Print comprehensive analysis summary"""
    
    print("\n" + "="*70)
    print("ANALYSIS SUMMARY")
    print("="*70)
    
    for device in ['cpu', 'gpu']:
        device_df = df[df['device'] == device].copy()
        
        if len(device_df) == 0:
            continue
        
        print(f"\n{device.upper()}:")
        print(f"  Samples: {len(device_df)}")
        print(f"  Duration: {device_df['seconds'].max() / 3600:.2f} hours")
        
        # RLE stats
        print(f"  RLE: {device_df['rle_smoothed'].mean():.2f} ± {device_df['rle_smoothed'].std():.2f}")
        print(f"    Min: {device_df['rle_smoothed'].min():.2f}, Max: {device_df['rle_smoothed'].max():.2f}")
        
        # Collapse count
        if 'collapse' in device_df.columns:
            collapse_col = pd.to_numeric(device_df['collapse'], errors='coerce')
            collapse_count = int(collapse_col.sum()) if pd.notna(collapse_col.sum()) else 0
        else:
            collapse_count = 0
        collapse_pct = (collapse_count / len(device_df)) * 100 if len(device_df) > 0 else 0
        print(f"  Collapses: {collapse_count} ({collapse_pct:.1f}%)")
        
        # Instability windows
        windows = instability.get(device, [])
        print(f"  Instability windows: {len(windows)}")
        for event_type, start, end in windows:
            print(f"    {event_type}: {start/3600:.2f}h - {end/3600:.2f}h ({end-start:.0f}s)")
        
        # Knee
        if device in knees:
            print(f"  Knee detected at {knees[device]['seconds']/3600:.2f}h")
    
    print("\n" + "="*70)
    print("KEY INSIGHTS")
    print("="*70)
    
    # Which device becomes limiting factor first
    cpu_df = df[df['device'] == 'cpu'].copy()
    gpu_df = df[df['device'] == 'gpu'].copy()
    
    if len(cpu_df) > 0 and len(gpu_df) > 0:
        # Find when each device's RLE drops below 50% of its peak
        cpu_peak = cpu_df['rle_smoothed'].max()
        gpu_peak = gpu_df['rle_smoothed'].max()
        
        cpu_low = cpu_df[cpu_df['rle_smoothed'] < cpu_peak * 0.5]
        gpu_low = gpu_df[gpu_df['rle_smoothed'] < gpu_peak * 0.5]
        
        if len(cpu_low) > 0 and len(gpu_low) > 0:
            cpu_first = cpu_low['seconds'].min()
            gpu_first = gpu_low['seconds'].min()
            
            if cpu_first < gpu_first:
                print("CPU becomes limiting factor first (thermal inefficiency)")
            else:
                print("GPU becomes limiting factor first (thermal inefficiency)")
        else:
            print("Both devices maintain >50% of peak RLE")
    
    # Predictive control viability
    # Check if RLE drops BEFORE collapse flags
    for device in ['cpu', 'gpu']:
        device_df = df[df['device'] == device].copy()
        if len(device_df) == 0 or 'collapse' not in device_df.columns:
            continue
        
        # Find collapse periods (convert to numeric first)
        if 'collapse' in device_df.columns:
            collapse_col = pd.to_numeric(device_df['collapse'], errors='coerce').fillna(0)
            collapses = device_df[collapse_col > 0]
        else:
            collapses = pd.DataFrame()
        
        if len(collapses) > 0:
            first_collapse_time = collapses['seconds'].min()
            before_collapse = device_df[device_df['seconds'] < first_collapse_time]
            
            if len(before_collapse) > 0:
                avg_rle_before = before_collapse['rle_smoothed'].mean()
                avg_rle_collapse = collapses['rle_smoothed'].mean()
                
                if avg_rle_before > avg_rle_collapse:
                    drop = ((avg_rle_before - avg_rle_collapse) / avg_rle_before) * 100
                    print(f"{device.upper()}: RLE drops {drop:.1f}% before collapse detected")
                    print(f"  → Predictive control viable (early warning system)")

def main():
    parser = argparse.ArgumentParser(description="RLE comprehensive timeline analysis")
    parser.add_argument("csv_files", nargs='+', help="CSV files to merge and analyze")
    parser.add_argument("--plot", action="store_true", help="Generate comprehensive visualization")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("RLE COMPREHENSIVE TIMELINE ANALYSIS")
    print("="*70)
    
    # Merge sessions
    merged_df = merge_sessions(args.csv_files)
    
    if merged_df is None or len(merged_df) == 0:
        print("ERROR: No data to analyze")
        return
    
    # Identify instability windows
    instability = identify_instability_windows(merged_df)
    
    # Extract efficiency knee
    knees = extract_efficiency_knee(merged_df)
    
    # Print summary
    print_analysis_summary(merged_df, instability, knees)
    
    # Generate visualization
    if args.plot:
        output_dir = Path("sessions/archive/plots")
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_comprehensive_timeline(merged_df, instability, knees, output_dir)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. Review knee points for automatic throttling policy")
    print("  2. Analyze instability windows for predictive patterns")
    print("  3. Extract 'don't operate past this line' boundary")
    print("  4. Validate control model on live data")

if __name__ == "__main__":
    main()

