# RLE Master Document

## 1. Executive Summary
RLE (Recursive Load Efficiency) is a dimensionless, predictive, topology-invariant efficiency law for any thermal-work system. It quantifies how efficiently power is converted into useful work while preserving thermal stability. Validated across desktop CPU, desktop GPU, and mobile SoC.

- Cross-domain dispersion σ ≈ 0.16 (universal behavior)
- Predictive lead time: ~0.7–1.0 s before firmware throttling
- Mobile constants (S24 Ultra): collapse -0.0043 RLE/s, stabilization 0.0048 RLE/s, thermal sensitivity -0.2467 RLE/°C

See: [RLE Theory (first-principles derivation)](RLE_THEORY.md)

---

## 2. What is RLE (Definition, Formula, Components)
RLE measures efficiency as a balance of productive work versus stress, waste, instability, and time-to-burnout. It is unitless, so values can be compared across devices and form factors.

Formula:
```
RLE = (util × stability) / (A_load × (1 + 1/T_sustain))
  where
    util ∈ [0,1]      # utilization
    stability = 1 / (1 + stddev(util_last_k))
    A_load = power_actual / power_rated
    T_sustain = (temp_limit - temp_c) / max(dT/dt, ε)
```
Split diagnostics:
- E_th = stability / (1 + 1/T_sustain)  (thermal efficiency)
- E_pw = util / A_load                   (power efficiency)

Why dimensionless:
- util, stability, A_load, (1 + 1/T_sustain) are all ratios or pure numbers → units cancel.

Interpretation bands:
- RLE > 0.8: Excellent
- 0.5–0.8: Good
- 0.2–0.5: Moderate (check power/thermal limits)
- < 0.2: Poor (overstressed)

---

## 3. Lab Overview (What the Lab Is)
The RLE Lab is a lightweight monitoring and analysis suite that:
- Samples GPU/CPU telemetry (~1 Hz)
- Computes RLE and diagnostics in real time
- Detects true efficiency collapses with evidence
- Logs to CSV for analysis and reporting
- Generates per-hour plots and session reports

Typical flow: Start monitor → Play/Run workload → CSV logs → Analyze/Report.

---

## 4. Folder Structure and Purpose
```
lab/
├─ monitoring/   # Daemons & live tools (keep <1% CPU)
│  ├─ hardware_monitor.py     # Core polling loop + RLE + collapse
│  ├─ rle_streamlit.py        # Live dashboard
│  └─ generate_report.py      # Auto report on shutdown
├─ analysis/     # Post-session tools
│  ├─ analyze_session.py      # Quick stats & health
│  ├─ rle_comprehensive_timeline.py  # Multi-session overlays
│  ├─ report_sessions.py      # Multi-page PDF reports
│  └─ summarize_sessions.py   # Batch CSV summaries
├─ stress/       # Load generators (safe, focused)
│  └─ simple_stress.py        # Example stress tool
├─ sessions/
│  ├─ recent/    # Hourly rotating CSVs (current)
│  └─ archive/   # Historical data & plots
└─ docs/         # Documentation (this folder)
```

---

## 5. Architecture (Flow & Collapse Detection)
End-to-end pipeline:
1) Collect → 2) Compute → 3) Detect → 4) Log → 5) Visualize/Analyze → 6) Report

Collection:
- GPU: NVML (util_pct, power_w, temp_c, fan_pct, clocks, perf state, throttle reasons)
- CPU: psutil (util), optional HWiNFO CSV (CPU power/temp)

Computation:
- util, stability (rolling util variance), A_load, T_sustain → RLE, E_th, E_pw

Collapse detection (improved v0.3):
- Rolling peak with decay (≈0.998 per tick)
- Gate: util > 60% OR A_load > 0.75 AND temp rising > 0.05°C/s
- Drop: RLE_smoothed < 0.65 × rolling_peak (threshold)
- Hysteresis: sustained for ≥7 consecutive seconds
- Evidence required: T_sustain < 60s OR temp > (limit-5°C) OR A_load > 0.95
- Output: collapse ∈ {0,1}; alerts pipe-list for warnings

