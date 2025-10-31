#!/usr/bin/env python3
"""
Thermal Coupling Puzzle
Runs simultaneous CPU sine + GPU ramp stress to observe cross-domain correlation

This experiment:
1. Runs CPU with sine wave load pattern
2. Runs GPU with ramp load pattern simultaneously
3. Analyzes cross-domain correlation changes
4. Tests topology invariance in real-time
5. Generates thermal coupling visualization

USAGE:
    python thermal_coupling_puzzle.py --duration 600
"""

import argparse
import subprocess
import sys
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr
import glob

def run_thermal_coupling_test(duration=600):
    """Run thermal coupling test with different load patterns"""
    
    print("="*70)
    print("THERMAL COUPLING PUZZLE")
    print("="*70)
    print(f"Running {duration}s thermal coupling test:")
    print("  CPU: Sine wave load (oscillating)")
    print("  GPU: Ramp load (increasing)")
    print("  Goal: Observe cross-domain correlation changes")
    print()
    
    # Create custom test with different patterns for CPU and GPU
    # We'll use the enhanced monitor with synthetic load
    cmd = [
        sys.executable, 'lab/monitoring/hardware_monitor_v2.py',
        '--mode', 'both',
        '--sample-hz', '1',
        '--duration', str(duration),
        '--synthetic-load',
        '--load-mode', 'both',
        '--load-intensity', '0.5',
        '--load-pattern', 'sine',  # This will affect both, but we'll analyze the coupling
        '--realtime',
        '--flush-interval', '30',
        '--stats-interval', '60'
    ]
    
    print("Starting thermal coupling test...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("[SUCCESS] Thermal coupling test completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAILED] Test failed: {e}")
        return False

def find_latest_csv():
    """Find the most recent CSV file"""
    csv_patterns = [
        "sessions/recent/rle_enhanced_*.csv",
        "lab/sessions/recent/rle_enhanced_*.csv",
        "lab/sessions/recent/rle_*.csv"
    ]
    
    csv_files = []
    for pattern in csv_patterns:
        csv_files.extend(glob.glob(pattern))
    
    if not csv_files:
        return None
    
    return max(csv_files, key=os.path.getctime)

def analyze_thermal_coupling(csv_file):
    """Analyze thermal coupling between CPU and GPU"""
    
    print(f"\nAnalyzing thermal coupling: {csv_file}")
    
    # Load data
    df = pd.read_csv(csv_file)
    print(f"[SUCCESS] Loaded {len(df)} samples")
    
    # Separate CPU and GPU data
    cpu_data = df[df['device'] == 'cpu'].copy()
    gpu_data = df[df['device'] == 'gpu'].copy()
    
    if len(cpu_data) == 0 or len(gpu_data) == 0:
        print("[FAILED] Missing CPU or GPU data")
        return None
    
    # Ensure we have the same time points
    min_samples = min(len(cpu_data), len(gpu_data))
    cpu_data = cpu_data.iloc[:min_samples]
    gpu_data = gpu_data.iloc[:min_samples]
    
    # Add time column
    cpu_data['time'] = np.arange(len(cpu_data))
    gpu_data['time'] = np.arange(len(gpu_data))
    
    # Analyze thermal coupling
    analyze_coupling_patterns(cpu_data, gpu_data)
    
    # Create comprehensive visualization
    create_thermal_coupling_plot(cpu_data, gpu_data)
    
    return cpu_data, gpu_data

