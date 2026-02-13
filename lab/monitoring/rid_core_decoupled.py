#!/usr/bin/env python3
"""
RID Core - Decoupled LTP Variant

ChatGPT's decisive experiment:
Remove temperature from LTP entirely to test if thermal coupling is necessary.

LTP_decoupled = power_headroom × fan_authority
(no thermal component)

This tests:
- Does early warning still occur without thermal coupling?
- Is current thermal coupling over-amplified?
- Is the 91% gap physically meaningful or excessive?

Comparison protocol:
1. Run coupled version (original): LTP = (thermal × power × fan)^(1/3)
2. Run decoupled version (this): LTP = (power × fan)^(1/2)  
3. Compare early warning onset points
4. Quantify delta in collapse prediction

If decoupled performs similarly → coupling is over-amplification
If coupled predicts earlier without false positives → coupling is feature
"""

from __future__ import annotations
import statistics
from dataclasses import dataclass
from typing import Optional, List
import sys
from pathlib import Path

# Import base RLE engine
sys.path.insert(0, str(Path(__file__).parent))
from rle_core import RLECore, RLEResult

@dataclass
class RIDResultDecoupled:
    """RID result with decoupled LTP"""
    # Core RID invariants
    RLE: float
    LTP_coupled: float    # Original (with thermal)
    LTP_decoupled: float  # New (no thermal)
    RSR: float
    S_n_coupled: float    # S_n using coupled LTP
    S_n_decoupled: float  # S_n using decoupled LTP
    
    # RLE components (passthrough)
    rle_raw: float
    rle_smoothed: float
    rle_norm: float
    e_th: float
    e_pw: float
    stability: float
    a_load: float
    t_sustain_s: float
    rolling_peak: float
    collapse: int
    
    # RSR components
    state_error: float
    phase_lag: float
    
    # LTP components (both versions)
    thermal_headroom: float
    power_headroom: float
    structural_capacity_coupled: float
    structural_capacity_decoupled: float
    demand_level: float
    
    # Diagnostics
    failure_mode_coupled: str
    failure_mode_decoupled: str
    pre_collapse_coupled: bool
    pre_collapse_decoupled: bool
    delta_S_n: float  # How much difference does coupling make?
    alerts: str


