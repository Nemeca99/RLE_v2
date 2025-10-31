# RLE LIVE SCADA Dashboard - Complete User Guide

**Purpose**: Real-time thermal efficiency monitoring and control center for hardware performance analysis  
**Version**: 1.0  
**Last Updated**: 2025-10-31

---

## Table of Contents

1. [Overview](#overview)
2. [Control Panel (Sidebar)](#control-panel-sidebar)
3. [Main Dashboard Layout](#main-dashboard-layout)
4. [Reading the Metrics](#reading-the-metrics)
5. [Interpreting the Data](#interpreting-the-data)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The RLE LIVE SCADA Dashboard provides **real-time visualization** of thermal efficiency data collected by the RLE monitoring system. It displays hardware telemetry from CPU/GPU sensors and computes Recursive Load Efficiency (RLE) metrics to track system performance under load.

**RLE Definition**: Recursive Load Efficiency (RLE) is a dimensionless ratio describing system stability and efficiency under thermal feedback, computed as `(utilization × stability) / (load_factor × thermal_constant)`.

**Access**: `http://localhost:8501`  
**Data Source**: Live CSV files from RLE monitor daemon  
**Update Rate**: Configurable (default: every 5 seconds with auto-refresh)

### Data Flow Architecture

```
Hardware Sensors → Monitor Daemon → CSV Logger → Dashboard Display
     (NVML/HWiNFO)   (polling)   (hourly files)   (real-time plots)
```

**Components**:
- **Hardware Sensors**: NVML (GPU), HWiNFO (temperature), psutil (CPU)
- **Monitor Daemon**: `start_monitor.py` runs in background, polls sensors at 1-5 Hz
- **CSV Logger**: Writes timestamped rows to `rle_YYYYMMDD_HH.csv` (new file every hour)
- **Dashboard**: Streamlit reads latest CSV, displays live plots and statistics

---

## Control Panel (Sidebar)

Located on the left side of the dashboard. All controls modify how data is collected, displayed, or filtered.

### 1. Monitoring Mode

**Radio Buttons**: cpu | gpu | both

**Meaning**: Which hardware device(s) the background monitor should collect data from.

- **cpu**: Only CPU sensors (utilization, frequency, temperature via HWiNFO)
- **gpu**: Only GPU sensors (NVML: utilization, memory, temperature, power, clocks)
- **both**: Both devices simultaneously (alternating samples)

**Default**: gpu  
**Note**: This controls **data collection**, not **data display**.

---

### 2. Sample Rate (Hz)

**Slider**: 1 to 5 Hz

**Meaning**: How many times per second the monitor polls hardware sensors.

- **1 Hz**: 1 sample/second (recommended for normal use)
- **5 Hz**: 5 samples/second (high-resolution, more CPU intensive)

**Default**: 1 Hz  
**Impact**: Higher rates produce smoother graphs but larger CSV files and more CPU usage.

---

### 3. Display Device

**Radio Buttons**: cpu | gpu | both

**Meaning**: Which device's data to show in the dashboard visualizations.

- **cpu**: Only display CPU samples (filter GPU rows out)
- **gpu**: Only display GPU samples (filter CPU rows out)
- **both**: Show all samples (mixed CPU/GPU)

**Default**: cpu  
**Note**: This controls **data display**, separate from **Monitoring Mode**.

---

### 4. Display Settings

#### Auto-refresh (5s)

**Checkbox**: Enabled/Disabled

**Meaning**: Automatically reload dashboard every 5 seconds to show latest data.

- **Enabled**: Dashboard refreshes automatically (shows live updates)
- **Disabled**: Manual refresh only (click browser refresh button)

**Default**: Disabled (to prevent visual "pulsing")  
**Use Case**: Enable during active stress testing to watch real-time changes.

---

#### Smoothing Window

**Slider**: 1 to 20 samples

**Meaning**: *Currently unused in dashboard* (display-only placeholder).

**Planned**: Apply moving average to graph traces to reduce noise.  
**Current Behavior**: Data displayed as-is with 5-sample rolling average from monitor.

---

### 5. Alert Thresholds

#### RLE Warning

**Slider**: 0.00 to 1.00

**Meaning**: RLE value below which to trigger visual warning.

- **0.50**: Moderate efficiency threshold (reduced performance)
- **0.20**: Critical efficiency threshold (significant degradation)
- **<0.10**: Very poor efficiency (thermal throttling likely)

**Current Behavior**: *Display-only* (does not generate alerts yet).  
**Default**: 0.50

---

#### Temp Warning (°C)

**Slider**: 40 to 100°C

**Meaning**: Temperature above which to trigger visual warning.

- **70°C**: Moderate thermal stress
- **85°C**: High thermal stress (throttling imminent)
- **95°C+**: Critical (thermal shutdown possible)

**Current Behavior**: *Display-only* (does not generate alerts yet).  
**Default**: 70°C

---

### 6. HWiNFO Integration

#### HWiNFO CSV Path (optional)

**Text Input**: File path to HWiNFO sensor CSV

**Meaning**: Location of HWiNFO's CSV logging output for CPU/GPU temperature data.

**Default**: `F:\RLE\sessions\hwinfo\10_30_2025_702pm.CSV`  
**Required**: HWiNFO must be running with CSV logging enabled (Sensors → Logging menu)  
**Impact**: Without this, temperature may show "N/A" (monitor falls back to synthetic values).

**Setup**:
1. Open HWiNFO
2. Go to Sensors window
3. Enable "Logging" to CSV
4. Copy file path to this field

---

### 7. Monitor Control

#### ▶️ START Monitor

**Button**: Click to launch background monitoring daemon

**Action**: Starts `start_monitor.py` in background Python process.

**Output**: Shows success message with PID (process ID)  
**Requirements**: 
- Python venv at `F:\RLE\venv\Scripts\python.exe`
- Monitor script at `F:\RLE\lab\start_monitor.py`

**Status**: Check "File: rle_XXXXXXX.csv" line to verify new file created.

---

#### ⏹️ STOP Monitor

**Button**: Click to terminate monitoring daemon

**Action**: Kills any running `start_monitor.py` processes.

**Impact**: Stops data collection immediately (CSV still readable).  
**Safe**: Can click while data collection active.

---

## Main Dashboard Layout

Three-column layout with header bar.

### Header Bar

**Title**: "CURRENT EFFICIENCY"  
**Value**: Latest RLE value (e.g., "0.0492")

**Color Coding**:
- **Green** (0.2-1.0): Good efficiency
- **Yellow** (0.1-0.2): Reduced efficiency
- **Red** (<0.1): Poor efficiency

**File Info**: 
- **File**: Current CSV filename (`rle_YYYYMMDD_HH.csv`)
- **Size**: File size in KB
- **Age**: Seconds since last write (0s = actively collecting)
- **Samples**: Total rows in current file

**Note**: New CSV created **hourly** (timestamp `_HH` increments). Previous hour's file remains on disk.

---

### Column 1: Live Gauge & System Status

#### 📊 Live Gauge

**Circular Gauge**: 0.0 to 1.0 scale

**Meaning**: Current RLE efficiency as analog gauge.

- **0.0**: No efficiency (idle or thermal shutdown)
- **0.5**: 50% efficiency (normal under load)
- **1.0**: Maximum efficiency (optimal conditions)

**Color**: Matches header value (green/yellow/red gradient).

---

#### 🔢 System Status

**Metrics**:

1. **Temperature**: 38.0°C
   - **Source**: HWiNFO (CPU), NVML (GPU), or synthetic fallback
   - **Range**: 30-90°C typical
   - **Interpretation**: Higher = more thermal stress

2. **Power**: 36.5W
   - **Source**: NVML (GPU), HWiNFO (CPU package), or utilization estimate
   - **Range**: 1-300W typical
   - **Interpretation**: Higher = more active computation

3. **Utilization**: 9.1%
   - **Source**: NVML (GPU), psutil (CPU)
   - **Range**: 0-100%
   - **Interpretation**: Percent of device actively processing

4. **Sustain Time**: 600.0s
   - **Meaning**: How long current power level has been maintained
   - **Range**: 0-600s (maximum 10 minutes)
   - **Interpretation**: Higher = stable load, lower = fluctuating power

---

#### ⚠️ System Status

**Indicator**: ● 🟢 STABLE

**States**:
- **🟢 STABLE**: No collapse events detected
- **🔴 COLLAPSE**: Efficiency instability detected

**Trigger**: RLE drops below 65% of rolling peak for 7+ consecutive seconds with evidence (temp spike, power spike, or high load).

---

### Column 2: Time Series

**Three Stacked Graphs**: Shared horizontal time axis

#### RLE Efficiency

**Y-axis**: 0 to 1.5 (varies based on data)  
**Color**: Blue line

**Meaning**: RLE values over time.

**Interpretation**:
- **Baseline 0.03-0.08**: Idle or low load
- **Spikes >0.5**: High efficiency periods
- **Flat line <0.05**: Sustained low efficiency (thermal stress)

---

#### Temperature & Power

**Y-axis**: 0 to 80 (dual scale)  
**Colors**: Red (temperature), Green (power)

**Meaning**: Simultaneous display of thermal and power metrics.

**Interpretation**:
- **Correlation**: Power spikes → temperature rises after delay
- **Decay**: Temperature lags power (thermal mass effect)
- **Gap**: Large gap between power/temp = thermal throttling

---

#### Utilization

**Y-axis**: 0 to 40 (varies)  
**Color**: Orange line

**Meaning**: CPU/GPU workload intensity.

**Interpretation**:
- **0-10%**: Idle
- **10-50%**: Moderate load
- **50-100%**: Heavy load

**Shapes**:
- **Spikes**: Burst workloads
- **Flat high**: Sustained computation
- **Flat low**: Waiting/IO bound

---

### Column 3: Statistics & Distribution

#### 📉 Statistics

**Table**: Descriptive statistics for all numeric columns

**Columns**:
- **count**: Number of samples (rows)
- **mean**: Average value
- **std**: Standard deviation (spread)
- **min/max**: Lowest/highest values
- **25%/50%/75%**: Quartiles (median = 50%)

**Example**:
```
rle_smoothed: count=697, mean=0.052, std=0.045, min=0.008, max=0.134
```

**Interpretation**:
- **Large std**: High variability (unstable efficiency)
- **Small std**: Consistent efficiency
- **Outliers**: Check min/max for anomalies

---

#### 📊 Distribution

**Histogram**: Frequency of RLE values

**X-axis**: RLE value (0 to 1.0)  
**Y-axis**: Count (how many samples at each RLE level)

**Meaning**: Shows probability distribution of efficiency.

**Interpretation**:
- **Peak left (0-0.1)**: Most time spent at low efficiency
- **Peak middle (0.4-0.6)**: Balanced efficiency distribution
- **Peak right (>0.8)**: Most time spent at high efficiency
- **Bimodal**: Two operating regimes (e.g., idle vs. load)

---

#### Collapse Events

**Text**: "0/697 (0.0%)"

**Meaning**: Number of collapse events vs. total samples.

**Interpretation**:
- **0%**: No efficiency instabilities detected
- **<1%**: Rare instabilities (normal under stress)
- **>5%**: Frequent instabilities (thermal issues)

**Formula**: `collapse_count / total_samples × 100`

---

#### 📥 Export CSV

**Button**: Download current filtered data as CSV

**Output**: Exports only visible device's data (cpu/gpu/both filter applied)  
**Use Case**: Post-session analysis in Excel/pandas

---

### Bottom Panel: Event Log

**Title**: "📋 Event Log"

**Content**: Pipe-separated alert messages from CSV `alerts` column

**Format**: `timestamp | alert_text | rle_value | temp | power`

**Current Display**: "No alerts in current session" (empty alerts column)

**Future**: Will show thermal warnings, power spikes, collapse events, etc.

---

## Reading the Metrics

### Example Scenario: CPU Burst Stress Test

**Observation**: Temperature spikes from 38°C to 63°C, RLE drops from 0.08 to 0.03

**Interpretation**:
1. **Burst started**: Utilization jumps to 75%
2. **Power surge**: 36W → 91W within 10 seconds
3. **Thermal lag**: Temperature rises slowly over 60 seconds
4. **Efficiency drop**: RLE decreases due to thermal stress penalty
5. **Recovery**: After burst, temperature decays, RLE returns to baseline

**Conclusion**: System handles burst loads but incurs efficiency penalty during thermal buildup.

---

### Example Scenario: Sustained Load

**Observation**: RLE steady at 0.12, temperature stable at 55°C, power constant at 65W

**Interpretation**:
1. **Thermal equilibrium**: Heat generation = heat dissipation
2. **Stable efficiency**: Constant RLE indicates no throttling
3. **Sustained performance**: Can maintain this load indefinitely

**Conclusion**: System thermal design adequate for sustained workload.

---

### Example Scenario: Collapse Event

**Observation**: RLE drops from 0.6 → 0.2 → 0.4 in 7 seconds

**Interpretation**:
1. **Efficiency cliff**: RLE drops below 65% of peak
2. **Thermal stress**: Temperature >75°C or power >90W
3. **Instability**: System oscillating between states
4. **Recovery**: RLE rebounds after thermal management intervenes

**Conclusion**: Thermal limits reached, but system recovers (not shutdown).

---

## Interpreting the Data

### Efficiency Ranges

| RLE Range | Meaning | Typical Load |
|-----------|---------|--------------|
| **>0.15** | Excellent | Near-ideal conditions, sustained load |
| **0.10-0.15** | Good | Normal operation under load |
| **0.05-0.10** | Fair | Idle/baseline, light load |
| **0.02-0.05** | Poor | Heavy throttling or idle thermal inefficiency |
| **<0.02** | Critical | Severe degradation or thermal shutdown approaching |

**Important**: RLE is **relative to load**. Idle systems typically show 0.03-0.05 RLE. **Only compare RLE values under similar workload conditions**.

---

### Thermal States

| Temperature | Power | Utilization | State |
|-------------|-------|-------------|-------|
| **<40°C** | <30W | <10% | **Idle** |
| **40-60°C** | 30-80W | 20-60% | **Active** |
| **60-80°C** | 80-120W | 60-100% | **Load** |
| **>80°C** | >120W | >90% | **Stress** |

---

### Power Efficiency

**Formula**: `RLE = (utilization × stability) / (load_factor × (1 + 1/thermal_constant))`

**Drivers**:
- **High utilization + high stability = high RLE**
- **Low temperature + short sustain time = high RLE**
- **High load factor = lower RLE**

**Trade-offs**:
- **More power** → **Higher output** but **Lower RLE** (efficiency penalty)
- **Cooler system** → **Higher RLE** but **Lower performance**

---

## Troubleshooting

### Problem: Temperature Shows "N/A"

**Cause**: HWiNFO CSV path incorrect or logging disabled

**Solution**:
1. Open HWiNFO → Sensors window
2. Enable CSV logging
3. Update "HWiNFO CSV Path" in sidebar
4. Restart monitor

---

### Problem: "No session data found"

**Cause**: Monitor not running or CSV file not created

**Solution**:
1. Click "▶️ START Monitor" in sidebar
2. Wait 10 seconds
3. Refresh browser

---

### Problem: Graph Shows Only Recent Data

**Cause**: New CSV file created (hourly rollover)

**Explanation**: Every hour, monitor creates new file (`rle_YYYYMMDD_01.csv`, `_02.csv`, etc.)

**Solution**: Old data still in previous hour's file. Current file starts fresh.

---

### Problem: Auto-Refresh Causes "Pulsing"

**Cause**: Dashboard reloads every 5 seconds

**Solution**: Uncheck "Auto-refresh (5s)" and manually refresh when needed

---

### Problem: Statistics Show "490" Instead of "3000"

**Cause**: Device filter active (showing only CPU or only GPU)

**Solution**: Select "both" in "Show Device" radio buttons to see all samples

---

## Quick Reference

**Start Monitoring**: Click "▶️ START Monitor"  
**View Live Data**: Enable "Auto-refresh (5s)"  
**Export Data**: Click "📥 Export CSV"  
**Switch Devices**: Use "Show Device" radio buttons  
**Adjust Rate**: Change "Sample Rate (Hz)" slider

---

## Safety & Best Practices

### Hardware Temperature Monitoring

**⚠️ WARNING**: During stress testing, monitor hardware temperatures closely to prevent thermal damage.

**Recommended Limits**:
- **CPU**: <85°C sustained, <95°C peak
- **GPU**: <83°C sustained, <90°C peak
- **VRAM**: <100°C sustained, <110°C peak

**Red Flags**:
- Temperature >90°C for >5 minutes
- Collapse events >10% of samples
- Power fluctuating wildly (thermal throttling)
- System instability or random shutdowns

**Actions**:
1. Reduce load immediately if temperatures exceed limits
2. Check fan speeds and airflow
3. Verify thermal paste and cooler contact
4. Allow full cooldown before next test

**Note**: The collapse detection algorithm is designed to flag efficiency instability, not thermal shutdown. Always monitor actual temperature readings when stress testing.

---

## Further Reading

- **RLE Formula**: `lab/docs/WHAT_IS_RLE.md`
- **Theory**: `lab/docs/TOPOLOGY_INVARIANT_CLAIM.md`
- **Validation**: `lab/docs/BURST_TEST_VALIDATION.md`
- **Analysis Tools**: `lab/README.md`

---

*Generated by: RLE Monitoring Lab*  
*Last Updated: 2025-10-31*