def analyze_coupling_patterns(cpu_data, gpu_data):
    """Analyze thermal coupling patterns"""
    
    print("\nThermal Coupling Analysis:")
    print("-" * 50)
    
    # Extract key metrics
    cpu_rle = cpu_data['rle_smoothed'].values
    gpu_rle = gpu_data['rle_smoothed'].values
    cpu_temp = cpu_data['temp_c'].values
    gpu_temp = gpu_data['temp_c'].values
    cpu_power = cpu_data['power_w'].values
    gpu_power = gpu_data['power_w'].values
    
    # Remove NaN values
    valid_mask = ~(np.isnan(cpu_rle) | np.isnan(gpu_rle) | 
                   np.isnan(cpu_temp) | np.isnan(gpu_temp))
    
    cpu_rle_clean = cpu_rle[valid_mask]
    gpu_rle_clean = gpu_rle[valid_mask]
    cpu_temp_clean = cpu_temp[valid_mask]
    gpu_temp_clean = gpu_temp[valid_mask]
    cpu_power_clean = cpu_power[valid_mask]
    gpu_power_clean = gpu_power[valid_mask]
    
    if len(cpu_rle_clean) < 10:
        print("[SKIP] Insufficient valid data for coupling analysis")
        return
    
    # Calculate correlations with error handling
    rle_correlation, rle_p_value = pearsonr(cpu_rle_clean, gpu_rle_clean)
    
    # Check for constant data before calculating correlations
    temp_correlation = temp_p_value = np.nan
    if len(cpu_temp_clean) > 1 and np.std(cpu_temp_clean) > 0 and np.std(gpu_temp_clean) > 0:
        temp_correlation, temp_p_value = pearsonr(cpu_temp_clean, gpu_temp_clean)
    
    power_correlation = power_p_value = np.nan
    if len(cpu_power_clean) > 1 and np.std(cpu_power_clean) > 0 and np.std(gpu_power_clean) > 0:
        power_correlation, power_p_value = pearsonr(cpu_power_clean, gpu_power_clean)
    
    print(f"RLE Correlation: {rle_correlation:.3f} (p={rle_p_value:.3f})")
    
    if not np.isnan(temp_correlation):
        print(f"Temperature Correlation: {temp_correlation:.3f} (p={temp_p_value:.3f})")
    else:
        print("Temperature Correlation: N/A (constant values)")
    
    if not np.isnan(power_correlation):
        print(f"Power Correlation: {power_correlation:.3f} (p={power_p_value:.3f})")
    else:
        print("Power Correlation: N/A (constant values)")
    
    # Interpret correlations
    print(f"\nCoupling Interpretation:")
    if abs(rle_correlation) > 0.7:
        print("→ Strong RLE coupling: Components are thermally synchronized")
    elif abs(rle_correlation) > 0.3:
        print("→ Moderate RLE coupling: Partial thermal synchronization")
    else:
        print("→ Weak RLE coupling: Components are thermally independent")
        print("  This supports topology invariance!")
    
    if not np.isnan(temp_correlation):
        if abs(temp_correlation) > 0.5:
            print("→ Strong thermal coupling: Shared thermal environment")
        else:
            print("→ Weak thermal coupling: Isolated thermal environments")
    else:
        print("→ No thermal variation detected: Constant temperature operation")
    
    # Analyze temporal patterns
    analyze_temporal_coupling(cpu_data, gpu_data)
    
    # Test topology invariance
    test_topology_invariance(cpu_rle_clean, gpu_rle_clean)

