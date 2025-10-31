#!/usr/bin/env python3
"""
RLE Spectral Analysis
Fourier/FFT analysis to detect periodic patterns that precede instability
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from scipy import signal
from pathlib import Path

def analyze_rle_spectrum(df, output_dir):
    """Perform FFT analysis on RLE time series"""
    
    print("="*70)
    print("RLE SPECTRAL ANALYSIS")
    print("="*70)
    
    cpu_df = df[df['device'] == 'cpu'].copy()
    
    if 'rle_smoothed' not in cpu_df.columns:
        print("ERROR: No RLE data available")
        return
    
    # Extract RLE time series
    rle_series = cpu_df['rle_smoothed'].values
    rle_series = rle_series[~np.isnan(rle_series)]
    
    if len(rle_series) < 100:
        print(f"Insufficient samples for FFT (need >100, have {len(rle_series)})")
        return
    
    print(f"\nAnalyzing {len(rle_series)} RLE samples")
    
    # Compute FFT
    sampling_rate = 1.0  # 1 Hz
    duration = len(rle_series)
    
    # FFT
    fft_values = np.fft.rfft(rle_series)
    frequencies = np.fft.rfftfreq(len(rle_series), 1/sampling_rate)
    power_spectrum = np.abs(fft_values) ** 2
    
    # Find dominant frequencies
    dominant_freq_idx = np.argsort(power_spectrum)[-5:][::-1]
    
    print("\n" + "="*70)
    print("DOMINANT FREQUENCIES")
    print("="*70)
    print(f"{'Frequency (Hz)':<20} {'Period (s)':<20} {'Power':<20}")
    print("-"*70)
    
    for idx in dominant_freq_idx:
        freq = frequencies[idx]
        period = 1 / freq if freq > 0 else float('inf')
        power = power_spectrum[idx]
        print(f"{freq:<20.4f} {period:<20.2f} {power:<20.4e}")
    
    # Detect periodic patterns
    print("\n" + "="*70)
    print("PERIODIC PATTERN DETECTION")
    print("="*70)
    
    # Check for low-frequency components (thermal cycles)
    low_freq_mask = (frequencies > 0.001) & (frequencies < 0.1)
    low_freq_power = power_spectrum[low_freq_mask].sum()
    total_power = power_spectrum.sum()
    low_freq_ratio = low_freq_power / total_power if total_power > 0 else 0
    
    print(f"Low-frequency power (<0.1 Hz): {low_freq_ratio*100:.2f}%")
    
    if low_freq_ratio > 0.3:
        print("⚠ Thermal cycling detected - slow periodic heating/cooling")
    else:
        print("✓ No significant thermal cycling")
    
    # Check for high-frequency noise
    high_freq_mask = frequencies > 0.5
    high_freq_power = power_spectrum[high_freq_mask].sum()
    high_freq_ratio = high_freq_power / total_power if total_power > 0 else 0
    
    print(f"High-frequency noise (>0.5 Hz): {high_freq_ratio*100:.2f}%")
    
    if high_freq_ratio > 0.1:
        print("⚠ High-frequency noise present - unstable system")
    else:
        print("✓ System relatively stable")
    
    # Generate plots
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    
    # Plot 1: RLE time series
    ax1 = axes[0]
    time_axis = np.arange(len(rle_series))
    ax1.plot(time_axis, rle_series, linewidth=0.5, alpha=0.7)
    ax1.set_xlabel('Sample Index', fontsize=11)
    ax1.set_ylabel('RLE', fontsize=11)
    ax1.set_title('RLE Time Series', fontsize=13, fontweight='bold')
    ax1.grid(alpha=0.3)
    
    # Plot 2: Power spectrum
    ax2 = axes[1]
    ax2.plot(frequencies, power_spectrum, linewidth=1)
    
    # Highlight dominant frequencies
    for idx in dominant_freq_idx[:3]:
        ax2.axvline(x=frequencies[idx], color='red', linestyle='--', alpha=0.5)
        ax2.text(frequencies[idx], power_spectrum[idx], 
                f"{frequencies[idx]:.3f} Hz", rotation=90, ha='right')
    
    ax2.set_xlabel('Frequency (Hz)', fontsize=11)
    ax2.set_ylabel('Power', fontsize=11)
    ax2.set_title('RLE Power Spectrum (FFT)', fontsize=13, fontweight='bold')
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.grid(alpha=0.3)
    
    # Plot 3: Spectrogram (if long enough)
    if len(rle_series) > 200:
        ax3 = axes[2]
        f, t, Sxx = signal.spectrogram(rle_series, fs=1.0, nperseg=64)
        im = ax3.pcolormesh(t, f, 10 * np.log10(Sxx), shading='gouraud')
        plt.colorbar(im, ax=ax3, label='Power (dB)')
        ax3.set_xlabel('Time', fontsize=11)
        ax3.set_ylabel('Frequency (Hz)', fontsize=11)
        ax3.set_title('RLE Spectrogram (Time-Frequency Analysis)', fontsize=13, fontweight='bold')
    else:
        ax3 = axes[2]
        ax3.text(0.5, 0.5, 'Insufficient data for spectrogram', 
                ha='center', va='center', transform=ax3.transAxes)
        ax3.set_title('RLE Spectrogram', fontsize=13, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/rle_spectral_analysis.png', dpi=150)
    print(f"\n✓ Saved: {output_dir}/rle_spectral_analysis.png")
    plt.close()
    
    print("\n" + "="*70)
    print("INTERPRETATION")
    print("="*70)
    
    dominant_period = 1 / frequencies[dominant_freq_idx[0]] if frequencies[dominant_freq_idx[0]] > 0 else 0
    
    if dominant_period > 100:
        print(f"Dominant period: {dominant_period:.1f}s")
        print("→ Thermal relaxation cycles (slow heating/cooling)")
    elif dominant_period > 10:
        print(f"Dominant period: {dominant_period:.1f}s")
        print("→ Thermal response to load changes")
    else:
        print(f"Dominant period: {dominant_period:.1f}s")
        print("→ High-frequency variation (possible instability)")

def main():
    parser = argparse.ArgumentParser(description="RLE spectral analysis")
    parser.add_argument("csv", help="Path to CSV file")
    parser.add_argument("--plot", action="store_true", help="Generate visualization")
    
    args = parser.parse_args()
    
    print(f"Loading: {args.csv}")
    df = pd.read_csv(args.csv)
    
    # Clean data
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.drop_duplicates(subset=['timestamp', 'device'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Run analysis
    if args.plot:
        output_dir = Path("sessions/archive/plots")
        output_dir.mkdir(parents=True, exist_ok=True)
        analyze_rle_spectrum(df, output_dir)
    else:
        print("Add --plot flag to generate visualizations")
    
    print("\n" + "="*70)
    print("SPECTRAL ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