Why this works:
- Prevents scene-change noise (requires sustained, evidenced drop)
- Adapts to capability via rolling peak decay

---

## 6. Data Schema (CSV Columns & Meaning)
Schema v0.3.0 (frozen)

Core columns:
- Identification: `timestamp`, `device`
- Efficiency: `rle_smoothed`, `rle_raw`, `E_th`, `E_pw`, `rolling_peak`
- Temperature: `temp_c`, `vram_temp_c`, `t_sustain_s`
- Power/Performance: `power_w`, `util_pct`, `a_load`, `fan_pct`
- Events/Diagnostics: `collapse`, `alerts`

Extended (if available):
- `gpu_clock_mhz`, `mem_clock_mhz`, `mem_used_mb`, `mem_total_mb`, `perf_state`, `throttle_reasons`, `power_limit_w`, `cycles_per_joule`

Stability of schema:
- Append-only; types/order do not change to preserve tool compatibility

---

## 7. Interpreting Results (Patterns & Decisions)
Healthy Gaming:
- RLE 0.3–0.8 most of session; temps 60–72°C; collapses <5% → OK

Thermal Saturation:
- RLE gradual decline with rising temps; more collapses late session → Improve cooling / take breaks

Power Limited:
- A_load near 1.0, E_pw low, temps OK; RLE suppressed → Expected when power-capped; consider undervolt or higher power limit

True Thermal Collapse:
- RLE sustained 0.15–0.25; temp near limit; T_sustain low; collapses clustered → Back off load or improve cooling

Efficiency Degradation:
- Same scene; RLE lower later → thermal mass saturation; schedule cooldowns

Quick decisions:
- RLE > 0.4 consistently → Healthy
- Many collapses with evidence → Thermal/power problem
- Low E_th vs low E_pw identifies thermal vs power bottleneck

---

## 8. RLE Physics (Why It’s Universal)
- Dimensionless: unit cancellation enables cross-device comparison
- Encodes thermal headroom (E_th) and power use (E_pw)
- Predictive: RLE fall precedes firmware throttling by ~0.7–1.0 s
- Cross-domain variance σ ≈ 0.16 across CPU/GPU/SoC proves universal behavior

---

## 9. Mobile Validation (Galaxy S24 Ultra)
- Dataset: 1000 samples (16.7 min), 33→44.4°C, RLE 0.131–0.489
- Constants: collapse -0.0043 RLE/s; stabilization 0.0048 RLE/s; sensitivity -0.2467 RLE/°C
- Outcome: mobile overlaps desktop RLE ranges; predictive lead time <1 s

---

## 10. Topology Invariance
- Isolation (r ≈ 0) vs Coupling (r ≈ 0.47): RLE remains predictive
- No coupling assumption required; adapts to topology

---

## 11. Publication Package (Abstract & Figures)
- Methods, figures checklist (timeline, knee boundary, topology panels, ceiling)
- Abstract emphasizes universality, predictivity, constants, reproducibility

---

## 12. Usage & Troubleshooting (Pointers)
- Start monitor, live dashboard, per-hour PDF reports
- Common issues: NVML load, old CSVs missing new columns, dashboard path

---

## 13. Glossary
- RLE, E_th, E_pw, A_load, T_sustain, rolling peak, collapse

---

## 14. Evidence & Reproducibility
- Proof sessions and metrics: see `lab/sessions/PROOF_SESSIONS.md`
- Mobile dataset and constants scripts available in repo

---

## 15. Indices & Next Steps
- Docs Index: `INDEX.md`
- Next Steps: stress tests, figure extraction, arXiv submission
- Changelog: `CHANGELOG.md`

---

## 16. Key Claims (One Page)
- Universal, predictive, dimensionless; economic boundary via knee point; σ ≈ 0.16
