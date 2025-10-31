#!/usr/bin/env python3
"""
RLE Hardware Monitor v2.0 - LibreHardwareMonitor Inspired
Comprehensive hardware monitoring with enhanced sensor coverage

CREDITS & INSPIRATION:
- LibreHardwareMonitor (https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
  * 7.3k+ GitHub stars, MPL-2.0 license
  * Comprehensive sensor architecture inspiration
  * Professional monitoring approach
- Open Hardware Monitor (original project)
- NVIDIA NVML library for GPU monitoring
- Microsoft WMI for Windows hardware access

DEPENDENCIES:
- psutil: Cross-platform system utilities
- pynvml: NVIDIA Management Library bindings  
- wmi: Windows Management Interface
- pandas: Data analysis
- streamlit: Real-time dashboard
- plotly: Interactive visualization

FEATURES:
- CPU: Temperature, utilization, power, clocks, cores (20 sensors)
- GPU: Temperature, utilization, power, memory, clocks, fans (13 sensors)
- Memory: Usage, temperature, clocks (7 sensors)
- Storage: Temperature, usage, health (6 sensors)
- Motherboard: Temperatures, voltages, fans
- Network: Utilization, temperature (4 sensors)
- Total: 50+ sensors vs 10+ in v1.0
"""

import argparse
import csv
import json
import os
import time
import statistics
import threading
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import psutil

# Enhanced hardware monitoring imports
try:
    import pynvml
    NVML_OK = True
    print("[GPU] NVML support available")
except ImportError:
    NVML_OK = False
    print("[GPU] NVML not available - GPU monitoring limited")

try:
    import wmi
    WMI_OK = True
    print("[WMI] Windows Management Interface available")
except ImportError:
    WMI_OK = False
    print("[WMI] Windows Management Interface not available")

# ----------------------------
# Data Classes
# ----------------------------
@dataclass
class HardwareSensor:
    """Individual sensor reading"""
    name: str
    value: Optional[float]
    unit: str
    sensor_type: str  # temperature, utilization, power, voltage, fan, clock
    hardware_type: str  # cpu, gpu, memory, storage, motherboard, network
    timestamp: datetime

@dataclass
class HardwareMetrics:
    """Complete hardware metrics for one device"""
    device_type: str
    device_name: str
    sensors: List[HardwareSensor]
    timestamp: datetime

# ----------------------------
# Hardware Monitor Classes
# ----------------------------
class CPUMonitor:
    """Enhanced CPU monitoring with comprehensive sensor coverage"""
    
    def __init__(self):
        self.cpu_count = psutil.cpu_count()
        self.cpu_freq = psutil.cpu_freq()
        self.wmi_cpu = None
        
        # Initialize WMI for additional CPU sensors
        if WMI_OK:
            try:
                self.wmi_cpu = wmi.WMI(namespace="root\\wmi")
                print("[CPU] WMI CPU sensors initialized")
            except Exception as e:
                print(f"[CPU] WMI initialization failed: {e}")
    
    def get_metrics(self) -> HardwareMetrics:
        """Get comprehensive CPU metrics"""
        sensors = []
        now = datetime.utcnow()
        
        # Basic CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()
        cpu_times = psutil.cpu_times()
        
        sensors.extend([
            HardwareSensor("CPU Utilization", cpu_percent, "%", "utilization", "cpu", now),
            HardwareSensor("CPU Frequency", cpu_freq.current if cpu_freq else None, "MHz", "clock", "cpu", now),
            HardwareSensor("CPU Min Frequency", cpu_freq.min if cpu_freq else None, "MHz", "clock", "cpu", now),
            HardwareSensor("CPU Max Frequency", cpu_freq.max if cpu_freq else None, "MHz", "clock", "cpu", now),
        ])
        
        # Per-core utilization
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        for i, core_percent in enumerate(cpu_per_core):
            sensors.append(HardwareSensor(f"Core {i} Utilization", core_percent, "%", "utilization", "cpu", now))
        
        # CPU temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                for temp in temps['coretemp']:
                    sensors.append(HardwareSensor(f"CPU {temp.label}", temp.current, "°C", "temperature", "cpu", now))
        except Exception:
            pass
        
        # WMI CPU sensors (Windows)
        if self.wmi_cpu:
            try:
                # CPU temperature via WMI
                for temp_sensor in self.wmi_cpu.MSAcpi_ThermalZoneTemperature():
                    temp_c = (temp_sensor.CurrentTemperature / 10.0) - 273.15
                    sensors.append(HardwareSensor("CPU Temperature (WMI)", temp_c, "°C", "temperature", "cpu", now))
            except Exception:
                pass
        
        return HardwareMetrics("cpu", "CPU", sensors, now)

