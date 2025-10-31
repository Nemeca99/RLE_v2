import argparse, csv, os, time, statistics
from datetime import datetime
import psutil
import requests

# NVML (GPU) - Pre-load DLL first on Windows
NVML_OK = False
pynvml = None
nvmlInit = None
nvmlDeviceGetHandleByIndex = None
nvmlDeviceGetUtilizationRates = None
nvmlDeviceGetPowerUsage = None
nvmlDeviceGetTemperature = None
nvmlDeviceGetFanSpeed = None
nvmlDeviceGetComputeRunningProcesses = None

try:
    import pynvml
    NVML_OK = True
    
    # On Windows, force-load the DLL from System32 before any operations
    if os.name == 'nt':
        import ctypes
        system32_dll = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'nvml.dll')
        if os.path.exists(system32_dll):
            # Force load the DLL into memory
            ctypes.CDLL(system32_dll)
            print(f"[NVML] Force-loaded nvml.dll from System32")
            
            # Now initialize pynvml
            try:
                pynvml.nvmlInit()
            except Exception as e:
                print(f"[NVML] Initialization failed: {e}")
                NVML_OK = False
        else:
            print(f"[NVML] nvml.dll not found in System32")
    
    # Import all the functions we need
    from pynvml import (
        nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetUtilizationRates,
        nvmlDeviceGetPowerUsage, nvmlDeviceGetTemperature, nvmlDeviceGetFanSpeed,
        nvmlDeviceGetComputeRunningProcesses
    )
    
    # Constants for temperature sensors
    NVML_TEMPERATURE_GPU = 0  # core temp
    NVML_TEMPERATURE_MEMORY = 1  # memory junction
    
except Exception as e:
    NVML_OK = False
    print(f"NVML import failed: {e}")

# ----------------------------
# Config defaults (tweakable)
# ----------------------------
DEFAULTS = dict(
    rated_gpu_w = 200.0,   # 3060 Ti board power ballpark
    rated_cpu_w = 125.0,   # your sustained CPU power (PL1-ish)
    gpu_temp_limit = 83.0,
    vram_temp_limit = 90.0,
    cpu_temp_limit = 80.0,
    warmup_sec = 60,
    collapse_drop_frac = 0.70,
    collapse_sustain_sec = 5,
    load_gate_util_pct = 50.0,
    load_gate_a_load = 0.60,
    sample_hz = 1,
    smooth_n = 5,
    max_t_sustain = 600.0
)

# ----------------------------
# Utilities
# ----------------------------
class Rolling:
    def __init__(self, n):
        self.n = n
        self.buf = []

    def add(self, x):
        self.buf.append(x)
        if len(self.buf) > self.n:
            self.buf.pop(0)

    def last(self, k=1):
        return self.buf[-k:] if k>1 else (self.buf[-1] if self.buf else None)

    def mean(self, k=None):
        data = self.buf if k is None else self.last(k)
        return sum(data)/len(data) if data else 0.0

    def stdev(self, k=None):
        data = self.buf if k is None else self.last(k)
        if not data or len(data) < 2: return 0.0
        return statistics.pstdev(data)

def below_normal_priority():
    try:
        p = psutil.Process()
        if os.name == "nt":
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            p.nice(10)
    except Exception:
        pass

def now_iso():
    """Return ISO UTC timestamp from World Time API using system timezone, fallback to system time."""
    try:
        # Get time for America/Chicago (CDT/CST)
        tz_response = requests.get('http://worldtimeapi.org/api/timezone/America/Chicago', timeout=1.0)
        if tz_response.status_code == 200:
            data = tz_response.json()
            return data['datetime']  # Local time with offset
    except Exception:
        pass
    # Fallback to system local time
    return datetime.now().isoformat()

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def rotate_writer(base_dir, append_cols=None):
    ensure_dir(base_dir)
    current_key = None
    fh, writer = None, None
    def get():
        nonlocal current_key, fh, writer
        key = datetime.utcnow().strftime("%Y%m%d_%H")
        if key != current_key:
            if fh: fh.close()
            fname = os.path.join(base_dir, f"rle_{key}.csv")
            new_file = not os.path.exists(fname)
            fh = open(fname, "a", newline="", buffering=1)
            writer = csv.writer(fh)
            if new_file:
                header = ["timestamp","device","rle_smoothed","rle_raw","rle_norm","E_th","E_pw","temp_c","vram_temp_c",
                          "power_w","util_pct","a_load","t_sustain_s","fan_pct","rolling_peak","collapse","alerts",
                          "cpu_freq_ghz","cycles_per_joule"]
                if append_cols:
                    header.extend(append_cols)
                writer.writerow(header)
            current_key = key
        return writer
    return get

