#!/usr/bin/env python3
"""
AI Training Correlation Analysis
Analyzes correlation between gradient norm and thermal collapse events

Parses training logs and RLE data to determine if learning dynamics
correlate with thermal instability.
"""

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import glob
import os

def parse_training_log(log_text):
    """Parse training output for grad_norm values"""
    # Extract grad_norm from lines like: {'loss': 4.5152, 'grad_norm': 12.816...}
    pattern = r"'grad_norm':\s*([\d.]+)"
    grad_norms = [float(m) for m in re.findall(pattern, log_text)]
    
    # Extract loss values
    loss_pattern = r"'loss':\s*([\d.]+)"
    losses = [float(m) for m in re.findall(loss_pattern, log_text)]
    
    # Assume ~1 second per step (19.4s / 20 steps)
    steps = list(range(len(grad_norms)))
    
    return pd.DataFrame({
        'step': steps,
        'grad_norm': grad_norms,
        'loss': losses
    })

def load_rle_data():
    """Load most recent RLE CSV from AI training"""
    # Try both root and lab directories
    csv_files = glob.glob("sessions/recent/rle_enhanced_*.csv")
    if not csv_files:
        csv_files = glob.glob("../sessions/recent/rle_enhanced_*.csv")
    if not csv_files:
        return None
    
    latest_csv = max(csv_files, key=os.path.getctime)
    df = pd.read_csv(latest_csv)
    
    # Filter CPU data only
    cpu_data = df[df['device'] == 'cpu'].copy()
    return cpu_data

def align_timelines(training_df, rle_df):
    """Align training steps with RLE samples"""
    # Assume training ran for ~20 seconds
    # Map step number to RLE sample index
    
    training_duration = len(rle_df)
    steps_per_second = len(training_df) / training_duration
    
    training_df['rle_time'] = training_df['step'] / steps_per_second
    
    return training_df

def calculate_correlation(training_df, rle_df):
    """Calculate correlation between grad_norm spikes and collapse events"""
    
    # Identify grad_norm spikes (above mean + 1 std)
    mean_grad = training_df['grad_norm'].mean()
    std_grad = training_df['grad_norm'].std()
    spike_threshold = mean_grad + std_grad
    
    spikes = training_df[training_df['grad_norm'] > spike_threshold]
    
    # Count collapse events near spike times
    collapses = rle_df[rle_df['collapse'] == 1]
    
    correlation_data = {
        'total_spikes': len(spikes),
        'total_collapses': len(collapses),
        'spike_threshold': spike_threshold,
        'mean_grad_norm': mean_grad
    }
    
    return correlation_data

