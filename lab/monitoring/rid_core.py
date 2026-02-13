#!/usr/bin/env python3
"""
RID (Recursive Invariant Dynamics) Core Engine
Implements the full stability triangle: S_n = RLE_n × LTP_n × RSR_n

Based on the RID framework documents:
- RLE: Recursive Loss Equation (efficiency retention)
- LTP: Layer Transition Principle (structure vs demand)
- RSR: Recursive State Reconstruction (state estimation fidelity)

Operational Definitions for Thermal/Hardware Systems:
- RLE: Already implemented in rle_core.py (efficiency invariant)
- RSR: Reconstruction error between current vs smoothed/lagged sensor readings
- LTP: Thermal/power headroom ratio (capacity vs demand)

Usage:
    from rid_core import RIDCore
    
    rid = RIDCore(temp_limit=85.0, power_limit=100.0)
    result = rid.compute(util_pct=75.0, temp_c=65.0, power_w=80.0)
    print(f"RID Stability: {result.S_n:.3f}")
"""

from __future__ import annotations
import statistics
from dataclasses import dataclass
from typing import Optional, List

# Import RLE engine
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from rle_core import RLECore, RLEResult

# ----------------------------
# Data classes
# ----------------------------
@dataclass
class RIDResult:
    """Complete RID stability triangle result"""
    # Core RID invariants
    RLE: float  # Efficiency retention [0,1]
    LTP: float  # Structure vs demand [0,1]
    RSR: float  # State reconstruction fidelity [0,1]
    S_n: float  # Combined stability scalar [0,1]
    
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
    state_error: float  # Normalized reconstruction error
    phase_lag: float    # Temporal lag indicator
    
    # LTP components
    thermal_headroom: float  # Available thermal capacity
    power_headroom: float    # Available power capacity
    structural_capacity: float  # Combined structure metric
    demand_level: float  # Combined demand metric
    
    # Diagnostics
    failure_mode: str  # Which invariant is limiting
    pre_collapse: bool  # S_n < 0.4 threshold
    alerts: str