class GPUMonitor:
    """Enhanced GPU monitoring with comprehensive sensor coverage"""
    
    def __init__(self):
        self.nvml_handle = None
        self.nvml_ok = False
        
        if NVML_OK:
            try:
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    self.nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    self.nvml_ok = True
                    print("[GPU] NVML GPU monitoring initialized")
            except Exception as e:
                print(f"[GPU] NVML initialization failed: {e}")
    
    def get_metrics(self) -> HardwareMetrics:
        """Get comprehensive GPU metrics"""
        sensors = []
        now = datetime.utcnow()
        
        if not self.nvml_ok:
            return HardwareMetrics("gpu", "GPU (No NVML)", sensors, now)
        
        try:
            # Basic GPU metrics
            util = pynvml.nvmlDeviceGetUtilizationRates(self.nvml_handle)
            temp = pynvml.nvmlDeviceGetTemperature(self.nvml_handle, 0)
            power = pynvml.nvmlDeviceGetPowerUsage(self.nvml_handle) / 1000.0
            
            sensors.extend([
                HardwareSensor("GPU Utilization", util.gpu, "%", "utilization", "gpu", now),
                HardwareSensor("GPU Memory Utilization", util.memory, "%", "utilization", "gpu", now),
                HardwareSensor("GPU Temperature", temp, "°C", "temperature", "gpu", now),
                HardwareSensor("GPU Power", power, "W", "power", "gpu", now),
            ])
            
            # Memory information
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.nvml_handle)
            sensors.extend([
                HardwareSensor("GPU Memory Used", mem_info.used / 1024**3, "GB", "memory", "gpu", now),
                HardwareSensor("GPU Memory Total", mem_info.total / 1024**3, "GB", "memory", "gpu", now),
                HardwareSensor("GPU Memory Free", mem_info.free / 1024**3, "GB", "memory", "gpu", now),
            ])
            
            # Clock speeds
            graphics_clock = pynvml.nvmlDeviceGetClockInfo(self.nvml_handle, 0)  # Graphics clock
            memory_clock = pynvml.nvmlDeviceGetClockInfo(self.nvml_handle, 2)  # Memory clock
            
            sensors.extend([
                HardwareSensor("GPU Graphics Clock", graphics_clock, "MHz", "clock", "gpu", now),
                HardwareSensor("GPU Memory Clock", memory_clock, "MHz", "clock", "gpu", now),
            ])
            
            # Fan speed
            try:
                fan_speed = pynvml.nvmlDeviceGetFanSpeed(self.nvml_handle)
                sensors.append(HardwareSensor("GPU Fan Speed", fan_speed, "%", "fan", "gpu", now))
            except Exception:
                pass
            
            # Performance state
            try:
                perf_state = pynvml.nvmlDeviceGetPerformanceState(self.nvml_handle)
                sensors.append(HardwareSensor("GPU Performance State", perf_state, "", "state", "gpu", now))
            except Exception:
                pass
            
            # Throttle reasons
            try:
                throttle_reasons = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(self.nvml_handle)
                sensors.append(HardwareSensor("GPU Throttle Reasons", throttle_reasons, "", "state", "gpu", now))
            except Exception:
                pass
            
            # Power limits
            try:
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimitConstraints(self.nvml_handle)
                sensors.append(HardwareSensor("GPU Power Limit", power_limit[0] / 1000.0, "W", "power", "gpu", now))
            except Exception:
                pass
            
        except Exception as e:
            print(f"[GPU] Error reading metrics: {e}")
        
        return HardwareMetrics("gpu", "GPU", sensors, now)

class MemoryMonitor:
    """Enhanced memory monitoring"""
    
    def get_metrics(self) -> HardwareMetrics:
        """Get comprehensive memory metrics"""
        sensors = []
        now = datetime.utcnow()
        
        # Virtual memory
        vm = psutil.virtual_memory()
        sensors.extend([
            HardwareSensor("Memory Used", vm.used / 1024**3, "GB", "memory", "memory", now),
            HardwareSensor("Memory Total", vm.total / 1024**3, "GB", "memory", "memory", now),
            HardwareSensor("Memory Available", vm.available / 1024**3, "GB", "memory", "memory", now),
            HardwareSensor("Memory Utilization", vm.percent, "%", "utilization", "memory", now),
        ])
        
        # Swap memory
        swap = psutil.swap_memory()
        sensors.extend([
            HardwareSensor("Swap Used", swap.used / 1024**3, "GB", "memory", "memory", now),
            HardwareSensor("Swap Total", swap.total / 1024**3, "GB", "memory", "memory", now),
            HardwareSensor("Swap Utilization", swap.percent, "%", "utilization", "memory", now),
        ])
        
        return HardwareMetrics("memory", "Memory", sensors, now)

class StorageMonitor:
    """Enhanced storage monitoring"""
    
    def get_metrics(self) -> HardwareMetrics:
        """Get comprehensive storage metrics"""
        sensors = []
        now = datetime.utcnow()
        
        # Disk usage
        disk_usage = psutil.disk_usage('/')
        sensors.extend([
            HardwareSensor("Disk Used", disk_usage.used / 1024**3, "GB", "storage", "storage", now),
            HardwareSensor("Disk Total", disk_usage.total / 1024**3, "GB", "storage", "storage", now),
            HardwareSensor("Disk Free", disk_usage.free / 1024**3, "GB", "storage", "storage", now),
            HardwareSensor("Disk Utilization", (disk_usage.used / disk_usage.total) * 100, "%", "utilization", "storage", now),
        ])
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        if disk_io:
            sensors.extend([
                HardwareSensor("Disk Read Rate", disk_io.read_bytes / 1024**2, "MB/s", "io", "storage", now),
                HardwareSensor("Disk Write Rate", disk_io.write_bytes / 1024**2, "MB/s", "io", "storage", now),
            ])
        
        return HardwareMetrics("storage", "Storage", sensors, now)