# ----------------------------
# HWiNFO CSV tail (optional)
# ----------------------------
class HwinfoCsvTail:
    """
    Lightweight CSV tailer. Expects HWiNFO to roll files or append rows with timestamps.
    You pass target column names you'd like; we try to map fuzzy names.
    """
    def __init__(self, path, target_cols=None):
        self.path = path
        self.last_pos = 0
        self.header = None
        self.col_index = {}
        self.target_cols = target_cols or []

    def _scan_header(self):
        try:
            with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
                head = f.readline()
                if not head: return False
                self.header = [h.strip() for h in head.strip().split(",")]
                # fuzzy map: lower no spaces
                canon = {h.lower().replace(" ", ""): i for i,h in enumerate(self.header)}
                self.col_index = {}
                for want in self.target_cols:
                    key = want.lower().replace(" ", "")
                    # best-effort: exact or contains
                    match = None
                    if key in canon:
                        match = canon[key]
                    else:
                        for k,i in canon.items():
                            if key in k:
                                match = i; break
                    if match is not None:
                        self.col_index[want] = match
                return True
        except Exception:
            return False

    def latest(self):
        if not self.path or not os.path.exists(self.path): return {}
        if self.header is None:
            if not self._scan_header(): return {}
        # read last non-empty line
        try:
            with open(self.path, "rb") as f:
                try:
                    f.seek(-4096, os.SEEK_END)
                except OSError:
                    f.seek(0)
                chunk = f.read().decode("utf-8", errors="ignore")
            lines = [ln for ln in chunk.strip().splitlines() if ln.strip()]
            if not lines: return {}
            last = lines[-1]
            parts = [p.strip() for p in last.split(",")]
            out = {}
            for want, idx in self.col_index.items():
                if idx < len(parts):
                    try:
                        out[want] = float(parts[idx])
                    except:
                        out[want] = None
            return out
        except Exception:
            return {}

# ----------------------------
# NVML helpers
# ----------------------------
class GpuNVML:
    def __init__(self):
        if not NVML_OK:
            raise RuntimeError("NVML not available")
        
        # Initialize NVML
        try:
            nvmlInit()
        except Exception as e:
            raise RuntimeError(f"Could not initialize NVML: {e}")
        
        self.handle = nvmlDeviceGetHandleByIndex(0)
        print("[GPU] NVML initialized successfully")

    def poll(self):
        h = self.handle
        util = nvmlDeviceGetUtilizationRates(h).gpu  # %
        power = nvmlDeviceGetPowerUsage(h) / 1000.0  # W
        temp_core = nvmlDeviceGetTemperature(h, NVML_TEMPERATURE_GPU)  # °C
        # Try memory/junction temp if supported
        vram_temp = None
        try:
            vram_temp = nvmlDeviceGetTemperature(h, NVML_TEMPERATURE_MEMORY)
        except Exception:
            vram_temp = None
        try:
            fan = nvmlDeviceGetFanSpeed(h)  # %
        except Exception:
            fan = 0
        return dict(util=util, power=power, temp_core=temp_core, temp_vram=vram_temp, fan=fan)

