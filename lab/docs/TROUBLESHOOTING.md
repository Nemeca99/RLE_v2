# Troubleshooting RLE Monitoring

## Common Issues and Solutions

### Monitor Won't Start

**Symptoms**: `hardware_monitor.py` fails to initialize, typically with:
```
pynvml.NVMLError_LibraryNotFound: NVML Shared Library Not Found
```

**Root Cause**: The `nvidia-ml-py3` package uses a redirector that may fail to find `nvml.dll` on Windows, even when the DLL exists in System32.

**Solutions**:

```bash
# 1. Check if nvml.dll exists
dir C:\Windows\System32\nvml.dll

# 2. Uninstall conflicting packages and install standalone pynvml
pip uninstall nvidia-ml-py3 -y
pip install "pynvml==11.5.0"

# 3. Verify NVML initialization
python -c "import pynvml; pynvml.nvmlInit(); print('NVML OK')"

# 4. If step 3 fails, check nvidia-smi (driver installation)
nvidia-smi

# 5. Force DLL path (already implemented in hardware_monitor.py)
# The monitor auto-detects System32 DLL and loads it before initialization
```

**Key Fix**: The monitor now force-loads `nvml.dll` from `C:\Windows\System32` before calling `nvmlInit()`. This was added in Oct 2025 after discovering that redirector packages sometimes fail even when the DLL is present.

**Alternative**: If GPU monitoring fails, run monitor with `--mode cpu` for CPU-only monitoring.

### High False Positive Collapse Rate (>50%)

**Symptoms**: Session analysis shows 50-80% collapse rate

**Cause**: Using old session data (pre-v0.3.0) with simple 70% threshold detector

**Solutions**:
- Re-record session with updated monitor
- Ignore collapse flags in old CSVs
- Check `AGENTS.md` "Recent Changes" to identify detector version

### Streamlit Dashboard Not Updating

**Symptoms**: Dashboard shows old data or "No data available"

**Solutions**:
```python
# 1. Check CSV path in rle_streamlit.py (line ~30)
# Should point to: lab/sessions/recent/

# 2. Verify monitor is writing CSVs
ls lab/sessions/recent/rle_*.csv

# 3. Check file permissions
# Monitor needs write access to sessions/recent/

# 4. Verify monitor is running
# Check terminal for heartbeat messages
```

### Missing Columns in CSV

**Symptoms**: Analysis fails with "KeyError: 'E_th'" or similar

**Cause**: CSV from old monitor version (pre-v0.3.0)

**Columns Added in v0.3.0**:
- `E_th` - Thermal efficiency component
- `E_pw` - Power efficiency component  
- `rolling_peak` - Adaptive peak reference

**Solutions**:
- Re-record session with `hardware_monitor.py` v0.3.0+
- Or use legacy analysis script that doesn't require these columns
- Check `CHANGELOG.md` for version dates

### System Appears "Overstressed" But Temps Are Fine

**Symptoms**: High collapse rate but max temp < 80°C

**Possible Causes**:
1. Power limit throttling (check `a_load > 0.95`)
2. Old detector (see "High False Positive" above)
3. Thermal throttling from VRAM (check `vram_temp_c`)

**Solutions**:
```python
# Check power limiting
df = pd.read_csv('session.csv')
print(df[df['a_load'] > 0.95].shape[0], "samples power-limited")

# Check VRAM temps
if 'vram_temp_c' in df.columns:
    print("VRAM temp max:", df['vram_temp_c'].max())
```

### "Permission Denied" Writing CSV

**Symptoms**: Monitor crashes trying to write to `sessions/recent/`

**Solutions**:
```bash
# 1. Check directory exists
if not exist "lab\sessions\recent" mkdir lab\sessions\recent

# 2. Check write permissions (Windows)
icacls lab\sessions\recent

# 3. Run monitor as administrator if needed
# (Not recommended, fix permissions instead)
```

### Analysis Script Shows Wrong Session

**Symptoms**: `analyze_session.py` analyzes old/wrong CSV

**Solutions**:
```bash
# Explicitly specify file
python analyze_session.py sessions/recent/rle_20251027_04.csv

# Check what's in recent directory
ls lab/sessions/recent/

# Old sessions should be in archive/
mv lab/sessions/recent/rle_OLD.csv lab/sessions/archive/
```

### Validation Script Errors

**Symptoms**: `kia_validate.py` fails with encoding errors or crashes

