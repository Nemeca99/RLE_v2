#!/usr/bin/env python3
"""
Revised Axiom III Validation: Probabilistic Containment with Bounds
Implements proper drift metrics, knee-point detection, and regime segmentation
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
from scipy import stats

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
    
    for c in ['temp_c', 'power_w', 'util_pct', 'collapse']:
        if c in df.columns:
            cols[c] = pd.to_numeric(df[c], errors='coerce')
    
    cols['index'] = range(len(df))
    return pd.DataFrame(cols)

def detect_knee_power(data, window=20):
    """
    Detect knee point P_k: power level where efficiency starts to drop
    Returns power level at knee
    """
    if 'power_w' not in data.columns or 'rle' not in data.columns:
        return None
    
    valid = data[['power_w', 'rle']].dropna()
    if len(valid) < window:
        return None
    
    # Bin by power and compute mean RLE
    valid_sorted = valid.sort_values('power_w')
    bins = np.linspace(valid_sorted['power_w'].min(), valid_sorted['power_w'].max(), 20)
    valid_sorted['bin'] = pd.cut(valid_sorted['power_w'], bins=bins)
    
    bin_means = valid_sorted.groupby('bin').agg({'rle': 'mean', 'power_w': 'mean'}).reset_index()
    bin_means = bin_means.dropna()
    
    if len(bin_means) < 3:
        return None
    
    # Find peak efficiency (knee is where RLE starts dropping after peak)
    peak_idx = bin_means['rle'].idxmax()
    peak_power = bin_means.loc[peak_idx, 'power_w']
    
    return float(peak_power)

def measure_robust_drift(rle_series, quantiles=(0.01, 0.99)):
    """
    Measure robust drift: winsorized range / MAD
    Returns: robust drift measure
    """
    rle_clean = rle_series.dropna()
    if len(rle_clean) < 10:
        return None
    
    q01, q99 = np.quantile(rle_clean, quantiles)
    mad = np.median(np.abs(rle_clean - np.median(rle_clean)))
    
    if mad == 0:
        return None
    
    robust_drift = (q99 - q01) / mad
    return float(robust_drift)

def segment_regimes(data, power_col='power_w', grace_period=120):
    """
    Segment data into steady-state regimes, excluding transitions
    Returns: list of (start_idx, end_idx, regime_type) tuples
    """
    if power_col not in data.columns:
        return [(0, len(data), 'unknown')]
    
    power = data[power_col].dropna()
    if len(power) < grace_period:
        return [(0, len(data), 'transient')]
    
    # Compute rolling mean and std
    rolling_mean = power.rolling(window=grace_period, center=True).mean()
    rolling_std = power.rolling(window=grace_period, center=True).std()
    
    # Detect regime changes (large shifts in power)
    regime_changes = []
    for i in range(grace_period, len(power) - grace_period):
        if abs(rolling_mean.iloc[i] - rolling_mean.iloc[i - grace_period]) > 2 * rolling_std.iloc[i]:
            regime_changes.append(i)
    
    # Split into regimes
    regimes = []
    prev_idx = grace_period
    for change_idx in regime_changes:
        if change_idx - prev_idx > grace_period:
            regimes.append((prev_idx, change_idx - grace_period, 'steady'))
        prev_idx = change_idx
    regimes.append((prev_idx, len(data) - grace_period, 'steady'))
    
    return regimes if regimes else [(0, len(data), 'unknown')]

def compute_allan_variance(rle_series, max_tau=100):
    """
    Compute Allan variance over different time scales
    Measures mean reversion (containment)
    """
    rle_clean = rle_series.dropna().values
    if len(rle_clean) < 2 * max_tau:
        return None, None
    
    taus = np.logspace(0, np.log10(max_tau), 20).astype(int)
    taus = taus[taus < len(rle_clean) // 2]
    
    allan_vars = []
    for tau in taus:
        num_groups = len(rle_clean) // tau
        if num_groups < 2:
            break
        
        groups = rle_clean[:num_groups * tau].reshape(num_groups, tau)
        means = np.mean(groups, axis=1)
        variances = np.var(np.diff(means))  # Simplified Allan variance
        allan_vars.append(variances)
    
    return taus[:len(allan_vars)], np.array(allan_vars)

def validate_revised_axiom_3():
    """
    Validate Revised Axiom III with probabilistic bounds
    """
    print("\n" + "="*70)
    print("REVISED AXIOM III VALIDATION: Probabilistic Containment")
    print("="*70)
    
    datasets = [
        ('Phone', PATHS['phone_alt'], 'mobile'),
        ('Laptop', PATHS['laptop_1'], 'cpu'),
        ('PC GPU', PATHS['pc_gpu'], 'gpu'),
    ]
    
    results = []
    
    for label, path, dev_type in datasets:
        print(f"\n{'='*70}")
        print(f"Testing: {label}")
        print('='*70)
        
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns:
            print("⚠️  Insufficient data")
            continue
        
        rle = data['rle'].dropna()
        
        # 1. Detect knee power
        pk = detect_knee_power(data)
        print(f"\n1. Knee Power Detection:")
        if pk:
            print(f"   P_k = {pk:.1f}W")
        else:
            print(f"   ⚠️  Could not detect knee")
        
        # 2. Robust drift measurement
        robust_drift = measure_robust_drift(rle)
        print(f"\n2. Robust Drift (Q99-Q01 / MAD):")
        if robust_drift:
            print(f"   delta_robust = {robust_drift:.2f}")
        else:
            print(f"   ⚠️  Could not compute")
        
        # 3. Segment regimes
        regimes = segment_regimes(data)
        print(f"\n3. Regime Segmentation:")
        print(f"   Found {len(regimes)} regimes")
        for start, end, reg_type in regimes:
            print(f"   [{start}:{end}] {reg_type}")
        
        # 4. Allan variance (mean reversion test)
        taus, allan_vars = compute_allan_variance(rle)
        print(f"\n4. Allan Variance (Mean Reversion):")
        if allan_vars is not None and len(allan_vars) > 0:
            # Check if variance decreases with time scale (mean reversion)
            slope = np.polyfit(np.log10(taus[:len(allan_vars)]), np.log10(allan_vars + 1e-10), 1)[0]
            print(f"   Slope: {slope:.3f}")
            if slope < -0.5:
                print(f"   ✅ Mean reversion confirmed (slope < -0.5)")
            else:
                print(f"   ⚠️  Weak mean reversion (slope ≥ -0.5)")
        
        # 5. Evaluate containment
        print(f"\n5. Containment Evaluation:")
        
        # Get power info if available
        below_knee = True
        if pk and 'power_w' in data.columns:
            mean_power = data['power_w'].dropna().mean()
            below_knee = mean_power <= pk
            print(f"   Mean power: {mean_power:.1f}W")
            print(f"   Below knee (≤{pk:.1f}W): {below_knee}")
        
        # Evaluate bounds
        q99 = rle.quantile(0.99)
        q01 = rle.quantile(0.01)
        rle_range = q99 - q01
        
        if below_knee and robust_drift and robust_drift < 5.0:
            print(f"   ✅ PASS: Robust drift < 5.0")
            verdict = 'PASS'
        elif below_knee and robust_drift:
            print(f"   🟡 WARNING: Robust drift = {robust_drift:.2f}")
            verdict = 'WARNING'
        elif not below_knee:
            print(f"   🟡 WARNING: Above knee power, containment not guaranteed")
            verdict = 'EXEMPT'
        else:
            print(f"   🔴 FAIL: Unbounded behavior detected")
            verdict = 'FAIL'
        
        results.append({
            'label': label,
            'P_k': pk,
            'robust_drift': robust_drift,
            'q99_q01': float(rle_range),
            'below_knee': bool(below_knee),
            'verdict': verdict,
            'regimes': len(regimes),
        })
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    
    passes = sum(1 for r in results if r['verdict'] == 'PASS')
    warnings = sum(1 for r in results if r['verdict'] in ['WARNING', 'EXEMPT'])
    fails = sum(1 for r in results if r['verdict'] == 'FAIL')
    
    print(f"\n✅ PASS: {passes}")
    print(f"🟡 WARNING/EXEMPT: {warnings}")
    print(f"🔴 FAIL: {fails}")
    
    return results

def visualize_revised_validation():
    """Generate visualization of revised Axiom III validation"""
    datasets = [
        ('Phone', PATHS['phone_alt'], 'mobile'),
        ('Laptop', PATHS['laptop_1'], 'cpu'),
        ('PC GPU', PATHS['pc_gpu'], 'gpu'),
    ]
    
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle('Revised Axiom III: Probabilistic Containment Validation', fontsize=16, fontweight='bold')
    
    for idx, (label, path, dev_type) in enumerate(datasets):
        data = load_device_data(path, dev_type)
        if data is None or 'rle' not in data.columns:
            continue
        
        rle = data['rle'].dropna()
        
        # Left: RLE timeline with bounds
        axes[idx, 0].plot(rle.values, lw=1.5, alpha=0.7, color='blue')
        q01, q99 = rle.quantile([0.01, 0.99])
        axes[idx, 0].axhline(q01, color='red', linestyle='--', alpha=0.5, label='Q01')
        axes[idx, 0].axhline(q99, color='red', linestyle='--', alpha=0.5, label='Q99')
        axes[idx, 0].set_ylabel('RLE')
        axes[idx, 0].set_title(f'{label}: RLE Timeline')
        axes[idx, 0].legend()
        axes[idx, 0].grid(alpha=0.3)
        
        # Right: Allan variance
        taus, allan_vars = compute_allan_variance(rle)
        if allan_vars is not None and len(allan_vars) > 0:
            axes[idx, 1].loglog(taus[:len(allan_vars)], allan_vars + 1e-10, 'o-', lw=2, alpha=0.7)
            axes[idx, 1].set_xlabel('Time Scale τ (samples)')
            axes[idx, 1].set_ylabel('Allan Variance')
            axes[idx, 1].set_title(f'{label}: Mean Reversion')
            axes[idx, 1].grid(alpha=0.3, which='both')
        else:
            axes[idx, 1].text(0.5, 0.5, 'Insufficient data', ha='center', va='center', transform=axes[idx, 1].transAxes)
            axes[idx, 1].set_title(f'{label}: Allan Variance')
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'revised_axiom_3_validation.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"\n📁 Saved: revised_axiom_3_validation.png")

def main():
    print("\n" + "="*70)
    print("REVISED AXIOM III VALIDATION")
    print("="*70)
    print("\nTesting probabilistic containment with:")
    print("- Knee power detection (P_k)")
    print("- Robust drift measurement (Q99-Q01 / MAD)")
    print("- Regime segmentation")
    print("- Allan variance (mean reversion)")
    print("- Domain restrictions (< P_k)\n")
    
    results = validate_revised_axiom_3()
    visualize_revised_validation()
    
    # Save results
    with open(OUT_DIR / '../REVISED_AXIOM_3_RESULTS.json', 'w') as f:
        json.dump({
            'timestamp': datetime.utcnow().isoformat(),
            'results': results,
            'tests': [
                'knee_power_detection',
                'robust_drift_measurement',
                'regime_segmentation',
                'allan_variance',
                'domain_restrictions'
            ]
        }, f, indent=2)
    
    print(f"\n📁 Results saved: REVISED_AXIOM_3_RESULTS.json\n")

if __name__ == '__main__':
    main()

