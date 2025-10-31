#!/usr/bin/env python3
"""
RLE Core Engine
- Canonical formula (η, σ, α, τ) → RLE, E_th, E_pw
- Scaling model (power/temperature/time factors)
- Improved collapse detection (rolling peak, gates, hysteresis)
- Minimal control loop (decision states)
- CSV CLI: augment input CSV or simulate from simple columns
- Optional micro-scale correction (Planck-ish penalty for low-energy regimes)

Usage:
  python lab/monitoring/rle_core.py --in sessions/recent/rle_YYYYMMDD_HH.csv --out out.csv
  python lab/monitoring/rle_core.py --help
  
  # With micro-scale addon (experimental):
  python lab/monitoring/rle_core.py --in mobile_data.csv --out augmented.csv --micro-scale --sensor-lsb 0.5 --power-knee 3.0
"""

from __future__ import annotations
import argparse
import csv
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict

# ----------------------------
# Data classes
# ----------------------------
@dataclass
class RLEResult:
    # Primary
    rle_raw: float
    rle_smoothed: float
    e_th: float
    e_pw: float
    rle_norm: float
    # Components
    stability: float
    a_load: float
    t_sustain_s: float
    rolling_peak: float
    collapse: int
    # Optional diagnostics
    alerts: str = ""
    # Micro-scale addon (experimental)
    F_mu: float = 1.0
    F_q: float = 1.0
    F_s: float = 1.0
    F_p: float = 1.0
    # Micro-scale (augmented) variants (when enabled; otherwise mirrors of primary)
    # Appended to CSV as new columns; originals remain unchanged
    rle_raw_ms: float = 0.0
    rle_smoothed_ms: float = 0.0
    rle_norm_ms: float = 0.0
    # Unified (blended) variants
    rle_raw_uni: float = 0.0
    rle_smoothed_uni: float = 0.0
    rle_norm_uni: float = 0.0
    # Theta-clock diagnostics (appended when enabled)
    T0_s: float = 0.0
    theta_index: float = 0.0
    T_sustain_hat: float = 0.0
    theta_gap: int = 0
    # Micro-scale theta-aware diagnostics
    Gamma: float = 0.0
    log_Gamma: float = 0.0

@dataclass
class ControlDecision:
    state: str
    cpu_freq_limit_ghz: Optional[float] = None
    gpu_freq_limit_ghz: Optional[float] = None
    fan_speed_pct: Optional[int] = None
    power_limit_pct: Optional[int] = None
    workload_reduction_pct: Optional[int] = None

