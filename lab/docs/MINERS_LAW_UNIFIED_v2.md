# MINER’S UNIFIED LAW (RLE v2, θ-Clock Core)

Version: v2.0 (θ-clock + substrate diagnostics)
Status: Canonical reference

## 1. Overview
- Purpose, scope, and compatibility notes (append-only outputs; dashboards unchanged)
- What changed vs v1 (no wall-seconds; θ-time; Ξ diagnostics)

## 2. Canonical Definitions
- Internal period T₀: machine “heartbeat” (update every 60 s, EMA α=0.2, ±10% clamp)
- Dimensionless time: θ = t / T₀, Δθ = Δt / T₀
- Sustainability (dimensionless): T̂_sustain = T_sustain / T₀

## 3. RLE Core (θ)
RLE_θ = (η · σ) / (α · (1 + 1/T̂_sustain))
- η (utilization), σ (stability), α (load factor), T̂_sustain (dimensionless)
- Normalization and collapse detection (unchanged; canonical path)

## 4. Micro-Scale (Planck-Flavored)
- N_q = (P · T₀ / (k_B · T)) · Δθ
- F_q = 1 − e^(−min(N_q, 50)), F_s = 1/(1 + (ΔT_min/σ_T)²), F_p = P/(P+P₀)
- F_μ = (F_q · F_s · F_p)^(1/3) (inert on desktops; active on phones)

## 5. Substrate Diagnostics (Dimensionless, θ-Based)
Ξ_E = F_q                  # energy adequacy per internal period (clip to [0, 2])
Ξ_H = E_th                 # hot-path efficiency (clip to [0, 1])
Ξ_C = F_s · F_p            # cold-path/material proxy (clip to [0, 1])
Φ_substrate = (Ξ_E · Ξ_H · Ξ_C)^(1/3)  # combined envelope

## 6. Invariants & Guards
- Time-invariance: resampling 0.5/1/2 Hz preserves collapse parity
- Boundaries: no NaN/Inf in T₀, Δθ, θ_index, T̂_sustain, log_Γ
- Decay/EMA clamps: α=0.2; ±10% per update; device θ-bounds (phones 2–120 s, desktops 5–600 s)

## 7. CSV Schema (Append-Only)
- New columns: T0_s, theta_index, T_sustain_hat, theta_gap
- Micro-scale: Gamma, log_Gamma; Diagnostics: Xi_E, Xi_H, Xi_C, Phi_substrate
- Envelope (diagnostic): rle_raw_sub, rle_smoothed_sub, rle_norm_sub

## 8. Validation Summary
- Time-invariance (KS), θ jitter ≤10% steady, F_μ monotone w.r.t. power
- Phone corr(F_μ, power) ≥ 0.5; desktops F_μ ≈ 1

## 9. Appendix (Parameter Defaults)
- θ-update-sec=60; α=0.2; decay=0.998; hysteresis=7 (samples), drop=0.65, etc.
