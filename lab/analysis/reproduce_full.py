#!/usr/bin/env python3
"""
Full reproduction pipeline for Miner's Unified Laws
Regenerates all figures and computes summary metrics
"""
import json
import sys
from pathlib import Path
from datetime import datetime

def main():
    print("\n" + "="*70)
    print("MINER'S UNIFIED LAWS - FULL REPRODUCTION")
    print("="*70)
    
    print("\n1. Generating cross-device overlay figures...")
    try:
        from generate_publication_figures import main as gen_pub
        gen_pub()
        print("   [OK] Cross-device overlays generated")
    except Exception as e:
        print(f"   [FAIL] Failed: {e}")
        return 1
    
    print("\n2. Generating visualization suite...")
    try:
        from generate_visualization_suite import main as gen_viz
        gen_viz()
        print("   [OK] Visualization suite generated")
    except Exception as e:
        print(f"   [FAIL] Failed: {e}")
        return 1
    
    print("\n3. Running revised Axiom III validation...")
    try:
        from revised_axiom_3_validation import main as val_axiom3
        val_axiom3()
        print("   [OK] Axiom III validation complete")
    except Exception as e:
        print(f"   [FAIL] Failed: {e}")
        return 1
    
    print("\n4. Compiling summary metrics...")
    try:
        from generate_cross_device_report import generate_report
        generate_report()
        print("   [OK] Cross-device report generated")
    except Exception as e:
        print(f"   [FAIL] Failed: {e}")
        return 1
    
    print("\n" + "="*70)
    print("REPRODUCTION COMPLETE")
    print("="*70)
    
    # Read and display key metrics
    try:
        results_path = Path('lab/sessions/archive/REVISED_AXIOM_3_RESULTS.json')
        if results_path.exists():
            with open(results_path) as f:
                results = json.load(f)
            
            print("\nKey Metrics:")
            for r in results['results']:
                print(f"  {r['label']}:")
                print(f"    P_k = {r['P_k']:.1f}W")
                print(f"    Robust drift = {r['robust_drift']:.2f}")
                print(f"    Below knee: {r['below_knee']}")
                print(f"    Verdict: {r['verdict']}")
    except Exception as e:
        print(f"   [WARN] Could not load metrics: {e}")
    
    print(f"\nAll outputs saved to: lab/sessions/archive/")
    print("\nReproduction complete. Verify figures match published results.\n")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

