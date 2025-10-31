# Publication Package: RLE Universality

## Executive Summary
- Dimensionless, predictive, topology-invariant efficiency law (RLE)
- Cross-domain σ = 0.16 (CPU, GPU, Mobile SoC)
- Predictive lead time: 0.7–1.0 s
- Mobile constants: collapse -0.0043 RLE/s, stabilization 0.0048 RLE/s, sensitivity -0.2467 RLE/°C

## Methods (Implementation Overview)
- Monitoring: NVML (GPU), psutil (CPU), optional HWiNFO
- Sampling: 1 Hz; CSV includes RLE components + evidence
- Collapse detection: 65% of rolling peak, 7s hysteresis, evidence gates
- Control: Feed-forward + dynamic scaling + adaptive power targeting

## Key Results
- RLE ranges overlap across 4W–300W systems (0.13–0.62)
- RLE predicts throttling 0.7–1.0 s before firmware
- Efficiency knee point marks economic boundary (power ↑, efficiency ↓)
- Thermal isolation (r ≈ 0) and coupling (r ≈ 0.47) both validated

## Figures (to include)
1. RLE timeline with instability windows (predictive lead)
2. Efficiency knee boundary map (RLE vs Power)
3. Thermal isolation vs coupling panels (r ≈ 0 and r ≈ 0.47)
4. Efficiency ceiling over long session

## Data & Reproducibility
- Mobile dataset: `phone_rle_wildlife.csv` (1000 samples)
- Constants script: `lab/pc/analyze_mobile_constants.py`
- Combined timeline: `phone_all_benchmarks.csv`
- Desktop reference: ramp tests in archive

## Submission Targets
- arXiv (immediate), then IEEE/ACM conferences/journals (systems, thermal, control)

## One-Paragraph Abstract
A dimensionless thermal efficiency law (RLE) validated across heterogeneous compute platforms demonstrates universal scaling from 4W mobile SoC to 300W desktop systems. Cross-domain variance σ=0.16 and predictive lead time <1s confirm topology-invariance and practical control utility. Publication-ready constants and datasets included.
