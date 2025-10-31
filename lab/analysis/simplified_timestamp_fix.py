#!/usr/bin/env python3
"""
Simplified Timestamp Fix for Thermal-Optimization Coupling
Addresses the core synchronization issue identified in validation
"""

import subprocess
import time
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def run_synchronized_session():
    """Run a single synchronized session with proper timestamp alignment"""
    
    print("="*70)
    print("SIMPLIFIED SYNCHRONIZED SESSION")
    print("="*70)
    
    # Create session directory
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path("sessions/bulletproof") / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Shared clock start time
    t0 = time.time()
    print(f"Session ID: {session_id}")
    print(f"Shared clock start: {t0}")
    print(f"Session directory: {session_dir}")
    
    # Start RLE monitoring with shared clock
    print("\n[1/3] Starting RLE monitoring...")
    rle_cmd = [
        "..\\venv\\Scripts\\python.exe",
        "monitoring\\hardware_monitor_v2.py",
        "--mode", "both",
        "--sample-hz", "1",
        "--duration", "90",
        "--realtime",
        "--model-name", f"Sync Session {session_id}",
        "--training-mode", "Synchronized training",
        "--ambient-temp", "21.0",
        "--notes", f"Shared clock session {session_id}"
    ]
    
    rle_process = subprocess.Popen(rle_cmd, cwd=".")
    time.sleep(2)  # Let RLE initialize
    
    # Start training with shared clock
    print("[2/3] Starting synchronized training...")
    train_cmd = [
        "..\\venv\\Scripts\\python.exe",
        "L:\\models\\luna_trained_final\\extended_training_with_sync.py"
    ]
    
    train_process = subprocess.run(train_cmd, cwd="L:\\models\\luna_trained_final")
    
    # Wait for RLE to finish
    print("[3/3] Waiting for RLE monitoring to complete...")
    rle_process.wait()
    
    print(f"\n✅ Session complete!")
    print(f"Training exit code: {train_process.returncode}")
    print(f"RLE exit code: {rle_process.returncode}")
    
    return session_dir, t0

