#!/usr/bin/env python3
"""
Stress Test Miner's Unified Laws - Find break points, not confirmations
Tests theoretical predictions against empirical data to identify failure modes
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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

def test_1_topology_independence():
    """
    Test Axiom III: Harmonic Containment
    Prediction: RLE should be independent of thermal topology
    Break condition: Significant correlation between devices with isolated thermal paths
    """
    print("\n" + "="*70)
    print("TEST 1: Topology Independence (Axiom III)")
    print("="*70)
    
    # Load PC CPU + GPU (should be partially coupled via shared case)
    cpu_data = load_device_data(PATHS['pc_cpu'], 'cpu')
    gpu_data = load_device_data(PATHS['pc_gpu'], 'gpu')
    
    if cpu_data is None or gpu_data is None or 'rle' not in cpu_data.columns or 'rle' not in gpu_data.columns:
        print("⚠️  Insufficient data")
        return None
    
    # Align by index
    min_len = min(len(cpu_data), len(gpu_data))
    cpu_rle = cpu_data['rle'].iloc[:min_len]
    gpu_rle = gpu_data['rle'].iloc[:min_len]
    
    # Calculate correlation
    correlation = cpu_rle.corr(gpu_rle)
    
    print(f"\n📊 CPU-GPU RLE Correlation: {correlation:.4f}")
    
    # Break condition: |correlation| > 0.3 suggests coupling dependency
    if abs(correlation) > 0.3:
        print(f"🔴 BREAK: Topology NOT independent (correlation = {correlation:.4f})")
        print(f"   Prediction failed: Devices are thermally coupled, violating independence claim")
    elif 0.1 < abs(correlation) <= 0.3:
        print(f"🟡 WARNING: Moderate coupling (correlation = {correlation:.4f})")
        print(f"   Independence claim is partially violated")
    else:
        print(f"✅ PASS: Topology independence confirmed (|correlation| < 0.1)")
    
    # Plot for visual confirmation
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Topology Independence Test', fontsize=14, fontweight='bold')
    
    # Scatter plot
    axes[0].scatter(cpu_rle, gpu_rle, alpha=0.4, s=20, edgecolors='none')
    axes[0].set_xlabel('CPU RLE')
    axes[0].set_ylabel('GPU RLE')
    axes[0].set_title(f'CPU vs GPU RLE (r={correlation:.3f})')
    axes[0].grid(alpha=0.3)
    
    # Time series overlay
    axes[1].plot(cpu_rle.values, label='CPU', alpha=0.7, lw=2)
    axes[1].plot(gpu_rle.values, label='GPU', alpha=0.7, lw=2)
    axes[1].set_xlabel('Sample Index')
    axes[1].set_ylabel('RLE')
    axes[1].set_title('Time Series Comparison')
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'test_1_topology_independence.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"📁 Saved: test_1_topology_independence.png\n")
    
    return {'test': 'topology_independence', 'correlation': float(correlation)}

def test_2_universal_scaling():
    """
    Test Axiom I: RLE formula universality
    Prediction: Same formula works across all platforms (dimensionless)
    Break condition: Different efficiency curves suggest platform-specific behavior
    """
    print("\n" + "="*70)
    print("TEST 2: Universal Scaling (Axiom I)")
    print("="*70)
    
    datasets = [
        ('Phone', PATHS['phone_alt'], 'mobile'),
        ('Laptop', PATHS['laptop_1'], 'cpu'),
        ('PC GPU', PATHS['pc_gpu'], 'gpu'),
    ]
    
    scaling_data = []
    for label, path, dev_type in datasets:
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns:
            continue
        
        rle = data['rle'].dropna()
        scaling_data.append({
            'label': label,
            'mean': float(rle.mean()),
            'std': float(rle.std()),
            'min': float(rle.min()),
            'max': float(rle.max()),
            'cv': float(rle.std() / rle.mean()) if rle.mean() != 0 else np.inf
        })
        
        print(f"\n{label}:")
        print(f"  Mean: {rle.mean():.4f}")
        print(f"  Std:  {rle.std():.4f}")
        print(f"  CV:   {rle.std() / rle.mean():.4f}")
    
    # Check coefficient of variation (CV) uniformity
    cvs = [d['cv'] for d in scaling_data if np.isfinite(d['cv'])]
    cv_mean = np.mean(cvs)
    cv_std = np.std(cvs)
    
    print(f"\n📊 Cross-Platform CV:")
    print(f"  Mean CV: {cv_mean:.4f}")
    print(f"  Std CV:  {cv_std:.4f}")
    
    # Break condition: CV spread > 50% suggests non-universal scaling
    if cv_std / cv_mean > 0.5:
        print(f"🔴 BREAK: Non-universal scaling (CV spread = {cv_std/cv_mean:.2%})")
        print(f"   Prediction failed: Platforms scale differently")
    else:
        print(f"✅ PASS: Universal scaling confirmed (CV spread < 50%)")
    
    # Comparison plot
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Universal Scaling Test', fontsize=14, fontweight='bold')
    
    # Boxplots
    labels = [d['label'] for d in scaling_data]
    means = [d['mean'] for d in scaling_data]
    stds = [d['std'] for d in scaling_data]
    
    axes[0, 0].bar(labels, means, yerr=stds, capsize=5, alpha=0.7)
    axes[0, 0].set_ylabel('Mean RLE ± Std')
    axes[0, 0].set_title('Mean RLE by Platform')
    axes[0, 0].tick_params(axis='x', rotation=45)
    axes[0, 0].grid(alpha=0.3, axis='y')
    
    # CV comparison
    cvs_plot = [d['cv'] for d in scaling_data if np.isfinite(d['cv'])]
    labels_plot = [d['label'] for d in scaling_data if np.isfinite(d['cv'])]
    axes[0, 1].bar(labels_plot, cvs_plot, alpha=0.7, color='orange')
    axes[0, 1].set_ylabel('Coefficient of Variation')
    axes[0, 1].set_title('Variability Across Platforms')
    axes[0, 1].tick_params(axis='x', rotation=45)
    axes[0, 1].grid(alpha=0.3, axis='y')
    
    # Ranges
    mins = [d['min'] for d in scaling_data]
    maxs = [d['max'] for d in scaling_data]
    axes[1, 0].bar(labels, [maxs[i] - mins[i] for i in range(len(labels))], alpha=0.7, color='green')
    axes[1, 0].set_ylabel('RLE Range')
    axes[1, 0].set_title('Dynamic Range by Platform')
    axes[1, 0].tick_params(axis='x', rotation=45)
    axes[1, 0].grid(alpha=0.3, axis='y')
    
    # Summary table
    axes[1, 1].axis('off')
    table_data = [[d['label'], f"{d['mean']:.4f}", f"{d['std']:.4f}", f"{d['cv']:.4f}"] for d in scaling_data if np.isfinite(d['cv'])]
    table = axes[1, 1].table(cellText=table_data,
                            colLabels=['Platform', 'Mean', 'Std', 'CV'],
                            cellLoc='center',
                            loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    axes[1, 1].set_title('Summary Statistics')
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'test_2_universal_scaling.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"📁 Saved: test_2_universal_scaling.png\n")
    
    return {'test': 'universal_scaling', 'cv_mean': float(cv_mean), 'cv_std': float(cv_std)}

def test_3_thermal_paths():
    """
    Test Axiom II: The Two Thermal Paths
    Prediction: Heat → faster resolution, Cold → faster recursion
    Break condition: No correlation between temp and efficiency parameters
    """
    print("\n" + "="*70)
    print("TEST 3: Thermal Paths (Axiom II)")
    print("="*70)
    
    # Focus on phone data (has temp measurements)
    data = load_device_data(PATHS['phone_alt'], 'mobile')
    
    if data is None or 'rle' not in data.columns or 'temp_c' not in data.columns:
        print("⚠️  Insufficient temperature data")
        return None
    
    # Calculate correlations
    rle_temp_corr = data['rle'].corr(data['temp_c'])
    
    # Split into heating vs cooling phases
    temp_diff = data['temp_c'].diff().dropna()
    heating = data.iloc[1:].copy()
    heating = heating[temp_diff > 0].index
    cooling = data.iloc[1:].copy()
    cooling = cooling[temp_diff < 0].index
    
    heating_rle = data.loc[heating, 'rle'].mean() if len(heating) > 0 else np.nan
    cooling_rle = data.loc[cooling, 'rle'].mean() if len(cooling) > 0 else np.nan
    
    print(f"\n📊 RLE-Temperature Correlation: {rle_temp_corr:.4f}")
    print(f"   Mean RLE during heating: {heating_rle:.4f}")
    print(f"   Mean RLE during cooling: {cooling_rle:.4f}")
    
    # Break condition: No significant temp-RLE correlation violates thermal path hypothesis
    if abs(rle_temp_corr) < 0.1:
        print(f"🔴 BREAK: No thermal correlation (r={rle_temp_corr:.4f})")
        print(f"   Prediction failed: Temperature doesn't affect efficiency as claimed")
    elif 0.1 <= abs(rle_temp_corr) < 0.3:
        print(f"🟡 WARNING: Weak thermal correlation (r={rle_temp_corr:.4f})")
        print(f"   Thermal path theory partially supported")
    else:
        print(f"✅ PASS: Thermal correlation confirmed (|r| > 0.3)")
    
    # Visualization
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    fig.suptitle('Thermal Paths Test (Axiom II)', fontsize=14, fontweight='bold')
    
    # Scatter
    axes[0].scatter(data['temp_c'], data['rle'], alpha=0.4, s=20, edgecolors='none', c=data['index'], cmap='viridis')
    axes[0].set_xlabel('Temperature (°C)')
    axes[0].set_ylabel('RLE')
    axes[0].set_title(f'Temperature vs RLE (r={rle_temp_corr:.3f})')
    axes[0].grid(alpha=0.3)
    
    # Time series
    axes[1].plot(data['index'], data['rle'], label='RLE', lw=2, alpha=0.7)
    ax1_twin = axes[1].twinx()
    ax1_twin.plot(data['index'], data['temp_c'], color='red', label='Temp', lw=1.5, alpha=0.6)
    axes[1].set_xlabel('Sample Index')
    axes[1].set_ylabel('RLE', color='blue')
    ax1_twin.set_ylabel('Temperature (°C)', color='red')
    axes[1].legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    axes[1].grid(alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'test_3_thermal_paths.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"📁 Saved: test_3_thermal_paths.png\n")
    
    return {'test': 'thermal_paths', 'correlation': float(rle_temp_corr)}

def test_4_harmonic_containment():
    """
    Test Axiom III: Harmonic Containment - bounded growth/decay
    Prediction: RLE should stay bounded, not diverge to infinity
    Break condition: Unbounded growth or systemic instability
    """
    print("\n" + "="*70)
    print("TEST 4: Harmonic Containment (Axiom III)")
    print("="*70)
    
    datasets = [
        ('Phone', PATHS['phone_alt'], 'mobile'),
        ('Laptop', PATHS['laptop_1'], 'cpu'),
        ('PC GPU', PATHS['pc_gpu'], 'gpu'),
    ]
    
    containment_tests = []
    for label, path, dev_type in datasets:
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns:
            continue
        
        rle = data['rle'].dropna()
        
        # Test for boundedness
        max_rle = rle.max()
        min_rle = rle.min()
        range_rle = max_rle - min_rle
        
        # Test for stability (low drift)
        first_half = rle.iloc[:len(rle)//2].mean()
        second_half = rle.iloc[len(rle)//2:].mean()
        drift = abs(second_half - first_half)
        
        # Test for escape behavior
        q99 = rle.quantile(0.99)
        q01 = rle.quantile(0.01)
        
        containment_tests.append({
            'label': label,
            'max': float(max_rle),
            'min': float(min_rle),
            'range': float(range_rle),
            'drift': float(drift),
            'q99_q01': float(q99 - q01)
        })
        
        print(f"\n{label}:")
        print(f"  Range: [{min_rle:.4f}, {max_rle:.4f}]")
        print(f"  Drift: {drift:.4f}")
        print(f"  99%-1% range: {q99 - q01:.4f}")
    
    # Break condition: Extreme drift or unbounded range
    avg_drift = np.mean([d['drift'] for d in containment_tests])
    max_range = max([d['range'] for d in containment_tests])
    
    print(f"\n📊 Containment Metrics:")
    print(f"  Average drift: {avg_drift:.4f}")
    print(f"  Maximum range: {max_range:.4f}")
    
    if avg_drift > 0.5 or max_range > 10:
        print(f"🔴 BREAK: Containment violated")
        print(f"   Prediction failed: System shows unbounded behavior")
    elif avg_drift > 0.2 or max_range > 5:
        print(f"🟡 WARNING: Marginal containment (drift={avg_drift:.4f}, range={max_range:.4f})")
        print(f"   Harmonic bounds are weak")
    else:
        print(f"✅ PASS: Containment confirmed")
    
    # Visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Harmonic Containment Test (Axiom III)', fontsize=14, fontweight='bold')
    
    # Ranges
    labels = [d['label'] for d in containment_tests]
    ranges = [d['range'] for d in containment_tests]
    axes[0, 0].bar(labels, ranges, alpha=0.7, color='blue')
    axes[0, 0].set_ylabel('RLE Range')
    axes[0, 0].set_title('Boundedness Test')
    axes[0, 0].tick_params(axis='x', rotation=45)
    axes[0, 0].grid(alpha=0.3, axis='y')
    
    # Drifts
    drifts = [d['drift'] for d in containment_tests]
    axes[0, 1].bar(labels, drifts, alpha=0.7, color='orange')
    axes[0, 1].set_ylabel('Mean Drift')
    axes[0, 1].set_title('Stability Test')
    axes[0, 1].tick_params(axis='x', rotation=45)
    axes[0, 1].grid(alpha=0.3, axis='y')
    
    # Time series for each
    for idx, (label, path, dev_type) in enumerate(datasets):
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns:
            continue
        row = idx // 2
        col = idx % 2
        if row < 2:
            axes[row, col].plot(data['index'], data['rle'], lw=1.5, alpha=0.8)
            axes[row, col].set_title(f'{label} RLE Timeline')
            axes[row, col].set_xlabel('Sample Index')
            axes[row, col].set_ylabel('RLE')
            axes[row, col].grid(alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'test_4_harmonic_containment.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"📁 Saved: test_4_harmonic_containment.png\n")
    
    return {'test': 'harmonic_containment', 'avg_drift': float(avg_drift), 'max_range': float(max_range)}

def main():
    print("\n" + "="*70)
    print("STRESS TESTING MINER'S UNIFIED LAWS")
    print("="*70)
    print("\nObjective: Find break points, not confirmations")
    print("Testing theoretical predictions against empirical data\n")
    
    results = []
    
    # Run all tests
    try:
        result = test_1_topology_independence()
        if result:
            results.append(result)
    except Exception as e:
        print(f"❌ Test 1 failed: {e}\n")
    
    try:
        result = test_2_universal_scaling()
        if result:
            results.append(result)
    except Exception as e:
        print(f"❌ Test 2 failed: {e}\n")
    
    try:
        result = test_3_thermal_paths()
        if result:
            results.append(result)
    except Exception as e:
        print(f"❌ Test 3 failed: {e}\n")
    
    try:
        result = test_4_harmonic_containment()
        if result:
            results.append(result)
    except Exception as e:
        print(f"❌ Test 4 failed: {e}\n")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    breaks = sum(1 for r in results if 'correlation' in r and (abs(r.get('correlation', 0)) > 0.3 or abs(r.get('correlation', 0)) < 0.1))
    
    print(f"\n✅ Tests completed: {len(results)}")
    print(f"🔴 Breaks found: {breaks}")
    print(f"📊 Overall verdict: {'BREAK DETECTED' if breaks > 0 else 'PASSING WITH WARNINGS'}")
    
    # Save results
    out_file = OUT_DIR / '../STRESS_TEST_RESULTS.json'
    with open(out_file, 'w') as f:
        json.dump({
            'timestamp': datetime.utcnow().isoformat(),
            'results': results,
            'breaks_detected': breaks,
        }, f, indent=2)
    
    print(f"\n📁 Results saved: {out_file}\n")

if __name__ == '__main__':
    main()

