# What Changed: RLE v1 → v2 (θ-Clock Core)

## Core Changes
- θ-clock: T₀, θ = t/T₀; no wall-second dependence
- θ-windows: optional; default OFF
- Micro-scale: unchanged in math; integrated with θ via Γ, Δθ
- Diagnostics: Xi_E, Xi_H, Xi_C, Phi_substrate (append-only)
- Envelope: rle_*_sub (diagnostic-only)

## CSV Schema (Header Diff)
`
# v1 (excerpt)
timestamp,device,rle_smoothed,rle_raw,E_th,E_pw,temp_c,vram_temp_c,power_w,util_pct,a_load,t_sustain_s,fan_pct,rolling_peak,collapse,alerts

# v2 (append-only additions after v1)
...,T0_s,theta_index,T_sustain_hat,theta_gap,Gamma,log_Gamma,Xi_E,Xi_H,Xi_C,Phi_substrate,rle_raw_sub,rle_smoothed_sub,rle_norm_sub
`

## Operational Defaults (v2)
- θ-update-sec=60; EMA α=0.2; ±10% per update; device θ-bounds (phones 2–120 s, desktops 5–600 s)
- Collapse detection unchanged (canonical path)
- Augmenter: --theta-clock ON by default; --theta-windows OFF; --substrate-envelope OFF

