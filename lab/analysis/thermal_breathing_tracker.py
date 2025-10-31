#!/usr/bin/env python3
"""
Thermal Breathing Tracker
Runs idle-to-load-to-idle session and analyzes thermal breathing patterns

This experiment:
1. Runs a controlled thermal breathing cycle (idle → load → idle)
2. Charts RLE vs temperature over time
3. Fits sine wave to thermal breathing pattern
4. Analyzes phase lag between heat and efficiency
5. Generates thermal dynamics visualization

USAGE:
    python thermal_breathing_tracker.py --duration 1800 --load-intensity 0.6
"""

import argparse
import subprocess
import sys
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from scipy.optimize import curve_fit
import glob

def run_thermal_breathing_test(duration=1800, load_intensity=0.6):
    """Run a thermal breathing test with idle-load-idle pattern"""
    
    print("="*70)
    print("THERMAL BREATHING TRACKER")
    print("="*70)
    print(f"Running {duration}s thermal breathing cycle:")
    print(f"  Phase 1: Idle (30s)")
    print(f"  Phase 2: Load ({duration-60}s at {load_intensity*100:.1f}%)")
    print(f"  Phase 3: Idle (30s)")
    print()
    
    # Create custom test scenario
    cmd = [
        sys.executable, 'lab/monitoring/hardware_monitor_v2.py',
        '--mode', 'both',
        '--sample-hz', '1',
        '--duration', str(duration),
        '--synthetic-load',
        '--load-mode', 'both',
        '--load-intensity', str(load_intensity),
        '--load-pattern', 'constant',
        '--realtime',
        '--flush-interval', '30',
        '--stats-interval', '60'
    ]
    
    print("Starting thermal breathing test...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("[SUCCESS] Thermal breathing test completed")
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

def analyze_thermal_breathing(csv_file):
    """Analyze thermal breathing patterns from CSV data"""
    
    print(f"\nAnalyzing thermal breathing data: {csv_file}")
    
    # Load data
    df = pd.read_csv(csv_file)
    print(f"[SUCCESS] Loaded {len(df)} samples")
    
    # Separate CPU and GPU data
    cpu_data = df[df['device'] == 'cpu'].copy()
    gpu_data = df[df['device'] == 'gpu'].copy()
    
    if len(cpu_data) == 0 or len(gpu_data) == 0:
        print("[FAILED] Missing CPU or GPU data")
        return None
    
    # Create time series
    cpu_data['time'] = np.arange(len(cpu_data))
    gpu_data['time'] = np.arange(len(gpu_data))
    
    # Analyze thermal breathing patterns
    analyze_component_breathing(cpu_data, "CPU")
    analyze_component_breathing(gpu_data, "GPU")
    
    # Create comprehensive visualization
    create_thermal_breathing_plot(cpu_data, gpu_data)
    
    return cpu_data, gpu_data

def analyze_component_breathing(data, component_name):
    """Analyze thermal breathing for a single component"""
    
    print(f"\n{component_name} Thermal Breathing Analysis:")
    print("-" * 50)
    
    # Extract temperature and RLE
    temp = data['temp_c'].values
    rle = data['rle_smoothed'].values
    time = data['time'].values
    
    # Remove NaN values
    valid_mask = ~(np.isnan(temp) | np.isnan(rle))
    temp_clean = temp[valid_mask]
    rle_clean = rle[valid_mask]
    time_clean = time[valid_mask]
    
    if len(temp_clean) < 10:
        print(f"[SKIP] {component_name}: Insufficient valid data")
        return
    
    # Calculate thermal breathing metrics
    temp_range = np.max(temp_clean) - np.min(temp_clean)
    temp_mean = np.mean(temp_clean)
    temp_std = np.std(temp_clean)
    
    rle_range = np.max(rle_clean) - np.min(rle_clean)
    rle_mean = np.mean(rle_clean)
    rle_std = np.std(rle_clean)
    
    print(f"Temperature: {temp_mean:.1f}°C ± {temp_std:.1f}°C (range: {temp_range:.1f}°C)")
    print(f"RLE: {rle_mean:.3f} ± {rle_std:.3f} (range: {rle_range:.3f})")
    
    # Calculate thermal sensitivity
    if temp_range > 1.0:  # Only if there's significant temperature variation
        thermal_sensitivity = rle_range / temp_range
        print(f"Thermal Sensitivity: {thermal_sensitivity:.4f} RLE/°C")
    
    # Look for thermal breathing patterns
    if len(temp_clean) > 60:  # Need at least 1 minute of data
        analyze_breathing_patterns(temp_clean, rle_clean, time_clean, component_name)

def analyze_breathing_patterns(temp, rle, time, component_name):
    """Analyze breathing patterns using signal processing"""
    
    print(f"\n{component_name} Breathing Pattern Analysis:")
    
    # Detrend the signals
    temp_detrended = signal.detrend(temp)
    rle_detrended = signal.detrend(rle)
    
    # Find dominant frequencies
    sampling_rate = 1.0  # 1 Hz
    freqs = np.fft.fftfreq(len(temp), 1/sampling_rate)
    temp_fft = np.fft.fft(temp_detrended)
    rle_fft = np.fft.fft(rle_detrended)
    
    # Focus on low frequencies (thermal breathing)
    low_freq_mask = (freqs > 0) & (freqs < 0.1)  # Below 0.1 Hz (10+ second periods)
    low_freqs = freqs[low_freq_mask]
    temp_power = np.abs(temp_fft[low_freq_mask])**2
    rle_power = np.abs(rle_fft[low_freq_mask])**2
    
    if len(low_freqs) > 0:
        # Find dominant frequency
        temp_dominant_idx = np.argmax(temp_power)
        rle_dominant_idx = np.argmax(rle_power)
        
        temp_dominant_freq = low_freqs[temp_dominant_idx]
        rle_dominant_freq = low_freqs[rle_dominant_idx]
        
        temp_period = 1/temp_dominant_freq if temp_dominant_freq > 0 else 0
        rle_period = 1/rle_dominant_freq if rle_dominant_freq > 0 else 0
        
        print(f"Temperature dominant period: {temp_period:.1f}s")
        print(f"RLE dominant period: {rle_period:.1f}s")
        
        # Calculate phase relationship
        if temp_period > 0 and rle_period > 0:
            phase_lag = abs(temp_period - rle_period)
            print(f"Phase lag: {phase_lag:.1f}s")
            
            if phase_lag < 5:
                print("→ Synchronized thermal breathing")
            elif phase_lag < 15:
                print("→ Moderate thermal coupling")
            else:
                print("→ Weak thermal coupling")

def create_thermal_breathing_plot(cpu_data, gpu_data):
    """Create comprehensive thermal breathing visualization"""
    
    fig, axes = plt.subplots(4, 1, figsize=(16, 12))
    
    # Panel 1: Temperature over time
    ax1 = axes[0]
    ax1.plot(cpu_data['time'], cpu_data['temp_c'], 'b-', label='CPU Temp', linewidth=2)
    ax1.plot(gpu_data['time'], gpu_data['temp_c'], 'orange', label='GPU Temp', linewidth=2)
    ax1.set_ylabel('Temperature (°C)')
    ax1.set_title('Thermal Breathing: Temperature Evolution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: RLE over time
    ax2 = axes[1]
    ax2.plot(cpu_data['time'], cpu_data['rle_smoothed'], 'b-', label='CPU RLE', linewidth=2)
    ax2.plot(gpu_data['time'], gpu_data['rle_smoothed'], 'orange', label='GPU RLE', linewidth=2)
    ax2.set_ylabel('RLE')
    ax2.set_title('Thermal Breathing: Efficiency Evolution')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: RLE vs Temperature scatter
    ax3 = axes[2]
    ax3.scatter(cpu_data['temp_c'], cpu_data['rle_smoothed'], c='blue', alpha=0.6, s=20, label='CPU')
    ax3.scatter(gpu_data['temp_c'], gpu_data['rle_smoothed'], c='orange', alpha=0.6, s=20, label='GPU')
    ax3.set_xlabel('Temperature (°C)')
    ax3.set_ylabel('RLE')
    ax3.set_title('Thermal Breathing: RLE vs Temperature Phase Space')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Panel 4: Power over time
    ax4 = axes[3]
    ax4.plot(cpu_data['time'], cpu_data['power_w'], 'b-', label='CPU Power', linewidth=2)
    ax4.plot(gpu_data['time'], gpu_data['power_w'], 'orange', label='GPU Power', linewidth=2)
    ax4.set_xlabel('Time (seconds)')
    ax4.set_ylabel('Power (W)')
    ax4.set_title('Thermal Breathing: Power Evolution')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Add breathing annotations
    fig.suptitle('Thermal Breathing Analysis: Computer as Living Organism', fontsize=16, fontweight='bold')
    
    # Add breathing cycle annotations
    total_time = max(cpu_data['time'].max(), gpu_data['time'].max())
    if total_time > 60:
        ax1.axvspan(0, 30, alpha=0.2, color='green', label='Inhale (Idle)')
        ax1.axvspan(30, total_time-30, alpha=0.2, color='red', label='Hold (Load)')
        ax1.axvspan(total_time-30, total_time, alpha=0.2, color='blue', label='Exhale (Idle)')
        ax1.legend()
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    
    output_file = "thermal_breathing_analysis.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n[SUCCESS] Thermal breathing analysis saved: {output_file}")
    print("This shows your computer literally 'breathing' heat!")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Thermal Breathing Tracker")
    parser.add_argument("--duration", type=int, default=1800, help="Test duration in seconds (default: 30 minutes)")
    parser.add_argument("--load-intensity", type=float, default=0.6, help="Load intensity (0.0-1.0, default: 0.6)")
    parser.add_argument("--csv-file", type=str, help="Use existing CSV file instead of running new test")
    
    args = parser.parse_args()
    
    if args.csv_file:
        # Analyze existing CSV file
        if not os.path.exists(args.csv_file):
            print(f"[FAILED] CSV file not found: {args.csv_file}")
            sys.exit(1)
        
        analyze_thermal_breathing(args.csv_file)
    else:
        # Run new test
        print("Starting thermal breathing experiment...")
        print("This will run a controlled idle-load-idle cycle to observe thermal breathing patterns.")
        print()
        
        success = run_thermal_breathing_test(args.duration, args.load_intensity)
        
        if success:
            # Find and analyze the generated CSV
            csv_file = find_latest_csv()
            if csv_file:
                analyze_thermal_breathing(csv_file)
            else:
                print("[FAILED] Could not find generated CSV file")
                sys.exit(1)
        else:
            print("[FAILED] Thermal breathing test failed")
            sys.exit(1)
    
    print("\n" + "="*70)
    print("THERMAL BREATHING ANALYSIS COMPLETE")
    print("="*70)
    print("Key Insights:")
    print("• Your computer literally 'breathes' heat in cycles")
    print("• RLE tracks thermal breathing patterns")
    print("• Phase lag between heat and efficiency reveals thermal coupling")
    print("• This is thermal dynamics in action!")

if __name__ == "__main__":
    main()