# ----------------------------
# RLE computation and normalization
# ----------------------------
def normalize_rle(rle, util, device_type="cpu"):
    """
    Normalize RLE to 0-1 range based on load level
    
    Args:
        rle: Raw RLE value
        util: Utilization percentage (0-100)
        device_type: "cpu" or "gpu"
    
    Returns:
        Normalized RLE (0.0 = baseline, 1.0 = optimal)
    """
    if device_type == "cpu":
        # Actual observed ranges: transient drops to ~0.005, idle ~0.05, sustained load up to ~0.16
        # Scale to expected operator range: transient drops stay >0.2, normal ~0.6, peak ~0.95
        min_raw = 0.005       # Transient minimum during load spikes (floor)
        normal_raw = 0.05     # Raw RLE at typical idle operation
        optimal_raw = 0.16    # Expanded headroom for high-efficiency load
        
        # Utilization-aware normalization: under load, transient drops are expected
        # Map [0.005, 0.05, 0.11] -> [0.2, 0.6, 0.9]
        # Higher floor (0.2) prevents collapse warnings on transient load spikes
        if rle < min_raw:
            # Extreme floor: transient spikes during heavy load transitions
            if util > 50:  # Under load, transient drops are expected
                normalized = 0.25  # Higher floor under load
            else:
                normalized = 0.2   # Standard floor at idle
        elif rle <= normal_raw:
            # Segment 1: 0.005 -> 0.2/0.25, 0.05 -> 0.6
            floor_val = 0.25 if util > 50 else 0.2
            scale_factor = (0.6 - floor_val) / (normal_raw - min_raw)
            normalized = floor_val + (rle - min_raw) * scale_factor
        else:
            # Segment 2: 0.05 -> 0.6, 0.16 -> 0.95 (more headroom, fewer 1.00 clips)
            scale_factor = (0.95 - 0.6) / (optimal_raw - normal_raw)
            normalized = 0.6 + (rle - normal_raw) * scale_factor
        
        # Clamp to [0.0, 1.0]
        normalized = max(0.0, min(1.0, normalized))
    else:  # gpu
        baseline_raw = 0.01
        optimal_raw = 0.15
        scale_factor = 0.8 / (optimal_raw - baseline_raw)
        normalized = 0.1 + (rle - baseline_raw) * scale_factor
        normalized = max(0.0, min(1.0, normalized))
    
    return normalized

def compute_t_sustain(temp_limit, temp_hist, dt, max_t=600.0):
    if len(temp_hist) < 2: return max_t
    dT = temp_hist[-1] - temp_hist[-2]
    dTdt = max(dT / max(dt, 1e-3), 1e-3)
    t_sustain = (temp_limit - temp_hist[-1]) / dTdt
    return max(min(t_sustain, max_t), 1.0)

def compute_rle(util_hist, temp_hist, q_in_w, a_load, temp_limit, dt, max_t=600.0):
    util = (util_hist[-1] / 100.0) if util_hist else 0.0
    stability = 1.0 / (1.0 + (statistics.pstdev(util_hist[-10:]) if len(util_hist) >= 5 else 0.0))
    t_sustain = compute_t_sustain(temp_limit, temp_hist, dt, max_t=max_t)
    denom = max(a_load, 1e-3) * (1.0 + 1.0 / t_sustain)
    # q_in_w is intentionally unused - available for future use
    rle = (util * stability) / denom
    
    # Split into thermal and power components for diagnosis
    E_th = stability / (1.0 + 1.0 / t_sustain)
    E_pw = util / max(a_load, 1e-3)
    
    return rle, t_sustain, E_th, E_pw

