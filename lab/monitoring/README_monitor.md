# Background RLE Monitor

Lightweight GPU/CPU telemetry daemon that computes smoothed RLE_real efficiency scores and detects thermal-driven performance collapses during gameplay.

## Quick Setup

```bash
pip install psutil nvidia-ml-py3 pandas
```

## Usage

### Basic GPU monitoring (1 Hz sampling):
```bash
python hardware_monitor.py --mode gpu --sample-hz 1
```

### Both GPU + CPU (higher sampling rate):
```bash
python hardware_monitor.py --mode both --sample-hz 2 --rated-gpu 200 --rated-cpu 125
```

### With HWiNFO integration:
```bash
python hardware_monitor.py --mode both --sample-hz 2 --hwinfo-csv "C:\Sensors\HWiNFO64.csv"
```

### Tune your 3060 Ti defaults:
```bash
python hardware_monitor.py --mode gpu --rated-gpu 220 --gpu-temp-limit 78
```

## What Gets Logged

Hourly rotating CSVs in `logs/rle_YYYYMMDD_HH.csv`:
- `timestamp` - ISO UTC
- `device` - "gpu" or "cpu"
- `rle_smoothed` - Rolling average RLE_real
- `rle_raw` - Instantaneous RLE
- `temp_c` - Core temp (°C)
- `vram_temp_c` - VRAM/junction temp if available
- `power_w` - Power draw (W)
- `util_pct` - Utilization %
- `a_load` - Normalized load (Q_in / P_rated)
- `t_sustain_s` - Time until thermal limit (seconds)
- `fan_pct` - Fan speed (GPU only)
- `collapse` - Binary flag: sustained efficiency drop detected
- `alerts` - Pipe-separated safety warnings

## Event Tagging (Optional)

Run `tag_events.ahk` in background, then:
- **F9** - Mark teamfight
- **F10** - Mark objective
- **F11** - Mark death

Events saved to `logs/rle_events.csv` for later correlation with telemetry.

## Analysis Hints

After your session, look for:
- **Hysteresis loops**: Temp vs Power plots showing thermal inertia
- **Recovery constants**: Time to cool 63% after load drops
- **RLE degradation**: Peak RLE decreasing across similar scenes (heat saturation)
- **Collapse patterns**: Correlate with specific game events

## Safety Alerts

Logged when:
- GPU core ≥ 83°C for 5 ticks
- VRAM ≥ 90°C for 5 ticks
- CPU package ≥ 80°C for 5 ticks
- A_load > 1.10 sustained (>30s)

## Collapse Detection

Triggered when (after 60s warmup):
- GPU/CPU utilization > 50% OR A_load > 0.6
- Smoothed RLE < 70% of observed peak
- Condition persists for ≥5 consecutive seconds

Matches sustained thermal throttling / efficiency collapses.

