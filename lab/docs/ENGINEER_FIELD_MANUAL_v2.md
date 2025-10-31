# ENGINEER FIELD MANUAL (RLE v2)

## Quick Start
pip install -r requirements.txt
python lab/monitoring/rle_core.py --in sessions/recent/your_session.csv --out sessions/recent/your_session_aug.csv
# Optional
--micro-scale, --theta-windows, --substrate-envelope

## New Flags (v2)
--theta-clock (augmenter default ON)
--theta-windows (advanced; off by default)
--substrate-envelope (diagnostic-only envelope path)

## CSV Columns (Append-Only)
T0_s, theta_index, T_sustain_hat, theta_gap
[if micro-scale] Gamma, log_Gamma
Xi_E, Xi_H, Xi_C, Phi_substrate
[if envelope] rle_raw_sub, rle_smoothed_sub, rle_norm_sub

## Operational Guidance
- Accept θ jitter ≤10% steady; expect 2–3 updates to settle after load change
- Micro-scale inert on desktops; active on phones
- Collapse parity must match across resamples

## Validation Checklist (Operator)
- No NaNs/Infs in θ/diagnostics
- Phone corr(F_μ, power) ≥ 0.5; desktop F_μ ≈ 1
- Time-invariance (0.5/1/2 Hz): collapse parity identical; Δmean(RLE_norm) < 0.01 in high-power windows

