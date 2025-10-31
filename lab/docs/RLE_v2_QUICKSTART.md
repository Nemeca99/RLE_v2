# RLE_v2 Quick Start

## Install

```bash
pip install -r requirements.txt
```

## Augment a CSV (θ-clock ON by default)

```bash
python lab/monitoring/rle_core.py \
  --in sessions/recent/your_session.csv \
  --out sessions/recent/your_session_aug.csv
```

## Optional: Micro-Scale (low-power precision)

```bash
python lab/monitoring/rle_core.py \
  --in sessions/recent/your_session.csv \
  --out sessions/recent/your_session_aug_ms.csv \
  --micro-scale
```

## Optional: θ-windows (advanced)

```bash
python lab/monitoring/rle_core.py \
  --in sessions/recent/your_session.csv \
  --out sessions/recent/your_session_theta_windows.csv \
  --theta-windows
```

## Columns (append-only)

- `T0_s, theta_index, T_sustain_hat, theta_gap`
- If micro-scale: `Gamma, log_Gamma`
- Diagnostics: `Xi_E, Xi_H, Xi_C, Phi_substrate`
- Envelope (diagnostic-only): `rle_raw_sub, rle_smoothed_sub, rle_norm_sub`

## Concepts

| Module             | Domain               | Output | Meaning                          |
| ------------------ | -------------------- | ------ | --------------------------------- |
| RLE core (θ)       | temporal stability   | RLE_θ  | steadiness of system rhythm       |
| Xi_E               | energy metabolism    | 0→1+   | adequacy of power input vs need   |
| Xi_H               | hot-path efficiency  | 0→1    | heat transfer efficiency          |
| Xi_C               | cold-path efficiency | 0→1    | cooling/restitution efficiency    |
| Φ_substrate        | combined envelope    | 0→1+   | geometric mean of Xi terms        |