# ----------------------------
# Core engine
# ----------------------------
class RLECore:
    def __init__(self,
                 rated_power_w: float = 100.0,
                 temp_limit_c: float = 85.0,
                 max_t_sustain_s: float = 600.0,
                 smooth_n: int = 5,
                 # Collapse detection params
                 rolling_decay: float = 0.998, # ~3% per 10s at 1Hz
                 drop_frac: float = 0.65,
                 hysteresis_s: int = 7,
                 util_gate_pct: float = 60.0,
                 a_load_gate: float = 0.75,
                 # Micro-scale addon (optional Planck-ish correction)
                 enable_micro_scale: bool = False,
                 sensor_temp_lsb_c: float = 0.1,
                 low_power_knee_w: float = 3.0,
                 # Theta clock options (safe defaults; non-breaking)
                 enable_theta_clock: bool = True,
                 theta_update_sec: float = 60.0,
                 theta_min_s: float = 5.0,
                 theta_max_s: float = 600.0,
                 # Theta windows (non-breaking; off by default)
                 use_theta_windows: bool = False,
                 stability_window_theta: float = 5.0,
                 smooth_window_theta: Optional[float] = None,
                 hysteresis_theta: Optional[float] = None):
        self.rated_power_w = rated_power_w
        self.temp_limit_c = temp_limit_c
        self.max_t_sustain_s = max_t_sustain_s
        self.smooth_n = max(1, int(smooth_n))
        self.rolling_decay = rolling_decay
        self.drop_frac = drop_frac
        self.hysteresis_s = hysteresis_s
        self.util_gate_pct = util_gate_pct
        self.a_load_gate = a_load_gate
        
        # Micro-scale addon
        self.enable_micro_scale = enable_micro_scale
        self.sensor_temp_lsb_c = sensor_temp_lsb_c
        self.low_power_knee_w = low_power_knee_w

        # Theta clock configuration
        self.enable_theta_clock = enable_theta_clock
        self.theta_update_sec = max(5.0, float(theta_update_sec))
        self.theta_min_s = max(1e-3, float(theta_min_s))
        self.theta_max_s = max(self.theta_min_s, float(theta_max_s))

        # Theta-window configuration
        self.use_theta_windows = use_theta_windows
        self.stability_window_theta = stability_window_theta
        self.smooth_window_theta = smooth_window_theta
        self.hysteresis_theta = hysteresis_theta

        self.util_hist: List[float] = []
        self.temp_hist: List[float] = []
        self.rle_hist: List[float] = []
        self.rle_hist_ms: List[float] = []
        self.rle_hist_uni: List[float] = []
        self.rolling_peak: float = 0.0
        self.below_ctr: int = 0

        # Theta clock state
        self._t0_s: float = 60.0  # initial internal period guess (s)
        self._theta_index: float = 0.0
        # Kahan summation compensation for theta_index
        self._theta_c: float = 0.0
        self._since_theta_update_s: float = 0.0
        # Ring buffers
        self._rb_len: int = 1024
        self._buf_rle_sm: List[float] = []
        self._buf_temp: List[float] = []
        self._buf_dt: List[float] = []

    def _mean_dt(self) -> float:
        if not self._buf_dt:
            return 1.0
        return sum(self._buf_dt) / len(self._buf_dt)

    def _theta_window_to_n(self, theta_window: float) -> int:
        dt_mean = self._mean_dt()
        dtheta_mean = dt_mean / max(self._t0_s, 1e-6)
        n = int(round(theta_window / max(dtheta_mean, 1e-6)))
        n = max(3, n)
        samples_in_update = int(round(self.theta_update_sec / max(dt_mean, 1e-6)))
        cap = max(12, 4 * samples_in_update)
        return min(n, cap)

    def _rolling_mean(self, data: List[float], n: int) -> float:
        if not data: return 0.0
        if len(data) <= n: return sum(data)/len(data)
        return sum(data[-n:]) / float(n)

    def _rolling_stdev(self, data: List[float], n: int) -> float:
        if len(data) < 2: return 0.0
        window = data[-n:] if len(data) >= n else data
        return statistics.pstdev(window)
    
    def _compute_micro_scale_factor(self, power_w: float, temp_c: Optional[float], dt_s: float, dtheta: float, T0_s: float) -> tuple[float, float, float, float, float, float]:
        """
        Compute F_mu micro-scale correction factor (Planck-ish quiet quanta penalty).
        
        Returns:
            Tuple of (F_mu, F_q, F_s, F_p) where F_mu is the composite factor in (0, 1]
        """
        import math
        
        if not self.enable_micro_scale:
            return (1.0, 1.0, 1.0, 1.0, 0.0, 0.0)
        
        # Constants
        k_B = 1.380649e-23  # Boltzmann constant (J/K)
        
        # Temperature in Kelvin (fallback to ambient if needed)
        T_c = temp_c if temp_c is not None else (self.temp_hist[-1] if self.temp_hist else 25.0)
        T_K = max(T_c + 273.15, 273.15)
        
        # Power and time
        P = max((power_w or 0.0), 1e-6)
        dt = max(dt_s, 1e-3)
        
        # a) Thermal-quanta term F_q
        # Count "thermal quanta" per sample
        # Theta-aware formulation: N_q = (P*T0_s/(k_B*T)) * dtheta
        quantum_scale_J = k_B * T_K
        Gamma = (P * max(T0_s, 1e-9)) / max(quantum_scale_J, 1e-30)
        N_q = Gamma * max(dtheta, 0.0)
        F_q = 1.0 - math.exp(-min(N_q, 50.0))  # Clamp exponent for safety
        
        # b) Sensor-resolution term F_s
        # Check if temperature jitter is resolved by sensor LSB
        sigma_T = self._rolling_stdev(self.temp_hist, n=5) if len(self.temp_hist) >= 2 else 1e-6
        F_s = 1.0 / (1.0 + (self.sensor_temp_lsb_c / max(sigma_T, 1e-6))**2)
        
        # c) Low-power SNR term F_p
        # Penalty for operating near quantization noise floor
        F_p = P / (P + self.low_power_knee_w)
        
        # Geometric mean: all three must agree
        F_mu = (F_q * F_s * F_p) ** (1.0/3.0)
        F_mu = max(1e-9, min(1.0, F_mu))  # Clamp to (0, 1]
        
        # Diagnostics: Gamma and log_Gamma for analysis
        log_Gamma = math.log(max(Gamma, 1e-30)) if Gamma > 0 else -1e9

        return (F_mu, F_q, F_s, F_p, Gamma, log_Gamma)

    def _theta_update_if_needed(self, rle_sm: float, temp_c: Optional[float], dt_s: float) -> None:
        """Maintain theta buffers and periodically update internal period T0_s.
        Light-weight; uses simple proxies to avoid heavy CPU.
        """
        if not self.enable_theta_clock:
            # Still track dt for robustness
            self._buf_dt.append(dt_s)
            if len(self._buf_dt) > self._rb_len:
                self._buf_dt.pop(0)
            return

        # Update buffers
        self._buf_rle_sm.append(rle_sm)
        if len(self._buf_rle_sm) > self._rb_len:
            self._buf_rle_sm.pop(0)
        if temp_c is not None:
            self._buf_temp.append(temp_c)
            if len(self._buf_temp) > self._rb_len:
                self._buf_temp.pop(0)
        self._buf_dt.append(dt_s)
        if len(self._buf_dt) > self._rb_len:
            self._buf_dt.pop(0)

        # Accumulate elapsed time and update periodically
        self._since_theta_update_s += dt_s
        if self._since_theta_update_s < self.theta_update_sec:
            return
        self._since_theta_update_s = 0.0

        # Estimate dt window stats
        if not self._buf_dt:
            return
        dt_mean = sum(self._buf_dt) / len(self._buf_dt)
        dt_win_s = dt_mean * min(len(self._buf_dt), 256)

        # Estimate thermal time constant proxy τ_th via simple slope ratio
        tau_th_est = None
        if len(self._buf_temp) >= 8:
            # Use recent segment
            window = self._buf_temp[-min(len(self._buf_temp), 256):]
            # Approximate derivative magnitude
            derivs = [max((window[i] - window[i-1]) / max(dt_mean, 1e-6), 0.0) for i in range(1, len(window))]
            avg_dTdt = sum(derivs) / max(len(derivs), 1)
            if avg_dTdt > 1e-6:
                # Scale by typical headroom (10°C) as a crude RC estimate
                tau_th_est = min(max(10.0 / avg_dTdt, self.theta_min_s), self.theta_max_s)

        # Recent mean of t_sustain as τ_sustain
        tau_sus_est = None
        if self.temp_hist:
            # Use last few computed t_sustain values if available via compute_components caller
            # Approximate via last values from compute_t_sustain inputs; if not available, fallback later
            pass

        # Effective τ_eff via harmonic mean if both available; else fallback
        def _harmonic_mean(a: Optional[float], b: Optional[float]) -> Optional[float]:
            if a and b and a > 0 and b > 0:
                return 2.0 * a * b / (a + b)
            return a or b

        tau_eff = _harmonic_mean(tau_th_est, tau_sus_est)

        # Find T_peak from autocorr of rle_smoothed as a simple proxy
        T_peak = None
        if len(self._buf_rle_sm) >= 32:
            series = self._buf_rle_sm[-min(len(self._buf_rle_sm), 512):]
            n = len(series)
            mean = sum(series) / n
            var = sum((x - mean) * (x - mean) for x in series) / max(n, 1)
            if var > 0:
                # Autocorr naive up to a cap for first peak search
                min_lag_sec = 2.0 * dt_win_s
                if tau_th_est:
                    min_lag_sec = max(min_lag_sec, 1.5 * tau_th_est)
                min_lag = max(1, int(min_lag_sec / max(dt_mean, 1e-6)))
                best_k = None; best_r = 0.0
                max_k = min(n // 2, 256)
                for k in range(min_lag, max_k):
                    num = sum((series[i] - mean) * (series[i - k] - mean) for i in range(k, n))
                    den = max(sum((series[i] - mean) * (series[i] - mean) for i in range(n)), 1e-12)
                    r = num / den
                    if r > best_r:
                        best_r = r; best_k = k
                # Require rudimentary SNR
                if best_k is not None and best_r >= 0.3:
                    T_peak = best_k * dt_mean

        # Fallbacks
        if T_peak is None:
            T_peak = tau_eff
        T0_candidate = T_peak if (tau_eff is None) else ((T_peak * tau_eff) ** 0.5) if T_peak is not None else tau_eff
        if T0_candidate is None:
            T0_candidate = self._t0_s

        # Clamp and EMA smooth with ±10% per update guard
        cand = min(max(T0_candidate, self.theta_min_s), self.theta_max_s)
        alpha = 0.2
        ema = (1.0 - alpha) * self._t0_s + alpha * cand
        # Limit change to ±10%
        up = self._t0_s * 1.10
        down = self._t0_s * 0.90
        self._t0_s = min(max(ema, down), up)

    def compute_components(self, util_pct: float, temp_c: Optional[float], power_w: Optional[float], dt_s: float = 1.0) -> Dict[str, float]:
        # Histories
        self.util_hist.append(max(0.0, min(100.0, util_pct)))
        if temp_c is not None:
            self.temp_hist.append(temp_c)

        # Utilization η
        eta = (self.util_hist[-1] / 100.0) if self.util_hist else 0.0

        # Stability σ (inverse of rolling std dev)
        n_stab = 5
        if self.enable_theta_clock and self.use_theta_windows and self.stability_window_theta and self.stability_window_theta > 0:
            n_stab = self._theta_window_to_n(self.stability_window_theta)
        stdev = self._rolling_stdev(self.util_hist, n=n_stab)
        stability = 1.0 / (1.0 + stdev)

        # Load factor α
        p = power_w if (power_w is not None and power_w > 0) else (self.rated_power_w * eta)
        a_load = p / max(self.rated_power_w, 1e-6)

        # Sustainability time τ (RC thermal model inspired)
        t_sustain = self.compute_t_sustain(self.temp_limit_c, self.temp_hist, dt_s, self.max_t_sustain_s)

        return dict(eta=eta, stability=stability, a_load=a_load, t_sustain=t_sustain)

    @staticmethod
    def compute_t_sustain(temp_limit_c: float, temp_hist: List[float], dt_s: float, max_t: float) -> float:
        if len(temp_hist) < 2:
            return max_t
        dT = temp_hist[-1] - temp_hist[-2]
        dTdt = max(dT / max(dt_s, 1e-3), 1e-3)
        t_sustain = (temp_limit_c - temp_hist[-1]) / dTdt
        return max(min(t_sustain, max_t), 1.0)

    def compute_rle(self, util_pct: float, temp_c: Optional[float], power_w: Optional[float], dt_s: float = 1.0) -> RLEResult:
        c = self.compute_components(util_pct, temp_c, power_w, dt_s)
        eta = c['eta']; stability = c['stability']; a_load = c['a_load']; t_sustain = c['t_sustain']
        denom = max(a_load, 1e-6) * (1.0 + 1.0 / max(t_sustain, 1e-6))
        # Core (unaltered) RLE—this drives collapse detection and baseline outputs
        rle_raw_core = (eta * stability) / denom
        
        # Maintain separate smoothing paths to keep collapse on original signal
        n_smooth = None
        if self.enable_theta_clock and self.use_theta_windows and self.smooth_window_theta and self.smooth_window_theta > 0:
            n_smooth = self._theta_window_to_n(self.smooth_window_theta)
        rle_smooth_core = self._smooth_rle(rle_raw_core, override_n=n_smooth)

        # Theta clock maintenance and theta increment (after we have smoothed value)
        self._theta_update_if_needed(rle_smooth_core, temp_c, dt_s)
        # Compute dtheta and accumulate with Kahan summation
        dtheta = 0.0
        theta_gap = 0
        if self.enable_theta_clock:
            if self._buf_dt:
                sdt = sorted(self._buf_dt)
                med_dt = sdt[len(sdt)//2]
                if dt_s > 3.0 * max(med_dt, 1e-6):
                    theta_gap = 1
            dtheta = dt_s / max(self._t0_s, 1e-6)
            y = dtheta - self._theta_c
            t = self._theta_index + y
            self._theta_c = (t - self._theta_index) - y
            self._theta_index = t

        # Micro-scale correction (optional Planck-ish penalty)
        F_mu, F_q, F_s, F_p, Gamma, log_Gamma = self._compute_micro_scale_factor(power_w, temp_c, dt_s, dtheta, self._t0_s)
        rle_raw_ms = rle_raw_core * F_mu
        # Smooth augmented path independently (does not affect collapse)
        self.rle_hist_ms.append(rle_raw_ms)
        rle_smooth_ms = self._rolling_mean(self.rle_hist_ms, n_smooth if n_smooth else self.smooth_n)

        # Unified blend: default to core on desktops (F_mu≈1), micro-scale on phones (lower F_mu)
        # Weight ramps from 0 at F_mu>=0.98 to 1 at F_mu<=0.90
        def _w_from_fmu(f: float) -> float:
            hi, lo = 0.98, 0.90
            if f >= hi: return 0.0
            if f <= lo: return 1.0
            span = hi - lo
            return max(0.0, min(1.0, (hi - f) / span))
        w = _w_from_fmu(F_mu)
        rle_raw_uni = rle_raw_core * (1.0 - w) + rle_raw_ms * w
        self.rle_hist_uni.append(rle_raw_uni)
        rle_smooth_uni = self._rolling_mean(self.rle_hist_uni, n_smooth if n_smooth else self.smooth_n)

        # Diagnostics
        e_th = stability / (1.0 + 1.0 / max(t_sustain, 1e-6))
        e_pw = eta / max(a_load, 1e-6)
        rle_norm_core = self.normalize_rle(rle_smooth_core, util_pct)
        rle_norm_ms = self.normalize_rle(rle_smooth_ms, util_pct)
        rle_norm_uni = self.normalize_rle(rle_smooth_uni, util_pct)

        # Collapse detection strictly uses the unaugmented smoothed value
        collapsed = self._detect_collapse(rle_smooth_core, util_pct, a_load, temp_c, t_sustain)

        # Theta-derived values for output
        T0_s_out = self._t0_s if self.enable_theta_clock else 0.0
        T_sustain_hat = (t_sustain / max(T0_s_out, 1e-6)) if (self.enable_theta_clock and T0_s_out > 0) else 0.0

        return RLEResult(
            rle_raw=rle_raw_core,
            rle_smoothed=rle_smooth_core,
            rle_raw_ms=rle_raw_ms,
            rle_smoothed_ms=rle_smooth_ms,
            rle_raw_uni=rle_raw_uni,
            rle_smoothed_uni=rle_smooth_uni,
            e_th=e_th,
            e_pw=e_pw,
            rle_norm=rle_norm_core,
            rle_norm_ms=rle_norm_ms,
            rle_norm_uni=rle_norm_uni,
            stability=stability,
            a_load=a_load,
            t_sustain_s=t_sustain,
            rolling_peak=self.rolling_peak,
            collapse=collapsed,
            alerts="",
            F_mu=F_mu,
            F_q=F_q,
            F_s=F_s,
            F_p=F_p,
            # Theta diagnostics
            T0_s=T0_s_out,
            theta_index=self._theta_index,
            T_sustain_hat=T_sustain_hat,
            theta_gap=theta_gap,
            # Micro-scale theta-aware diagnostics
            Gamma=Gamma,
            log_Gamma=log_Gamma
        )

    def _smooth_rle(self, rle_raw: float, override_n: Optional[int] = None) -> float:
        self.rle_hist.append(rle_raw)
        n = override_n if (override_n is not None and override_n > 0) else self.smooth_n
        return self._rolling_mean(self.rle_hist, n)

    def _detect_collapse(self, rle_sm: float, util_pct: float, a_load: float, temp_c: Optional[float], t_sustain: float) -> int:
        # Warm-up: require a few samples before enabling
        warm = len(self.rle_hist) >= max(self.smooth_n, 5)
        if not warm:
            self.rolling_peak = 0.0
            self.below_ctr = 0
            return 0

        # Rolling peak with decay
        self.rolling_peak = max(rle_sm, self.rolling_peak * self.rolling_decay)

        # Gates
        under_load = (util_pct > self.util_gate_pct) or (a_load > self.a_load_gate)
        heating = False
        if len(self.temp_hist) >= 2 and temp_c is not None:
            heating = (self.temp_hist[-1] - self.temp_hist[-2]) > 0.05
        gate = under_load and heating

        # Hysteresis (optionally θ-windowed)
        drop = rle_sm < (self.drop_frac * max(self.rolling_peak, 1e-6))
        if gate and drop:
            self.below_ctr += 1
        else:
            self.below_ctr = 0

        hysteresis_samples = self.hysteresis_s
        if self.enable_theta_clock and self.use_theta_windows and self.hysteresis_theta and self.hysteresis_theta > 0:
            hysteresis_samples = max(1, self._theta_window_to_n(self.hysteresis_theta))
        collapsed_flag = self.below_ctr >= hysteresis_samples

        # Evidence requirement
        thermal_evidence = (t_sustain < 60) or (temp_c is not None and temp_c > (self.temp_limit_c - 5))
        power_evidence = (a_load > 0.95)

        return 1 if (collapsed_flag and (thermal_evidence or power_evidence)) else 0

    # ----------------------------
    # Normalization & scaling
    # ----------------------------
    @staticmethod
    def normalize_rle(rle: float, util_pct: float, device_type: str = "cpu") -> float:
        # Same shape as hardware_monitor; keep consistent
        if device_type == "cpu":
            baseline = 0.3; optimal = 5.0; peak_load = 67.0
        else:
            baseline = 0.1; optimal = 3.0; peak_load = 60.0
        u = max(0.0, min(100.0, util_pct))
        if u <= peak_load:
            expected = baseline + (optimal - baseline) * (u / peak_load)
        else:
            expected = optimal - (optimal - baseline * 0.5) * ((u - peak_load) / (100 - peak_load))
        return max(0.0, min(1.0, rle / max(expected, 1e-6)))

    @staticmethod
    def scale_rle(rle: float, p_actual_w: float, t_actual_c: float,
                  p_ref_w: float = 100.0, t_ref_c: float = 60.0,
                  beta: float = 0.12, gamma: float = 0.08,
                  tau_actual_s: Optional[float] = None, tau_ref_s: float = 300.0, delta: float = 0.10) -> float:
        """Apply cross-domain scaling from RLE_SCALING_MODEL.md"""
        if p_actual_w <= 0 or t_actual_c <= 0:
            return rle
        factor = (p_ref_w / p_actual_w) ** beta * (t_ref_c / t_actual_c) ** gamma
        if tau_actual_s is not None and tau_actual_s > 0:
            factor *= (tau_ref_s / tau_actual_s) ** delta
        return rle * factor

    # ----------------------------
    # Control decisions
    # ----------------------------
    def control_decision(self, rle_current: float, rle_predicted: Optional[float] = None, thermal_headroom_c: Optional[float] = None) -> ControlDecision:
        pred = rle_predicted if (rle_predicted is not None) else rle_current
        # Adjust fan suggestion by headroom if provided
        headroom_bonus = 0
        if thermal_headroom_c is not None and thermal_headroom_c > 5:
            headroom_bonus = -10  # slightly less aggressive fans if ample headroom
        if rle_current < 0.2 or pred < 0.1:
            return ControlDecision('emergency', 0.8, 0.2, max(0, 100 + headroom_bonus), 50, 50)
        elif rle_current < 0.4 or pred < 0.3:
            return ControlDecision('aggressive', 1.2, 0.5, max(0, 80 + headroom_bonus), 70, 25)
        elif rle_current < 0.6 or pred < 0.5:
            return ControlDecision('moderate', 2.5, 0.9, max(0, 60 + headroom_bonus), 85, 10)
        else:
            return ControlDecision('maintain', None, None, None, None, None)

# ----------------------------
# CSV CLI
# ----------------------------

def augment_csv(in_path: Path, out_path: Path, rated_power_w: float, temp_limit_c: float,
                enable_micro_scale: bool = False, sensor_temp_lsb_c: float = 0.1, low_power_knee_w: float = 3.0,
                enable_theta_clock: bool = True, use_theta_windows: bool = False) -> None:
    core = RLECore(rated_power_w=rated_power_w, temp_limit_c=temp_limit_c,
                   enable_micro_scale=enable_micro_scale, sensor_temp_lsb_c=sensor_temp_lsb_c, 
                   low_power_knee_w=low_power_knee_w,
                   enable_theta_clock=enable_theta_clock,
                   use_theta_windows=use_theta_windows)
    with in_path.open('r', newline='', encoding='utf-8', errors='ignore') as f_in, out_path.open('w', newline='', encoding='utf-8') as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames or [])
        # Add outputs if missing
        for col in [
            'rle_smoothed','rle_raw','rle_norm','E_th','E_pw','temp_c','power_w','util_pct','a_load','t_sustain_s',
            'rolling_peak','collapse','alerts'
        ]:
            if col not in fieldnames:
                fieldnames.append(col)
        # Add theta-clock columns (augmenter defaults to theta enabled)
        for col in ['T0_s', 'theta_index', 'T_sustain_hat', 'theta_gap']:
            if col not in fieldnames:
                fieldnames.append(col)

        # Add micro-scale diagnostic columns if enabled
        if enable_micro_scale:
            for col in ['F_mu', 'F_q', 'F_s', 'F_p', 'Gamma', 'log_Gamma', 'rle_raw_ms', 'rle_smoothed_ms', 'rle_norm_ms', 'rle_raw_uni', 'rle_smoothed_uni', 'rle_norm_uni']:
                if col not in fieldnames:
                    fieldnames.append(col)
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        prev_ts = None
        for row in reader:
            # Try to read inputs; fall back if missing
            util = _to_float(row.get('util_pct')) or _to_float(row.get('cpu_util_pct')) or 0.0
            temp = _to_float(row.get('temp_c')) or _to_float(row.get('battery_temp_c'))
            power = _to_float(row.get('power_w'))

            # dt estimate (assume 1.0 if unknown)
            dt = 1.0
            cur_ts = row.get('timestamp')
            if prev_ts is not None and cur_ts == prev_ts:
                dt = 1.0
            prev_ts = cur_ts

            res = core.compute_rle(util, temp, power, dt)

            # Write augmented row
            row['rle_raw'] = f"{res.rle_raw:.6f}"
            row['rle_smoothed'] = f"{res.rle_smoothed:.6f}"
            row['rle_norm'] = f"{res.rle_norm:.6f}"
            row['E_th'] = f"{res.e_th:.6f}"
            row['E_pw'] = f"{res.e_pw:.6f}"
            row['a_load'] = f"{res.a_load:.6f}"
            row['t_sustain_s'] = f"{res.t_sustain_s:.1f}"
            row['rolling_peak'] = f"{res.rolling_peak:.6f}"
            row['collapse'] = res.collapse
            row['alerts'] = res.alerts
            # Micro-scale diagnostics (experimental)
            if enable_micro_scale:
                row['F_mu'] = f"{res.F_mu:.6f}"
                row['F_q'] = f"{res.F_q:.6f}"
                row['F_s'] = f"{res.F_s:.6f}"
                row['F_p'] = f"{res.F_p:.6f}"
                row['Gamma'] = f"{res.Gamma:.6f}"
                row['log_Gamma'] = f"{res.log_Gamma:.6f}"
                row['rle_raw_ms'] = f"{res.rle_raw_ms:.6f}"
                row['rle_smoothed_ms'] = f"{res.rle_smoothed_ms:.6f}"
                row['rle_norm_ms'] = f"{res.rle_norm_ms:.6f}"
                row['rle_raw_uni'] = f"{res.rle_raw_uni:.6f}"
                row['rle_smoothed_uni'] = f"{res.rle_smoothed_uni:.6f}"
                row['rle_norm_uni'] = f"{res.rle_norm_uni:.6f}"

            # Theta clock outputs
            row['T0_s'] = f"{res.T0_s:.3f}"
            row['theta_index'] = f"{res.theta_index:.6f}"
            row['T_sustain_hat'] = f"{res.T_sustain_hat:.6f}"
            row['theta_gap'] = f"{res.theta_gap}"
            # Ensure temp/power/util columns are present for downstream tools
            if 'temp_c' not in row or row['temp_c'] in (None, ''):
                row['temp_c'] = '' if temp is None else f"{temp:.2f}"
            if 'util_pct' not in row or row['util_pct'] in (None, ''):
                row['util_pct'] = f"{util:.2f}"
            if 'power_w' not in row or row['power_w'] in (None, ''):
                row['power_w'] = '' if power is None else f"{power:.2f}"

            writer.writerow(row)


def _to_float(x) -> Optional[float]:
    try:
        if x is None: return None
        s = str(x).strip()
        if s == '' or s.lower() == 'none': return None
        return float(s)
    except (ValueError, TypeError):
        return None

# ----------------------------
# CLI
# ----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RLE Core Engine - augment CSVs with canonical RLE metrics")
    p.add_argument('--in', dest='infile', type=str, required=True, help='Input CSV (must have timestamp and util/temp/power columns if available)')
    p.add_argument('--out', dest='outfile', type=str, required=True, help='Output CSV path')
    p.add_argument('--rated-power', dest='rated_power', type=float, default=100.0, help='Baseline/rated power for A_load normalization (W)')
    p.add_argument('--temp-limit', dest='temp_limit', type=float, default=85.0, help='Thermal limit (°C) used by T_sustain')
    p.add_argument('--micro-scale', dest='micro_scale', action='store_true', default=False, help='Enable micro-scale correction (Planck-ish penalty for low-energy regimes)')
    p.add_argument('--sensor-lsb', dest='sensor_lsb', type=float, default=0.1, help='Temperature sensor LSB (°C per tick) for micro-scale correction')
    p.add_argument('--power-knee', dest='power_knee', type=float, default=3.0, help='Low-power granularity knee (W) for micro-scale correction')
    # Theta-clock controls (augmenter): ON by default; windows OFF by default
    p.add_argument('--theta-clock', dest='theta_clock', action='store_true', default=True, help='Enable internal θ-clock (T0_s, theta_index, T_sustain_hat, theta_gap) [default ON]')
    p.add_argument('--no-theta-clock', dest='theta_clock', action='store_false', help='Disable θ-clock outputs')
    p.add_argument('--theta-windows', dest='theta_windows', action='store_true', default=False, help='Use θ-based windows (stability/smoothing/hysteresis) [default OFF]')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_path = Path(args.infile)
    out_path = Path(args.outfile)
    augment_csv(in_path, out_path, rated_power_w=args.rated_power, temp_limit_c=args.temp_limit,
                enable_micro_scale=args.micro_scale, sensor_temp_lsb_c=args.sensor_lsb, low_power_knee_w=args.power_knee,
                enable_theta_clock=args.theta_clock, use_theta_windows=args.theta_windows)
    print(f"Wrote augmented CSV → {out_path}")
    if args.micro_scale:
        print(f"Micro-scale addon: sensor_lsb={args.sensor_lsb}°C, power_knee={args.power_knee}W")


if __name__ == '__main__':
    main()