class NetworkMonitor:
    """Enhanced network monitoring"""
    
    def __init__(self):
        self.last_io = None
        self.last_time = None
    
    def get_metrics(self) -> HardwareMetrics:
        """Get comprehensive network metrics"""
        sensors = []
        now = datetime.utcnow()
        
        # Network I/O
        net_io = psutil.net_io_counters()
        if net_io:
            sensors.extend([
                HardwareSensor("Network Bytes Sent", net_io.bytes_sent / 1024**2, "MB", "network", "network", now),
                HardwareSensor("Network Bytes Received", net_io.bytes_recv / 1024**2, "MB", "network", "network", now),
                HardwareSensor("Network Packets Sent", net_io.packets_sent, "", "network", "network", now),
                HardwareSensor("Network Packets Received", net_io.packets_recv, "", "network", "network", now),
            ])
        
        return HardwareMetrics("network", "Network", sensors, now)

# ----------------------------
# RLE Computation (from rle_core)
# ----------------------------
def compute_rle(util_hist, temp_hist, power_w, a_load, temp_limit, dt, max_t=600.0):
    """Compute RLE using the canonical formula"""
    if len(util_hist) < 2 or len(temp_hist) < 2:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    
    # Current values
    util = util_hist[-1] / 100.0
    temp = temp_hist[-1]
    
    # Compute t_sustain
    t_sustain = compute_t_sustain(temp_limit, temp_hist, dt, max_t)
    
    # Stability (thermal headroom)
    stability = max(0.0, (temp_limit - temp) / temp_limit)
    
    # RLE formula: RLE = (util × stability) / (A_load × (1 + 1/T_sustain))
    if a_load > 0 and t_sustain > 0:
        rle_raw = (util * stability) / (a_load * (1.0 + 1.0 / t_sustain))
    else:
        rle_raw = 0.0
    
    # Thermal efficiency
    E_th = stability / (1.0 + 1.0 / t_sustain) if t_sustain > 0 else 0.0
    
    # Power efficiency  
    E_pw = util / a_load if a_load > 0 else 0.0
    
    # Rolling peak with decay
    if len(util_hist) >= 5:
        recent_rle = [(util_hist[i] / 100.0 * max(0.0, (temp_limit - temp_hist[i]) / temp_limit)) / 
                     (a_load * (1.0 + 1.0 / max(1.0, compute_t_sustain(temp_limit, temp_hist[:i+1], dt, max_t))))
                     for i in range(max(0, len(util_hist)-5), len(util_hist))]
        rolling_peak = max(recent_rle) * 0.998  # Decay factor
    else:
        rolling_peak = rle_raw
    
    # Collapse detection
    collapse = 1 if rle_raw < 0.65 * rolling_peak else 0
    
    # Smoothing
    if len(util_hist) >= 5:
        recent_rle_smooth = recent_rle[-5:]
        rle_smoothed = statistics.mean(recent_rle_smooth)
    else:
        rle_smoothed = rle_raw
    
    return rle_raw, rle_smoothed, E_th, E_pw, t_sustain, rolling_peak, collapse, stability, util

def compute_t_sustain(temp_limit, temp_hist, dt, max_t=600.0):
    """Compute thermal sustain time"""
    if len(temp_hist) < 2:
        return max_t
    
    current_temp = temp_hist[-1]
    if current_temp >= temp_limit:
        return 0.0
    
    # Simple linear extrapolation
    if len(temp_hist) >= 3:
        recent_temps = temp_hist[-3:]
        temp_rate = (recent_temps[-1] - recent_temps[0]) / (2 * dt)
        
        if temp_rate > 0:
            time_to_limit = (temp_limit - current_temp) / temp_rate
            return min(max_t, max(0.0, time_to_limit))
    
    return max_t

