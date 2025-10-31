# RLE v2 Overview (θ-Clock Core)

RLE v2 is fully dimensionless: an internal period T₀ defines θ-time, making all modules comparable across devices and sampling rates. Outputs are append-only and compatible with existing tools.

## Documents
- Law (mathematics): lab/pdf/MINERS_LAW_UNIFIED_v2.pdf
  - Canonical definitions (T₀, θ), RLE_θ, micro-scale, Ξ diagnostics, Φ_substrate
- Axioms (invariance): lab/pdf/MINERS_UNIFIED_AXIOMS_v2.pdf
  - Temporal invariance, substrate orthogonality, boundedness, collapse independence
- Manual (practice): lab/pdf/ENGINEER_FIELD_MANUAL_v2.pdf
  - Quick CLI, validation checklist, operational tolerances

## Quick Start
`ash
pip install -r requirements.txt
python lab/monitoring/rle_core.py \
  --in sessions/recent/your_session.csv \
  --out sessions/recent/your_session_aug.csv
`

## Key Columns (Append-Only)
- θ-clock: T0_s, theta_index, T_sustain_hat, theta_gap
- Micro-scale: Gamma, log_Gamma
- Diagnostics: Xi_E, Xi_H, Xi_C, Phi_substrate
- Envelope (diagnostic): rle_raw_sub, rle_smoothed_sub, rle_norm_sub

