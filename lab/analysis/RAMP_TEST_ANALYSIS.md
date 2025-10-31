# CPU Ramp Test Analysis Guide

After your 8-hour ramp test completes, follow these steps to extract the efficiency curve data.

## Step 1: Run Full Session Analysis

```bash
cd lab
python analyze_session.py sessions/recent/rle_YYYYMMDD_HH.csv
```

This gives you:
- Overall session duration
- Max/mean temps
- Mean/max RLE
- Collapse count and percentage
- a_load stats (power limiting)

## Step 2: Run Detailed Ramp Analysis

```bash
python analysis/analyze_ramp_test.py sessions/recent/rle_YYYYMMDD_HH.csv
```

This outputs:
- **Efficiency curve table** (RLE vs load step)
- **Collapse rate per load step** (validates detector)
- **Early vs Late comparison** (efficiency decay)
- **Sweet spot identification** (optimal load %)

The output will look like:

```
EFFICIENCY CURVE BY LOAD STEP
Load%      Mean RLE      Mean Temp    Mean Power    Collapse Rate   t_sustain  
----------------------------------------------------------------------
17         0.1234        45.2         12.5          0.0             600.0      
33         0.2345        52.3         25.1          0.0             450.0      
50         0.3456        58.4         37.8          5.0             280.0      
67         0.4123        62.1         50.2          12.0            120.0      
83         0.3567        68.9         62.8          45.0            45.0       
100        0.2890        74.2         75.5          78.0            25.0       

EFFICIENCY DECAY ANALYSIS (Early vs Late)
Load Step    Early RLE    Late RLE     Change       % Decay     
----------------------------------------------------------------------
17           0.1234       0.1234       0.0000       0.0%        
33           0.2345       0.2345       0.0000       0.0%        
50           0.3456       0.3420       -0.0036       -1.0%       
67           0.4123       0.3890       -0.0233      -5.7%       
83           0.3567       0.3120       -0.0447      -12.5%      
100          0.2890       0.2450       -0.0440      -15.2%      
```

## Step 3: Archive Baseline CSV

```bash
# Move to archive with descriptive name
mv sessions/recent/rle_YYYYMMDD_HH.csv sessions/archive/cpu_ramp_8h_baseline.csv
```

This becomes your reference dataset. Future changes (paste, fans, airflow, undervolt, etc.) can be compared against this baseline.

## What the Analysis Tells You

### A. Efficiency Sweet Spot
The load step with highest RLE is where your hardware is most efficient. Example: "Your CPU performs best at 67% load with RLE = 0.41"

### B. Collapse Detector Validation
- If collapses only appear at 83-100%: **Perfect** - detector working correctly
- If collapses appear at 50%: **Too sensitive** - adjust evidence gates
- If no collapses: **Too strict** - detector threshold too high

### C. Efficiency Decay
Compare early vs late RLE at the same load. This shows thermal aging within a session.

Example quotes:
- "At 67% load, RLE dropped from 0.412 to 0.389 after 7 hours (-5.7%)"
- "At 100% load, t_sustain dropped from 25s to 18s - you're hitting thermal limits faster"

### D. Thermal Recovery Speed
Check t_sustain trends. Longer recovery times indicate heat soak or poor airflow.

## Expected Results

Based on typical hardware:
- **Sweet spot**: 50-67% load (RLE peak)
- **Collapse starts**: 83-100% load (thermal/power limits)
- **Efficiency decay**: 5-15% over 8 hours at high loads
- **Low load stability**: <1% change (thermal headroom remains)

If your results differ significantly, review cooling, power delivery, or detector calibration.

