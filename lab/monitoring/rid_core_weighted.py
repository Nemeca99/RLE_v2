#!/usr/bin/env python3
"""
RID Core - Weighted Version (User's Insight)

User's idea: Weight each invariant by how much load you're putting on that dimension

Example:
- If using 40% of max power → power metrics get 0.4 weight
- If using 80% of max util → efficiency metrics get 0.8 weight
- If reconstruction error is 10% → fidelity metrics get 0.9 weight

This gives an activity-weighted health score instead of crushing everything with multiplication.

S_n = w_efficiency × RLE + w_structure × LTP + w_fidelity × RSR

Where weights are based on actual system stress levels.
"""

from __future__ import annotations
import statistics
from dataclasses import dataclass
from typing import Optional, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rle_core import RLECore

@dataclass
class RIDResultWeighted:
    """RID result with weighted combination"""
    # Core
    RLE: float
    LTP: float
    RSR: float
    
    # Weights (based on load)
    w_efficiency: float
    w_structure: float
    w_fidelity: float
    
    # Weighted score
    S_n: float  # w_eff×RLE + w_struct×LTP + w_fid×RSR
    
    # Components
    rle_raw: float
    rle_smoothed: float
    a_load: float
    util_pct: float
    temp_c: Optional[float]
    power_w: Optional[float]
    
    # Diagnostics
    failure_mode: str
    alerts: str


