#!/usr/bin/env python3
"""
Luna Training Reproducibility Test
Validates RLE consistency across multiple training sessions

Run 3-5 short training sessions and verify:
- Collapse rate stays within ±5%
- Mean RLE stays within ±5%
- Temperature range consistent
"""

import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime
from pathlib import Path

def load_recent_luna_sessions(num_sessions=5):
    """Load the most recent Luna training sessions"""
    
    csv_files = glob.glob("../sessions/recent/rle_enhanced_*.csv")
    csv_files.sort(key=os.path.getctime, reverse=True)
    
    # Get most recent sessions
    recent_files = csv_files[:num_sessions]
    
    print(f"[INFO] Found {len(recent_files)} recent sessions:")
    sessions = []
    for i, file_path in enumerate(recent_files):
        df = pd.read_csv(file_path)
        file_time = datetime.fromtimestamp(os.path.getctime(file_path))
        sessions.append({
            'file': file_path,
            'timestamp': file_time,
            'data': df,
            'duration': len(df),
            'session_id': i + 1
        })
        print(f"  Session {i+1}: {file_time.strftime('%Y-%m-%d %H:%M')} ({len(df)} samples)")
    
    return sessions

def analyze_reproducibility(sessions):
    """Analyze RLE consistency across sessions"""
    
    print("\n" + "="*70)
    print("REPRODUCIBILITY ANALYSIS")
    print("="*70)
    
    # Extract metrics for each session
    metrics = []
    for session in sessions:
        df = session['data']
        
        rle_mean = df['rle_smoothed'].mean()
        rle_std = df['rle_smoothed'].std()
        collapse_rate = df['collapse'].sum() / len(df) * 100
        temp_mean = df['temp_c'].mean()
        temp_range = df['temp_c'].max() - df['temp_c'].min()
        power_mean = df['power_w'].mean()
        
        metrics.append({
            'session': session['session_id'],
            'rle_mean': rle_mean,
            'rle_std': rle_std,
            'collapse_rate': collapse_rate,
            'temp_mean': temp_mean,
            'temp_range': temp_range,
            'power_mean': power_mean,
            'samples': len(df)
        })
    
    # Calculate statistics
    metrics_df = pd.DataFrame(metrics)
    
    print("\n📊 SESSION METRICS:")
    print(metrics_df.to_string(index=False))
    
    # Calculate reproducibility metrics
    rle_mean_std = metrics_df['rle_mean'].std()
    rle_mean_mean = metrics_df['rle_mean'].mean()
    rle_cv = (rle_mean_std / rle_mean_mean) * 100 if rle_mean_mean > 0 else 0
    
    collapse_rate_std = metrics_df['collapse_rate'].std()
    collapse_rate_mean = metrics_df['collapse_rate'].mean()
    
    print(f"\n🔬 REPRODUCIBILITY METRICS:")
    print(f"  RLE Mean: {rle_mean_mean:.3f} ± {rle_mean_std:.3f} (CV: {rle_cv:.1f}%)")
    print(f"  Collapse Rate: {collapse_rate_mean:.1f}% ± {collapse_rate_std:.1f}%")
    
    # Validation criteria
    print(f"\n✅ REPRODUCIBILITY CHECK:")
    
    rle_pass = rle_cv < 5.0
    collapse_pass = collapse_rate_std < 5.0
    
    print(f"  RLE Consistency: {'PASS' if rle_pass else 'FAIL'} (CV: {rle_cv:.1f}%, threshold: 5.0%)")
    print(f"  Collapse Rate: {'PASS' if collapse_pass else 'FAIL'} (std: {collapse_rate_std:.1f}%, threshold: 5.0%)")
    
    overall_pass = rle_pass and collapse_pass
    print(f"\n  Overall: {'PASS ✅' if overall_pass else 'FAIL ❌'}")
    
    return overall_pass, metrics_df