# ----------------------------
# Micro-scale addon (optional)
# ----------------------------
def compute_micro_scale_factor(enable, power_w, temp_hist, temp_c, sensor_temp_lsb_c, low_power_knee_w, dt_s):
    if not enable:
        return 1.0, 1.0, 1.0, 1.0
    import math
    k_B = 1.380649e-23
    T_c = temp_c if temp_c is not None else (temp_hist[-1] if temp_hist else 25.0)
    T_K = max(T_c + 273.15, 273.15)
    P = max(power_w or 0.0, 1e-6)
    dt = max(dt_s, 1e-3)
    energy_sample_J = P * dt
    quantum_scale_J = k_B * T_K
    N_q = energy_sample_J / max(quantum_scale_J, 1e-30)
    F_q = 1.0 - math.exp(-min(N_q, 50.0))
    # Rolling sigma_T: best-effort from history if available
    if temp_hist and len(temp_hist) >= 2:
        mu = sum(temp_hist)/len(temp_hist)
        tail = temp_hist[-5:] if len(temp_hist) >= 5 else temp_hist
        var = sum((x-mu)**2 for x in tail) / max(len(tail), 1)
        sigma_T = (var ** 0.5)
    else:
        sigma_T = 1e-6
    F_s = 1.0 / (1.0 + (sensor_temp_lsb_c / max(sigma_T, 1e-6))**2)
    F_p = P / (P + low_power_knee_w)
    F_mu = (F_q * F_s * F_p) ** (1.0/3.0)
    F_mu = max(1e-9, min(1.0, F_mu))
    return F_mu, F_q, F_s, F_p