class RIDCoreDecoupled:
    """
    RID Core with side-by-side coupled vs decoupled LTP comparison
    """
    
    def __init__(self,
                 temp_limit_c: float = 85.0,
                 power_limit_w: float = 100.0,
                 max_t_sustain_s: float = 600.0,
                 rsr_window_n: int = 10,
                 rsr_lag_threshold_s: float = 5.0,
                 fan_max_authority: float = 1.0,
                 thermal_resistance: float = 0.5,
                 pre_collapse_threshold: float = 0.4,
                 emergency_threshold: float = 0.2):
        
        self.rle_engine = RLECore(
            rated_power_w=power_limit_w,
            temp_limit_c=temp_limit_c,
            max_t_sustain_s=max_t_sustain_s
        )
        
        self.temp_limit_c = temp_limit_c
        self.power_limit_w = power_limit_w
        self.rsr_window_n = rsr_window_n
        self.rsr_lag_threshold_s = rsr_lag_threshold_s
        self.fan_max_authority = fan_max_authority
        self.thermal_resistance = thermal_resistance
        self.pre_collapse_threshold = pre_collapse_threshold
        self.emergency_threshold = emergency_threshold
        
        # State histories for RSR
        self.temp_raw_hist: List[float] = []
        self.temp_smooth_hist: List[float] = []
        self.power_raw_hist: List[float] = []
        self.power_smooth_hist: List[float] = []
        self.util_raw_hist: List[float] = []
        self.util_smooth_hist: List[float] = []
        self.timestamp_hist: List[float] = []
        self.fan_speed_pct_hist: List[float] = []
    
    def compute(self,
                util_pct: float,
                temp_c: Optional[float],
                power_w: Optional[float],
                fan_speed_pct: Optional[float] = None,
                dt_s: float = 1.0) -> RIDResultDecoupled:
        """
        Compute RID with both coupled and decoupled LTP
        """
        
        # 1. RLE (unchanged)
        rle_result = self.rle_engine.compute_rle(util_pct, temp_c, power_w, dt_s)
        RLE = rle_result.rle_smoothed
        
        # 2. RSR (unchanged)
        RSR, state_error, phase_lag = self._compute_rsr(
            util_pct, temp_c, power_w, dt_s
        )
        
        # 3. LTP - BOTH VERSIONS
        (LTP_coupled, LTP_decoupled,
         thermal_headroom, power_headroom,
         struct_cap_coupled, struct_cap_decoupled,
         demand_lvl) = self._compute_ltp_both(temp_c, power_w, fan_speed_pct)
        
        # 4. Stability scalars - BOTH
        S_n_coupled = RLE * LTP_coupled * RSR
        S_n_decoupled = RLE * LTP_decoupled * RSR
        
        # 5. Delta (how much does coupling change the result?)
        delta_S_n = S_n_coupled - S_n_decoupled
        
        # 6. Diagnostics for both
        failure_mode_coupled = self._identify_failure_mode(RLE, LTP_coupled, RSR)
        failure_mode_decoupled = self._identify_failure_mode(RLE, LTP_decoupled, RSR)
        
        pre_collapse_coupled = S_n_coupled < self.pre_collapse_threshold
        pre_collapse_decoupled = S_n_decoupled < self.pre_collapse_threshold
        
        # 7. Alerts
        alerts = self._generate_alerts_comparison(
            S_n_coupled, S_n_decoupled, RLE, LTP_coupled, LTP_decoupled, RSR,
            pre_collapse_coupled, pre_collapse_decoupled
        )
        
        return RIDResultDecoupled(
            RLE=RLE,
            LTP_coupled=LTP_coupled,
            LTP_decoupled=LTP_decoupled,
            RSR=RSR,
            S_n_coupled=S_n_coupled,
            S_n_decoupled=S_n_decoupled,
            rle_raw=rle_result.rle_raw,
            rle_smoothed=rle_result.rle_smoothed,
            rle_norm=rle_result.rle_norm,
            e_th=rle_result.e_th,
            e_pw=rle_result.e_pw,
            stability=rle_result.stability,
            a_load=rle_result.a_load,
            t_sustain_s=rle_result.t_sustain_s,
            rolling_peak=rle_result.rolling_peak,
            collapse=rle_result.collapse,
            state_error=state_error,
            phase_lag=phase_lag,
            thermal_headroom=thermal_headroom,
            power_headroom=power_headroom,
            structural_capacity_coupled=struct_cap_coupled,
            structural_capacity_decoupled=struct_cap_decoupled,
            demand_level=demand_lvl,
            failure_mode_coupled=failure_mode_coupled,
            failure_mode_decoupled=failure_mode_decoupled,
            pre_collapse_coupled=pre_collapse_coupled,
            pre_collapse_decoupled=pre_collapse_decoupled,
            delta_S_n=delta_S_n,
            alerts=alerts
        )
    
    def _compute_ltp_both(self,
                          temp_c: Optional[float],
                          power_w: Optional[float],
                          fan_speed_pct: Optional[float]) -> tuple:
        """
        Compute BOTH coupled and decoupled LTP variants
        
        Returns:
            (LTP_coupled, LTP_decoupled, thermal_headroom, power_headroom,
             struct_cap_coupled, struct_cap_decoupled, demand_level)
        """
        
        # Update fan history
        if fan_speed_pct is not None:
            self.fan_speed_pct_hist.append(fan_speed_pct)
        
        # === COUPLED VERSION (original) ===
        
        # Thermal headroom
        if temp_c is not None:
            thermal_headroom = max(0.0, self.temp_limit_c - temp_c)
        else:
            thermal_headroom = self.temp_limit_c * 0.5
        thermal_headroom_norm = thermal_headroom / self.temp_limit_c
        
        # Power headroom
        if power_w is not None:
            power_headroom = max(0.0, self.power_limit_w - power_w)
        else:
            power_headroom = self.power_limit_w * 0.5
        power_headroom_norm = power_headroom / self.power_limit_w
        
        # Fan authority
        if fan_speed_pct is not None:
            fan_authority = max(0.0, 100.0 - fan_speed_pct) / 100.0
        else:
            fan_authority = 0.5
        
        # Coupled: includes thermal (geometric mean of all three)
        struct_cap_coupled = (thermal_headroom_norm * power_headroom_norm * fan_authority) ** (1.0/3.0)
        
        # Decoupled: NO thermal (geometric mean of power + fan only)
        struct_cap_decoupled = (power_headroom_norm * fan_authority) ** (1.0/2.0)
        
        # === DEMAND (same for both) ===
        
        if temp_c is not None:
            thermal_demand = temp_c / self.temp_limit_c
        else:
            thermal_demand = 0.5
        
        if power_w is not None:
            power_demand = power_w / self.power_limit_w
        else:
            power_demand = 0.5
        
        demand_level = (thermal_demand + power_demand) / 2.0
        
        # === LTP COMPUTATION ===
        
        if demand_level < 0.01:
            LTP_coupled = 1.0
            LTP_decoupled = 1.0
        else:
            LTP_coupled = min(1.0, struct_cap_coupled / demand_level)
            LTP_decoupled = min(1.0, struct_cap_decoupled / demand_level)
        
        LTP_coupled = max(0.0, min(1.0, LTP_coupled))
        LTP_decoupled = max(0.0, min(1.0, LTP_decoupled))
        
        return (LTP_coupled, LTP_decoupled,
                thermal_headroom, power_headroom,
                struct_cap_coupled, struct_cap_decoupled,
                demand_level)
    
    def _compute_rsr(self, util_pct, temp_c, power_w, dt_s):
        """RSR computation (unchanged from original)"""
        self.util_raw_hist.append(util_pct)
        if temp_c is not None:
            self.temp_raw_hist.append(temp_c)
        if power_w is not None:
            self.power_raw_hist.append(power_w)
        self.timestamp_hist.append(dt_s)
        
        util_smooth = self._rolling_mean(self.util_raw_hist, self.rsr_window_n)
        self.util_smooth_hist.append(util_smooth)
        
        if temp_c is not None and self.temp_raw_hist:
            temp_smooth = self._rolling_mean(self.temp_raw_hist, self.rsr_window_n)
            self.temp_smooth_hist.append(temp_smooth)
        else:
            temp_smooth = None
        
        if power_w is not None and self.power_raw_hist:
            power_smooth = self._rolling_mean(self.power_raw_hist, self.rsr_window_n)
            self.power_smooth_hist.append(power_smooth)
        else:
            power_smooth = None
        
        if len(self.util_raw_hist) < self.rsr_window_n:
            return 1.0, 0.0, 0.0
        
        error_components = []
        util_error = abs(util_pct - util_smooth) / 100.0
        error_components.append(util_error)
        
        if temp_c is not None and temp_smooth is not None:
            temp_range = max(self.temp_limit_c - 20.0, 20.0)
            temp_error = abs(temp_c - temp_smooth) / temp_range
            error_components.append(temp_error)
        
        if power_w is not None and power_smooth is not None:
            power_range = max(self.power_limit_w, 20.0)
            power_error = abs(power_w - power_smooth) / power_range
            error_components.append(power_error)
        
        state_error = sum(error_components) / max(len(error_components), 1)
        RSR = max(0.0, min(1.0, 1.0 - state_error))
        
        phase_lag = 0.0
        if len(self.timestamp_hist) >= self.rsr_window_n:
            phase_lag = sum(self.timestamp_hist[-self.rsr_window_n:])
        
        return RSR, state_error, phase_lag
    
    def _identify_failure_mode(self, RLE, LTP, RSR):
        """Failure mode classification (unchanged)"""
        min_val = min(RLE, LTP, RSR)
        limiting = []
        threshold = min_val * 1.1
        
        if RLE <= threshold:
            limiting.append("RLE")
        if LTP <= threshold:
            limiting.append("LTP")
        if RSR <= threshold:
            limiting.append("RSR")
        
        if len(limiting) == 1:
            mode = limiting[0]
            if mode == "RLE":
                return "Type I: Dissipative"
            elif mode == "LTP":
                return "Type II: Structural"
            elif mode == "RSR":
                return "Type III: Observability"
        elif len(limiting) > 1:
            return "Type IV: Compound"
        else:
            return "Nominal"
    
    def _generate_alerts_comparison(self, S_n_coupled, S_n_decoupled, RLE, LTP_coupled, LTP_decoupled, RSR,
                                   pre_collapse_coupled, pre_collapse_decoupled):
        """Generate alerts comparing both versions"""
        alerts = []
        
        # Coupled alerts
        if S_n_coupled < 0.2:
            alerts.append("COUPLED: S_n < 0.2 (emergency)")
        elif pre_collapse_coupled:
            alerts.append("COUPLED: S_n < 0.4 (warning)")
        
        # Decoupled alerts
        if S_n_decoupled < 0.2:
            alerts.append("DECOUPLED: S_n < 0.2 (emergency)")
        elif pre_collapse_decoupled:
            alerts.append("DECOUPLED: S_n < 0.4 (warning)")
        
        # Comparison
        delta = abs(S_n_coupled - S_n_decoupled)
        if delta > 0.1:
            alerts.append(f"DELTA: {delta:.3f} (significant difference)")
        
        # Early warning comparison
        if pre_collapse_coupled and not pre_collapse_decoupled:
            alerts.append("COUPLED warns earlier")
        elif pre_collapse_decoupled and not pre_collapse_coupled:
            alerts.append("DECOUPLED warns earlier")
        
        return " | ".join(alerts) if alerts else ""
    
    @staticmethod
    def _rolling_mean(data: List[float], n: int) -> float:
        if not data:
            return 0.0
        if len(data) <= n:
            return sum(data) / len(data)
        return sum(data[-n:]) / float(n)


if __name__ == "__main__":
    # Quick comparison test
    print("RID Decoupled LTP Test")
    print("=" * 80)
    
    rid = RIDCoreDecoupled(temp_limit_c=85.0, power_limit_w=100.0)
    
    print(f"\n{'Temp°C':<8} {'Util%':<8} | {'LTP_coup':<10} {'LTP_decoup':<10} | {'S_n_coup':<10} {'S_n_decoup':<10} | {'Delta':<8}")
    print("-" * 80)
    
    # Simulate degradation
    for temp in [45, 55, 65, 75, 82]:
        for util in [50, 75, 90]:
            result = rid.compute(util, temp, util * 0.8)  # power ~ util
            
            print(f"{temp:<8} {util:<8} | {result.LTP_coupled:<10.3f} {result.LTP_decoupled:<10.3f} | "
                  f"{result.S_n_coupled:<10.3f} {result.S_n_decoupled:<10.3f} | {result.delta_S_n:+8.3f}")
