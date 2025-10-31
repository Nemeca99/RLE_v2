# Immediate Next Actions for RLE Validation

## Priority Tasks

### 1. Run 100% Sustained Load Test ✓ Ready
**Purpose**: Capture genuine collapses for model validation

```bash
cd lab
.\RUN_STRESS_TEST.bat
```

**What it does**:
- Starts monitoring (CPU + GPU)
- Runs 30-minute 100% CPU stress test
- Captures collapse events with thermal evidence
- Saves data to `sessions/recent/rle_*.csv`

**Expected Results**:
- Collapse rate: 5-15% (validates detector)
- Temperature: Near thermal limits
- RLE: Drops during sustained high load
- Model validation: Check if predictions match reality

### 2. Integrate HWiNFO ✓ Ready to Configure
**Purpose**: Full thermodynamic closure (CPU temperature data)

**Setup Steps**:
1. Install HWiNFO from https://www.hwinfo.com/
2. Launch HWiNFO
3. Settings → Logging → CSV Export enabled
4. Select these sensors:
   - `CPU Package Power (W)`
   - `CPU Package (°C)` or `CPU (Tctl/Tdie)`
5. Save CSV to: `C:\temp\hwinfo.csv` (or your path)

**Configure Monitor**:
```bash
python start_monitor.py --mode both --hwinfo-csv "C:\temp\hwinfo.csv"
```

**Or**: Edit `hardware_monitor.py` line 120 to set default HWiNFO path

**Result**: Complete instrumentation (CPU temp + power + utilization)

### 3. Deploy Streamlit Dashboard ✓ Ready
**Purpose**: Live monitoring of RLE, variance, and FFT bands

**Launch**:
```bash
cd lab
start_monitoring_suite.bat
```

**Or manually**:
```bash
# Terminal 1: Monitor
python start_monitor.py --mode both

# Terminal 2: Dashboard
streamlit run monitoring/rle_streamlit.py
```

**Dashboard Features**:
- Real-time RLE graph
- Power & temperature plots
- Collapse events (red X markers)
- Rolling peak threshold
- Efficiency components (E_th, E_pw)

**Enhanced Features** (to add):
- FFT spectral analysis panel
- Rolling variance display
- Collapse prediction warnings
- Live control system status

### 4. Archive Reference Datasets ✓
**Purpose**: Create benchmark baseline for future comparisons

**Current Archive**:
```
lab/sessions/archive/
├── cpu_ramp_8h.csv          ✓ Reference ramp test
├── plots/                    ✓ Visualizations
└── ANALYSIS_SUMMARY.md      ✓ Findings documentation
```

**To Archive**:
1. Stress test results (30-min sustained)
2. HWiNFO-instrumented runs
3. Cross-domain validation data
4. Collapse-detection validation

**Archive Command**:
```bash
# After session
mv sessions/recent/rle_*.csv sessions/archive/
```

---

## Quick Start Summary

```bash
# 1. Run stress test (30 minutes)
cd lab
.\RUN_STRESS_TEST.bat

# 2. Analyze results
python analysis\analyze_collapses.py sessions/recent\rle_*.csv

# 3. Verify model predictions
python analysis\collapse_detector.py sessions/recent\rle_*.csv

# 4. Archive reference dataset
mv sessions/recent\rle_*.csv sessions\archive\
```

---

## Validation Checklist

After stress test, verify:

- [ ] Collapse rate is realistic (5-15% at high load)
- [ ] Collapse events align with thermal evidence (temp > limit-5°C)
- [ ] RLE drops predictably at high load
- [ ] Control system would have prevented instability
- [ ] Model predictions match observed behavior

---

## Scientific Deliverables

### Complete Documentation ✓
- `RLE_TECHNICAL_SUMMARY.md` - Technical paper
- `lab/sessions/archive/ANALYSIS_SUMMARY.md` - Findings
- `RLE_Summary.md` - Quick reference
- `lab/control/README_CONTROL.md` - Control systems

### Validation Data
- 8-hour ramp test (baseline)
- 30-minute stress test (collapse validation)
- Cross-domain comparison (CPU vs GPU)

### Control System
- Feed-forward controller (pre-emptive throttling)
- Dynamic scaling (environmental adaptation)
- Adaptive control (power targeting)
- Collapse prediction (variance-based warnings)

---

## Expected Outcomes

### From Stress Test
1. **Genuine collapses** captured with thermal evidence
2. **Model validation** - predictions match reality
3. **Threshold refinement** - adjust detector if needed
4. **Control system proof** - demonstrate prevention

### With HWiNFO
1. **Full instrumentation** - CPU temp + power
2. **Thermodynamic closure** - complete energy balance
3. **Accurate RLE** - no more estimation
4. **Better validation** - all sensors reporting

### From Live Dashboard
1. **Real-time insights** - watch RLE as it happens
2. **Collapse warnings** - see predictions live
3. **Spectral analysis** - FFT patterns during stress
4. **Control feedback** - verify adaptive responses

---

## Status: Ready to Execute

All tools are ready. Next session:
1. Run stress test (30 min)
2. Analyze collapse events
3. Integrate HWiNFO (optional but recommended)
4. Deploy enhanced dashboard
5. Archive reference dataset

**Estimated time**: 2 hours (including setup and analysis)