# ----------------------------
# RID Core Engine
# ----------------------------
class RIDCore:
    """
    Recursive Invariant Dynamics Engine
    
    Computes full stability triangle S_n = RLE × LTP × RSR
    
    Mathematical definitions:
    - RLE_n = (E_{n+1} - U_n) / E_n  (from rle_core.py)
    - LTP_n = min(1, l_n / d_n)  where l = structure, d = demand
    - RSR_n = 1 - ||x_n - x̂_n|| / ||x||_max
    """
    
    def __init__(self,
                 # RLE parameters (passed to RLECore)
                 temp_limit_c: float = 85.0,
                 power_limit_w: float = 100.0,
                 max_t_sustain_s: float = 600.0,
                 
                 # RSR parameters (reconstruction fidelity)
                 rsr_window_n: int = 10,  # Smoothing window for state reconstruction
                 rsr_lag_threshold_s: float = 5.0,  # Phase lag warning threshold
                 
                 # LTP parameters (structure vs demand)
                 fan_max_authority: float = 1.0,  # Max fan effectiveness (0-1)
                 thermal_resistance: float = 0.5,  # °C/W thermal resistance estimate
                 
                 # Stability thresholds
                 pre_collapse_threshold: float = 0.4,
                 emergency_threshold: float = 0.2):
        
        # Initialize RLE engine
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
        
        # State histories for RSR computation
        self.temp_raw_hist: List[float] = []
        self.temp_smooth_hist: List[float] = []
        self.power_raw_hist: List[float] = []
        self.power_smooth_hist: List[float] = []
        self.util_raw_hist: List[float] = []
        self.util_smooth_hist: List[float] = []
        self.timestamp_hist: List[float] = []
        
        # LTP state tracking
        self.fan_speed_pct_hist: List[float] = []
    
    def compute(self,
                util_pct: float,
                temp_c: Optional[float],
                power_w: Optional[float],
                fan_speed_pct: Optional[float] = None,
                dt_s: float = 1.0) -> RIDResult:
        """
        Compute full RID stability triangle
        
        Args:
            util_pct: Utilization percentage [0-100]
            temp_c: Temperature in Celsius
            power_w: Power consumption in Watts
            fan_speed_pct: Fan speed percentage [0-100] (optional)
            dt_s: Time delta since last sample
            
        Returns:
            RIDResult with all RID invariants and diagnostics
        """
        
        # 1. Compute RLE (efficiency retention)
        rle_result = self.rle_engine.compute_rle(util_pct, temp_c, power_w, dt_s)
        RLE = rle_result.rle_smoothed  # Use smoothed for stability
        
        # 2. Compute RSR (state reconstruction fidelity)
        RSR, state_error, phase_lag = self._compute_rsr(
            util_pct, temp_c, power_w, dt_s
        )
        
        # 3. Compute LTP (structure vs demand)
        LTP, thermal_headroom, power_headroom, struct_cap, demand_lvl = self._compute_ltp(
            temp_c, power_w, fan_speed_pct
        )
        
        # 4. Compute combined stability scalar
        S_n = RLE * LTP * RSR
        
        # 5. Diagnostics
        failure_mode = self._identify_failure_mode(RLE, LTP, RSR)
        pre_collapse = S_n < self.pre_collapse_threshold
        
        # 6. Generate alerts
        alerts = self._generate_alerts(S_n, RLE, LTP, RSR, pre_collapse)
        
        return RIDResult(
            RLE=RLE,
            LTP=LTP,
            RSR=RSR,
            S_n=S_n,
            # RLE components
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
            # RSR components
            state_error=state_error,
            phase_lag=phase_lag,
            # LTP components
            thermal_headroom=thermal_headroom,
            power_headroom=power_headroom,
            structural_capacity=struct_cap,
            demand_level=demand_lvl,
            # Diagnostics
            failure_mode=failure_mode,
            pre_collapse=pre_collapse,
            alerts=alerts
        )
    
    def _compute_rsr(self,
                     util_pct: float,
                     temp_c: Optional[float],
                     power_w: Optional[float],
                     dt_s: float) -> tuple[float, float, float]:
        """
        Compute RSR (Recursive State Reconstruction)
        
        RSR_n = 1 - ||x_n - x̂_n|| / ||x||_max
        
        Where:
        - x_n: current observed state (raw sensor readings)
        - x̂_n: reconstructed state (smoothed/lagged readings)
        - ||·||: normalized distance metric
        
        Returns:
            (RSR, state_error, phase_lag)
        """
        
        # Update histories
        self.util_raw_hist.append(util_pct)
        if temp_c is not None:
            self.temp_raw_hist.append(temp_c)
        if power_w is not None:
            self.power_raw_hist.append(power_w)
        self.timestamp_hist.append(dt_s)
        
        # Compute smoothed (reconstructed) states
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
        
        # Warm-up period
        if len(self.util_raw_hist) < self.rsr_window_n:
            return 1.0, 0.0, 0.0
        
        # Compute reconstruction errors (normalized)
        error_components = []
        
        # Utilization error
        util_error = abs(util_pct - util_smooth) / 100.0
        error_components.append(util_error)
        
        # Temperature error (if available)
        if temp_c is not None and temp_smooth is not None:
            temp_range = max(self.temp_limit_c - 20.0, 20.0)  # Normalize by operating range
            temp_error = abs(temp_c - temp_smooth) / temp_range
            error_components.append(temp_error)
        
        # Power error (if available)
        if power_w is not None and power_smooth is not None:
            power_range = max(self.power_limit_w, 20.0)
            power_error = abs(power_w - power_smooth) / power_range
            error_components.append(power_error)
        
        # Combined state error (mean of normalized errors)
        state_error = sum(error_components) / max(len(error_components), 1)
        
        # RSR = 1 - error (bounded to [0, 1])
        RSR = max(0.0, min(1.0, 1.0 - state_error))
        
        # Phase lag detection (how much delay in response)
        phase_lag = 0.0
        if len(self.timestamp_hist) >= self.rsr_window_n:
            # Estimate lag as window duration
            phase_lag = sum(self.timestamp_hist[-self.rsr_window_n:])
        
        return RSR, state_error, phase_lag
    
    def _compute_ltp(self,
                     temp_c: Optional[float],
                     power_w: Optional[float],
                     fan_speed_pct: Optional[float]) -> tuple[float, float, float, float, float]:
        """
        Compute LTP (Layer Transition Principle)
        
        LTP_n = min(1, l_n / d_n)
        
        Where:
        - l_n: structural capacity (thermal headroom + power headroom + control authority)
        - d_n: demand (thermal load + power load)
        
        Returns:
            (LTP, thermal_headroom, power_headroom, structural_capacity, demand_level)
        """
        
        # Update fan history
        if fan_speed_pct is not None:
            self.fan_speed_pct_hist.append(fan_speed_pct)
        
        # === STRUCTURAL CAPACITY (l_n) ===
        
        # Thermal headroom: how much temperature margin remains
        if temp_c is not None:
            thermal_headroom = max(0.0, self.temp_limit_c - temp_c)
        else:
            # Assume 50% headroom if unknown
            thermal_headroom = self.temp_limit_c * 0.5
        
        # Normalize thermal headroom (0-1 scale)
        thermal_headroom_norm = thermal_headroom / self.temp_limit_c
        
        # Power headroom: how much power budget remains
        if power_w is not None:
            power_headroom = max(0.0, self.power_limit_w - power_w)
        else:
            # Assume 50% headroom if unknown
            power_headroom = self.power_limit_w * 0.5
        
        # Normalize power headroom (0-1 scale)
        power_headroom_norm = power_headroom / self.power_limit_w
        
        # Fan control authority: how much cooling capacity remains
        if fan_speed_pct is not None:
            # Fan authority decreases as fan speed increases (less room to ramp up)
            fan_authority = max(0.0, 100.0 - fan_speed_pct) / 100.0
        else:
            # Assume 50% authority if unknown
            fan_authority = 0.5
        
        # Combined structural capacity (geometric mean to enforce conjunctive necessity)
        structural_capacity = (thermal_headroom_norm * power_headroom_norm * fan_authority) ** (1.0/3.0)
        
        # === DEMAND LEVEL (d_n) ===
        
        # Thermal demand: current thermal stress
        if temp_c is not None:
            # Normalize by distance to limit
            thermal_demand = temp_c / self.temp_limit_c
        else:
            thermal_demand = 0.5
        
        # Power demand: current power usage
        if power_w is not None:
            power_demand = power_w / self.power_limit_w
        else:
            power_demand = 0.5
        
        # Combined demand (arithmetic mean)
        demand_level = (thermal_demand + power_demand) / 2.0
        
        # === LTP COMPUTATION ===
        
        # LTP = min(1, structure / demand)
        if demand_level < 0.01:
            # Avoid division by zero in idle states
            LTP = 1.0
        else:
            LTP = min(1.0, structural_capacity / demand_level)
        
        # Clamp to [0, 1]
        LTP = max(0.0, min(1.0, LTP))
        
        return LTP, thermal_headroom, power_headroom, structural_capacity, demand_level
    
    def _identify_failure_mode(self, RLE: float, LTP: float, RSR: float) -> str:
        """
        Identify which invariant is limiting stability
        
        Follows RID taxonomy:
        - Type I: Dissipative collapse (RLE limiting)
        - Type II: Structural overload (LTP limiting)
        - Type III: Observability failure (RSR limiting)
        - Type IV: Compound collapse (multiple limiting)
        """
        
        min_val = min(RLE, LTP, RSR)
        limiting = []
        
        # Find which invariants are within 10% of minimum
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
    
    def _generate_alerts(self, S_n: float, RLE: float, LTP: float, RSR: float, pre_collapse: bool) -> str:
        """Generate human-readable alerts based on RID state"""
        
        alerts = []
        
        if S_n < self.emergency_threshold:
            alerts.append("EMERGENCY: S_n < 0.2 (collapse imminent)")
        elif pre_collapse:
            alerts.append("WARNING: S_n < 0.4 (pre-collapse regime)")
        
        # Specific invariant warnings
        if RLE < 0.3:
            alerts.append("RLE: Efficiency loss (thermal/power dissipation)")
        if LTP < 0.3:
            alerts.append("LTP: Structural overload (demand exceeds capacity)")
        if RSR < 0.3:
            alerts.append("RSR: Observability failure (reconstruction error)")
        
        return " | ".join(alerts) if alerts else ""
    
    @staticmethod
    def _rolling_mean(data: List[float], n: int) -> float:
        """Compute rolling mean over last n samples"""
        if not data:
            return 0.0
        if len(data) <= n:
            return sum(data) / len(data)
        return sum(data[-n:]) / float(n)


