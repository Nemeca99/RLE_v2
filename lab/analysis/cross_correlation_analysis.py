#!/usr/bin/env python3
"""
Cross-Correlation Analysis: Grad Norm vs RLE
Tests thermal-optimization coupling hypothesis with synchronized data
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from pathlib import Path
import os

def load_synchronized_data():
    """Load both grad_norm logs and RLE data"""
    
    # Load grad_norm logs
    grad_log_file = "L:/models/luna_trained_final/grad_norm_sync_log.json"
    if not os.path.exists(grad_log_file):
        print(f"[ERROR] Grad norm log not found: {grad_log_file}")
        return None, None
    
    with open(grad_log_file, 'r') as f:
        grad_logs = json.load(f)
    
    print(f"[SUCCESS] Loaded {len(grad_logs)} training steps")
    
    # Load RLE data
    csv_files = sorted(Path("sessions/recent").glob("rle_enhanced_*.csv"), 
                      key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not csv_files:
        print("[ERROR] No RLE data found")
        return None, None
    
    rle_df = pd.read_csv(csv_files[0])
    print(f"[SUCCESS] Loaded {len(rle_df)} RLE samples from {csv_files[0]}")
    
    return grad_logs, rle_df

def align_synchronized_data(grad_logs, rle_df):
    """Align training and RLE data using shared timestamps"""
    
    # Convert grad_norm logs to DataFrame
    grad_df = pd.DataFrame(grad_logs)
    
    # Convert timestamps
    grad_df['timestamp'] = pd.to_datetime(grad_df['timestamp_shared'], unit='s')
    rle_df['timestamp'] = pd.to_datetime(rle_df['timestamp'])
    
    # Merge on timestamp with tolerance
    merged = pd.merge_asof(
        grad_df.sort_values('timestamp'),
        rle_df.sort_values('timestamp'),
        on='timestamp',
        direction='nearest',
        tolerance=pd.Timedelta(seconds=2)  # 2-second tolerance
    )
    
    print(f"[INFO] Aligned {len(merged)} samples")
    return merged

def create_cross_correlation_plots(merged_data, output_file="cross_correlation_analysis.png"):
    """Create three scatter plots for correlation analysis"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.patch.set_facecolor('white')
    
    # Panel 1: grad_norm vs RLE (CPU)
    ax1 = axes[0, 0]
    cpu_data = merged_data[merged_data['device'] == 'cpu']
    if len(cpu_data) > 0:
        ax1.scatter(cpu_data['grad_norm'], cpu_data['rle_smoothed'], 
                   color='blue', alpha=0.7, s=50, label='CPU')
        
        # Calculate correlation
        corr_cpu = cpu_data['grad_norm'].corr(cpu_data['rle_smoothed'])
        ax1.set_title(f'CPU: grad_norm vs RLE (r={corr_cpu:.3f})', 
                     fontsize=14, fontweight='bold')
    
    ax1.set_xlabel('Gradient Norm', fontsize=12, fontweight='bold')
    ax1.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: grad_norm vs RLE (GPU)
    ax2 = axes[0, 1]
    gpu_data = merged_data[merged_data['device'] == 'gpu']
    if len(gpu_data) > 0:
        ax2.scatter(gpu_data['grad_norm'], gpu_data['rle_smoothed'], 
                   color='red', alpha=0.7, s=50, label='GPU')
        
        # Calculate correlation
        corr_gpu = gpu_data['grad_norm'].corr(gpu_data['rle_smoothed'])
        ax2.set_title(f'GPU: grad_norm vs RLE (r={corr_gpu:.3f})', 
                     fontsize=14, fontweight='bold')
    
    ax2.set_xlabel('Gradient Norm', fontsize=12, fontweight='bold')
    ax2.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: loss vs RLE (CPU)
    ax3 = axes[1, 0]
    if len(cpu_data) > 0:
        ax3.scatter(cpu_data['loss'], cpu_data['rle_smoothed'], 
                   color='blue', alpha=0.7, s=50, label='CPU')
        
        # Calculate correlation
        corr_loss_cpu = cpu_data['loss'].corr(cpu_data['rle_smoothed'])
        ax3.set_title(f'CPU: loss vs RLE (r={corr_loss_cpu:.3f})', 
                     fontsize=14, fontweight='bold')
    
    ax3.set_xlabel('Training Loss', fontsize=12, fontweight='bold')
    ax3.set_ylabel('RLE', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Panel 4: temperature vs grad_norm
    ax4 = axes[1, 1]
    if len(cpu_data) > 0:
        ax4.scatter(cpu_data['temp_c'], cpu_data['grad_norm'], 
                   color='blue', alpha=0.7, s=50, label='CPU')
    
    if len(gpu_data) > 0:
        ax4.scatter(gpu_data['temp_c'], gpu_data['grad_norm'], 
                   color='red', alpha=0.7, s=50, label='GPU')
        
        # Calculate correlation
        corr_temp_grad = merged_data['temp_c'].corr(merged_data['grad_norm'])
        ax4.set_title(f'Temperature vs grad_norm (r={corr_temp_grad:.3f})', 
                     fontsize=14, fontweight='bold')
    
    ax4.set_xlabel('Temperature (°C)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Gradient Norm', fontsize=12, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Cross-correlation plots saved: {output_file}")

def analyze_correlations(merged_data):
    """Analyze correlation coefficients and interpret results"""
    
    print("\n" + "="*70)
    print("CROSS-CORRELATION ANALYSIS")
    print("="*70)
    
    # Separate CPU and GPU data
    cpu_data = merged_data[merged_data['device'] == 'cpu']
    gpu_data = merged_data[merged_data['device'] == 'gpu']
    
    correlations = {}
    
    # CPU correlations
    if len(cpu_data) > 0:
        correlations['cpu_grad_rle'] = cpu_data['grad_norm'].corr(cpu_data['rle_smoothed'])
        correlations['cpu_loss_rle'] = cpu_data['loss'].corr(cpu_data['rle_smoothed'])
        correlations['cpu_temp_grad'] = cpu_data['temp_c'].corr(cpu_data['grad_norm'])
    
    # GPU correlations
    if len(gpu_data) > 0:
        correlations['gpu_grad_rle'] = gpu_data['grad_norm'].corr(gpu_data['rle_smoothed'])
        correlations['gpu_loss_rle'] = gpu_data['loss'].corr(gpu_data['rle_smoothed'])
        correlations['gpu_temp_grad'] = gpu_data['temp_c'].corr(gpu_data['grad_norm'])
    
    # Overall correlations
    correlations['overall_temp_grad'] = merged_data['temp_c'].corr(merged_data['grad_norm'])
    
    # Print results
    print(f"\nCorrelation Coefficients:")
    for name, corr in correlations.items():
        if not np.isnan(corr):
            print(f"  {name}: {corr:.3f}")
    
    # Interpretation
    print(f"\nInterpretation:")
    
    # Check for strong coupling
    strong_coupling = []
    moderate_coupling = []
    weak_coupling = []
    
    for name, corr in correlations.items():
        if not np.isnan(corr):
            if abs(corr) > 0.7:
                strong_coupling.append((name, corr))
            elif abs(corr) > 0.3:
                moderate_coupling.append((name, corr))
            else:
                weak_coupling.append((name, corr))
    
    if strong_coupling:
        print(f"\n✅ STRONG COUPLING DETECTED:")
        for name, corr in strong_coupling:
            print(f"  {name}: {corr:.3f}")
        print("  → Novel thermal-optimization coupling discovered!")
        print("  → Publishable research finding!")
    
    if moderate_coupling:
        print(f"\n⚠️  MODERATE COUPLING:")
        for name, corr in moderate_coupling:
            print(f"  {name}: {corr:.3f}")
        print("  → Some relationship present, needs more data")
    
    if weak_coupling:
        print(f"\n❌ WEAK/NO COUPLING:")
        for name, corr in weak_coupling:
            print(f"  {name}: {corr:.3f}")
        print("  → Independent systems, validates metric purity")
    
    return correlations

def main():
    """Main cross-correlation analysis"""
    
    print("="*70)
    print("CROSS-CORRELATION ANALYSIS: GRAD NORM vs RLE")
    print("="*70)
    print("Testing thermal-optimization coupling hypothesis")
    print()
    
    # Load synchronized data
    grad_logs, rle_df = load_synchronized_data()
    
    if grad_logs is None or rle_df is None:
        print("[FAILED] Could not load required data")
        return
    
    # Align data
    merged_data = align_synchronized_data(grad_logs, rle_df)
    
    if merged_data.empty:
        print("[FAILED] Could not align data")
        return
    
    # Analyze correlations
    correlations = analyze_correlations(merged_data)
    
    # Create visualization
    create_cross_correlation_plots(merged_data)
    
    print("\n" + "="*70)
    print("CROSS-CORRELATION ANALYSIS COMPLETE")
    print("="*70)
    print("Files generated:")
    print("• cross_correlation_analysis.png")
    print()
    print("Next steps:")
    print("1. Review scatter plots for clustering patterns")
    print("2. Check correlation coefficients for coupling strength")
    print("3. Document findings for publication")

if __name__ == "__main__":
    main()

