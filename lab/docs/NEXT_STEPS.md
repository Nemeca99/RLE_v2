# RLE Next Steps - Implementation Plan

Based on the 8-hour ramp test analysis, here's the roadmap for validating and expanding RLE.

## 1. Stress-Test for Collapse Detection

**Goal**: Capture real thermal collapses to validate RLE thresholds

**Protocol**:
- Run sustained 100% CPU load for 30 minutes
- Monitor for collapse flags (should appear after ~7s below rolling peak)
- Verify collapse correlates with thermal limits (temp > 80°C OR a_load > 0.95)
- Check that RLE drops predictably before collapse

**Test Script**: `lab/stress/max_sustained_load.py`
```bash
# 30-minute sustained load test
python stress/max_sustained_load.py --duration 30
python analysis/analyze_collapses.py sessions/recent/rle_*.csv
```

**Expected Results**:
- Collapses appear only at sustained high load
- RLE < 0.3 preceding collapse events
- Clear correlation between RLE drop and thermal evidence

## 2. RLE Normalization (0-1 Range)

**Goal**: Rescale RLE to always represent safe ↔ unstable states

**Current Issue**: RLE values vary by load level (0.4 at idle, 5.4 at 33% load)

**Proposed Solution**:
```python
# Normalize RLE based on load level
RLE_norm = (RLE - RLE_min) / (RLE_max - RLE_min)

Where:
- RLE_min = baseline RLE at minimal load
- RLE_max = peak RLE at optimal efficiency zone
```

**Implementation**: Add to `hardware_monitor.py`
```python
def normalize_rle(rle, util, device_type="cpu"):
    """Normalize RLE to 0-1 range based on load level"""
    if device_type == "cpu":
        baseline = 0.3  # RLE at idle
        optimal = 5.0   # Peak RLE at sweet spot
    else:  # GPU
        baseline = 0.1
        optimal = 3.0
    
    # Linear interpolation based on expected efficiency curve
    expected_rle = baseline + (optimal - baseline) * (util / 67.0)
    
    # Normalize: 1.0 = optimal, 0.0 = baseline
    return min(1.0, max(0.0, rle / expected_rle))
```

**Benefits**:
- Consistent interpretation (0.9 always means "very good")
- Easier decision-making (thresholds don't change)
- Can combine RLE from different hardware

## 3. Operating Envelope Visualization

**Goal**: Define "safe" operating zones in RLE-space

**Plots to Generate**:

### A. RLE vs Temperature
```python
# Map RLE to temperature bounds
plot_rle_temp_envelope(data):
    plt.scatter(data['temp_c'], data['rle_smoothed'])
    plt.xlabel('Temperature (°C)')
    plt.ylabel('RLE')
    
    # Annotate zones
    plt.axhline(y=5.0, color='green', linestyle='--', label='Optimal')
    plt.axhline(y=1.0, color='yellow', linestyle='--', label='Good')
    plt.axhline(y=0.3, color='red', linestyle='--', label='Warning')
```

### B. RLE vs Power
```python
# Show efficiency vs power draw
plot_rle_power_curve(data):
    plt.scatter(data['power_w'], data['rle_smoothed'])
    plt.xlabel('Power (W)')
    plt.ylabel('RLE')
    
    # Identify sweet spot
    sweet_spot_power = data.loc[data['rle_smoothed'].idxmax(), 'power_w']
    plt.axvline(x=sweet_spot_power, color='green', linestyle='--')
```

### C. Efficiency Map
```python
# 2D efficiency surface
plot_efficiency_map(data):
    from matplotlib import cm
    plt.scatter(data['util_pct'], data['power_w'], 
                c=data['rle_smoothed'], cmap='RdYlGn')
    plt.colorbar(label='RLE')
    plt.xlabel('Utilization (%)')
    plt.ylabel('Power (W)')
    plt.title('Efficiency Map: Optimal Zone = Bright Green')
```

**Analysis Tool**: `lab/analysis/plot_envelopes.py`
```bash
python analysis/plot_envelopes.py sessions/archive/cpu_ramp_8h.csv
# Generates:
# - rle_temp_envelope.png
# - rle_power_curve.png  
# - efficiency_map.png
```

## 4. GPU RLE Analysis

**Goal**: Apply RLE to GPU to validate generalizability

**Test Protocol**:
- GPU ramp test (same 8-hour protocol)
- Compare GPU vs CPU efficiency curves
- Identify GPU-specific optimal zones

**Expected**: GPU has different sweet spot (likely 60-75% load vs CPU's 33%)

**Analysis**:
```python
# Compare CPU vs GPU efficiency
compare_devices(data):
    cpu = data[data['device'] == 'cpu']
    gpu = data[data['device'] == 'gpu']
    
    plt.plot(cpu['util_pct'], cpu['rle_smoothed'], label='CPU')
    plt.plot(gpu['util_pct'], gpu['rle_smoothed'], label='GPU')
    plt.legend()
    plt.xlabel('Utilization (%)')
    plt.ylabel('RLE')
```

## 5. Multi-Device System RLE

**Goal**: Combined CPU+GPU system efficiency

**Formula**:
```python
RLE_sys = (RLE_cpu × P_cpu + RLE_gpu × P_gpu) / (P_cpu + P_gpu)

Weighted average by power contribution
```

**Visualization**: System heatmap
- X-axis: CPU utilization
- Y-axis: GPU utilization
- Color: System RLE
- Annotate efficiency zones

## 6. Real-Time Dashboard Enhancement

**Goal**: Add RLE-based alerts to Streamlit

**Features**:
- Live RLE gauge (0-1 normalized)
- Efficiency trend (up/down)
- Predicted time to thermal limit
- "Sweet spot" indicator
- Collapse event detection with audio alert

**Implementation**: Update `lab/monitoring/rle_streamlit.py`
```python
def render_rle_gauge(current_rle, optimal_rle=1.0):
    normalized = current_rle / optimal_rle
    
    if normalized > 0.8:
        st.success("✓ Optimal efficiency")
    elif normalized > 0.5:
        st.info("→ Good efficiency")
    elif normalized > 0.3:
        st.warning("⚠ Reduced efficiency")
    else:
        st.error("🚨 Inefficient/stressed - reduce load")
    
    st.progress(normalized)
```

## 7. Automated Reporting

**Goal**: Generate RLE reports after each session

**Output Format**: Markdown report with:
- Session overview (duration, mean RLE, load distribution)
- Efficiency curve by load step
- Degradation analysis (first vs last hour)
- Collapse events (if any)
- Recommendations (upgrade cooling, optimize load, etc.)

**Tool**: `lab/analysis/generate_rle_report.py`
```bash
python analysis/generate_rle_report.py sessions/recent/rle_*.csv
# Generates: RLE_REPORT_YYYYMMDD.md
```

## Priority Order

1. **Stress-test for collapses** (validate detector)
2. **Normalize RLE** (enable consistent thresholds)
3. **Visualize envelopes** (define safe zones)
4. **GPU analysis** (expand beyond CPU)
5. **Real-time alerts** (user-facing value)
6. **Automated reports** (operationalize insights)

## Success Metrics

✅ **Collapse detector**: <5% false positives, captures real thermal events
✅ **RLE normalization**: Values consistently 0-1 across all tests
✅ **Efficiency map**: Clear optimal zone identification
✅ **GPU validation**: Similar correlation patterns as CPU
✅ **Real-time dashboard**: Actionable insights during monitoring
✅ **Automated reports**: Consistent analysis across sessions

---
*Created: October 27, 2025*
*Based on: 8-hour CPU ramp test analysis*

