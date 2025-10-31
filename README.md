# RLE: Recursive Load Efficiency Monitor

[![Repository](https://img.shields.io/badge/GitHub-Nemeca99%2FRLE-blue)](https://github.com/Nemeca99/RLE)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)

**RLE** measures hardware efficiency by balancing useful output vs stress, waste, instability, and time-to-burnout. Real-time monitoring for GPU/CPU systems.

## RLE_v2 Highlights

- θ-clock integrated (augmenter default ON) for fully dimensionless time.
- θ-windows gated (advanced, OFF by default).
- Diagnostics appended-only: `Xi_E, Xi_H, Xi_C, Phi_substrate`.
- Compatible with existing dashboards/scripts (append-only schema).

## Quick Start

```bash
pip install -r requirements.txt

# Augment a CSV (θ-clock ON by default)
python lab/monitoring/rle_core.py \
  --in sessions/recent/your_session.csv \
  --out sessions/recent/your_session_aug.csv

# Optional: enable micro-scale (low-power precision)
python lab/monitoring/rle_core.py \
  --in sessions/recent/your_session.csv \
  --out sessions/recent/your_session_aug_ms.csv \
  --micro-scale

# Optional: θ-windows (advanced, off by default)
python lab/monitoring/rle_core.py \
  --in sessions/recent/your_session.csv \
  --out sessions/recent/your_session_theta_windows.csv \
  --theta-windows
```

New columns (append-only):
- `T0_s, theta_index, T_sustain_hat, theta_gap`
- If micro-scale: `Gamma, log_Gamma`
- Diagnostics: `Xi_E, Xi_H, Xi_C, Phi_substrate`
- Envelope (diagnostic-only): `rle_raw_sub, rle_smoothed_sub, rle_norm_sub`

## Concepts (Dimensionless Stability Vector)

Each module is a self-contained, dimensionless feedback loop on the shared θ time base:

| Module                 | Domain                    | Output  | Meaning (simplified)                          |
| ---------------------- | ------------------------- | ------- | --------------------------------------------- |
| θ-clock / RLE core     | temporal stability        | RLE_θ   | how steady the system’s rhythm is             |
| Xi_E                   | energy metabolism         | 0→1+    | adequacy of power input vs need               |
| Xi_H                   | hot-path material flow    | 0→1     | efficiency of heat transfer / resistance path |
| Xi_C                   | cold-path material return | 0→1     | efficiency of cooling / restitution path      |
| Φ_substrate            | combined envelope         | 0→1+    | geometric mean — total systemic balance       |

Stability vector: `Ξ(θ) = [ RLE_θ, Xi_E, Xi_H, Xi_C ]` and envelope `Φ_substrate = (Xi_E·Xi_H·Xi_C)^(1/3)`.

Range discipline:
- `Xi_E` is clamped internally to [0, 2]; `Xi_H, Xi_C` to [0, 1].
- `Φ_substrate` uses the clamped terms; collapse detection remains on canonical RLE.


## 📁 Structure

```
RLE/
├── lab/           # 🧪 Main monitoring lab
│   ├── monitoring/      # Background daemons & tools
│   ├── analysis/        # Post-session analysis
│   ├── stress/          # Stress test generators
│   └── sessions/        # Session data (CSVs & screenshots)
├── Magic/         # 🔢 Separate project (magic squares)
└── README.md      # This file
```

## 🙏 Credits & Dependencies

RLE builds upon excellent open-source projects:

### Core Libraries
- **[psutil](https://github.com/giampaolo/psutil)** - Cross-platform system and process utilities
- **[pynvml](https://github.com/gpuopenanalytics/pynvml)** - NVIDIA Management Library Python bindings
- **[pandas](https://github.com/pandas-dev/pandas)** - Data analysis and manipulation
- **[streamlit](https://github.com/streamlit/streamlit)** - Real-time web dashboard
- **[plotly](https://github.com/plotly/plotly.py)** - Interactive plotting and visualization

### Enhanced Monitoring (v2.0)
- **[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)** - Comprehensive hardware monitoring inspiration
- **[WMI](https://github.com/tjguk/wmi)** - Windows Management Interface for additional sensors

### Development Tools
- **[Python](https://python.org)** - Core runtime environment
- **[GitHub](https://github.com)** - Version control and collaboration

### Special Thanks
- **LibreHardwareMonitor team** - For the comprehensive sensor architecture that inspired our enhanced monitoring system
- **Open Hardware Monitor** - Original project that LibreHardwareMonitor forked from
- **NVIDIA** - For NVML library enabling GPU monitoring
- **Microsoft** - For WMI providing Windows hardware access

All projects are used under their respective open-source licenses. See individual project repositories for license details.

## 🚀 Quick Start

### ⚡ One-Click Launch (Easiest)

**Just double-click `RUN_RLE.bat`** in the repo root!

It will automatically:
- ✅ Check Python installation
- ✅ Install dependencies
- ✅ Start the monitor
- ✅ Open live dashboard in browser
- ✅ Show where CSVs are being saved
- ✅ Generate auto-report when you stop monitoring

**When you stop monitoring** (Ctrl+C), you'll automatically get:
- 📄 Session summary report (`REPORT_rle_YYYYMMDD_HH.txt`)
- 🩺 Health verdict ("System healthy" / "Needs attention")
- 📊 Key metrics (temp, power, RLE, collapse rate)
- 💡 Personalized recommendations

### 🔧 Manual Start

```bash
# Option A: Live SCADA Dashboard (Recommended)
cd lab/monitoring
streamlit run scada_dashboard_live.py
# Click "START Monitor" in sidebar, HWiNFO path pre-filled

# Option B: Full suite (monitor + live graphs)
cd lab
start_monitoring_suite.bat

# Option C: Monitoring only
cd lab
python start_monitor.py --mode gpu --sample-hz 1
```

### 📊 Analyze Session

```bash
# Quick analysis
python lab/analyze_session.py

# Validate system
python kia_validate.py
```

### 🧠 Core Engine (Executable Physics)

Augment any CSV with canonical RLE metrics using the core engine:

```bash
python lab/monitoring/rle_core.py \
  --in lab/sessions/recent/rle_YYYYMMDD_HH.csv \
  --out lab/sessions/recent/rle_YYYYMMDD_HH_core.csv \
  --rated-power 125 --temp-limit 85
```

## 📊 RLE_real Formula

Computes a metric balancing useful output vs stress, waste, instability, and time-to-burnout:

```
RLE_real = (util × stability) / (A_load × (1 + 1/T_sustain))
```

Where:
- **util** = utilization percentage
- **stability** = 1 / (1 + util_stddev)
- **A_load** = current_power / rated_power
- **T_sustain** = time until thermal limit (seconds)

## 📱 Mobile Deployment (Android)

RLE now runs on **mobile devices** (Android 9.0+) with full Kotlin/Compose app:

```bash
# Build and install on your Galaxy S24 (or similar)
cd lab/android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/rle-mobile-debug.apk
```

**What it does**:
- ✅ Same RLE computation engine (adapted for mobile sensors)
- ✅ CSV logging compatible with desktop analysis pipeline
- ✅ Live dashboard (Compose UI)
- ✅ Safety guardrails for passive-cooled operation
- ✅ No root required

**Documentation**:
- 📖 [Getting Started](lab/docs/GETTING_STARTED.md) - 5-minute walkthrough
- ⚡ [Quick Reference](lab/docs/QUICK_REFERENCE.md) - Command cheat sheet & CSV guide
- 🐛 [Troubleshooting](lab/docs/TROUBLESHOOTING.md) - Common issues & solutions
- 📖 [RLE Master (canonical)](lab/docs/RLE_Master.md) - One doc to rule them all
- 📚 [Docs Index](lab/docs/INDEX.md) - All docs in one place
- 🧭 [Docs Architecture](lab/docs/README_ARCHITECTURE.md) - Full document graph & policy

**After collecting data**, analyze with same tools:

```bash
python lab/analysis/rle_comprehensive_timeline.py \
    phone_rle_20251027_19_mobile.csv

# Compare across platforms
python lab/analysis/cross_domain_rle.py \
    sessions/recent/rle_20251027_18_cpu.csv \
    sessions/recent/rle_20251027_18_gpu.csv \
    phone_rle_20251027_19_mobile.csv
```

**Proof**: RLE is universal, not just cross-device but **cross-form-factor** (desktop → mobile).

## 🎯 Features

### Improved Collapse Detection
- ✅ Rolling peak with decay (prevents false positives)
- ✅ Thermal evidence required (t_sustain < 60s OR temp > limit-5°C)
- ✅ Power evidence (A_load > 0.95)
- ✅ Hysteresis: 65% threshold for 7+ seconds
- ✅ Split diagnostics: E_th vs E_pw components

### Lab Tools

| Location | Purpose |
|----------|---------|
| `lab/monitoring/` | Background daemons & core engine |
| `lab/analysis/` | Post-session analysis & plotting tools |
| `lab/stress/` | CPU/GPU stress test generators |
| `lab/sessions/recent/` | Current gaming session CSVs |
| `lab/sessions/archive/` | Historical data & screenshots |

## 📊 CSV Output Format

Each session logs to `sessions/recent/rle_YYYYMMDD_HH.csv` with columns organized by type:
- **Identification**: `timestamp`, `device`
- **Efficiency Metrics**: `rle_smoothed`, `rle_raw`, `E_th`, `E_pw`, `rolling_peak`
- **Temperature Metrics**: `temp_c`, `vram_temp_c`, `t_sustain_s`
- **Power/Performance**: `power_w`, `util_pct`, `a_load`, `fan_pct`
- **Events/Diagnostics**: `collapse`, `alerts`

📚 See `lab/docs/DATA_COLLECTION.md` for the full, up-to-date schema and column details.

## 🧠 AI Training Validation & Bidirectional Coupling Discovery

RLE successfully characterizes AI model training as a distinct thermal workload and has discovered **bidirectional thermal-optimization coupling**:

### AI Workload Characterization
- **CPU Training**: DistilGPT-2 fine-tuning shows 14.3% collapse rate, mean RLE 0.28, sustained 125W
- **GPU Training**: Luna model (Llama-3.1-8B LoRA) shows 16.7% collapse, 77W power, 54-59°C temp
- **Workload Comparison**: GPU AI vs CPU AI shows 3x power difference and distinct thermal signatures

### Scientific Breakthrough: Thermal-Optimization Personality
- **Reproducibility**: 3 identical training sessions show consistent correlation (-0.087 ± 0.040)
- **Workload Independence**: Training vs inference show different coupling patterns (sign flip)
- **Bidirectional Control**: Both grad_norm→RLE and RLE→grad_norm directions observed
- **Personality Discovery**: 
  - **Training Mode**: "I feel the math stress and respond thermally" (reactive)
  - **Inference Mode**: "I set the thermal tone for the math" (proactive)
- **Status**: First bidirectional thermal-optimization coupling analysis ever documented

### Validation Commands
```bash
# Run AI training with RLE monitoring
python lab/run_joint_session.py --model distilgpt2 --duration 180 --output ai_training_test

# Analyze correlation between gradient norm and thermal efficiency
python lab/analysis/lag_analysis_comprehensive.py

# Generate thermal personality report
python lab/analysis/reproducibility_analysis.py
```

Sample row:

| Column | Description | Example |
|--------|-------------|---------|
| `timestamp` | ISO UTC timestamp | `2025-10-27T12:34:56.789Z` |
| `device` | "gpu" or "cpu" | `gpu` |
| `rle_smoothed` | 5-sample rolling average RLE | `0.723456` |
| `rle_raw` | Instantaneous RLE | `0.845678` |
| `E_th` | Thermal efficiency component | `0.580000` |
| `E_pw` | Power efficiency component | `1.350000` |
| `temp_c` | Core temperature (°C) | `75.00` |
| `vram_temp_c` | VRAM/junction temp (°C) | `82.00` |
| `power_w` | Power draw (W) | `198.50` |
| `util_pct` | Utilization (%) | `99.00` |
| `a_load` | Normalized load (power/rated) | `0.993` |
| `t_sustain_s` | Seconds to thermal limit | `310.0` |
| `fan_pct` | Fan speed (%) | `80` |
| `rolling_peak` | Adaptive peak reference | `1.001545` |
| `collapse` | Collapse event flag (0/1) | `1` |
| `alerts` | Pipe-separated warnings | `GPU_TEMP_LIMIT|VRAM_TEMP_LIMIT` |

## 📈 Example Session

From a typical gaming session:
```
Session: 26.6 minutes, 1597 samples
├─ Power: 15-200W range (median 184W)
├─ Temperature: 58-76°C (peak 76°C)
├─ Max RLE: 1.00
├─ Mean RLE: 0.17 (bimodal: idle vs maxed)
└─ Collapse Events: ~5% with improved detector (v0.3+)
```

**Interpretation**:
- System healthy (temp < 80°C)
- Hitting power limit frequently (at 200W rated)
- Bimodal load normal for gaming (idle menus + maxed gameplay)
- Low mean RLE from scene switching, not thermal issues

## 🔧 Magic Squares (Separate Project)

The `Magic/` folder contains magic square search code (intensive CPU/GPU workload).

See `Magic/README_data_tools.md` for details.

---

**Documentation**:
- 📖 [RLE Master (canonical)](lab/docs/RLE_Master.md)
- 📚 [Docs Index](lab/docs/INDEX.md)
- 🧭 [Docs Architecture](lab/docs/README_ARCHITECTURE.md)
- 🚀 [Getting Started](lab/docs/GETTING_STARTED.md) - 5-minute walkthrough
- ⚡ [Quick Reference](lab/docs/QUICK_REFERENCE.md) - Command cheat sheet & CSV guide
- 🐛 [Troubleshooting](lab/docs/TROUBLESHOOTING.md) - Common issues & solutions
- 📊 [Publication Package](lab/docs/PUBLICATION.md) - Results & figures

**Analysis Tools**:
- `analyze_session.py` - Single session analysis with health assessment
- `scripts/batch_analyze.py` - Multi-session comparison

**Recent improvements** (v0.4.0):
- ✅ Improved collapse detection (rolling peak, evidence requirements, 7s hysteresis)
- ✅ Reduced false positives from 51% → single digits
- ✅ Added Streamlit real-time dashboard
- ✅ Split diagnostics (E_th vs E_pw)
- ✅ **Core engine**: `lab/monitoring/rle_core.py` for canonical formula/scaling/control
- ✅ **Mobile RLE validated**: Cross-form-factor data and scaling model consolidated in docs

### Micro-Scale Correction Addon (Experimental)
- Optional, multiplicative factor `F_mu` that attenuates RLE in low-energy, sensor-limited regimes (phones), inert on desktops.
- Appends columns only: `F_mu,F_q,F_s,F_p,rle_raw_ms,rle_smoothed_ms,rle_norm_ms` when enabled in monitor or via offline tool.
- Collapse detection continues to use the original RLE stream.

Validation (2025-10-31):
- Desktop: `F_mu` mean 0.9673 (p5–p95: 0.9299–0.9860), mean |Δrle_norm| = 0.0041, collapse parity unchanged.
- Phone (archived): Wildlife OFF 73.4% → ON 0.0% collapses; corr(F_mu,power_w)=0.618; high-power KS D=0.781 (p≈0.000).

Commands:
```bash
# Offline append-only augmentation
py -3 lab/monitoring/apply_micro_scale.py --in path.csv --out path_on.csv --sensor-lsb 0.2 --power-knee 3.0

# A/B stats
py -3 lab/analysis/micro_scale_ab_stats.py --off path_off.csv --on path_on.csv --device phone
```

### Unified Path (Adaptive Blend)
- Unified stream `rle_*_uni` blends core and micro-scale based on `F_mu` (inert on desktops; active on phones).
- Default behavior matches experimental design (w=0 at F_mu≥0.98; w=1 at F_mu≤0.90). CLI threshold hint: `--uni-thresh-w 10` in apply tool.

Unified commands (append-only CSV):
```bash
py -3 lab/monitoring/apply_micro_scale.py \
  --in path.csv --out path_ms_uni.csv \
  --sensor-lsb 0.2 --power-knee 3.0 --uni-thresh-w 10
```

Final report:
- `lab/sessions/archive/reports/micro_scale_validation_final.md` (timestamped, includes verdict table and section outputs)

