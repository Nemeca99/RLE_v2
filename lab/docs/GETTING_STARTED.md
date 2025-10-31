# Getting Started with RLE Monitoring

A quick walkthrough to get you up and running in 5 minutes.

## Prerequisites

- Windows 10/11
- Python 3.10 or later
- NVIDIA GPU with NVML support
- 5 minutes of your time

## Step 1: Install Dependencies

```bash
# Navigate to project
cd F:\RLE

# Install Python packages
pip install -r lab/requirements_lab.txt
```

**Expected output**:
```
Successfully installed psutil-5.x.x nvidia-ml-py3-12.x.x pandas-2.x.x streamlit-1.x.x
```

## Step 2: Verify Your System

```bash
# Check GPU is detected
python -c "import pynvml; pynvml.nvmlInit(); h = pynvml.nvmlDeviceGetHandleByIndex(0); print('GPU:', pynvml.nvmlDeviceGetName(h).decode())"
```

**Expected output**:
```
GPU: NVIDIA GeForce RTX 3060
```

If you see an error, check [Troubleshooting Guide](lab/docs/TROUBLESHOOTING.md).

## Step 3: Start Monitoring

### ⚡ One-Click Launch (Easiest)

**Just double-click `RUN_RLE.bat`** in the repo root!

This automatically:
- ✅ Checks Python installation
- ✅ Installs dependencies
- ✅ Starts the monitor
- ✅ Opens Streamlit dashboard in browser
- ✅ Shows where CSVs are being saved

**That's it!** No command line needed.

### 🔧 Manual Start (Alternative)

```bash
# Full suite
cd lab
start_monitoring_suite.bat

# Or monitor only
cd lab
python start_monitor.py --mode gpu --sample-hz 1
```

## Step 4: Generate Some Data

Now do one of:
- Play a game for 10 minutes
- Run a stress test: `python lab/stress/simple_stress.py`
- Use an existing workload

The monitor will log to: `lab/sessions/recent/rle_YYYYMMDD_HH.csv`

## Step 5: Analyze Your Session

### Quick Check

```bash
python lab/analyze_session.py
```

**Sample output**:
```
======================================================================
RLE Session Analysis: rle_20251027_04.csv
======================================================================

📅 Session Duration
   Start: 2025-10-27 04:33:22Z
   End:   2025-10-27 04:43:52Z
   Duration: 10.5 minutes (630 samples)

📈 RLE Efficiency
   Max smoothed:  1.0015
   Mean smoothed: 0.2456

💡 Health Assessment:
   ✅ Temperature: Good (below 80°C)
   ✅ Collapse rate: Very low (2.3%) - healthy operation
```

### Validate System Integrity

```bash
python kia_validate.py lab/sessions/recent/LATEST.csv
```

Generates report in `validation_logs/` with:
- Formula validation results
- Session statistics
- Health assessment

### View Real-time Dashboard

If you ran `start_monitoring_suite.bat`, the Streamlit dashboard should be open at:
```
http://localhost:8501
```

Shows:
- Live power/temperature graphs
- RLE efficiency over time
- Collapse events (red markers)
- Summary statistics

## Step 6: Interpret Results

### What Does RLE Mean?

**RLE** (Recursive Load Efficiency) measures how efficiently your hardware converts power into useful work while staying thermally sustainable.

- `RLE > 0.8`: Excellent - system running optimally
- `RLE 0.5-0.8`: Good - normal operation
- `RLE 0.2-0.5`: Moderate - may be power/thermal limited
- `RLE < 0.2`: Poor - system overstressed

### Understanding Collapse Events

**Collapse events** occur when:
1. RLE drops below 65% of recent peak
2. System is under load (util > 60% OR a_load > 0.75)
3. Temperature is rising (>0.05°C/s)
4. Evidence of thermal stress (t_sustain < 60s) OR power limiting (a_load > 0.95)

**Healthy systems** have collapse rate < 5%.

**High collapse rate (>15%)** suggests:
- Thermal throttling (improve cooling)
- Power limit reached (lower power target or load)
- Thermal mass effect (slow cooldown from previous stress)

### Interpreting Components

**E_th (Thermal Efficiency)**:
- How well you're managing thermal headroom
- Low = approaching temp limit
- High = plenty of thermal room

**E_pw (Power Efficiency)**:
- How effectively power is being utilized
- Low = hitting power limits
- High = underutilized or efficient

**t_sustain (Time to Limit)**:
- Seconds until thermal throttling
- <60s = Very close to limit
- >300s = Plenty of headroom

## Step 7: Optimization Strategies

Based on your results:

### If RLE is Low (< 0.5) and Collapse Rate High

**Thermal-Limited** (E_th low):
- Improve airflow
- Adjust fan curve
- Lower ambient temperature
- Undervolt (reduces power → less heat)

**Power-Limited** (E_pw low, a_load > 0.95):
- Increase power limit (MSI Afterburner)
- Reduce load (lower game settings)
- Or accept occasional power throttling (normal)

### If Collapse Rate is False High (>50%)

**Cause**: Using old detector (pre-v0.3.0)

**Fix**: Re-record session with updated monitor

### If System Runs Fine But RLE Low

**Cause**: Scene switching (normal for games)

**Fix**: This is expected - games load new assets, transition menus, etc.
- Low mean RLE is normal for bimodal load
- Check max RLE (should be > 0.8 during gameplay peaks)

## Example Workflows

### Workflow 1: First Session

```bash
# 1. Start monitoring
python lab\start_monitoring_suite.bat

# 2. Play for 15 minutes

# 3. Analyze results
python lab\analyze_session.py

# 4. Check health
# If collapse rate < 5%: ✅ System healthy
# If collapse rate > 15%: ⚠️ Check cooling
```

### Workflow 2: Optimization Test

```bash
# 1. Baseline measurement
python lab\start_monitor.py --mode gpu > baseline.csv

# 2. Run with new settings (e.g., different fan curve)

# 3. Compare sessions
python scripts/batch_analyze.py sessions/recent/

# 4. See which has better RLE and lower collapse rate
```

### Workflow 3: Validation

```bash
# After any monitoring session
python kia_validate.py sessions/recent/LATEST.csv

# Check validation_logs/kia_report_*.md
# Verify: 90%+ match rate = formula correct
# Verify: Collapse rate matches expectations
```

## Next Steps

1. **Read the docs**:
   - [Quick Reference](QUICK_REFERENCE.md) - Command cheat sheet
   - [What is RLE?](lab/docs/WHAT_IS_RLE.md) - Formula explained
   - [Architecture](lab/docs/ARCHITECTURE.md) - System overview
   - [Troubleshooting](lab/docs/TROUBLESHOOTING.md) - Common issues

2. **Customize your setup**:
   - Adjust sampling rate (--sample-hz)
   - Set custom temp limits
   - Add custom stress generators

3. **Analyze historical data**:
   - Move old sessions to `archive/`
   - Run batch analysis for trends
   - Compare different configurations

## Troubleshooting

If something doesn't work:

1. Check [Troubleshooting Guide](lab/docs/TROUBLESHOOTING.md)
2. Run diagnostics: `python kia_validate.py`
3. Check system: `nvidia-smi` and `python --version`
4. Review logs in `validation_logs/`

## Getting Help

- **Quick answers**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Technical details**: [lab/docs/](lab/docs/)
- **Agent guidance**: [AGENTS.md](AGENTS.md)
- **Version history**: [CHANGELOG.md](CHANGELOG.md)

---

**Last Updated**: Session 2025-10-27  
**Agent**: Kia v1.0