# ----------------------------
# Monitor
# ----------------------------
def monitor(args):
    below_normal_priority()
    tick = 1.0 / max(1, int(args.sample_hz))
    append_cols = None
    if args.micro_scale and getattr(args, 'theta_clock', False):
        append_cols = [
            "F_mu","F_q","F_s","F_p","rle_raw_ms","rle_smoothed_ms","rle_norm_ms",
            "T0_s","theta_index","T_sustain_hat","theta_gap","Gamma","log_Gamma"
        ]
    elif args.micro_scale:
        append_cols = ["F_mu","F_q","F_s","F_p","rle_raw_ms","rle_smoothed_ms","rle_norm_ms"]
    elif getattr(args, 'theta_clock', False):
        append_cols = ["T0_s","theta_index","T_sustain_hat","theta_gap"]
    writer_get = rotate_writer("sessions/recent", append_cols=append_cols)

    # HWiNFO CSV tail (optional)
    hw_targets = [
        "GPU Memory Junction Temperature",  # vram temp
        "CPU Package Power",                # W
        "CPU Package",                      # temp C (sometimes named like this)
        "CPU (Tctl/Tdie)",                  # alt temp name
        "GPU Memory Usage"                  # optional VRAM used
    ]
    hw = HwinfoCsvTail(args.hwinfo_csv, target_cols=hw_targets) if args.hwinfo_csv else None

    gpu = None
    gpu_util_hist = None
    gpu_temp_hist = None
    rle_hist_gpu = Rolling(args.smooth_n)
    rle_hist_gpu_ms = Rolling(args.smooth_n) if args.micro_scale else None
    rle60_gpu = Rolling(60)
    gpu_peak = 0.0
    gpu_below_ctr = 0
    gpu_peak_val = 0.0  # For tracking rolling peak
    core_gpu = None
    
    if args.mode in ("gpu","both"):
        if not NVML_OK:
            raise RuntimeError("GPU mode requested but NVML not available.")
        gpu = GpuNVML()
        gpu_util_hist = Rolling(120)
        gpu_temp_hist = Rolling(120)
        if getattr(args, 'theta_clock', False):
            try:
                from lab.monitoring.rle_core import RLECore
            except Exception:
                from .rle_core import RLECore
            core_gpu = RLECore(rated_power_w=args.rated_gpu if hasattr(args, 'rated_gpu') else DEFAULTS['rated_gpu_w'],
                               temp_limit_c=args.gpu_temp_limit,
                               enable_micro_scale=args.micro_scale,
                               enable_theta_clock=True)

    cpu_util_hist = Rolling(120)
    cpu_temp_hist = Rolling(120)  # only filled if we get temps
    rle_hist_cpu = Rolling(args.smooth_n)
    rle_hist_cpu_ms = Rolling(args.smooth_n) if args.micro_scale else None
    rle60_cpu = Rolling(60)
    cpu_peak = 0.0
    cpu_below_ctr = 0
    core_cpu = None
    if getattr(args, 'theta_clock', False):
        try:
            from lab.monitoring.rle_core import RLECore
        except Exception:
            from .rle_core import RLECore
        core_cpu = RLECore(rated_power_w=args.rated_cpu if hasattr(args, 'rated_cpu') else DEFAULTS['rated_cpu_w'],
                           temp_limit_c=args.cpu_temp_limit,
                           enable_micro_scale=args.micro_scale,
                           enable_theta_clock=True)

    start = time.time()
    last_status_time = start
    last_loop_time = start

    while True:
        ts = now_iso()
        alerts = []
        tnow = time.time()
        dt_loop = max(tnow - last_loop_time, 1e-3)
        last_loop_time = tnow
        warm = (tnow - start) > args.warmup_sec

        # -------- GPU --------
        if gpu and gpu_util_hist and gpu_temp_hist and rle_hist_gpu:
            g = gpu.poll()
            g_util = g["util"] or 0.0
            g_power = g["power"] or 0.0
            g_temp = g["temp_core"] or 0.0
            g_vram_temp = g["temp_vram"]
            g_fan = g["fan"] or 0

            # If no VRAM temp from NVML, try HWiNFO CSV
            if g_vram_temp is None and hw:
                latest = hw.latest()
                v = latest.get("GPU Memory Junction Temperature")
                if v is not None: g_vram_temp = v

            gpu_util_hist.add(g_util)
            gpu_temp_hist.add(g_temp)
            a_load_gpu = (g_power / args.rated_gpu) if args.rated_gpu>0 else 0.0
            rle_raw_gpu, t_sus_gpu, e_th_gpu, e_pw_gpu = compute_rle(
                gpu_util_hist.buf, gpu_temp_hist.buf, g_power, a_load_gpu, args.gpu_temp_limit, tick, DEFAULTS['max_t_sustain']
            )
            rle_hist_gpu.add(rle_raw_gpu)
            rle_sm_gpu = rle_hist_gpu.mean()
            
            # Normalize RLE to 0-1 range
            rle_norm_gpu = normalize_rle(rle_sm_gpu, g_util, device_type="gpu")
            rle60_gpu.add(rle_norm_gpu)

            # Improved collapse detection with rolling peak and hysteresis
            collapsed_gpu = 0
            gpu_peak_val = gpu_peak if warm else 0.0  # For logging
            if warm:
                # Rolling peak with decay (0.998 = 3% drop per 10s at 1Hz)
                gpu_peak = max(rle_sm_gpu, gpu_peak * 0.998)
                gpu_peak_val = gpu_peak  # For logging
                
                # Smart gate: require real load AND heating
                under_load = (g_util > 60) or (a_load_gpu > 0.75)
                heating = (len(gpu_temp_hist.buf) >= 2) and (gpu_temp_hist.buf[-1] - gpu_temp_hist.buf[-2] > 0.05)
                gate = under_load and heating
                
                # Two-stage hysteresis with recovery
                drop = rle_sm_gpu < 0.65 * gpu_peak
                if gate and drop:
                    gpu_below_ctr += 1
                else:
                    gpu_below_ctr = 0
                
                collapsed_flag = gpu_below_ctr >= 7
                
                # Require thermal or power evidence
                thermal_evidence = (t_sus_gpu < 60) or (g_temp > (args.gpu_temp_limit - 5))
                # TODO: track NVML perf cap reasons if available
                # For now, power-capped is inferred from a_load near 1.0
                power_capped = (a_load_gpu > 0.95)
                
                collapsed_gpu = 1 if (collapsed_flag and (thermal_evidence or power_capped)) else 0

            # Safety alerts (log-only)
            if g_temp >= args.gpu_temp_limit:
                alerts.append("GPU_TEMP_LIMIT")
            if g_vram_temp is not None and g_vram_temp >= args.vram_temp_limit:
                alerts.append("VRAM_TEMP_LIMIT")
            if a_load_gpu > 1.10:
                alerts.append("GPU_A_LOAD>1.10")

            F_mu_g, F_q_g, F_s_g, F_p_g = compute_micro_scale_factor(
                args.micro_scale, g_power, gpu_temp_hist.buf, g_temp, args.sensor_lsb, args.power_knee, tick)
            rle_raw_gpu_ms = (rle_raw_gpu * F_mu_g) if args.micro_scale else rle_raw_gpu
            rle_sm_gpu_ms = rle_sm_gpu if args.micro_scale else rle_sm_gpu
            rle_norm_gpu_ms = rle_norm_gpu if args.micro_scale else rle_norm_gpu

            base_row = [ts,"gpu",f"{rle_sm_gpu:.6f}",f"{rle_raw_gpu:.6f}",f"{rle_norm_gpu:.6f}",
                        f"{e_th_gpu:.6f}", f"{e_pw_gpu:.6f}", f"{g_temp:.2f}", f"{'' if g_vram_temp is None else f'{g_vram_temp:.2f}'}",
                        f"{g_power:.2f}", f"{g_util:.2f}", f"{a_load_gpu:.3f}",
                        f"{t_sus_gpu:.1f}", f"{g_fan}", f"{gpu_peak_val:.6f}", collapsed_gpu, "|".join(alerts)]
            if args.micro_scale:
                base_row.extend([
                    f"{F_mu_g:.6f}", f"{F_q_g:.6f}", f"{F_s_g:.6f}", f"{F_p_g:.6f}",
                    f"{rle_raw_gpu_ms:.6f}", f"{rle_sm_gpu_ms:.6f}", f"{rle_norm_gpu_ms:.6f}"
                ])
            # Theta clock fields
            if core_gpu is not None:
                res_gpu = core_gpu.compute_rle(g_util, g_temp, g_power, dt_loop)
                base_row.extend([
                    f"{res_gpu.T0_s:.3f}", f"{res_gpu.theta_index:.6f}", f"{res_gpu.T_sustain_hat:.6f}", f"{res_gpu.theta_gap}"
                ])
                if args.micro_scale:
                    base_row.extend([f"{res_gpu.Gamma:.6f}", f"{res_gpu.log_Gamma:.6f}"])
            w = writer_get()
            w.writerow(base_row)

        # -------- CPU --------
        if args.mode in ("cpu","both"):
            c_util = psutil.cpu_percent(interval=None)
            
            # Get CPU frequency (MHz -> GHz)
            try:
                freq_obj = psutil.cpu_freq()
                c_freq_mhz = freq_obj.current if freq_obj else None
                c_freq_ghz = (c_freq_mhz / 1000.0) if c_freq_mhz else None
            except:
                c_freq_ghz = None
            
            c_power = None
            c_temp = None
            if hw:
                latest = hw.latest()
                pw = latest.get("CPU Package Power")
                if pw is not None: c_power = pw
                # Try temps in likely fields
                for key in ("CPU Package","CPU (Tctl/Tdie)"):
                    tv = latest.get(key)
                    if tv is not None:
                        c_temp = tv
                        break

            cpu_util_hist.add(c_util)
            if c_temp is not None: cpu_temp_hist.add(c_temp)
            # If we have no temp history, synthesize a flat line to keep math stable
            temp_hist = cpu_temp_hist.buf if cpu_temp_hist.buf else [40.0, 40.0]

            # Fallback: estimate CPU power from utilization if no sensor available
            if c_power is None:
                # Rough estimate: assume CPU power scales with utilization
                # Typical CPU: 20-30W idle, 100-125W at full load for desktop
                c_power = args.rated_cpu * (c_util / 100.0) if args.rated_cpu > 0 else c_util * 1.5
            
            # Calculate clock cycles per joule (GHz * seconds per sample / joules)
            # cycles_per_joule = (GHz * sample_time_sec) / joules
            sample_time_sec = tick
            cycles_per_joule = None
            if c_freq_ghz and c_power and c_power > 0:
                clock_cycles_per_sample = c_freq_ghz * 1e9 * sample_time_sec  # cycles
                joules_per_sample = c_power * sample_time_sec  # joules
                cycles_per_joule = clock_cycles_per_sample / joules_per_sample if joules_per_sample > 0 else None

            a_load_cpu = (c_power / args.rated_cpu) if args.rated_cpu > 0 else 0.0
            rle_raw_cpu, t_sus_cpu, e_th_cpu, e_pw_cpu = compute_rle(
                cpu_util_hist.buf, temp_hist, (c_power or 0.0), a_load_cpu,
                args.cpu_temp_limit, tick, DEFAULTS['max_t_sustain']
            )
            rle_hist_cpu.add(rle_raw_cpu)
            rle_sm_cpu = rle_hist_cpu.mean()
            
            # Normalize RLE to 0-1 range
            rle_norm_cpu = normalize_rle(rle_sm_cpu, c_util, device_type="cpu")
            rle60_cpu.add(rle_norm_cpu)

            # Improved collapse detection with rolling peak and hysteresis
            collapsed_cpu = 0
            cpu_peak_val = cpu_peak if warm else 0.0  # For logging
            if warm:
                # Rolling peak with decay
                cpu_peak = max(rle_sm_cpu, cpu_peak * 0.998)
                cpu_peak_val = cpu_peak  # For logging
                
                # Smart gate: require real load AND heating
                under_load = (c_util > 60) or (a_load_cpu > 0.75)
                heating = (len(temp_hist) >= 2) and (temp_hist[-1] - temp_hist[-2] > 0.05)
                gate = under_load and heating
                
                # Two-stage hysteresis
                drop = rle_sm_cpu < 0.65 * cpu_peak
                if gate and drop:
                    cpu_below_ctr += 1
                else:
                    cpu_below_ctr = 0
                
                collapsed_flag = cpu_below_ctr >= 7
                
                # Require thermal or power evidence
                thermal_evidence = (t_sus_cpu < 60) or (c_temp is not None and c_temp > (args.cpu_temp_limit - 5))
                power_capped = (a_load_cpu > 0.95)
                
                collapsed_cpu = 1 if (collapsed_flag and (thermal_evidence or power_capped)) else 0

            alerts_cpu = []
            if c_temp is not None and c_temp >= args.cpu_temp_limit:
                alerts_cpu.append("CPU_TEMP_LIMIT")
            if a_load_cpu > 1.10:
                alerts_cpu.append("CPU_A_LOAD>1.10")

            F_mu_c, F_q_c, F_s_c, F_p_c = compute_micro_scale_factor(
                args.micro_scale, c_power, temp_hist, c_temp, args.sensor_lsb, args.power_knee, tick)
            rle_raw_cpu_ms = (rle_raw_cpu * F_mu_c) if args.micro_scale else rle_raw_cpu
            rle_sm_cpu_ms = rle_sm_cpu if args.micro_scale else rle_sm_cpu
            rle_norm_cpu_ms = rle_norm_cpu if args.micro_scale else rle_norm_cpu

            base_row = [ts,"cpu",f"{rle_sm_cpu:.6f}",f"{rle_raw_cpu:.6f}",f"{rle_norm_cpu:.6f}",
                        f"{e_th_cpu:.6f}", f"{e_pw_cpu:.6f}", f"{'' if c_temp is None else f'{c_temp:.2f}'}","",
                        f"{'' if c_power is None else f'{c_power:.2f}'}", f"{c_util:.2f}", f"{a_load_cpu:.3f}",
                        f"{t_sus_cpu:.1f}","", f"{cpu_peak_val:.6f}", collapsed_cpu, "|".join(alerts_cpu),
                        f"{'' if c_freq_ghz is None else f'{c_freq_ghz:.3f}'}", f"{'' if cycles_per_joule is None else f'{cycles_per_joule:.6e}'}"]
            if args.micro_scale:
                base_row.extend([
                    f"{F_mu_c:.6f}", f"{F_q_c:.6f}", f"{F_s_c:.6f}", f"{F_p_c:.6f}",
                    f"{rle_raw_cpu_ms:.6f}", f"{rle_sm_cpu_ms:.6f}", f"{rle_norm_cpu_ms:.6f}"
                ])
            # Theta clock fields
            if core_cpu is not None:
                res_cpu = core_cpu.compute_rle(c_util, c_temp if c_temp is not None else None, c_power if c_power is not None else None, dt_loop)
                base_row.extend([
                    f"{res_cpu.T0_s:.3f}", f"{res_cpu.theta_index:.6f}", f"{res_cpu.T_sustain_hat:.6f}", f"{res_cpu.theta_gap}"
                ])
                if args.micro_scale:
                    base_row.extend([f"{res_cpu.Gamma:.6f}", f"{res_cpu.log_Gamma:.6f}"])
            w = writer_get()
            w.writerow(base_row)

        # Status output every 5 seconds
        if tnow - last_status_time >= 5.0:
            status_parts = []
            if args.mode in ("gpu", "both") and gpu:
                if rle60_gpu.buf:
                    status_parts.append(
                        f"GPU_RLE: {rle_norm_gpu:.4f} (raw: {rle_sm_gpu:.4f}) | 60s mean {rle60_gpu.mean():.3f} min {min(rle60_gpu.buf):.3f} max {max(rle60_gpu.buf):.3f}"
                    )
                else:
                    status_parts.append(f"GPU_RLE: {rle_norm_gpu:.4f} (raw: {rle_sm_gpu:.4f})")
            if args.mode in ("cpu", "both"):
                if rle60_cpu.buf:
                    status_parts.append(
                        f"CPU_RLE: {rle_norm_cpu:.4f} (raw: {rle_sm_cpu:.4f}) | 60s mean {rle60_cpu.mean():.3f} min {min(rle60_cpu.buf):.3f} max {max(rle60_cpu.buf):.3f}"
                    )
                else:
                    status_parts.append(f"CPU_RLE: {rle_norm_cpu:.4f} (raw: {rle_sm_cpu:.4f})")
            if status_parts:
                print(f"[{ts}] {' | '.join(status_parts)}")
            last_status_time = tnow

        # Sleep
        time.sleep(tick)

