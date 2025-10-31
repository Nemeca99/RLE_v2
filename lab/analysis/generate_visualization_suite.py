#!/usr/bin/env python3
"""
Generate comprehensive visualization suite for cross-device RLE data
Creates: efficiency curves, collapse maps, thermal overlays, entropy strips, animated GIFs, correlation heatmaps
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime
import json

PATHS = {
    'phone': Path('lab/sessions/archive/mobile/phone_all_benchmarks.csv'),
    'phone_alt': Path('lab/sessions/archive/mobile/phone_rle_wildlife.csv'),
    'laptop_1': Path('sessions/laptop/rle_20251030_19.csv'),
    'laptop_2': Path('sessions/laptop/rle_20251030_20 - Copy.csv'),
    'pc_cpu': Path('lab/sessions/recent/rle_20251027_09.csv'),
    'pc_gpu': Path('lab/sessions/recent/rle_20251028_08.csv'),
}

OUT_DIR = Path('lab/sessions/archive/plots')
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_device_data(path, device_type=None):
    """Load and prepare device data"""
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if device_type and 'device' in df.columns:
        df = df[df['device'] == device_type]
    
    # Standardize column names
    cols = {}
    if 'rle_smoothed' in df.columns:
        cols['rle'] = pd.to_numeric(df['rle_smoothed'], errors='coerce')
    elif 'rle_raw' in df.columns:
        cols['rle'] = pd.to_numeric(df['rle_raw'], errors='coerce')
    
    for c in ['temp_c', 'power_w', 'util_pct', 'collapse', 'E_th', 'E_pw']:
        if c in df.columns:
            cols[c] = pd.to_numeric(df[c], errors='coerce')
    
    cols['index'] = range(len(df))
    return pd.DataFrame(cols)

def figure_1_efficiency_vs_load():
    """Plot RLE vs utilization to show efficiency curves"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Efficiency Curves: RLE vs Utilization', fontsize=16, fontweight='bold')
    
    datasets = [
        (PATHS['phone_alt'], 'mobile', 'Phone', 'tab:orange', axes[0]),
        (PATHS['laptop_1'], 'cpu', 'Laptop', 'tab:green', axes[1]),
        (PATHS['pc_gpu'], 'gpu', 'PC (GPU)', 'tab:blue', axes[2]),
    ]
    
    for path, dev_type, label, color, ax in datasets:
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns or 'util_pct' not in data.columns:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(label)
            continue
        
        # Scatter with alpha
        valid = data[['rle', 'util_pct']].dropna()
        ax.scatter(valid['util_pct'], valid['rle'], alpha=0.4, s=20, c=color, edgecolors='none')
        
        # Fit polynomial trend
        if len(valid) > 10:
            z = np.polyfit(valid['util_pct'], valid['rle'], 2)
            p = np.poly1d(z)
            x_trend = np.linspace(valid['util_pct'].min(), valid['util_pct'].max(), 100)
            ax.plot(x_trend, p(x_trend), '--', color=color, lw=2, alpha=0.8)
        
        ax.set_xlabel('Utilization (%)')
        ax.set_ylabel('RLE')
        ax.set_title(label)
        ax.grid(alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'efficiency_vs_load.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("✅ Saved efficiency_vs_load.png")

def figure_2_collapse_maps():
    """Heatmaps showing collapse events over time"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 9))
    fig.suptitle('Collapse Event Maps', fontsize=16, fontweight='bold')
    
    datasets = [
        (PATHS['phone_alt'], 'mobile', 'Phone', axes[0]),
        (PATHS['laptop_1'], 'cpu', 'Laptop', axes[1]),
        (PATHS['pc_gpu'], 'gpu', 'PC GPU', axes[2]),
    ]
    
    for path, dev_type, label, ax in datasets:
        data = load_device_data(path, dev_type)
        if data is None or 'collapse' not in data.columns:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_ylabel(label)
            continue
        
        c = data['collapse'].fillna(0).values
        # Reshape into 2D for heatmap
        grid_size = int(np.ceil(np.sqrt(len(c))))
        c_padded = np.pad(c, (0, grid_size**2 - len(c)), mode='constant')
        c_grid = c_padded[:grid_size**2].reshape(grid_size, grid_size)
        
        im = ax.imshow(c_grid, aspect='auto', cmap='Reds', interpolation='nearest', vmin=0, vmax=1)
        ax.set_title(label)
        ax.set_xlabel('Time blocks')
        ax.set_ylabel('Collapse events')
        plt.colorbar(im, ax=ax, label='Collapse')
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'collapse_maps.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("✅ Saved collapse_maps.png")

def figure_3_thermal_overlays():
    """Overlay temperature and power on RLE timeline"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    fig.suptitle('Thermal Overlays: RLE + Temp + Power', fontsize=16, fontweight='bold')
    
    datasets = [
        (PATHS['phone_alt'], 'mobile', 'Phone', axes[0]),
        (PATHS['laptop_1'], 'cpu', 'Laptop', axes[1]),
        (PATHS['pc_gpu'], 'gpu', 'PC GPU', axes[2]),
    ]
    
    for path, dev_type, label, ax in datasets:
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(label)
            continue
        
        ax1 = ax
        ax1.plot(data['index'], data['rle'], 'b-', lw=2, alpha=0.7, label='RLE')
        ax1.set_xlabel('Sample Index')
        ax1.set_ylabel('RLE', color='b')
        ax1.tick_params(axis='y', labelcolor='b')
        ax1.grid(alpha=0.3)
        ax1.legend(loc='upper left')
        
        # Twin axis for temp if available
        if 'temp_c' in data.columns and not data['temp_c'].isna().all():
            ax2 = ax.twinx()
            ax2.plot(data['index'], data['temp_c'], 'r-', lw=1.5, alpha=0.6, label='Temp (°C)')
            ax2.set_ylabel('Temperature (°C)', color='r')
            ax2.tick_params(axis='y', labelcolor='r')
            ax2.legend(loc='upper right')
        
        ax.set_title(label)
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'thermal_overlays.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("✅ Saved thermal_overlays.png")

def figure_4_entropy_strips():
    """Compact entropy art strips for all devices"""
    fig, axes = plt.subplots(3, 1, figsize=(16, 6))
    fig.suptitle('Entropy Art: Visual Efficiency Representations', fontsize=16, fontweight='bold')
    
    datasets = [
        (PATHS['phone_alt'], 'mobile', 'Phone', 'tab:orange', axes[0]),
        (PATHS['laptop_1'], 'cpu', 'Laptop', 'tab:green', axes[1]),
        (PATHS['pc_gpu'], 'gpu', 'PC GPU', 'tab:blue', axes[2]),
    ]
    
    for path, dev_type, label, color, ax in datasets:
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(label)
            continue
        
        rle = data['rle'].fillna(0).values
        # Normalize to 0-1 for intensity
        rle_norm = (rle - rle.min()) / (rle.max() - rle.min() + 1e-6)
        
        # Create 1D heatmap strip
        for i in range(len(rle_norm)):
            ax.axvspan(i-0.5, i+0.5, color=plt.cm.viridis(rle_norm[i]), alpha=0.8)
        
        ax.set_xlim(-0.5, len(rle_norm)-0.5)
        ax.set_ylim(-0.5, 0.5)
        ax.set_title(label)
        ax.axis('off')
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'entropy_strips.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("✅ Saved entropy_strips.png")

def figure_5_correlation_heatmap():
    """Correlation matrices for key variables"""
    # Load all data into single dataframe per device
    all_data = []
    
    datasets = [
        ('Phone', PATHS['phone_alt'], 'mobile'),
        ('Laptop', PATHS['laptop_1'], 'cpu'),
        ('PC GPU', PATHS['pc_gpu'], 'gpu'),
    ]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Correlation Heatmaps by Device', fontsize=16, fontweight='bold')
    
    for idx, (label, path, dev_type) in enumerate(datasets):
        data = load_device_data(path, dev_type)
        if data is None:
            axes[idx].text(0.5, 0.5, 'No data', ha='center', va='center', transform=axes[idx].transAxes)
            axes[idx].set_title(label)
            continue
        
        # Select numeric columns
        numeric_cols = ['rle', 'temp_c', 'power_w', 'util_pct', 'E_th', 'E_pw']
        numeric_cols = [c for c in numeric_cols if c in data.columns]
        corr_df = data[numeric_cols].corr()
        
        im = axes[idx].imshow(corr_df, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
        axes[idx].set_xticks(range(len(corr_df.columns)))
        axes[idx].set_xticklabels(corr_df.columns, rotation=45, ha='right')
        axes[idx].set_yticks(range(len(corr_df.columns)))
        axes[idx].set_yticklabels(corr_df.columns)
        axes[idx].set_title(label)
        plt.colorbar(im, ax=axes[idx], label='Correlation')
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'correlation_heatmaps.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("✅ Saved correlation_heatmaps.png")

def figure_6_animated_gif():
    """Animated time series showing RLE evolution"""
    # Use phone data as example
    data = load_device_data(PATHS['phone_alt'], 'mobile')
    if data is None or 'rle' not in data.columns:
        print("⚠️ Skipping GIF - no phone data")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    rle = data['rle'].fillna(0).values
    x_data, y_data = [], []
    
    line, = ax.plot([], [], 'b-', lw=2)
    ax.set_xlim(0, len(rle))
    ax.set_ylim(rle.min() - 0.1, rle.max() + 0.1)
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('RLE')
    ax.set_title('RLE Evolution (Animated)')
    ax.grid(alpha=0.3)
    
    def animate(frame):
        x_data.append(frame)
        y_data.append(rle[frame])
        line.set_data(x_data, y_data)
        return line,
    
    frames = min(200, len(rle))  # Limit to 200 frames
    anim = FuncAnimation(fig, animate, frames=frames, interval=50, blit=True, repeat=False)
    
    out_path = OUT_DIR / 'rle_evolution_animated.gif'
    anim.save(out_path, writer='pillow', fps=10)
    plt.close(fig)
    print(f"✅ Saved {out_path.name}")

def figure_7_power_efficiency():
    """RLE per watt efficiency curves"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Power Efficiency: RLE per Watt', fontsize=16, fontweight='bold')
    
    datasets = [
        (PATHS['phone_alt'], 'mobile', 'Phone', 'tab:orange', axes[0]),
        (PATHS['laptop_1'], 'cpu', 'Laptop', 'tab:green', axes[1]),
        (PATHS['pc_gpu'], 'gpu', 'PC GPU', 'tab:blue', axes[2]),
    ]
    
    for path, dev_type, label, color, ax in datasets:
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns or 'power_w' not in data.columns:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(label)
            continue
        
        # Calculate efficiency
        valid = data[['rle', 'power_w']].dropna()
        if len(valid) == 0 or (valid['power_w'] > 0).sum() == 0:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(label)
            continue
        
        efficiency = valid['rle'] / valid['power_w']
        ax.scatter(valid['power_w'], efficiency, alpha=0.4, s=20, c=color, edgecolors='none')
        
        # Trend line
        if len(valid) > 10:
            z = np.polyfit(valid['power_w'], efficiency, 2)
            p = np.poly1d(z)
            x_trend = np.linspace(valid['power_w'].min(), valid['power_w'].max(), 100)
            ax.plot(x_trend, p(x_trend), '--', color=color, lw=2, alpha=0.8)
        
        ax.set_xlabel('Power (W)')
        ax.set_ylabel('RLE per Watt')
        ax.set_title(label)
        ax.grid(alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'power_efficiency.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("✅ Saved power_efficiency.png")

def main():
    print("\n" + "="*70)
    print("GENERATING VISUALIZATION SUITE")
    print("="*70 + "\n")
    
    try:
        figure_1_efficiency_vs_load()
        figure_2_collapse_maps()
        figure_3_thermal_overlays()
        figure_4_entropy_strips()
        figure_5_correlation_heatmap()
        figure_7_power_efficiency()
    except Exception as e:
        print(f"⚠️ Error in static figures: {e}")
    
    try:
        figure_6_animated_gif()
    except ImportError:
        print("⚠️ Skipping GIF - Pillow not available for animation")
    except Exception as e:
        print(f"⚠️ Error in GIF: {e}")
    
    print("\n" + "="*70)
    print("VISUALIZATION SUITE COMPLETE")
    print("="*70)
    print(f"\nAll figures saved to: {OUT_DIR}\n")

if __name__ == '__main__':
    main()

