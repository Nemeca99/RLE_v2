# Micro-Scale Correction Addon

**Status**: Experimental  
**Purpose**: Optional Planck-flavored penalty for low-energy regimes where quantization and sensor granularity dominate

## Overview

The core RLE law remains **sacred and unmodified**. This addon multiplies computed RLE by a dimensionless factor `F_mu` that quietly penalizes regimes where:
- Energy per sample approaches thermal quantum scales
- Temperature sensors can't resolve actual jitter
- Power is too low for meaningful SNR

**Key Principle**: `F_mu` is **inert by default** on desktop/laptop systems. It only activates on phones/tiny devices where these limits matter.

## Formula

```
RLE_aug = RLE × F_mu
```

Where `F_mu` is the **geometric mean** of three dimensionless factors:

### a) Thermal-Quanta Term F_q

"How many thermal quanta per sample?"

```
N_q = (P × Δt) / (k_B × T)
F_q = 1 - e^(-N_q)
```

- `P` = instantaneous power (W)
- `Δt` = sampling period (default 1 s)
- `T` = absolute temperature (K)
- `k_B` = Boltzmann constant (1.38×10⁻²³ J/K)

**Interpretation**: If `N_q << 1`, you're pushing almost no energy per sample and get penalized. Big iron makes `F_q → 1`.

### b) Sensor-Resolution Term F_s

"Can sensors resolve real thermal motion?"

```
F_s = 1 / (1 + (ΔT_min / σ_T)²)
```

- `ΔT_min` = temperature sensor LSB (°C per tick)
- `σ_T` = rolling std dev of temperature over stability window

If the sensor's least significant bit is bigger than actual thermal wiggle, `F_s` drops.

### c) Low-Power SNR Term F_p

"Below this scale, everything looks dice-rolled."

```
F_p = P / (P + P_0)
```

- `P_0` = reference "granularity power" where quantization noise dominates

**Geometric Mean**:

```
F_mu = (F_q × F_s × F_p)^(1/3)
```

All three must agree you're in the microscopic danger zone.

## Platform Tuning

### Phone Class (≈ 3-10 W)

```python
sensor_temp_lsb_c = 0.2-0.5  # °C
low_power_knee_w = 3-5       # W
```

Expect `F_mu` to float in 0.7-0.95 during jittery app loads, near 1.0 during sustained benches.

### Laptop (≈ 15-45 W sustained)

```python
sensor_temp_lsb_c = 0.1-0.2  # °C
low_power_knee_w = 1-2       # W
```

`F_mu → 1` unless in whisper mode.

### Desktop GPU/CPU (≫ 75 W)

```python
sensor_temp_lsb_c = 0.1      # °C
low_power_knee_w ≤ 0.5       # W
```

`F_mu ≈ 1` basically always. The addon is inert, which is the point.

## Usage

### In Python

```python
from monitoring.rle_core import RLECore

# Enable micro-scale correction
core = RLECore(
    rated_power_w=100.0,
    temp_limit_c=85.0,
    enable_micro_scale=True,      # Toggle this
    sensor_temp_lsb_c=0.1,         # °C per tick
    low_power_knee_w=3.0           # W
)

# Compute RLE (original + micro-scale variants)
result = core.compute_rle(util_pct=50.0, temp_c=60.0, power_w=5.0)
print(f"RLE raw (core): {result.rle_raw}")
print(f"RLE raw (micro-scale): {result.rle_raw_ms}")
```

### In CLI

```bash
# Augment an existing CSV by appending micro-scale columns only (noninvasive)
python lab/monitoring/apply_micro_scale.py \
    --in sessions/recent/rle_20251030_19.csv \
    --out out_augmented.csv \
    --sensor-lsb 0.2 \
    --power-knee 3.0

### Unified Path (Adaptive Blend)

Unified stream blends core and micro-scale based on F_mu (inert on desktops, active on phones). Appends `rle_raw_uni,rle_smoothed_uni,rle_norm_uni`.

```bash
python lab/monitoring/apply_micro_scale.py \
  --in sessions/recent/rle_20251030_19.csv \
  --out out_ms_uni.csv \
  --sensor-lsb 0.2 --power-knee 3.0 --uni-thresh-w 10