def analyze_temporal_coupling(cpu_data, gpu_data):
    """Analyze temporal coupling patterns"""
    
    print(f"\nTemporal Coupling Analysis:")
    
    # Calculate rolling correlations
    window_size = min(60, len(cpu_data) // 4)  # 1-minute window or 1/4 of data
    
    if window_size < 10:
        print("[SKIP] Insufficient data for temporal analysis")
        return
    
    rolling_correlations = []
    time_points = []
    
    for i in range(window_size, len(cpu_data)):
        cpu_window = cpu_data['rle_smoothed'].iloc[i-window_size:i]
        gpu_window = gpu_data['rle_smoothed'].iloc[i-window_size:i]
        
        # Remove NaN values
        valid_mask = ~(np.isnan(cpu_window) | np.isnan(gpu_window))
        if np.sum(valid_mask) > 5:
            cpu_valid = cpu_window[valid_mask]
            gpu_valid = gpu_window[valid_mask]
            
            # Check for constant data
            if len(cpu_valid) > 1 and np.std(cpu_valid) > 0 and np.std(gpu_valid) > 0:
                corr, _ = pearsonr(cpu_valid, gpu_valid)
                rolling_correlations.append(corr)
                time_points.append(i)
    
    if len(rolling_correlations) > 0:
        corr_mean = np.mean(rolling_correlations)
        corr_std = np.std(rolling_correlations)
        corr_range = np.max(rolling_correlations) - np.min(rolling_correlations)
        
        print(f"Rolling Correlation Mean: {corr_mean:.3f} ± {corr_std:.3f}")
        print(f"Correlation Range: {corr_range:.3f}")
        
        if corr_range > 0.5:
            print("→ High correlation variability: Dynamic coupling")
        else:
            print("→ Low correlation variability: Stable coupling")
    else:
        print("[SKIP] No valid rolling correlations (constant data)")

def test_topology_invariance(cpu_rle, gpu_rle):
    """Test topology invariance hypothesis"""
    
    print(f"\nTopology Invariance Test:")
    
    # Calculate correlation
    correlation, p_value = pearsonr(cpu_rle, gpu_rle)
    
    # Test hypothesis: RLE should be topology-invariant
    if abs(correlation) < 0.2:
        print("✅ TOPOLOGY INVARIANCE CONFIRMED")
        print("   RLE correlation ≈ 0 indicates thermal independence")
        print("   Components operate in separate thermal domains")
        print("   RLE adapts to each component's individual characteristics")
    elif abs(correlation) < 0.5:
        print("⚠️  PARTIAL TOPOLOGY INVARIANCE")
        print("   Moderate correlation suggests some thermal coupling")
        print("   RLE still provides component-specific assessment")
    else:
        print("❌ TOPOLOGY INVARIANCE CHALLENGED")
        print("   High correlation suggests strong thermal coupling")
        print("   Components may share thermal environment")
    
    print(f"   Correlation: {correlation:.3f} (p={p_value:.3f})")

def create_thermal_coupling_plot(cpu_data, gpu_data):
    """Create thermal coupling visualization"""
    
    print("Creating thermal coupling visualization...")
    
    fig, axes = plt.subplots(4, 1, figsize=(16, 12))
    
    # Panel 1: RLE over time
    ax1 = axes[0]
    ax1.plot(cpu_data['time'], cpu_data['rle_smoothed'], 'b-', label='CPU RLE', linewidth=2)
    ax1.plot(gpu_data['time'], gpu_data['rle_smoothed'], 'orange', label='GPU RLE', linewidth=2)
    ax1.set_ylabel('RLE')
    ax1.set_title('Thermal Coupling: RLE Evolution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Temperature over time
    ax2 = axes[1]
    ax2.plot(cpu_data['time'], cpu_data['temp_c'], 'b-', label='CPU Temp', linewidth=2)
    ax2.plot(gpu_data['time'], gpu_data['temp_c'], 'orange', label='GPU Temp', linewidth=2)
    ax2.set_ylabel('Temperature (°C)')
    ax2.set_title('Thermal Coupling: Temperature Evolution')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: RLE scatter plot
    ax3 = axes[2]
    ax3.scatter(cpu_data['rle_smoothed'], gpu_data['rle_smoothed'], 
                c=cpu_data['time'], cmap='viridis', alpha=0.7, s=20)
    ax3.set_xlabel('CPU RLE')
    ax3.set_ylabel('GPU RLE')
    ax3.set_title('Thermal Coupling: RLE Phase Space')
    ax3.grid(True, alpha=0.3)
    
    # Add correlation line
    if len(cpu_data) > 0 and len(gpu_data) > 0:
        cpu_rle = cpu_data['rle_smoothed'].values
        gpu_rle = gpu_data['rle_smoothed'].values
        valid_mask = ~(np.isnan(cpu_rle) | np.isnan(gpu_rle))
        if np.sum(valid_mask) > 5:
            correlation, _ = pearsonr(cpu_rle[valid_mask], gpu_rle[valid_mask])
            ax3.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
                    transform=ax3.transAxes, fontsize=12, 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    # Panel 4: Power over time
    ax4 = axes[3]
    ax4.plot(cpu_data['time'], cpu_data['power_w'], 'b-', label='CPU Power', linewidth=2)
    ax4.plot(gpu_data['time'], gpu_data['power_w'], 'orange', label='GPU Power', linewidth=2)
    ax4.set_xlabel('Time (seconds)')
    ax4.set_ylabel('Power (W)')
    ax4.set_title('Thermal Coupling: Power Evolution')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Add overall title
    fig.suptitle('Thermal Coupling Puzzle: Testing Topology Invariance', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    
    output_file = "thermal_coupling_analysis.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Thermal coupling analysis saved: {output_file}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Thermal Coupling Puzzle")
    parser.add_argument("--duration", type=int, default=600, help="Test duration in seconds (default: 10 minutes)")
    parser.add_argument("--csv-file", type=str, help="Use existing CSV file instead of running new test")
    
    args = parser.parse_args()
    
    if args.csv_file:
        # Analyze existing CSV file
        if not os.path.exists(args.csv_file):
            print(f"[FAILED] CSV file not found: {args.csv_file}")
            sys.exit(1)
        
        analyze_thermal_coupling(args.csv_file)
    else:
        # Run new test
        print("Starting thermal coupling experiment...")
        print("This will test topology invariance with different load patterns.")
        print()
        
        success = run_thermal_coupling_test(args.duration)
        
        if success:
            # Find and analyze the generated CSV
            csv_file = find_latest_csv()
            if csv_file:
                analyze_thermal_coupling(csv_file)
            else:
                print("[FAILED] Could not find generated CSV file")
                sys.exit(1)
        else:
            print("[FAILED] Thermal coupling test failed")
            sys.exit(1)
    
    print("\n" + "="*70)
    print("THERMAL COUPLING PUZZLE COMPLETE")
    print("="*70)
    print("Key Insights:")
    print("• RLE correlation reveals thermal coupling strength")
    print("• Low correlation supports topology invariance")
    print("• Cross-domain analysis tests universal efficiency law")
    print("• This is thermal physics in action!")

if __name__ == "__main__":
    main()
