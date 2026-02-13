#!/usr/bin/env python3
"""
RID Real Session Validation - The Only Test That Matters

ChatGPT's final challenge:
"Run both versions on archived real session logs. Not synthetic. Not sweeps.
Not controlled ramps. Messy historical data."

Measures:
1. True positive rate (did it predict actual collapses?)
2. False positive rate (did it warn when nothing happened?)
3. Lead time (how much earlier than classical thresholds?)
4. Stability under noise (does S_n jump around chaotically?)

If decoupled version holds on real data → you have something practical.

Usage:
    python3 lab/analysis/rid_real_session_validation.py --csv sessions/archive/rle_20251030_19.csv
    
    # Or batch process all sessions
    python3 lab/analysis/rid_real_session_validation.py --batch sessions/archive/
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent / "monitoring"))
from rid_core import RIDCore
from rid_core_decoupled import RIDCoreDecoupled


class SessionValidator:
    """Validates RID on real session data"""
    
    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.samples = []
        self.classical_collapses = []  # From existing collapse column
        
    def load_session(self) -> bool:
        """Load session CSV and extract samples"""
        try:
            with open(self.csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Strip BOM if present
                content = f.read()
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                reader = csv.DictReader(content.splitlines())
                
                for i, row in enumerate(reader):
                    try:
                        # Required columns
                        util = float(row.get('util_pct', 0))
                        temp = float(row.get('temp_c', 0)) if row.get('temp_c') else None
                        power = float(row.get('power_w', 0)) if row.get('power_w') else None
                        
                        # Classical collapse detection (existing)
                        collapse = 1 if row.get('collapse', '0').strip() in ['1', '1.0'] else 0
                        
                        self.samples.append({
                            'index': i,
                            'util': util,
                            'temp': temp,
                            'power': power,
                            'classical_collapse': collapse
                        })
                        
                        if collapse:
                            self.classical_collapses.append(i)
                    
                    except (ValueError, KeyError) as e:
                        continue
            
            return len(self.samples) > 0
        
        except Exception as e:
            print(f"Error loading {self.csv_path}: {e}")
            return False
    
    def run_validation(self) -> Dict:
        """
        Run both coupled and decoupled versions, measure performance
        
        Returns dict with metrics:
        - true_positive_rate
        - false_positive_rate  
        - lead_time_samples
        - stability_score
        """
        
        if not self.samples:
            return None
        
        print(f"\nValidating: {self.csv_path.name}")
        print(f"  Samples: {len(self.samples)}")
        print(f"  Classical collapses: {len(self.classical_collapses)}")
        print()
        
        # Run both versions
        rid_coupled = RIDCore()
        rid_decoupled = RIDCoreDecoupled()
        
        results_coupled = []
        results_decoupled = []
        
        for sample in self.samples:
            # Coupled
            rc = rid_coupled.compute(
                sample['util'],
                sample['temp'],
                sample['power']
            )
            results_coupled.append(rc)
            
            # Decoupled
            rd = rid_decoupled.compute(
                sample['util'],
                sample['temp'],
                sample['power']
            )
            results_decoupled.append(rd)
        
        # Analyze both
        metrics_coupled = self._analyze_results(
            results_coupled, 
            [r.S_n for r in results_coupled],
            "Coupled"
        )
        
        metrics_decoupled = self._analyze_results(
            results_decoupled,
            [r.S_n_decoupled for r in results_decoupled],
            "Decoupled"
        )
        
        # Stability comparison
        self._compare_stability(
            [r.S_n for r in results_coupled],
            [r.S_n_decoupled for r in results_decoupled]
        )
        
        return {
            'coupled': metrics_coupled,
            'decoupled': metrics_decoupled,
            'classical_collapse_count': len(self.classical_collapses)
        }
    
    def _analyze_results(self, results, S_n_values, version_name: str) -> Dict:
        """Analyze RID predictions vs classical collapses"""
        
        # Find RID warnings/emergencies
        rid_warnings = []  # S_n < 0.4
        rid_emergencies = []  # S_n < 0.2
        
        for i, S_n in enumerate(S_n_values):
            if S_n < 0.4:
                rid_warnings.append(i)
            if S_n < 0.2:
                rid_emergencies.append(i)
        
        print(f"{version_name} Version:")
        print(f"  RID warnings (S_n < 0.4): {len(rid_warnings)}")
        print(f"  RID emergencies (S_n < 0.2): {len(rid_emergencies)}")
        
        # True positives: RID warned before classical collapse
        true_positives = 0
        lead_times = []
        
        for collapse_idx in self.classical_collapses:
            # Check if RID warned in window before collapse
            warning_window = range(max(0, collapse_idx - 20), collapse_idx)
            
            if any(i in rid_warnings for i in warning_window):
                true_positives += 1
                
                # Find first warning in window
                for i in warning_window:
                    if i in rid_warnings:
                        lead_times.append(collapse_idx - i)
                        break
        
        # False positives: RID warned but no classical collapse nearby
        false_positives = 0
        
        for warning_idx in rid_warnings:
            # Check if there's a classical collapse within ±20 samples
            nearby_window = range(max(0, warning_idx - 20), min(len(self.samples), warning_idx + 20))
            
            if not any(i in self.classical_collapses for i in nearby_window):
                false_positives += 1
        
        # Metrics
        tpr = true_positives / len(self.classical_collapses) if self.classical_collapses else 0.0
        fpr = false_positives / len(rid_warnings) if rid_warnings else 0.0
        avg_lead = statistics.mean(lead_times) if lead_times else 0.0
        
        print(f"  True positives: {true_positives}/{len(self.classical_collapses)} ({tpr*100:.1f}%)")
        print(f"  False positives: {false_positives}/{len(rid_warnings)} ({fpr*100:.1f}%)")
        if lead_times:
            print(f"  Lead time: {avg_lead:.1f} samples avg (range {min(lead_times)}-{max(lead_times)})")
        print()
        
        # Stability (variance of S_n)
        S_n_variance = statistics.variance(S_n_values) if len(S_n_values) > 1 else 0.0
        S_n_jumps = [abs(S_n_values[i] - S_n_values[i-1]) for i in range(1, len(S_n_values))]
        avg_jump = statistics.mean(S_n_jumps) if S_n_jumps else 0.0
        max_jump = max(S_n_jumps) if S_n_jumps else 0.0
        
        print(f"  S_n stability:")
        print(f"    Variance: {S_n_variance:.4f}")
        print(f"    Avg jump: {avg_jump:.4f}")
        print(f"    Max jump: {max_jump:.4f}")
        
        if avg_jump < 0.05:
            print(f"    ✓ Smooth (avg jump < 0.05)")
        else:
            print(f"    ⚠ Noisy (avg jump > 0.05)")
        print()
        
        return {
            'true_positive_rate': tpr,
            'false_positive_rate': fpr,
            'avg_lead_time': avg_lead,
            'variance': S_n_variance,
            'avg_jump': avg_jump,
            'max_jump': max_jump,
            'warnings_count': len(rid_warnings),
            'emergencies_count': len(rid_emergencies)
        }
    
    def _compare_stability(self, coupled_S_n, decoupled_S_n):
        """Compare noise characteristics"""
        
        print("Stability Comparison:")
        
        # Correlation
        if len(coupled_S_n) == len(decoupled_S_n):
            n = len(coupled_S_n)
            mean_c = sum(coupled_S_n) / n
            mean_d = sum(decoupled_S_n) / n
            
            cov = sum((coupled_S_n[i] - mean_c) * (decoupled_S_n[i] - mean_d) for i in range(n))
            std_c = (sum((x - mean_c)**2 for x in coupled_S_n) / n) ** 0.5
            std_d = (sum((x - mean_d)**2 for x in decoupled_S_n) / n) ** 0.5
            
            corr = cov / (std_c * std_d) if std_c * std_d > 0 else 0.0
            
            print(f"  Correlation: {corr:.3f}")
            
            if corr > 0.95:
                print(f"  → Very high agreement (> 0.95)")
            elif corr > 0.8:
                print(f"  → High agreement (0.8-0.95)")
            else:
                print(f"  → Moderate agreement (< 0.8)")
        
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate RID on real session data - the only test that matters"
    )
    parser.add_argument('--csv', type=str, help='Path to session CSV file')
    parser.add_argument('--batch', type=str, help='Path to directory with multiple CSVs')
    
    args = parser.parse_args()
    
    if not args.csv and not args.batch:
        print("Error: Must provide --csv or --batch")
        print()
        print("Usage:")
        print("  Single file:  python3 rid_real_session_validation.py --csv sessions/archive/rle_20251030_19.csv")
        print("  Batch:        python3 rid_real_session_validation.py --batch sessions/archive/")
        return 1
    
    print()
    print("=" * 100)
    print("RID REAL SESSION VALIDATION")
    print("The Only Test That Matters")
    print("=" * 100)
    print()
    print("Testing on REAL messy historical data (not synthetic sweeps)")
    print()
    print("Measures:")
    print("  1. True positive rate (predicted actual collapses?)")
    print("  2. False positive rate (warned when nothing happened?)")
    print("  3. Lead time (how much earlier than classical threshold?)")
    print("  4. Stability under noise (does S_n jump chaotically?)")
    print()
    print("If decoupled version holds here → you have something practical")
    print()
    
    csv_files = []
    
    if args.csv:
        csv_files = [Path(args.csv)]
    elif args.batch:
        batch_path = Path(args.batch)
        csv_files = list(batch_path.glob('*.csv'))
    
    if not csv_files:
        print("Error: No CSV files found")
        return 1
    
    print(f"Found {len(csv_files)} session file(s)")
    print()
    
    # Validate each session
    all_results = []
    
    for csv_path in csv_files:
        validator = SessionValidator(csv_path)
        
        if not validator.load_session():
            print(f"Skipping {csv_path.name} (failed to load)")
            continue
        
        results = validator.run_validation()
        
        if results:
            all_results.append({
                'file': csv_path.name,
                'metrics': results
            })
    
    # Summary
    if len(all_results) > 1:
        print("=" * 100)
        print("BATCH SUMMARY")
        print("=" * 100)
        print()
        
        coupled_tpr = [r['metrics']['coupled']['true_positive_rate'] for r in all_results]
        decoupled_tpr = [r['metrics']['decoupled']['true_positive_rate'] for r in all_results]
        
        coupled_fpr = [r['metrics']['coupled']['false_positive_rate'] for r in all_results]
        decoupled_fpr = [r['metrics']['decoupled']['false_positive_rate'] for r in all_results]
        
        print(f"Coupled:")
        print(f"  Avg TPR: {statistics.mean(coupled_tpr)*100:.1f}%")
        print(f"  Avg FPR: {statistics.mean(coupled_fpr)*100:.1f}%")
        print()
        
        print(f"Decoupled:")
        print(f"  Avg TPR: {statistics.mean(decoupled_tpr)*100:.1f}%")
        print(f"  Avg FPR: {statistics.mean(decoupled_fpr)*100:.1f}%")
        print()
        
        if abs(statistics.mean(coupled_tpr) - statistics.mean(decoupled_tpr)) < 0.05:
            print("VERDICT: Decoupled performs equivalently")
            print("  → Simplify to decoupled version")
        elif statistics.mean(coupled_tpr) > statistics.mean(decoupled_tpr):
            print("VERDICT: Coupled provides advantage")
            print("  → Keep thermal coupling")
        else:
            print("VERDICT: Decoupled outperforms")
            print("  → Definitely use decoupled version")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
