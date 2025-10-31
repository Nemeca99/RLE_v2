# RLE Monitoring Lab - Usage Guide

## 🚀 Quick Start

### Install Dependencies
```bash
pip install psutil nvidia-ml-py3 pandas streamlit plotly
```

### Option 1: Monitoring Only (Background)
```bash
cd lab
python start_monitor.py --mode gpu --sample-hz 1
```
- Runs silently in background
- Logs to `sessions/recent/rle_YYYYMMDD_HH.csv`
- Press Ctrl+C to stop

### Option 2: Full Suite (Monitor + Live Graphs)
```bash
cd lab
start_monitoring_suite.bat
```

**What happens:**
1. Opens terminal running the monitor daemon
2. Opens browser with Streamlit real-time dashboard
3. Both run simultaneously

**Dashboard shows:**
- Power consumption (W)
- Temperature (°C)
- RLE efficiency (smoothed)
- Rolling peak threshold
- Collapse events (red X markers)
- E_th / E_pw split components
- Raw data table

## 📊 Features

### Improved Collapse Detection
- **Rolling Peak**: Decays 0.2% per second (prevents false alarms)
- **Evidence Required**: Thermal OR power cap evidence needed
- **Hysteresis**: 65% drop sustained for 7+ seconds
- **Split Components**: E_th (thermal) vs E_pw (power) diagnostics

### Session Data
All CSV logs in `sessions/recent/` contain:
```
timestamp, device, rle_smoothed, rle_raw, E_th, E_pw,
temp_c, vram_temp_c, power_w, util_pct, a_load,
t_sustain_s, fan_pct, rolling_peak, collapse, alerts
```

## 🔧 Configuration

Edit `monitoring/hardware_monitor.py` defaults:
- `rated_gpu_w` = 200 (your GPU TDP)
- `gpu_temp_limit` = 83°C
- `vram_temp_limit` = 90°C
- `warmup_sec` = 60
- `collapse_drop_frac` = 0.65
- `collapse_sustain_sec` = 7

Or override via CLI:
```bash
python start_monitor.py --mode gpu --rated-gpu 220 --gpu-temp-limit 75
```

## 📈 Analysis

```bash
# Quick stats
python analyze_session.py sessions/recent/rle_20251027_04.csv

# Or use Python/pandas directly
>>> import pandas as pd
>>> df = pd.read_csv('lab/sessions/recent/rle_20251027_04.csv')
>>> df.describe()
```

## 🎮 During Gaming

1. Start monitor before launching game
2. Run your normal session
3. Stop monitor (Ctrl+C) when done
4. CSV auto-saves to `sessions/recent/`
5. Analyze later or view in Streamlit

## 🔍 What RLE Tells You

**High RLE (>0.5)**: System operating efficiently
- Good utilization
- Stable load
- Thermal headroom

**Low RLE (<0.2)**: Efficiency issues
- Thermal throttling (check E_th)
- Power limited (check E_pw)
- Load volatility

**Collapse Events**: True efficiency drops
- Only fires with thermal/power evidence
- 7+ second sustained condition
- Not scene-change noise