class RIDCoreWeighted:
    """RID with activity-weighted combination"""
    
    def __init__(self,
                 temp_limit_c: float = 85.0,
                 power_limit_w: float = 100.0,
                 warning_threshold: float = 0.6,
                 emergency_threshold: float = 0.4):
        
        self.rle_engine = RLECore(
            rated_power_w=power_limit_w,
            temp_limit_c=temp_limit_c
        )
        
        self.temp_limit_c = temp_limit_c
        self.power_limit_w = power_limit_w
        self.warning_threshold = warning_threshold
        self.emergency_threshold = emergency_threshold
        
        # Histories for RSR
        self.util_hist = []
        self.temp_hist = []
        self.power_hist = []
    
    def compute(self, util_pct: float, temp_c: Optional[float], 
                power_w: Optional[float], dt_s: float = 1.0) -> RIDResultWeighted:
        """Compute weighted RID score"""
        
        # 1. RLE
        rle_result = self.rle_engine.compute_rle(util_pct, temp_c, power_w, dt_s)
        RLE = max(0.0, min(1.0, rle_result.rle_smoothed / 2.0))  # Normalize to [0,1]
        
        # 2. LTP (structural capacity)
        LTP = self._compute_ltp(temp_c, power_w)
        
        # 3. RSR (reconstruction fidelity)
        RSR = self._compute_rsr(util_pct, temp_c, power_w)
        
        # 4. WEIGHTS based on load intensity
        
        # Efficiency weight: How hard are we pushing utilization?
        w_efficiency = util_pct / 100.0
        
        # Structure weight: How hard are we pushing power?
        if power_w is not None and power_w > 0:
            w_structure = min(1.0, power_w / self.power_limit_w)
        else:
            w_structure = util_pct / 100.0  # Fallback to util
        
        # Fidelity weight: Always important (baseline 0.5, up to 1.0)
        w_fidelity = 0.5 + 0.5 * RSR
        
        # Normalize weights to sum to 1.0
        total_w = w_efficiency + w_structure + w_fidelity
        w_efficiency /= total_w
        w_structure /= total_w
        w_fidelity /= total_w
        
        # 5. WEIGHTED COMBINATION
        S_n = w_efficiency * RLE + w_structure * LTP + w_fidelity * RSR
        
        # 6. Diagnostics
        failure_mode = self._identify_failure_mode(RLE, LTP, RSR, w_efficiency, w_structure)
        alerts = self._generate_alerts(S_n, RLE, LTP, RSR)
        
        return RIDResultWeighted(
            RLE=RLE,
            LTP=LTP,
            RSR=RSR,
            w_efficiency=w_efficiency,
            w_structure=w_structure,
            w_fidelity=w_fidelity,
            S_n=S_n,
            rle_raw=rle_result.rle_raw,
            rle_smoothed=rle_result.rle_smoothed,
            a_load=rle_result.a_load,
            util_pct=util_pct,
            temp_c=temp_c,
            power_w=power_w,
            failure_mode=failure_mode,
            alerts=alerts
        )
    
    def _compute_ltp(self, temp_c, power_w):
        """Structural capacity (decoupled, no thermal)"""
        
        # Power headroom
        if power_w is not None and power_w > 0:
            power_headroom = max(0.0, self.power_limit_w - power_w)
            power_headroom_norm = power_headroom / self.power_limit_w
        else:
            power_headroom_norm = 0.5
        
        # Simple capacity metric
        LTP = power_headroom_norm
        
        return max(0.0, min(1.0, LTP))
    
    def _compute_rsr(self, util_pct, temp_c, power_w):
        """Reconstruction fidelity"""
        
        self.util_hist.append(util_pct)
        if temp_c is not None:
            self.temp_hist.append(temp_c)
        if power_w is not None:
            self.power_hist.append(power_w)
        
        if len(self.util_hist) < 5:
            return 1.0
        
        # Simple smoothness check
        util_smooth = sum(self.util_hist[-5:]) / 5.0
        util_error = abs(util_pct - util_smooth) / 100.0
        
        RSR = max(0.0, min(1.0, 1.0 - util_error))
        return RSR
    
    def _identify_failure_mode(self, RLE, LTP, RSR, w_eff, w_struct):
        """Identify which dimension is failing"""
        
        # Weighted contributions
        contrib_eff = w_eff * RLE
        contrib_struct = w_struct * LTP
        contrib_fid = RSR  # Always matters
        
        min_contrib = min(contrib_eff, contrib_struct, contrib_fid)
        
        if min_contrib == contrib_eff:
            return "Type I: Efficiency"
        elif min_contrib == contrib_struct:
            return "Type II: Structure"
        else:
            return "Type III: Fidelity"
    
    def _generate_alerts(self, S_n, RLE, LTP, RSR):
        """Generate alerts"""
        alerts = []
        
        if S_n < self.emergency_threshold:
            alerts.append(f"EMERGENCY: S_n={S_n:.3f}")
        elif S_n < self.warning_threshold:
            alerts.append(f"WARNING: S_n={S_n:.3f}")
        
        if RLE < 0.3:
            alerts.append(f"Efficiency low (RLE={RLE:.3f})")
        if LTP < 0.3:
            alerts.append(f"Structure stressed (LTP={LTP:.3f})")
        if RSR < 0.8:
            alerts.append(f"Fidelity degraded (RSR={RSR:.3f})")
        
        return " | ".join(alerts) if alerts else ""


if __name__ == "__main__":
    print("RID Weighted Version Test")
    print("=" * 80)
    print()
    
    rid = RIDCoreWeighted()
    
    scenarios = [
        (30, 40, 30, "Idle"),
        (50, 50, 50, "Normal"),
        (75, 65, 75, "Heavy"),
        (95, 80, 95, "Critical")
    ]
    
    print(f"{'Case':<10} {'U%':<5} {'T°C':<5} | {'RLE':<6} {'LTP':<6} {'RSR':<6} | "
          f"{'w_e':<5} {'w_s':<5} {'w_f':<5} | {'S_n':<6}")
    print("-" * 80)
    
    for util, temp, power, desc in scenarios:
        r = rid.compute(util, temp, power)
        print(f"{desc:<10} {util:<5} {temp:<5} | "
              f"{r.RLE:<6.3f} {r.LTP:<6.3f} {r.RSR:<6.3f} | "
              f"{r.w_efficiency:<5.2f} {r.w_structure:<5.2f} {r.w_fidelity:<5.2f} | "
              f"{r.S_n:<6.3f}")