def create_reproducibility_plot(sessions, output_file="luna_reproducibility_test.png"):
    """Create reproducibility visualization"""
    
    import matplotlib.pyplot as plt
    
    # Add timestamps to filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = f"luna_reproducibility_{timestamp}.png"
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.patch.set_facecolor('white')
    
    # Panel 1: RLE Mean across sessions
    ax1 = axes[0, 0]
    session_ids = [s['session_id'] for s in sessions]
    rle_means = [s['data']['rle_smoothed'].mean() for s in sessions]
    ax1.plot(session_ids, rle_means, 'o-', linewidth=2, markersize=10, color='purple')
    ax1.axhline(np.mean(rle_means), color='gray', linestyle='--', alpha=0.5, label=f'Mean: {np.mean(rle_means):.3f}')
    ax1.set_xlabel('Session Number')
    ax1.set_ylabel('RLE Mean')
    ax1.set_title('RLE Consistency Across Sessions')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Collapse Rate across sessions
    ax2 = axes[0, 1]
    collapse_rates = [(s['data']['collapse'].sum() / len(s['data']) * 100) for s in sessions]
    ax2.plot(session_ids, collapse_rates, 'o-', linewidth=2, markersize=10, color='red')
    ax2.axhline(np.mean(collapse_rates), color='gray', linestyle='--', alpha=0.5, label=f'Mean: {np.mean(collapse_rates):.1f}%')
    ax2.set_xlabel('Session Number')
    ax2.set_ylabel('Collapse Rate (%)')
    ax2.set_title('Thermal Stability Across Sessions')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Temperature range
    ax3 = axes[1, 0]
    temp_means = [s['data']['temp_c'].mean() for s in sessions]
    ax3.plot(session_ids, temp_means, 'o-', linewidth=2, markersize=10, color='orange')
    ax3.axhline(np.mean(temp_means), color='gray', linestyle='--', alpha=0.5, label=f'Mean: {np.mean(temp_means):.1f}°C')
    ax3.set_xlabel('Session Number')
    ax3.set_ylabel('Temperature (°C)')
    ax3.set_title('Thermal Profile Consistency')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Panel 4: Power consumption
    ax4 = axes[1, 1]
    power_means = [s['data']['power_w'].mean() for s in sessions]
    ax4.plot(session_ids, power_means, 'o-', linewidth=2, markersize=10, color='green')
    ax4.axhline(np.mean(power_means), color='gray', linestyle='--', alpha=0.5, label=f'Mean: {np.mean(power_means):.0f}W')
    ax4.set_xlabel('Session Number')
    ax4.set_ylabel('Power (W)')
    ax4.set_title('Energy Consumption Consistency')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Reproducibility plot saved: {output_file}")

def main():
    """Main reproducibility test"""
    
    print("="*70)
    print("LUNA TRAINING REPRODUCIBILITY TEST")
    print("="*70)
    print("Validating RLE consistency across multiple training sessions")
    print()
    
    # Load recent sessions
    sessions = load_recent_luna_sessions(num_sessions=5)
    
    if len(sessions) < 2:
        print("[ERROR] Need at least 2 sessions for reproducibility test")
        return
    
    # Analyze reproducibility
    overall_pass, metrics_df = analyze_reproducibility(sessions)
    
    # Create visualization
    create_reproducibility_plot(sessions)
    
    print("\n" + "="*70)
    print("REPRODUCIBILITY TEST COMPLETE")
    print("="*70)
    
    if overall_pass:
        print("✅ RLE validated for Luna training - Results are REPRODUCIBLE")
        print("   Ready for production use and extended monitoring")
    else:
        print("⚠️  RLE needs improvement - Results show variability")
        print("   Consider extending session duration or improving thermal control")
    
    print("\nFiles generated:")
    print(f"• luna_reproducibility_{datetime.now().strftime('%Y%m%d_%H%M')}.png")

if __name__ == "__main__":
    main()