```
```

## Important Design Decisions

1. **Noninvasive**: Desktop/laptop behavior stays validated
2. **Multiplicative**: Doesn't break existing normalization
3. **Optional**: Off by default (`enable_micro_scale=False`)
4. **Collapse-Independent**: Detector uses original RLE, not augmented
5. **Dimensionless**: Every piece is a pure ratio
6. **Monotone**: More energy/SNR → higher F_mu

## What This Fixes

Without micro-scale correction on phones:
- Fake "collapses" from thermal sensor quantization
- Spurious RLE drops during low-power transitions
- Unphysical efficiency cliffs from tiny energy per sample

With micro-scale correction:
- RLE quietly penalized in regimes where signal < noise
- Collapse detector still uses validated physics
- Big systems completely unaffected

## Validation Plan

1. Run on phone data: expect `F_mu` correlated with power level
2. Run on desktop: confirm `F_mu ≈ 1.0` always
3. Compare collapse rates: should decrease on phones, unchanged on desktop
4. Check cross-device plots: mobile RLE should move closer to desktop range

## Notes

This is **experimental**. The core law is unchanged. If micro-scale proves useful, we keep it. If it's a distraction, flip the flag and forget it exists. No breaking changes either way.

---

## Test Procedure (No-Excuses)

### 1) Unit sanity (no hardware)
- Run: `python lab/analysis/micro_scale_unit_sanity.py`
- Expect: F_mu increases with power; F_mu→1 above 50W; F_mu≪1 below 5W and rising.

### 2) CSV augmentation test (offline)
Baseline:
```bash
python lab/monitoring/rle_core.py \
  --in lab/sessions/recent/ANY_SESSION.csv \
  --out out_baseline.csv
```
Augmented:
```bash
python lab/monitoring/apply_micro_scale.py \
  --in lab/sessions/recent/ANY_SESSION.csv \
  --out out_aug.csv \
  --sensor-lsb 0.2 \
  --power-knee 3.0
```
Pass:
- `out_aug.csv` has originals intact plus appended `F_mu,F_q,F_s,F_p,rle_raw_ms,rle_smoothed_ms,rle_norm_ms` (no reordering).
- `rle_smoothed_ms ≈ rle_smoothed × F_mu` within float error.
- Desktop CSVs: `F_mu ≈ 1`; phone CSVs: `F_mu` tracks power.

### 3) Live A/B on phone
Collect OFF (addon off) and ON (addon on in monitor flags) ~10–15 min each.
Analyze:
```bash
python lab/analyze_session.py path/to/phone_off.csv
python lab/analyze_session.py path/to/phone_on.csv
```
Expect: Lower collapse rate ON; smoother `rle_norm_ms` <5W; real events preserved.

### 4) Live A/B on desktop/laptop
Expect: Mean `rle_norm` delta < 0.02; collapse unchanged; `F_mu ≈ 1`.

### 5) Quick stats
```bash
python lab/analysis/micro_scale_ab_stats.py --off path/off.csv --on path/on.csv --device phone
```

Unified vs Original drift/jitter:
```bash
python lab/analysis/unified_vs_original_stats.py --in path/on_ms_uni.csv --device phone
```
Outputs: corr(`F_mu`,`power_w`) positive on phone; KS: low-power distribution tightens upward; high-power unchanged.

### 6) Acceptance checklist
- [ ] Desktop/laptop unchanged, `F_mu ≈ 1`
- [ ] Phone collapse rate falls; low-power jitter reduced; benches match baseline
- [ ] CSV compatibility intact (appended columns only); Streamlit/SCADA still render

### 7) Safety
- Default flag OFF in monitor/CLI; columns marked experimental; collapse uses original RLE.

### 8) Reporting
- All section reports are timestamped in UTC and consolidated into:
  - `lab/sessions/archive/reports/micro_scale_validation_final.md`
- If a regime is missing (e.g., <5 W), use data-driven extrapolation (block bootstrap on your real data). Store derived CSVs under `sessions/archive/synthetic/` and tag rows with `extrapolated=1`. Originals remain unchanged.