# ----------------------------
# Convenience function
# ----------------------------
def compute_rid_stability(util_pct: float,
                          temp_c: Optional[float],
                          power_w: Optional[float],
                          temp_limit_c: float = 85.0,
                          power_limit_w: float = 100.0) -> float:
    """
    One-shot RID stability computation (no history tracking)
    
    Returns:
        S_n: Combined stability scalar [0, 1]
    """
    rid = RIDCore(temp_limit_c=temp_limit_c, power_limit_w=power_limit_w)
    result = rid.compute(util_pct, temp_c, power_w)
    return result.S_n


if __name__ == "__main__":
    # Quick test
    print("RID Core Engine Test")
    print("=" * 50)
    
    rid = RIDCore(temp_limit_c=85.0, power_limit_w=100.0)
    
    # Simulate gradual degradation
    test_cases = [
        (50.0, 45.0, 50.0, "Nominal operation"),
        (70.0, 60.0, 70.0, "Moderate load"),
        (85.0, 75.0, 85.0, "High load"),
        (95.0, 82.0, 95.0, "Near limits"),
        (98.0, 84.0, 98.0, "Critical"),
    ]
    
    for util, temp, power, desc in test_cases:
        result = rid.compute(util, temp, power)
        print(f"\n{desc}:")
        print(f"  Util: {util:.1f}%, Temp: {temp:.1f}°C, Power: {power:.1f}W")
        print(f"  RLE: {result.RLE:.3f} | LTP: {result.LTP:.3f} | RSR: {result.RSR:.3f}")
        print(f"  S_n: {result.S_n:.3f} ({result.failure_mode})")
        if result.alerts:
            print(f"  ALERT: {result.alerts}")
