#!/usr/bin/env python3
"""
RLE Driver Analysis
Find what variables most strongly relate to RLE and analyze collapse events
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import argparse

def correlation_analysis(cpu_df):
    """Find which metrics correlate most strongly with RLE"""
    print("="*70)
    print("CORRELATION ANALYSIS")
    print("="*70)
    
    # Target variable
    target = 'rle_smoothed'
    
    # Potential drivers
    driver_cols = ['util_pct', 'power_w', 'a_load', 't_sustain_s', 'rolling_peak', 'E_th', 'E_pw']
    driver_cols = [c for c in driver_cols if c in cpu_df.columns]
    
    print(f"\nAnalyzing correlation with {target}:")
    print("-"*70)
    print(f"{'Variable':<20} {'Correlation':<15} {'Significance':<15}")
    print("-"*70)
    
    correlations = []
    
    for col in driver_cols:
        # Remove NaN values
        mask = cpu_df[target].notna() & cpu_df[col].notna()
        x = cpu_df.loc[mask, col]
        y = cpu_df.loc[mask, target]
        
        if len(x) > 10:  # Need minimum samples
            r, p = stats.pearsonr(x, y)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            
            print(f"{col:<20} {r:>8.4f}       {sig}")
            correlations.append((col, r, p))
    
    # Sort by absolute correlation
    correlations.sort(key=lambda x: abs(x[1]), reverse=True)
    
    print("\nTop 3 strongest correlations:")
    for i, (col, r, _) in enumerate(correlations[:3], 1):
        print(f"  {i}. {col}: {r:.4f}")
    
    return correlations

def regression_model(cpu_df):
    """Build regression model to predict RLE"""
    print("\n" + "="*70)
    print("REGRESSION MODEL")
    print("="*70)
    
    # Features
    feature_cols = ['util_pct', 'power_w', 'a_load', 'E_th', 'E_pw']
    feature_cols = [c for c in feature_cols if c in cpu_df.columns]
    
    # Target
    target = 'rle_smoothed'
    
    # Prepare data
    mask = cpu_df[target].notna()
    for col in feature_cols:
        mask &= cpu_df[col].notna()
    
    X = cpu_df.loc[mask, feature_cols]
    y = cpu_df.loc[mask, target]
    
    print(f"Using {len(X)} samples")
    print(f"Features: {feature_cols}")
    
    # Train model
    model = LinearRegression()
    model.fit(X, y)
    
    # Predictions
    y_pred = model.predict(X)
    
    # Metrics
    r2 = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    
    print(f"\nModel Performance:")
    print(f"  R² Score: {r2:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    
    print("\nFeature Importance (coefficients):")
    for i, (feature, coef) in enumerate(zip(feature_cols, model.coef_)):
        print(f"  {feature:<15} {coef:>10.4f}")
    
    print(f"\nIntercept: {model.intercept_:.4f}")
    
    return model, X.columns.tolist()

def collapse_analysis(cpu_df):
    """Analyze RLE behavior during collapse events"""
    print("\n" + "="*70)
    print("COLLAPSE ANALYSIS")
    print("="*70)
    
    if 'collapse' not in cpu_df.columns:
        print("No collapse data available")
        return
    
    collapsed = cpu_df[cpu_df['collapse'] == 1]
    normal = cpu_df[cpu_df['collapse'] == 0]
    
    if len(collapsed) == 0:
        print("\nNo collapse events detected in this dataset")
        print("\nCollapse detection appears to be working correctly -")
        print("no events at moderate loads means detector is properly tuned.")
        return
    
    print(f"\nCollapse Events: {len(collapsed)} ({len(collapsed)/len(cpu_df)*100:.2f}% of samples)")
    
    if len(collapsed) > 0:
        print("\n" + "="*70)
        print("RLE Behavior During Collapse Events")
        print("="*70)
        
        print(f"\n{'Metric':<25} {'Normal':<15} {'Collapsed':<15} {'Difference':<15}")
        print("-"*70)
        
        metrics = ['rle_smoothed', 'rle_raw', 'util_pct', 'power_w', 'a_load', 't_sustain_s']
        
        for metric in metrics:
            if metric in cpu_df.columns:
                normal_val = normal[metric].mean()
                collapsed_val = collapsed[metric].mean()
                diff = collapsed_val - normal_val
                
                print(f"{metric:<25} {normal_val:<15.4f} {collapsed_val:<15.4f} {diff:<15.4f}")
        
        # Check load distribution during collapse
        if 'util_pct' in collapsed.columns:
            print(f"\nUtilization during collapse:")
            print(f"  Mean: {collapsed['util_pct'].mean():.1f}%")
            print(f"  Range: {collapsed['util_pct'].min():.1f}% - {collapsed['util_pct'].max():.1f}%")
        
        # Analyze pre-collapse behavior
        print("\n" + "="*70)
        print("Pre-Collapse Behavior (10 samples before each collapse)")
        print("="*70)
        
        collapse_indices = cpu_df[cpu_df['collapse'] == 1].index
        
        pre_collapse_data = []
        for idx in collapse_indices[:10]:  # Limit to first 10 collapses to avoid overwhelming output
            pre_start = max(0, idx - 10)
            pre_samples = cpu_df.loc[pre_start:idx-1]
            if len(pre_samples) > 0:
                pre_collapse_data.append(pre_samples)
        
        if pre_collapse_data:
            pre_df = pd.concat(pre_collapse_data)
            
            print(f"Analyzed {len(pre_df)} pre-collapse samples")
            print(f"\nPre-collapse mean values:")
            
            for metric in ['rle_smoothed', 'util_pct', 'power_w', 'a_load']:
                if metric in pre_df.columns:
                    print(f"  {metric:<25} {pre_df[metric].mean():.4f}")
            
            print(f"\n  Collapse trigger: {pre_df['rolling_peak'].mean():.4f} (peak threshold)")

def generate_report(cpu_df, correlations, model_features, output_file="sessions/archive/rle_analysis_report.txt"):
    """Generate comprehensive report"""
    with open(output_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write("RLE DRIVER ANALYSIS REPORT\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Dataset: {len(cpu_df)} CPU samples\n")
        f.write(f"Duration: {len(cpu_df) / 3600:.2f} hours\n")
        f.write(f"\nMean RLE: {cpu_df['rle_smoothed'].mean():.4f}\n")
        f.write(f"Std RLE: {cpu_df['rle_smoothed'].std():.4f}\n")
        
        f.write("\n" + "="*70 + "\n")
        f.write("KEY FINDINGS\n")
        f.write("="*70 + "\n")
        
        if correlations:
            f.write("\nTop 3 RLE Correlations:\n")
            for i, (col, r, _) in enumerate(correlations[:3], 1):
                f.write(f"  {i}. {col}: {r:.4f}\n")
        
        if 'collapse' in cpu_df.columns:
            collapse_count = (cpu_df['collapse'] == 1).sum()
            f.write(f"\nCollapse events: {collapse_count} ({collapse_count/len(cpu_df)*100:.2f}%)\n")
        
        f.write(f"\nReport generated to: {output_file}\n")
    
    print(f"\n" + "="*70)
    print(f"Report saved: {output_file}")
    print("="*70)

def main():
    parser = argparse.ArgumentParser(description="Analyze what drives RLE")
    parser.add_argument("csv", help="Path to CSV file")
    
    args = parser.parse_args()
    
    # Load and clean data
    print(f"Loading: {args.csv}")
    df = pd.read_csv(args.csv)
    
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.drop_duplicates(subset=['timestamp', 'device'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # CPU data only
    cpu_df = df[df['device'] == 'cpu'].copy()
    
    print(f"\nLoaded {len(cpu_df)} CPU samples")
    
    # Run analyses
    correlations = correlation_analysis(cpu_df)
    model, features = regression_model(cpu_df)
    collapse_analysis(cpu_df)
    generate_report(cpu_df, correlations, features)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