# ----------------------------
# CLI
# ----------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Background RLE_real monitor")
    p.add_argument("--mode", choices=["gpu","cpu","both"], default="gpu")
    p.add_argument("--sample-hz", type=int, default=DEFAULTS['sample_hz'])
    p.add_argument("--rated-gpu", type=float, default=DEFAULTS['rated_gpu_w'])
    p.add_argument("--rated-cpu", type=float, default=DEFAULTS['rated_cpu_w'])
    p.add_argument("--gpu-temp-limit", type=float, default=DEFAULTS['gpu_temp_limit'])
    p.add_argument("--vram-temp-limit", type=float, default=DEFAULTS['vram_temp_limit'])
    p.add_argument("--cpu-temp-limit", type=float, default=DEFAULTS['cpu_temp_limit'])
    p.add_argument("--warmup-sec", type=int, default=DEFAULTS['warmup_sec'])
    p.add_argument("--collapse-drop-frac", type=float, default=DEFAULTS['collapse_drop_frac'])
    p.add_argument("--collapse-sustain-sec", type=int, default=DEFAULTS['collapse_sustain_sec'])
    p.add_argument("--load-gate-util-pct", type=float, default=DEFAULTS['load_gate_util_pct'])
    p.add_argument("--load-gate-a-load", type=float, default=DEFAULTS['load_gate_a_load'])
    p.add_argument("--smooth-n", type=int, default=DEFAULTS['smooth_n'])
    p.add_argument("--hwinfo-csv", type=str, default="", help="Optional HWiNFO CSV path for CPU power/temp or VRAM temp")
    p.add_argument("--micro-scale", action="store_true", default=False, help="Enable micro-scale correction (append *_ms columns)")
    p.add_argument("--sensor-lsb", type=float, default=0.1, help="Temperature sensor LSB (°C per tick) for micro-scale correction")
    p.add_argument("--power-knee", type=float, default=3.0, help="Low-power knee (W) for micro-scale correction")
    p.add_argument("--theta-clock", action="store_true", default=False, help="Append θ-clock fields (T0_s,theta_index,T_sustain_hat,theta_gap) to CSV")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    monitor(args)