**Solutions**:
```bash
# 1. Ensure Python 3.10+ (emojis need UTF-8)
python --version

# 2. Set UTF-8 encoding in terminal (Windows)
chcp 65001

# 3. Run without emojis (modify script temporarily)
# Search-replace "✅" with "[OK]" etc.

# 4. Check CSV exists
python kia_validate.py FULL_PATH_TO_CSV
```

### CPU Monitoring Not Working

**Symptoms**: Only GPU data appears (no CPU rows)

**Solutions**:
- Check HWiNFO CSV output is enabled (if using HWiNFO)
- Verify psutil can read CPU metrics: `python -c "import psutil; print(psutil.cpu_percent())"`
- Check monitor mode: `--mode cpu` vs `--mode both`
- CPU package temp requires motherboard sensor support (may be N/A)

### Streamlit Port Already in Use

**Symptoms**: "Address already in use" error when starting dashboard

**Solutions**:
```bash
# 1. Find and kill existing streamlit
taskkill /F /IM streamlit.exe

# 2. Use different port
streamlit run lab/monitoring/rle_streamlit.py --server.port 8502

# 3. Or modify start_monitoring_suite.bat
# Add: --server.port 8502
```

### CSV Files Growing Too Large

**Symptoms**: Individual CSV files > 50MB

**Solutions**:
- CSVs rotate hourly automatically (1Hz = ~3600 rows/hour)
- Archive old sessions regularly
- Compress archived CSVs: `gzip lab/sessions/archive/*.csv` (Linux)
- Or use 7-zip: `7z a archive.7z *.csv`

---

## Performance Issues

### Monitor Using Too Much CPU (>1%)

**Solutions**:
```python
# Reduce sampling rate
python start_monitor.py --mode gpu --sample-hz 0.5

# Check for heavy operations in loop
# Monitor should be lightweight (<100 LOC per tick)
```

### Analysis Takes Too Long

**Symptoms**: `analyze_session.py` takes >10 seconds for 1000-row session

**Solutions**:
```python
# Use sample data for testing
df = pd.read_csv('session.csv', nrows=100)

# Profile the analysis
python -m cProfile -o profile.stats analyze_session.py

# Check for unnecessary loops or operations
```

---

## Hardware-Specific Issues

### NVIDIA GPU Not Detected

**Symptoms**: `RuntimeError: NVML not available`

**Solutions**:
```bash
# 1. Check driver is installed
nvidia-smi

# 2. Install nvidia-ml-py3
pip install nvidia-ml-py3

# 3. Verify GPU is enabled (not disabled in BIOS)
# Check Device Manager -> Display Adapters

# 4. Try fallback
pip install pynvml  # Older but stable
```

### VRAM Temperature Not Available

**Symptoms**: `vram_temp_c` column is empty

**Cause**: Older GPUs (<2018) don't expose memory junction temp

**Solutions**:
- This is normal for older hardware
- Use `temp_c` (core temp) instead
- Upgrade GPU for VRAM monitoring (optional)

### HWiNFO CSV Tailing Fails

**Symptoms**: CPU power/temp always shows 0

**Solutions**:
```python
# 1. Check HWiNFO is logging to CSV
# Settings -> Logging -> CSV Export enabled

# 2. Verify file path in hardware_monitor.py
# Update hwinfo_path = "path/to/hwinfo.csv"

# 3. Check CSV format matches expected columns
# Should have: CPU Package Power, CPU Package, etc.

# 4. CPU package sensors need motherboard support
# May not be available on all systems
```

---

## Diagnostic Commands

```bash
# Check system health
python kia_validate.py sessions/recent/LATEST.csv

# Batch analyze all sessions
python scripts/batch_analyze.py sessions/recent/

# Quick session check
python -c "import pandas as pd; df=pd.read_csv('session.csv'); print(df.describe())"

# Find problematic sessions
python -c "import pandas as pd; import glob; [print(f.fname, df['collapse'].sum()/len(df)*100) for f in glob.glob('sessions/recent/*.csv')]"
```

---

## Getting Help

1. **Check `QUICK_REFERENCE.md`** for command cheat sheet
2. **Review `AGENTS.md`** for system constraints
3. **See `CHANGELOG.md`** for version history
4. **Examine `validation_logs/`** for detailed diagnostics

---

**Last Updated**: Session 2025-10-27  
**Agent**: Kia v1.0