def analyze_timestamp_alignment(session_dir, t0):
    """Analyze timestamp alignment between training and RLE data"""
    
    print("\n" + "="*70)
    print("TIMESTAMP ALIGNMENT ANALYSIS")
    print("="*70)
    
    # Find latest RLE CSV
    csv_files = sorted(Path("sessions/recent").glob("rle_enhanced_*.csv"), 
                      key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not csv_files:
        print("❌ No RLE CSV files found!")
        return None
    
    rle_file = csv_files[0]
    print(f"Using RLE file: {rle_file}")
    
    # Load RLE data
    rle_df = pd.read_csv(rle_file)
    rle_df['timestamp'] = pd.to_datetime(rle_df['timestamp'])
    
    # Load training data
    train_file = Path("L:/models/luna_trained_final/grad_norm_sync_log.json")
    if not train_file.exists():
        print("❌ No training log file found!")
        return None
    
    with open(train_file, 'r') as f:
        train_logs = json.load(f)
    
    train_df = pd.DataFrame(train_logs)
    train_df['timestamp'] = pd.to_datetime(train_df['timestamp_shared'], unit='s')
    
    print(f"RLE samples: {len(rle_df)}")
    print(f"Training samples: {len(train_df)}")
    
    # Convert to elapsed time since session start
    rle_df['elapsed_time'] = (rle_df['timestamp'] - pd.Timestamp.fromtimestamp(t0)).dt.total_seconds()
    train_df['elapsed_time'] = (train_df['timestamp'] - pd.Timestamp.fromtimestamp(t0)).dt.total_seconds()
    
    print(f"\nRLE elapsed time range: {rle_df['elapsed_time'].min():.1f}s to {rle_df['elapsed_time'].max():.1f}s")
    print(f"Training elapsed time range: {train_df['elapsed_time'].min():.1f}s to {train_df['elapsed_time'].max():.1f}s")
    
    # Align data using elapsed time
    merged_data = pd.merge_asof(
        train_df.sort_values('elapsed_time'),
        rle_df[rle_df['device'] == 'gpu'].sort_values('elapsed_time'),
        on='elapsed_time',
        direction='nearest',
        tolerance=2.0  # 2 second tolerance
    )
    
    if len(merged_data) == 0:
        print("❌ No aligned data found!")
        return None
    
    print(f"\nAligned samples: {len(merged_data)}")
    
    # Calculate correlations
    correlations = {
        'gpu_grad_rle': merged_data['grad_norm'].corr(merged_data['rle_smoothed']),
        'gpu_temp_grad': merged_data['temp_c'].corr(merged_data['grad_norm']),
        'gpu_loss_rle': merged_data['loss'].corr(merged_data['rle_smoothed'])
    }
    
    print(f"\nCORRELATIONS (with proper timestamp alignment):")
    print(f"GPU grad_norm ↔ RLE: {correlations['gpu_grad_rle']:.3f}")
    print(f"GPU temp ↔ grad_norm: {correlations['gpu_temp_grad']:.3f}")
    print(f"GPU loss ↔ RLE: {correlations['gpu_loss_rle']:.3f}")
    
    # Lag analysis with proper timestamps
    print(f"\nLAG ANALYSIS (using elapsed time):")
    for lag in range(-3, 4):
        if lag < 0:
            # grad_norm leads RLE
            corr = merged_data['grad_norm'].shift(lag).corr(merged_data['rle_smoothed'])
        elif lag > 0:
            # RLE leads grad_norm
            corr = merged_data['grad_norm'].corr(merged_data['rle_smoothed'].shift(lag))
        else:
            # Simultaneous
            corr = merged_data['grad_norm'].corr(merged_data['rle_smoothed'])
        
        print(f"  Lag {lag:+2d}s: {corr:.3f}")
    
    # Find peak correlation lag
    lag_correlations = []
    for lag in range(-3, 4):
        if lag < 0:
            corr = merged_data['grad_norm'].shift(lag).corr(merged_data['rle_smoothed'])
        elif lag > 0:
            corr = merged_data['grad_norm'].corr(merged_data['rle_smoothed'].shift(lag))
        else:
            corr = merged_data['grad_norm'].corr(merged_data['rle_smoothed'])
        lag_correlations.append((lag, corr))
    
    peak_lag, peak_corr = max(lag_correlations, key=lambda x: abs(x[1]))
    
    print(f"\nPEAK CORRELATION: {peak_corr:.3f} at lag {peak_lag}s")
    
    if peak_lag < 0:
        print("✅ CAUSAL ORDER: grad_norm spikes precede RLE drops")
    elif peak_lag > 0:
        print("⚠️  REVERSE CAUSALITY: RLE drops precede grad_norm spikes")
    else:
        print("⚠️  SIMULTANEOUS: No clear temporal ordering")
    
    # Save analysis results
    analysis_results = {
        'session_id': session_dir.name,
        'session_start_timestamp': t0,
        'aligned_samples': len(merged_data),
        'correlations': correlations,
        'peak_lag': peak_lag,
        'peak_correlation': peak_corr,
        'causal_order': peak_lag < 0
    }
    
    results_file = session_dir / "timestamp_analysis.json"
    with open(results_file, 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"\nAnalysis saved to: {results_file}")
    
    return analysis_results

def main():
    """Run simplified synchronized session"""
    
    # Run synchronized session
    session_dir, t0 = run_synchronized_session()
    
    # Analyze timestamp alignment
    results = analyze_timestamp_alignment(session_dir, t0)
    
    if results:
        print("\n" + "="*70)
        print("SIMPLIFIED VALIDATION COMPLETE")
        print("="*70)
        print(f"Session ID: {session_dir.name}")
        print(f"Aligned samples: {results['aligned_samples']}")
        print(f"Peak correlation: {results['peak_correlation']:.3f} at lag {results['peak_lag']}s")
        print(f"Causal order: {'grad_norm → RLE' if results['causal_order'] else 'RLE → grad_norm'}")
        
        if results['causal_order']:
            print("\n🎉 SUCCESS: Proper causal order established!")
            print("   grad_norm spikes cause RLE drops (thermal instability)")
        else:
            print("\n⚠️  REVERSE CAUSALITY: RLE drops precede grad_norm spikes")
            print("   This suggests thermal throttling affects optimization stability")

if __name__ == "__main__":
    main()