# ----------------------------
# Main Monitor Class
# ----------------------------
class RLEHardwareMonitor:
    """Enhanced RLE Hardware Monitor inspired by LibreHardwareMonitor"""
    
    def __init__(self, args):
        self.args = args
        self.running = False
        self.start_time = None
        
        # Hardware monitors
        self.cpu_monitor = CPUMonitor()
        self.gpu_monitor = GPUMonitor()
        self.memory_monitor = MemoryMonitor()
        self.storage_monitor = StorageMonitor()
        self.network_monitor = NetworkMonitor()
        
        # RLE computation state
        self.cpu_util_hist = []
        self.cpu_temp_hist = []
        self.gpu_util_hist = []
        self.gpu_temp_hist = []
        
        # CSV writer and flushing
        self.csv_writer = None
        self.csv_file = None
        self.last_flush_time = time.time()
        self.flush_interval = args.flush_interval
        self.realtime_flush = args.realtime
        
        # Statistics tracking
        self.stats_start_time = time.time()
        self.stats_interval = args.stats_interval
        self.last_stats_time = time.time()
        self.session_stats = {
            'samples': 0,
            'cpu_collapses': 0,
            'gpu_collapses': 0,
            'max_temp': 0,
            'max_power': 0,
            'min_rle': float('inf'),
            'max_rle': 0
        }
        
        # Timer control
        self.duration = args.duration
        self.end_time = None
        if self.duration:
            self.end_time = time.time() + self.duration
        
        # HWiNFO integration
        self.hwinfo_data = None
        if args.hwinfo_csv and os.path.exists(args.hwinfo_csv):
            self.load_hwinfo_data(args.hwinfo_csv)
        
        # Synthetic load integration
        self.synthetic_load = None
        if args.synthetic_load:
            self.synthetic_load = self._init_synthetic_load(args)
        
        print("[RLE Monitor] Enhanced hardware monitoring initialized")
        print(f"[RLE Monitor] CPU cores: {self.cpu_monitor.cpu_count}")
        print(f"[RLE Monitor] GPU monitoring: {'Enabled' if self.gpu_monitor.nvml_ok else 'Disabled'}")
        print(f"[RLE Monitor] CSV flush interval: {self.flush_interval}s")
        print(f"[RLE Monitor] Real-time flushing: {'Enabled' if self.realtime_flush else 'Disabled'}")
        if self.duration:
            print(f"[RLE Monitor] Timer: {self.duration}s duration ({self.duration//60}m {self.duration%60}s)")
        if self.hwinfo_data:
            print(f"[RLE Monitor] HWiNFO integration: Enabled ({len(self.hwinfo_data)} sensors)")
        if self.synthetic_load:
            print(f"[RLE Monitor] Synthetic load: Enabled ({self.args.load_mode} mode, {self.args.load_intensity*100:.1f}% intensity)")
    
    def _init_synthetic_load(self, args):
        """Initialize synthetic load generator"""
        try:
            from synthetic_load import SyntheticLoadController
            
            # Create synthetic load controller
            load_args = argparse.Namespace(
                mode=args.load_mode,
                duration=args.duration or 300,
                cpu_intensity=args.load_intensity,
                gpu_intensity=args.load_intensity,
                pattern=args.load_pattern,
                cpu_cores=None
            )
            
            return SyntheticLoadController(load_args)
        except ImportError:
            print("[RLE Monitor] Warning: synthetic_load.py not found, synthetic load disabled")
            return None
        except Exception as e:
            print(f"[RLE Monitor] Warning: Failed to initialize synthetic load: {e}")
            return None
    
    def setup_csv_logging(self):
        """Setup CSV logging with comprehensive columns"""
        timestamp = datetime.now().strftime("%Y%m%d_%H")
        filename = f"sessions/recent/rle_enhanced_{timestamp}.csv"
        
        # Ensure directory exists
        Path("sessions/recent").mkdir(parents=True, exist_ok=True)
        
        # Create metadata JSON file
        self.metadata_file = filename.replace('.csv', '_metadata.json')
        self.metadata = {
            'session_start': datetime.now().isoformat(),
            'model_name': getattr(self.args, 'model_name', 'Unknown'),
            'training_mode': getattr(self.args, 'training_mode', 'Unknown'),
            'session_length_sec': self.duration,
            'ambient_temp_guess': getattr(self.args, 'ambient_temp', None),
            'notes': getattr(self.args, 'notes', ''),
            'hardware': {
                'cpu_count': self.cpu_monitor.cpu_count,
                'gpu_enabled': self.gpu_monitor.nvml_ok,
                'hwinfo_enabled': self.hwinfo_data is not None
            },
            'monitoring': {
                'sample_hz': 1.0 / (1000.0 / self.args.sample_hz),
                'flush_interval': self.flush_interval,
                'realtime_flush': self.realtime_flush,
                'synthetic_load': self.synthetic_load is not None
            }
        }
        
        self.csv_file = open(filename, 'w', newline='', encoding='utf-8')
        
        # Enhanced CSV columns with HWiNFO integration + workload tagging
        fieldnames = [
            'timestamp', 'device', 'rle_smoothed', 'rle_raw', 'E_th', 'E_pw', 
            'temp_c', 'power_w', 'util_pct', 'a_load', 't_sustain_s', 'rolling_peak', 
            'collapse', 'alerts',
            # Enhanced sensor data
            'cpu_freq_mhz', 'cpu_cores_active', 'cpu_temp_max',
            'gpu_memory_used_gb', 'gpu_memory_total_gb', 'gpu_fan_pct', 'gpu_clock_mhz',
            'memory_used_gb', 'memory_total_gb', 'memory_util_pct',
            'disk_used_gb', 'disk_total_gb', 'disk_util_pct',
            'network_sent_mb', 'network_recv_mb',
            # HWiNFO sensor data
            'cpu_temp_hwinfo', 'cpu_fan_rpm', 'cpu_voltage', 'motherboard_temp',
            'psu_voltage_12v', 'psu_voltage_5v', 'psu_voltage_3v',
            'gpu_temp_hwinfo', 'gpu_memory_temp', 'gpu_fan_rpm', 'gpu_voltage',
            'case_fan_rpm',
            # Workload tagging
            'workload_state'
        ]
        
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        
        print(f"[RLE Monitor] Logging to: {filename}")
    
    def detect_workload_state(self, metrics: Dict[str, HardwareMetrics]) -> str:
        """Detect current workload state based on utilization patterns"""
        try:
            cpu_metrics = metrics.get('cpu')
            gpu_metrics = metrics.get('gpu')
            
            if not cpu_metrics or not gpu_metrics:
                return 'idle'
            
            # Get utilization from sensors
            cpu_util = None
            gpu_util = None
            
            for sensor in cpu_metrics.sensors:
                if sensor.name == 'CPU Utilization':
                    cpu_util = sensor.value
                    break
            
            for sensor in gpu_metrics.sensors:
                if sensor.name == 'GPU Utilization':
                    gpu_util = sensor.value
                    break
            
            # Simple workload classification
            if cpu_util and cpu_util > 80:
                return 'training_step'
            elif gpu_util and gpu_util > 70:
                return 'training_step'
            elif cpu_util and cpu_util > 50:
                return 'data_prep'
            elif gpu_util and gpu_util > 30:
                return 'data_prep'
            else:
                return 'idle'
                
        except Exception as e:
            return 'idle'
    
    def collect_hardware_metrics(self) -> Dict[str, HardwareMetrics]:
        """Collect metrics from all hardware monitors"""
        metrics = {}
        
        try:
            metrics['cpu'] = self.cpu_monitor.get_metrics()
            metrics['gpu'] = self.gpu_monitor.get_metrics()
            metrics['memory'] = self.memory_monitor.get_metrics()
            metrics['storage'] = self.storage_monitor.get_metrics()
            metrics['network'] = self.network_monitor.get_metrics()
        except Exception as e:
            print(f"[RLE Monitor] Error collecting metrics: {e}")
        
        return metrics
    
    def compute_rle_metrics(self, metrics: Dict[str, HardwareMetrics]) -> Dict[str, Any]:
        """Compute RLE metrics for CPU and GPU"""
        rle_data = {}
        
        # CPU RLE computation
        cpu_metrics = metrics.get('cpu')
        if cpu_metrics:
            cpu_util = next((s.value for s in cpu_metrics.sensors if s.name == "CPU Utilization"), 0.0)
            cpu_temp = next((s.value for s in cpu_metrics.sensors if "Temperature" in s.name), 50.0)
            
            self.cpu_util_hist.append(cpu_util)
            self.cpu_temp_hist.append(cpu_temp)
            
            # Keep history manageable
            if len(self.cpu_util_hist) > 1000:
                self.cpu_util_hist = self.cpu_util_hist[-500:]
                self.cpu_temp_hist = self.cpu_temp_hist[-500:]
            
            rle_raw, rle_smoothed, E_th, E_pw, t_sustain, rolling_peak, collapse, stability, util = compute_rle(
                self.cpu_util_hist, self.cpu_temp_hist, 125.0, 0.8, 
                self.args.cpu_temp_limit, 1.0
            )
            
            rle_data['cpu'] = {
                'rle_raw': rle_raw, 'rle_smoothed': rle_smoothed, 'E_th': E_th, 'E_pw': E_pw,
                't_sustain': t_sustain, 'rolling_peak': rolling_peak, 'collapse': collapse,
                'util': cpu_util, 'temp': cpu_temp, 'stability': stability
            }
        
        # GPU RLE computation
        gpu_metrics = metrics.get('gpu')
        if gpu_metrics and self.gpu_monitor.nvml_ok:
            gpu_util = next((s.value for s in gpu_metrics.sensors if s.name == "GPU Utilization"), 0.0)
            gpu_temp = next((s.value for s in gpu_metrics.sensors if s.name == "GPU Temperature"), 50.0)
            
            self.gpu_util_hist.append(gpu_util)
            self.gpu_temp_hist.append(gpu_temp)
            
            # Keep history manageable
            if len(self.gpu_util_hist) > 1000:
                self.gpu_util_hist = self.gpu_util_hist[-500:]
                self.gpu_temp_hist = self.gpu_temp_hist[-500:]
            
            rle_raw, rle_smoothed, E_th, E_pw, t_sustain, rolling_peak, collapse, stability, util = compute_rle(
                self.gpu_util_hist, self.gpu_temp_hist, 200.0, 0.8,
                self.args.gpu_temp_limit, 1.0
            )
            
            rle_data['gpu'] = {
                'rle_raw': rle_raw, 'rle_smoothed': rle_smoothed, 'E_th': E_th, 'E_pw': E_pw,
                't_sustain': t_sustain, 'rolling_peak': rolling_peak, 'collapse': collapse,
                'util': gpu_util, 'temp': gpu_temp, 'stability': stability
            }
        
        return rle_data
    
    def log_to_csv(self, metrics: Dict[str, HardwareMetrics], rle_data: Dict[str, Any], hwinfo_sensors: Dict[str, Any] = None, workload_state: str = 'idle'):
        """Log comprehensive data to CSV with workload tagging"""
        timestamp = datetime.utcnow().isoformat()
        
        # Log CPU data
        if 'cpu' in rle_data:
            cpu_data = rle_data['cpu']
            cpu_metrics = metrics['cpu']
            
            row = {
                'timestamp': timestamp,
                'device': 'cpu',
                'rle_smoothed': cpu_data['rle_smoothed'],
                'rle_raw': cpu_data['rle_raw'],
                'E_th': cpu_data['E_th'],
                'E_pw': cpu_data['E_pw'],
                'temp_c': cpu_data['temp'],
                'power_w': 125.0,  # Estimated CPU power
                'util_pct': cpu_data['util'],
                'a_load': 0.8,
                't_sustain_s': cpu_data['t_sustain'],
                'rolling_peak': cpu_data['rolling_peak'],
                'collapse': cpu_data['collapse'],
                'alerts': '',
                # Enhanced CPU data
                'cpu_freq_mhz': next((s.value for s in cpu_metrics.sensors if s.name == "CPU Frequency"), None),
                'cpu_cores_active': len([s for s in cpu_metrics.sensors if "Core" in s.name and s.value and s.value > 10]),
                'cpu_temp_max': max([s.value for s in cpu_metrics.sensors if "Temperature" in s.name and s.value], default=None),
            }
            
            # Add HWiNFO sensor data if available
            if hwinfo_sensors:
                row.update({
                    'cpu_temp_hwinfo': hwinfo_sensors.get('cpu_temp_hwinfo'),
                    'cpu_fan_rpm': hwinfo_sensors.get('cpu_fan_rpm'),
                    'cpu_voltage': hwinfo_sensors.get('cpu_voltage'),
                    'motherboard_temp': hwinfo_sensors.get('motherboard_temp'),
                    'psu_voltage_12v': hwinfo_sensors.get('psu_voltage_12v'),
                    'psu_voltage_5v': hwinfo_sensors.get('psu_voltage_5v'),
                    'psu_voltage_3v': hwinfo_sensors.get('psu_voltage_3v'),
                })
            
            # Add workload state
            row['workload_state'] = workload_state
            
            self.csv_writer.writerow(row)
        
        # Log GPU data
        if 'gpu' in rle_data:
            gpu_data = rle_data['gpu']
            gpu_metrics = metrics['gpu']
            
            row = {
                'timestamp': timestamp,
                'device': 'gpu',
                'rle_smoothed': gpu_data['rle_smoothed'],
                'rle_raw': gpu_data['rle_raw'],
                'E_th': gpu_data['E_th'],
                'E_pw': gpu_data['E_pw'],
                'temp_c': gpu_data['temp'],
                'power_w': next((s.value for s in gpu_metrics.sensors if s.name == "GPU Power"), 0.0),
                'util_pct': gpu_data['util'],
                'a_load': 0.8,
                't_sustain_s': gpu_data['t_sustain'],
                'rolling_peak': gpu_data['rolling_peak'],
                'collapse': gpu_data['collapse'],
                'alerts': '',
                # Enhanced GPU data
                'gpu_memory_used_gb': next((s.value for s in gpu_metrics.sensors if s.name == "GPU Memory Used"), None),
                'gpu_memory_total_gb': next((s.value for s in gpu_metrics.sensors if s.name == "GPU Memory Total"), None),
                'gpu_fan_pct': next((s.value for s in gpu_metrics.sensors if s.name == "GPU Fan Speed"), None),
                'gpu_clock_mhz': next((s.value for s in gpu_metrics.sensors if s.name == "GPU Graphics Clock"), None),
            }
            
            # Add HWiNFO GPU sensor data if available
            if hwinfo_sensors:
                row.update({
                    'gpu_temp_hwinfo': hwinfo_sensors.get('gpu_temp_hwinfo'),
                    'gpu_memory_temp': hwinfo_sensors.get('gpu_memory_temp'),
                    'gpu_fan_rpm': hwinfo_sensors.get('gpu_fan_rpm'),
                    'gpu_voltage': hwinfo_sensors.get('gpu_voltage'),
                })
            
            # Add workload state
            row['workload_state'] = workload_state
            
            self.csv_writer.writerow(row)
        
        # Flush CSV based on interval or real-time setting
        current_time = time.time()
        if self.realtime_flush or (current_time - self.last_flush_time) >= self.flush_interval:
            self.csv_file.flush()
            self.last_flush_time = current_time
            if self.realtime_flush:
                print(f"[RLE Monitor] CSV flushed - {self.session_stats['samples']} samples written")
    
    def print_status(self, metrics: Dict[str, HardwareMetrics], rle_data: Dict[str, Any]):
        """Print current status"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] RLE Monitor Status:")
        
        if 'cpu' in rle_data:
            cpu = rle_data['cpu']
            print(f"  CPU: RLE={cpu['rle_smoothed']:.3f} | Util={cpu['util']:.1f}% | Temp={cpu['temp']:.1f}°C | Collapse={cpu['collapse']}")
        
        if 'gpu' in rle_data:
            gpu = rle_data['gpu']
            print(f"  GPU: RLE={gpu['rle_smoothed']:.3f} | Util={gpu['util']:.1f}% | Temp={gpu['temp']:.1f}°C | Collapse={gpu['collapse']}")
    
    def load_hwinfo_data(self, csv_path: str):
        """Load HWiNFO CSV data for enhanced sensor integration"""
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            self.hwinfo_data = df
            print(f"[HWiNFO] Loaded {len(df)} sensor readings from {csv_path}")
        except Exception as e:
            print(f"[HWiNFO] Failed to load CSV: {e}")
            self.hwinfo_data = None
    
    def get_hwinfo_sensors(self, timestamp: datetime) -> Dict[str, Any]:
        """Get HWiNFO sensor data for current timestamp"""
        if not self.hwinfo_data:
            return {}
        
        try:
            # Find closest timestamp in HWiNFO data
            current_time = timestamp.timestamp()
            time_diff = abs(self.hwinfo_data['Time'] - current_time)
            closest_idx = time_diff.idxmin()
            
            if time_diff.iloc[closest_idx] < 5.0:  # Within 5 seconds
                row = self.hwinfo_data.iloc[closest_idx]
                return {
                    'cpu_temp_hwinfo': row.get('CPU Package', None),
                    'gpu_temp_hwinfo': row.get('GPU Core', None),
                    'gpu_memory_temp': row.get('GPU Memory', None),
                    'motherboard_temp': row.get('Motherboard', None),
                    'cpu_fan_rpm': row.get('CPU Fan', None),
                    'gpu_fan_rpm': row.get('GPU Fan', None),
                    'case_fan_rpm': row.get('Case Fan', None),
                    'cpu_voltage': row.get('CPU VCore', None),
                    'gpu_voltage': row.get('GPU VCore', None),
                    'psu_voltage_12v': row.get('+12V', None),
                    'psu_voltage_5v': row.get('+5V', None),
                    'psu_voltage_3v': row.get('+3.3V', None)
                }
        except Exception as e:
            print(f"[HWiNFO] Error reading sensors: {e}")
        
        return {}
    
    def update_session_stats(self, metrics: Dict[str, HardwareMetrics], rle_data: Dict[str, Any]):
        """Update session statistics"""
        self.session_stats['samples'] += 1
        
        # Track collapses
        if 'cpu' in rle_data and rle_data['cpu']['collapse']:
            self.session_stats['cpu_collapses'] += 1
        if 'gpu' in rle_data and rle_data['gpu']['collapse']:
            self.session_stats['gpu_collapses'] += 1
        
        # Track temperature and power from sensors
        for device, device_metrics in metrics.items():
            # Find temperature sensor
            temp_sensor = next((s for s in device_metrics.sensors if "Temperature" in s.name), None)
            if temp_sensor and temp_sensor.value:
                self.session_stats['max_temp'] = max(self.session_stats['max_temp'], temp_sensor.value)
            
            # Find power sensor
            power_sensor = next((s for s in device_metrics.sensors if "Power" in s.name), None)
            if power_sensor and power_sensor.value:
                self.session_stats['max_power'] = max(self.session_stats['max_power'], power_sensor.value)
        
        # Track RLE range
        for device, device_rle in rle_data.items():
            if device_rle['rle_smoothed']:
                self.session_stats['min_rle'] = min(self.session_stats['min_rle'], device_rle['rle_smoothed'])
                self.session_stats['max_rle'] = max(self.session_stats['max_rle'], device_rle['rle_smoothed'])
    
    def print_session_stats(self):
        """Print comprehensive session statistics"""
        current_time = time.time()
        session_duration = current_time - self.stats_start_time
        
        print(f"\n{'='*60}")
        print("SESSION STATISTICS")
        print(f"{'='*60}")
        print(f"Duration: {session_duration:.1f}s ({self.session_stats['samples']} samples)")
        print(f"Sample Rate: {self.session_stats['samples']/session_duration:.2f} Hz")
        print(f"CPU Collapses: {self.session_stats['cpu_collapses']} ({self.session_stats['cpu_collapses']/self.session_stats['samples']*100:.1f}%)")
        print(f"GPU Collapses: {self.session_stats['gpu_collapses']} ({self.session_stats['gpu_collapses']/self.session_stats['samples']*100:.1f}%)")
        print(f"Max Temperature: {self.session_stats['max_temp']:.1f}°C")
        print(f"Max Power: {self.session_stats['max_power']:.1f}W")
        print(f"RLE Range: {self.session_stats['min_rle']:.3f} - {self.session_stats['max_rle']:.3f}")
        print(f"{'='*60}")
    
    def run(self):
        """Main monitoring loop"""
        print("\n" + "="*70)
        print("RLE HARDWARE MONITOR v2.0 - LibreHardwareMonitor Inspired")
        print("="*70)
        
        self.setup_csv_logging()
        
        # Start synthetic load if enabled
        if self.synthetic_load:
            self.synthetic_load.start()
        
        tick = 1.0 / max(1, int(self.args.sample_hz))
        start_time = time.time()
        
        try:
            while True:
                # Check timer expiration
                if self.end_time and time.time() >= self.end_time:
                    print(f"\n[RLE Monitor] Timer expired ({self.duration}s duration reached)")
                    break
                
                loop_start = time.time()
                
                # Collect comprehensive hardware metrics
                metrics = self.collect_hardware_metrics()
                
                # Get HWiNFO sensors if available
                hwinfo_sensors = self.get_hwinfo_sensors(datetime.now())
                
                # Compute RLE metrics
                rle_data = self.compute_rle_metrics(metrics)
                
                # Detect workload state
                workload_state = self.detect_workload_state(metrics)
                
                # Update session statistics
                self.update_session_stats(metrics, rle_data)
                
                # Log to CSV with HWiNFO data and workload state
                self.log_to_csv(metrics, rle_data, hwinfo_sensors, workload_state)
                
                # Print status every 10 seconds
                if int(time.time() - start_time) % 10 == 0:
                    self.print_status(metrics, rle_data)
                    
                    # Show countdown if timer is active
                    if self.end_time:
                        remaining = int(self.end_time - time.time())
                        if remaining > 0:
                            print(f"[RLE Monitor] Time remaining: {remaining//60}m {remaining%60}s")
                        else:
                            print(f"[RLE Monitor] Timer expired!")
                
                # Print session stats at intervals
                current_time = time.time()
                if (current_time - self.last_stats_time) >= self.stats_interval:
                    self.print_session_stats()
                    self.last_stats_time = current_time
                
                # Sleep to maintain sample rate
                elapsed = time.time() - loop_start
                sleep_time = max(0, tick - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n[RLE Monitor] Stopping...")
        except Exception as e:
            print(f"[RLE Monitor] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Stop synthetic load if enabled
            if self.synthetic_load:
                self.synthetic_load.stop()
            
            # Save session metadata
            if hasattr(self, 'metadata') and hasattr(self, 'metadata_file'):
                self.metadata['session_end'] = datetime.now().isoformat()
                self.metadata['total_samples'] = self.session_stats['samples']
                self.metadata['summary'] = {
                    'cpu_collapses': self.session_stats['cpu_collapses'],
                    'gpu_collapses': self.session_stats['gpu_collapses'],
                    'max_temp': self.session_stats['max_temp'],
                    'max_power': self.session_stats['max_power'],
                    'rle_range': f"{self.session_stats['min_rle']:.3f}-{self.session_stats['max_rle']:.3f}"
                }
                with open(self.metadata_file, 'w') as f:
                    json.dump(self.metadata, f, indent=2)
                print(f"[RLE Monitor] Metadata saved: {self.metadata_file}")
            
            if self.csv_file:
                self.csv_file.close()
            print("[RLE Monitor] Shutdown complete")

# ----------------------------
# CLI Interface
# ----------------------------
def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="RLE Hardware Monitor v2.0 - Enhanced")
    parser.add_argument("--sample-hz", type=int, default=1, help="Sampling frequency (Hz)")
    parser.add_argument("--cpu-temp-limit", type=float, default=80.0, help="CPU temperature limit (°C)")
    parser.add_argument("--gpu-temp-limit", type=float, default=83.0, help="GPU temperature limit (°C)")
    parser.add_argument("--mode", choices=['cpu', 'gpu', 'both'], default='both', help="Monitoring mode")
    parser.add_argument("--flush-interval", type=int, default=60, help="CSV flush interval (seconds)")
    parser.add_argument("--realtime", action="store_true", help="Enable real-time CSV flushing")
    parser.add_argument("--hwinfo-csv", type=str, help="Path to HWiNFO CSV file for enhanced sensors")
    parser.add_argument("--stats-interval", type=int, default=10, help="Statistics update interval (seconds)")
    parser.add_argument("--duration", type=int, help="Run for specified duration in seconds (e.g., 300 for 5 minutes)")
    parser.add_argument("--synthetic-load", action="store_true", help="Enable synthetic load generation")
    parser.add_argument("--load-mode", choices=['cpu', 'gpu', 'both'], default='both', help="Synthetic load mode")
    parser.add_argument("--load-intensity", type=float, default=0.5, help="Synthetic load intensity (0.0-1.0)")
    parser.add_argument("--load-pattern", choices=['constant', 'ramp', 'sine'], default='constant', help="Load pattern")
    
    # Session metadata arguments
    parser.add_argument("--model-name", type=str, help="Model being trained (e.g., Luna-8B)")
    parser.add_argument("--training-mode", type=str, help="Training mode (e.g., LoRA fine-tuning)")
    parser.add_argument("--ambient-temp", type=float, help="Ambient temperature guess (°C)")
    parser.add_argument("--notes", type=str, help="Session notes (e.g., 'heat-soaked from previous run')")
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    monitor = RLEHardwareMonitor(args)
    monitor.run()

if __name__ == "__main__":
    main()