def create_correlation_plot(training_df, rle_df, output_file="ai_training_correlation.png"):
    """Create multi-panel correlation plot"""
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    fig.patch.set_facecolor('white')
    
    # Time axis (use RLE sample indices as proxy)
    time_axis = np.arange(len(rle_df))
    
    # Panel 1: Training Loss
    ax1 = axes[0]
    if len(training_df) > 0:
        # Interpolate training steps to match RLE timeline
        step_times = np.linspace(0, len(rle_df)-1, len(training_df))
        ax1.plot(step_times, training_df['loss'], 'b-', linewidth=2, label='Training Loss')
        ax1.set_ylabel('Loss', fontsize=12, fontweight='bold')
        ax1.set_title('AI Training Dynamics vs Thermal Efficiency', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
    
    # Panel 2: Grad Norm + Collapse Events
    ax2 = axes[1]
    if len(training_df) > 0:
        step_times = np.linspace(0, len(rle_df)-1, len(training_df))
        ax2.plot(step_times, training_df['grad_norm'], 'g-', linewidth=2, label='Gradient Norm')
        
        # Mark collapse events with vertical red bars
        collapse_times = time_axis[rle_df['collapse'] == 1]
        for ct in collapse_times:
            ax2.axvline(ct, color='red', alpha=0.3, linewidth=1)
        
        # Add shaded region for collapse windows
        if len(collapse_times) > 0:
            ax2.axhline(training_df['grad_norm'].mean(), color='gray', linestyle='--', alpha=0.5, label='Mean Grad Norm')
        
        ax2.set_ylabel('Gradient Norm', fontsize=12, fontweight='bold')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
    
    # Panel 3: RLE + Temperature
    ax3 = axes[2]
    ax3.plot(time_axis, rle_df['rle_smoothed'], 'purple', linewidth=2, label='RLE (Smoothed)')
    
    ax3_twin = ax3.twinx()
    ax3_twin.plot(time_axis, rle_df['temp_c'], 'orange', linewidth=2, label='Temperature (°C)', linestyle='--')
    
    # Mark collapse events
    collapse_mask = rle_df['collapse'] == 1
    ax3.scatter(time_axis[collapse_mask], rle_df['rle_smoothed'][collapse_mask], 
               color='red', s=100, zorder=5, label='Collapse Events', marker='x')
    
    ax3.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('RLE', fontsize=12, fontweight='bold', color='purple')
    ax3_twin.set_ylabel('Temperature (°C)', fontsize=12, fontweight='bold', color='orange')
    
    ax3.legend(loc='upper left')
    ax3_twin.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Correlation plot saved: {output_file}")

def main():
    """Main analysis entry point"""
    
    print("="*70)
    print("AI TRAINING CORRELATION ANALYSIS")
    print("="*70)
    print("Analyzing relationship between gradient norm and thermal collapse\n")
    
    # For demo, we'll use the console output from the last run
    # In practice, parse from saved log file
    training_log = """
    {'loss': 4.5152, 'grad_norm': 12.816308975219727, 'learning_rate': 0.0, 'epoch': 0.4}
    {'loss': 4.5452, 'grad_norm': 14.40941047668457, 'learning_rate': 1e-05, 'epoch': 0.8}
    {'loss': 4.3559, 'grad_norm': 15.550127983093262, 'learning_rate': 2e-05, 'epoch': 1.0}
    {'loss': 4.236, 'grad_norm': 13.564202308654785, 'learning_rate': 3e-05, 'epoch': 1.4}
    {'loss': 4.4301, 'grad_norm': 11.140070915222168, 'learning_rate': 4e-05, 'epoch': 1.8}
    {'loss': 3.5392, 'grad_norm': 14.640992164611816, 'learning_rate': 5e-05, 'epoch': 2.0}
    {'loss': 3.4973, 'grad_norm': 11.531964302062988, 'learning_rate': 4.666e-05, 'epoch': 2.4}
    {'loss': 3.8913, 'grad_norm': 9.928133964538574, 'learning_rate': 4.333e-05, 'epoch': 2.8}
    {'loss': 3.2229, 'grad_norm': 13.417043685913086, 'learning_rate': 4e-05, 'epoch': 3.0}
    {'loss': 3.2331, 'grad_norm': 9.984098434448242, 'learning_rate': 3.666e-05, 'epoch': 3.4}
    {'loss': 3.1248, 'grad_norm': 11.207138061523438, 'learning_rate': 3.333e-05, 'epoch': 3.8}
    {'loss': 3.1635, 'grad_norm': 12.537446975708008, 'learning_rate': 3e-05, 'epoch': 4.0}
    {'loss': 2.9503, 'grad_norm': 9.558563232421875, 'learning_rate': 2.666e-05, 'epoch': 4.4}
    {'loss': 3.0549, 'grad_norm': 10.38095474243164, 'learning_rate': 2.333e-05, 'epoch': 4.8}
    {'loss': 2.7484, 'grad_norm': 11.354321479797363, 'learning_rate': 2e-05, 'epoch': 5.0}
    {'loss': 2.9936, 'grad_norm': 9.766738891601562, 'learning_rate': 1.666e-05, 'epoch': 5.4}
    {'loss': 2.7423, 'grad_norm': 9.354145050048828, 'learning_rate': 1.333e-05, 'epoch': 5.8}
    {'loss': 2.5301, 'grad_norm': 12.322644233703613, 'learning_rate': 1e-05, 'epoch': 6.0}
    {'loss': 2.6905, 'grad_norm': 8.791358947753906, 'learning_rate': 6.666e-06, 'epoch': 6.4}
    {'loss': 2.7824, 'grad_norm': 9.534078598022461, 'learning_rate': 3.333e-06, 'epoch': 6.8}
    """
    
    # Parse training data
    training_df = parse_training_log(training_log)
    print(f"[SUCCESS] Parsed {len(training_df)} training steps")
    
    # Load RLE data
    rle_df = load_rle_data()
    if rle_df is None or rle_df.empty:
        print("[FAILED] No RLE data found")
        return
    
    print(f"[SUCCESS] Loaded {len(rle_df)} RLE samples")
    
    # Calculate correlation
    corr_data = calculate_correlation(training_df, rle_df)
    
    print(f"\nCorrelation Analysis:")
    print(f"  Total gradient spikes: {corr_data['total_spikes']}")
    print(f"  Total collapse events: {corr_data['total_collapses']}")
    print(f"  Spike threshold: {corr_data['spike_threshold']:.2f}")
    print(f"  Mean grad norm: {corr_data['mean_grad_norm']:.2f}")
    
    # Create visualization
    create_correlation_plot(training_df, rle_df)
    
    print("\n" + "="*70)
    print("CORRELATION ANALYSIS COMPLETE")
    print("="*70)
    print("Files generated:")
    print("• ai_training_correlation.png - Multi-panel correlation plot")
    print()
    print("Key findings:")
    if corr_data['total_spikes'] > 0 and corr_data['total_collapses'] > 0:
        print("→ Both gradient spikes and collapse events detected")
        print("→ Visual inspection shows temporal alignment (or lack thereof)")
    else:
        print("→ Insufficient events for correlation analysis")
    
if __name__ == "__main__":
    main()

