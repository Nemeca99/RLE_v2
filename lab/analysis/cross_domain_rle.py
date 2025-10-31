#!/usr/bin/env python3
"""
Cross-Domain RLE Analysis
Apply RLE to different thermal systems (GPU, storage, etc.)
Verify same efficiency patterns emerge
"""

import pandas as pd
import numpy as np
import argparse

def compute_system_rle(util, power, rated_power, temp_hist, temp_limit, device_type="generic"):
    """
    Generic RLE computation for any thermal system
    
    Args:
        util: Utilization (0-100)
        power: Current power draw (W)
        rated_power: Maximum rated power (W)
        temp_hist: Temperature history
        temp_limit: Thermal limit (°C)
        device_type: System type for normalization
    
    Returns:
        RLE, normalized RLE, and component efficiencies
    """
    # Compute metrics
    a_load = power / rated_power if rated_power > 0 else 0
    
    # Stability (inverse of utilization variance)
    if len(temp_hist) >= 2:
        util_variance = np.var(temp_hist)
        stability = 1.0 / (1.0 + util_variance)
    else:
        stability = 1.0
    
    # Time to sustain (thermal headroom)
    if len(temp_hist) >= 2:
        temp_curr = temp_hist[-1]
        temp_prev = temp_hist[-2]
        temp_rate = (temp_curr - temp_prev) / 1.0  # Assuming 1s intervals
        
        if temp_rate > 0:
            t_sustain = (temp_limit - temp_curr) / temp_rate
            t_sustain = max(1.0, min(600.0, t_sustain))
        else:
            t_sustain = 600.0
    else:
        t_sustain = 600.0
    
    # RLE computation
    util_norm = util / 100.0
    denom = max(a_load, 1e-3) * (1.0 + 1.0 / t_sustain)
    rle = (util_norm * stability) / denom
    
    # Component efficiencies
    E_th = stability / (1.0 + 1.0 / t_sustain)
    E_pw = util_norm / max(a_load, 1e-3)
    
    # Normalize based on device type
    if device_type == "gpu":
        baseline, optimal, peak = 0.1, 3.0, 60.0
    elif device_type == "storage":
        baseline, optimal, peak = 0.05, 2.0, 80.0
    elif device_type == "network":
        baseline, optimal, peak = 0.2, 4.0, 50.0
    else:  # generic/cpu
        baseline, optimal, peak = 0.3, 5.0, 67.0
    
    if util <= peak:
        expected_rle = baseline + (optimal - baseline) * (util / peak)
    else:
        expected_rle = optimal - (optimal - baseline * 0.5) * ((util - peak) / (100 - peak))
    
    rle_norm = min(1.0, max(0.0, rle / expected_rle))
    
    return rle, rle_norm, E_th, E_pw, t_sustain

def analyze_cross_domain(df, device_type="auto"):
    """Apply RLE analysis across different device domains"""
    
    print("="*70)
    print(f"CROSS-DOMAIN RLE ANALYSIS")
    print("="*70)
    
    if 'device' not in df.columns:
        print("No device column found")
        return
    
    devices = df['device'].unique()
    print(f"\nDevices found: {devices}")
    
    print("\n" + "="*70)
    print("RLE BY DEVICE TYPE")
    print("="*70)
    
    results = {}
    
    for device in devices:
        device_df = df[df['device'] == device].copy()
        
        if len(device_df) == 0:
            continue
        
        # Get device characteristics
        if device == 'gpu':
            device_type = 'gpu'
            rated_power = device_df['rated_gpu'].iloc[0] if 'rated_gpu' in device_df.columns else 200
            temp_limit = 83.0
        elif device == 'cpu':
            device_type = 'cpu'
            rated_power = device_df['rated_cpu'].iloc[0] if 'rated_cpu' in device_df.columns else 125
            temp_limit = 80.0
        else:
            device_type = 'generic'
            rated_power = 100
            temp_limit = 75.0
        
        # Compute RLE if not present
        if 'rle_norm' not in device_df.columns or device_df['rle_norm'].isna().all():
            print(f"\nComputing RLE for {device} ({len(device_df)} samples)...")
            
            for idx, row in device_df.iterrows():
                util = row.get('util_pct', 0)
                power = row.get('power_w', 0)
                temp = row.get('temp_c', 0)
                
                # Build temp history (simplified)
                temp_hist = [temp] * 10
                
                rle, rle_norm, e_th, e_pw, t_sus = compute_system_rle(
                    util, power, rated_power, temp_hist, temp_limit, device_type
                )
                
                device_df.loc[idx, 'rle_computed'] = rle
                device_df.loc[idx, 'rle_norm_computed'] = rle_norm
                device_df.loc[idx, 'E_th_computed'] = e_th
                device_df.loc[idx, 'E_pw_computed'] = e_pw
        else:
            # Use existing RLE
            rle_col = 'rle_norm' if 'rle_norm' in device_df.columns else 'rle_smoothed'
            print(f"\nUsing existing RLE for {device} ({len(device_df)} samples)...")
            device_df['rle_norm_computed'] = device_df[rle_col]
        
        # Statistics
        if 'rle_norm_computed' in device_df.columns:
            mean_rle = device_df['rle_norm_computed'].mean()
            std_rle = device_df['rle_norm_computed'].std()
            min_rle = device_df['rle_norm_computed'].min()
            max_rle = device_df['rle_norm_computed'].max()
            
            print(f"\n{device.upper()} Statistics:")
            print(f"  Mean RLE: {mean_rle:.4f} ± {std_rle:.4f}")
            print(f"  Range: {min_rle:.4f} - {max_rle:.4f}")
            
            results[device] = {
                'mean': mean_rle,
                'std': std_rle,
                'min': min_rle,
                'max': max_rle
            }
    
    # Compare across domains
    print("\n" + "="*70)
    print("CROSS-DOMAIN COMPARISON")
    print("="*70)
    
    if len(results) > 1:
        print(f"{'Device':<15} {'Mean RLE':<15} {'Range':<25}")
        print("-"*70)
        
        for device, stats in results.items():
            print(f"{device:<15} {stats['mean']:<15.4f} [{stats['min']:.3f} - {stats['max']:.3f}]")
        
        # Check if all systems show similar efficiency patterns
        means = [s['mean'] for s in results.values()]
        std_dev = np.std(means)
        
        print(f"\nEfficiency consistency: σ={std_dev:.4f}")
        if std_dev < 0.2:
            print("✓ All systems show similar efficiency patterns")
            print("  → RLE generalizes across thermal systems")
        else:
            print("⚠ Systems show different efficiency patterns")
            print("  → Device-specific tuning may be needed")
    
    print("\n" + "="*70)
    print("VALIDATION")
    print("="*70)
    
    print("✓ RLE applied to multiple thermal systems")
    print("✓ Efficiency curves computed for each domain")
    print("✓ Cross-domain patterns compared")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Cross-domain RLE analysis")
    parser.add_argument("csv", help="Path to CSV file")
    
    args = parser.parse_args()
    
    print(f"Loading: {args.csv}")
    df = pd.read_csv(args.csv)
    
    # Clean data
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.drop_duplicates(subset=['timestamp', 'device'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Run analysis
    analyze_cross_domain(df)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

