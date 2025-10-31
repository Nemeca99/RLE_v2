#!/usr/bin/env python3
"""
Luna Grad Norm vs Thermal Collapse Correlation Analysis
Tests hypothesis: optimization instability ↔ thermal instability

Analyzes correlation between gradient norm spikes and thermal collapse events
during Luna model training to discover if there's coupling between learning
dynamics and thermal efficiency.
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import glob
import os
from datetime import datetime
from pathlib import Path

def load_grad_norm_log(log_file="L:/models/luna_trained_final/grad_norm_log.json"):
    """Load gradient norm logs from training"""
    # Try alternative paths
    if not os.path.exists(log_file):
        alternatives = [
            "grad_norm_log.json",
            "L:/models/luna_trained_final/grad_norm_log.json",
            "../../models/luna_trained_final/grad_norm_log.json"
        ]
        for alt in alternatives:
            if os.path.exists(alt):
                log_file = alt
                break
        else:
            print(f"[ERROR] Grad norm log not found in any path")
            return None
    
    with open(log_file, 'r') as f:
        logs = json.load(f)
    
    print(f"[SUCCESS] Loaded {len(logs)} training steps from {log_file}")
    return logs

def load_rle_data(csv_file=None):
    """Load RLE thermal data"""
    if csv_file is None:
        # Find the most recent RLE file
        csv_files = Path("sessions/recent").glob("rle_enhanced_*.csv")
        csv_files = sorted(csv_files, key=lambda p: p.stat().st_mtime, reverse=True)
        if csv_files:
            csv_file = str(csv_files[0])
        else:
            # Try absolute path
            csv_file = "F:/RLE/lab/sessions/recent/rle_enhanced_20251028_18.csv"
    
    if not os.path.exists(csv_file):
        print(f"[ERROR] RLE data not found: {csv_file}")
        return None
    
    df = pd.read_csv(csv_file)
    print(f"[SUCCESS] Loaded {len(df)} RLE samples")
    return df

def align_timelines(grad_logs, rle_df):
    """Align training steps with RLE samples by timestamp"""
    
    # Convert timestamps
    grad_df = pd.DataFrame(grad_logs)
    grad_df['timestamp'] = pd.to_datetime(grad_df['timestamp'])
    rle_df['timestamp'] = pd.to_datetime(rle_df['timestamp'])
    
    # Merge on timestamp with tolerance
    merged = pd.merge_asof(
        grad_df.sort_values('timestamp'),
        rle_df.sort_values('timestamp'),
        on='timestamp',
        direction='nearest',
        tolerance=pd.Timedelta(seconds=1)
    )
    
    print(f"[INFO] Aligned {len(merged)} samples")
    return merged

def calculate_correlation(merged_data):
    """Calculate correlation between grad_norm and collapse events"""
    
    if 'grad_norm' not in merged_data.columns or 'collapse' not in merged_data.columns:
        print("[ERROR] Missing required columns for correlation")
        return None
    
    # Identify grad_norm spikes (above mean + 1 std)
    mean_grad = merged_data['grad_norm'].mean()
    std_grad = merged_data['grad_norm'].std()
    spike_threshold = mean_grad + std_grad
    
    spikes = merged_data[merged_data['grad_norm'] > spike_threshold]
    collapses = merged_data[merged_data['collapse'] == 1]
    
    # Calculate correlation
    if len(spikes) > 0 and len(collapses) > 0:
        correlation = merged_data['grad_norm'].corr(merged_data['collapse'])
    else:
        correlation = None
    
    correlation_data = {
        'total_spikes': len(spikes),
        'total_collapses': len(collapses),
        'spike_threshold': spike_threshold,
        'mean_grad_norm': mean_grad,
        'correlation': correlation
    }
    
    return correlation_data

def create_correlation_plot(merged_data, output_file="luna_grad_norm_correlation.png"):
    """Create multi-panel correlation visualization"""
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = f"luna_grad_norm_correlation_{timestamp}.png"
    
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))
    fig.patch.set_facecolor('white')
    
    # Panel 1: Training Loss
    ax1 = axes[0]
    if 'loss' in merged_data.columns:
        ax1.plot(merged_data['step'], merged_data['loss'], 'b-', linewidth=2, label='Training Loss')
        ax1.set_ylabel('Loss', fontsize=12, fontweight='bold')
        ax1.set_title('Luna Training Dynamics vs Thermal Efficiency', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
    
    # Panel 2: Gradient Norm + Collapse Events
    ax2 = axes[1]
    if 'grad_norm' in merged_data.columns:
        ax2.plot(merged_data['step'], merged_data['grad_norm'], 'g-', linewidth=2, label='Gradient Norm')
        
        # Mark collapse events with vertical bars
        collapse_steps = merged_data[merged_data['collapse'] == 1]['step']
        for cs in collapse_steps:
            ax2.axvline(cs, color='red', alpha=0.3, linewidth=1)
        
        # Add mean line
        if len(merged_data) > 0:
            mean_grad = merged_data['grad_norm'].mean()
            ax2.axhline(mean_grad, color='gray', linestyle='--', alpha=0.5, 
                        label=f'Mean: {mean_grad:.2f}')
        
        ax2.set_ylabel('Gradient Norm', fontsize=12, fontweight='bold')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
    
    # Panel 3: RLE + Temperature
    ax3 = axes[2]
    if 'rle_smoothed' in merged_data.columns:
        ax3.plot(merged_data['step'], merged_data['rle_smoothed'], 'purple', 
                linewidth=2, label='RLE (Smoothed)')
        
        # Mark collapse events
        collapse_mask = merged_data['collapse'] == 1
        ax3.scatter(merged_data[collapse_mask]['step'], 
                   merged_data[collapse_mask]['rle_smoothed'],
                   color='red', s=100, zorder=5, label='Collapse Events', marker='x')
        
        ax3.set_ylabel('RLE', fontsize=12, fontweight='bold')
        ax3.legend(loc='upper right')
        ax3.grid(True, alpha=0.3)
    
    # Panel 4: Temperature
    ax4 = axes[3]
    if 'temp_c' in merged_data.columns:
        ax4.plot(merged_data['step'], merged_data['temp_c'], 'orange', 
                linewidth=2, label='Temperature (°C)')
        
        ax4.set_xlabel('Training Step', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Temperature (°C)', fontsize=12, fontweight='bold')
        ax4.legend(loc='upper right')
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Correlation plot saved: {output_file}")

def analyze_coupling(correlation_data):
    """Analyze thermal-optimization coupling"""
    
    print("\n" + "="*70)
    print("THERMAL-OPTIMIZATION COUPLING ANALYSIS")
    print("="*70)
    
    if correlation_data is None:
        print("[ERROR] Cannot analyze coupling - missing correlation data")
        return
    
    print(f"\nGradient Norm Statistics:")
    print(f"  Mean: {correlation_data['mean_grad_norm']:.2f}")
    print(f"  Spike threshold: {correlation_data['spike_threshold']:.2f}")
    print(f"  Spikes detected: {correlation_data['total_spikes']}")
    
    print(f"\nCollapse Statistics:")
    print(f"  Collapse events: {correlation_data['total_collapses']}")
    
    if correlation_data['correlation'] is not None:
        print(f"\nCorrelation Analysis:")
        print(f"  Grad Norm ↔ Collapse correlation: {correlation_data['correlation']:.3f}")
        
        if abs(correlation_data['correlation']) > 0.7:
            print("\n  ✅ STRONG CORRELATION DETECTED")
            print("     Optimization instability COUPLED to thermal instability!")
            print("     This is a novel research finding!")
        elif abs(correlation_data['correlation']) > 0.3:
            print("\n  ⚠️  MODERATE CORRELATION")
            print("     Some coupling present, but not definitive")
        else:
            print("\n  ❌ NO STRONG CORRELATION")
            print("     Optimization and thermal instability are independent")

def main():
    """Main analysis entry point"""
    
    print("="*70)
    print("LUNA GRAD NORM vs THERMAL COLLAPSE CORRELATION")
    print("="*70)
    print("Testing hypothesis: optimization instability ↔ thermal instability")
    print()
    
    # Load data
    grad_logs = load_grad_norm_log()
    rle_df = load_rle_data()
    
    if grad_logs is None or rle_df is None:
        print("[FAILED] Could not load required data")
        print("\nTo collect data:")
        print("1. Run: python train_with_grad_norm_logging.py (in L:\\models\\luna_trained_final)")
        print("2. Run: python luna_training_with_rle.py (in L:\\AIOS)")
        print("3. Then run this analysis")
        return
    
    # Align timelines
    merged_data = align_timelines(grad_logs, rle_df)
    
    if merged_data.empty:
        print("[FAILED] Could not align timelines")
        return
    
    # Calculate correlation
    correlation_data = calculate_correlation(merged_data)
    
    # Analyze coupling
    analyze_coupling(correlation_data)
    
    # Create visualization
    create_correlation_plot(merged_data)
    
    print("\n" + "="*70)
    print("CORRELATION ANALYSIS COMPLETE")
    print("="*70)
    print("Files generated:")
    print(f"• luna_grad_norm_correlation_{datetime.now().strftime('%Y%m%d_%H%M')}.png")
    print()
    print("Next steps:")
    print("1. Review correlation plot for temporal alignment")
    print("2. Check if gradient spikes align with collapse events")
    print("3. Statistical significance testing if correlation >0.7")

if __name__ == "__main__":
    main()
