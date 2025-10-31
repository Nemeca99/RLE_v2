#!/usr/bin/env python3
"""
HWiNFO Integration for Enhanced RLE Monitoring
Provides more accurate sensor data by reading from HWiNFO CSV export
"""

import csv
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import os

@dataclass
class HWiNFOSensor:
    """HWiNFO sensor reading"""
    name: str
    value: float
    unit: str
    sensor_type: str
    timestamp: datetime

class HWiNFOReader:
    """Reads sensor data from HWiNFO CSV export"""
    
    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = csv_path or self._find_hwinfo_csv()
        self.last_read_time = 0
        self.sensor_cache = {}
        self.running = False
        self.reader_thread = None
        
        # Common HWiNFO sensor mappings
        self.sensor_mappings = {
            # CPU sensors
            'CPU Package': ('cpu', 'temperature', '°C'),
            'CPU Package Power': ('cpu', 'power', 'W'),
            'CPU Core #1': ('cpu', 'temperature', '°C'),
            'CPU Core #2': ('cpu', 'temperature', '°C'),
            'CPU Core #3': ('cpu', 'temperature', '°C'),
            'CPU Core #4': ('cpu', 'temperature', '°C'),
            'CPU Core #5': ('cpu', 'temperature', '°C'),
            'CPU Core #6': ('cpu', 'temperature', '°C'),
            'CPU Core #7': ('cpu', 'temperature', '°C'),
            'CPU Core #8': ('cpu', 'temperature', '°C'),
            'CPU Core #9': ('cpu', 'temperature', '°C'),
            'CPU Core #10': ('cpu', 'temperature', '°C'),
            'CPU Core #11': ('cpu', 'temperature', '°C'),
            'CPU Core #12': ('cpu', 'temperature', '°C'),
            'CPU Core #13': ('cpu', 'temperature', '°C'),
            'CPU Core #14': ('cpu', 'temperature', '°C'),
            'CPU Core #15': ('cpu', 'temperature', '°C'),
            'CPU Core #16': ('cpu', 'temperature', '°C'),
            'CPU Usage': ('cpu', 'utilization', '%'),
            'CPU Clock': ('cpu', 'clock', 'MHz'),
            
            # GPU sensors
            'GPU Temperature': ('gpu', 'temperature', '°C'),
            'GPU Memory Junction Temperature': ('gpu', 'temperature', '°C'),
            'GPU Power': ('gpu', 'power', 'W'),
            'GPU Usage': ('gpu', 'utilization', '%'),
            'GPU Memory Usage': ('gpu', 'utilization', '%'),
            'GPU Clock': ('gpu', 'clock', 'MHz'),
            'GPU Memory Clock': ('gpu', 'clock', 'MHz'),
            'GPU Fan': ('gpu', 'fan', '%'),
            
            # Memory sensors
            'Memory Usage': ('memory', 'utilization', '%'),
            'Memory Temperature': ('memory', 'temperature', '°C'),
            
            # Motherboard sensors
            'Motherboard Temperature': ('motherboard', 'temperature', '°C'),
            'VRM Temperature': ('motherboard', 'temperature', '°C'),
            'PCH Temperature': ('motherboard', 'temperature', '°C'),
            
            # Storage sensors
            'SSD Temperature': ('storage', 'temperature', '°C'),
            'HDD Temperature': ('storage', 'temperature', '°C'),
            'NVMe Temperature': ('storage', 'temperature', '°C'),
            
            # Fan sensors
            'CPU Fan': ('fan', 'speed', 'RPM'),
            'Case Fan #1': ('fan', 'speed', 'RPM'),
            'Case Fan #2': ('fan', 'speed', 'RPM'),
            'Case Fan #3': ('fan', 'speed', 'RPM'),
            'GPU Fan': ('fan', 'speed', 'RPM'),
            
            # Voltage sensors
            'CPU Core Voltage': ('voltage', 'core', 'V'),
            'CPU VCCIN': ('voltage', 'input', 'V'),
            'GPU Core Voltage': ('voltage', 'core', 'V'),
            'Memory Voltage': ('voltage', 'memory', 'V'),
        }
    
    def _find_hwinfo_csv(self) -> Optional[str]:
        """Find HWiNFO CSV export file"""
        # Common locations for HWiNFO CSV files
        possible_paths = [
            Path.home() / "Documents" / "HWiNFO64" / "HWiNFO64.CSV",
            Path.home() / "Desktop" / "HWiNFO64.CSV",
            Path("C:/Users") / os.getenv('USERNAME', '') / "Documents" / "HWiNFO64" / "HWiNFO64.CSV",
            Path("C:/Users") / os.getenv('USERNAME', '') / "Desktop" / "HWiNFO64.CSV",
        ]
        
        for path in possible_paths:
            if path.exists():
                print(f"[HWiNFO] Found CSV file: {path}")
                return str(path)
        
        print("[HWiNFO] No CSV file found - HWiNFO integration disabled")
        return None
    
    def start_monitoring(self):
        """Start HWiNFO monitoring thread"""
        if not self.csv_path or not Path(self.csv_path).exists():
            print("[HWiNFO] CSV file not available - monitoring disabled")
            return False
        
        self.running = True
        self.reader_thread = threading.Thread(target=self._monitor_csv, daemon=True)
        self.reader_thread.start()
        print("[HWiNFO] Monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop HWiNFO monitoring"""
        self.running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=2)
        print("[HWiNFO] Monitoring stopped")
    
    def _monitor_csv(self):
        """Monitor CSV file for updates"""
        last_size = 0
        
        while self.running:
            try:
                if not Path(self.csv_path).exists():
                    time.sleep(1)
                    continue
                
                current_size = Path(self.csv_path).stat().st_size
                
                # Only read if file has grown (new data)
                if current_size > last_size:
                    self._read_latest_data()
                    last_size = current_size
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                print(f"[HWiNFO] Error monitoring CSV: {e}")
                time.sleep(1)
    
    def _read_latest_data(self):
        """Read the latest data from CSV file"""
        try:
            with open(self.csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last few lines to get latest data
                lines = f.readlines()
                if len(lines) < 2:
                    return
                
                # Parse header
                header = lines[0].strip().split(',')
                
                # Parse latest data line
                latest_line = lines[-1].strip().split(',')
                
                if len(latest_line) != len(header):
                    return
                
                # Create sensor readings
                now = datetime.utcnow()
                for i, (col_name, value_str) in enumerate(zip(header, latest_line)):
                    if not value_str or value_str == 'N/A':
                        continue
                    
                    try:
                        value = float(value_str)
                        
                        # Map sensor name to our categories
                        sensor_info = self.sensor_mappings.get(col_name)
                        if sensor_info:
                            device_type, sensor_type, unit = sensor_info
                            
                            sensor = HWiNFOSensor(
                                name=col_name,
                                value=value,
                                unit=unit,
                                sensor_type=sensor_type,
                                timestamp=now
                            )
                            
                            self.sensor_cache[col_name] = sensor
                    
                    except ValueError:
                        continue
                
                self.last_read_time = time.time()
                
        except Exception as e:
            print(f"[HWiNFO] Error reading CSV: {e}")
    
    def get_sensor(self, name: str) -> Optional[HWiNFOSensor]:
        """Get a specific sensor reading"""
        return self.sensor_cache.get(name)
    
    def get_sensors_by_type(self, device_type: str, sensor_type: str) -> List[HWiNFOSensor]:
        """Get all sensors of a specific type"""
        sensors = []
        for sensor in self.sensor_cache.values():
            sensor_info = self.sensor_mappings.get(sensor.name)
            if sensor_info and sensor_info[0] == device_type and sensor_info[1] == sensor_type:
                sensors.append(sensor)
        return sensors
    
    def get_cpu_temperature(self) -> Optional[float]:
        """Get CPU package temperature"""
        sensor = self.get_sensor('CPU Package')
        return sensor.value if sensor else None
    
    def get_cpu_power(self) -> Optional[float]:
        """Get CPU package power"""
        sensor = self.get_sensor('CPU Package Power')
        return sensor.value if sensor else None
    
    def get_gpu_temperature(self) -> Optional[float]:
        """Get GPU temperature"""
        sensor = self.get_sensor('GPU Temperature')
        return sensor.value if sensor else None
    
    def get_gpu_power(self) -> Optional[float]:
        """Get GPU power"""
        sensor = self.get_sensor('GPU Power')
        return sensor.value if sensor else None
    
    def get_cpu_core_temperatures(self) -> List[float]:
        """Get all CPU core temperatures"""
        core_temps = []
        for i in range(1, 17):  # Check cores 1-16
            sensor = self.get_sensor(f'CPU Core #{i}')
            if sensor:
                core_temps.append(sensor.value)
        return core_temps
    
    def get_fan_speeds(self) -> Dict[str, float]:
        """Get all fan speeds"""
        fans = {}
        fan_sensors = self.get_sensors_by_type('fan', 'speed')
        for sensor in fan_sensors:
            fans[sensor.name] = sensor.value
        return fans
    
    def get_voltage_readings(self) -> Dict[str, float]:
        """Get all voltage readings"""
        voltages = {}
        voltage_sensors = self.get_sensors_by_type('voltage', 'core')
        voltage_sensors.extend(self.get_sensors_by_type('voltage', 'input'))
        voltage_sensors.extend(self.get_sensors_by_type('voltage', 'memory'))
        
        for sensor in voltage_sensors:
            voltages[sensor.name] = sensor.value
        return voltages
    
    def is_available(self) -> bool:
        """Check if HWiNFO data is available"""
        return self.csv_path is not None and Path(self.csv_path).exists()
    
    def get_status(self) -> Dict[str, Any]:
        """Get HWiNFO integration status"""
        return {
            'available': self.is_available(),
            'csv_path': self.csv_path,
            'sensors_count': len(self.sensor_cache),
            'last_read': self.last_read_time,
            'running': self.running
        }

# Integration with enhanced monitor
class HWiNFOEnhancedMonitor:
    """Enhanced monitor with HWiNFO integration"""
    
    def __init__(self, base_monitor):
        self.base_monitor = base_monitor
        self.hwinfo = HWiNFOReader()
        
        if self.hwinfo.is_available():
            self.hwinfo.start_monitoring()
            print("[HWiNFO] Integration enabled")
        else:
            print("[HWiNFO] Integration disabled - CSV not found")
    
    def get_enhanced_cpu_metrics(self):
        """Get CPU metrics enhanced with HWiNFO data"""
        base_metrics = self.base_monitor.cpu_monitor.get_metrics()
        
        if not self.hwinfo.is_available():
            return base_metrics
        
        # Enhance with HWiNFO data
        enhanced_sensors = list(base_metrics.sensors)
        
        # Add HWiNFO CPU temperature if available
        hwinfo_temp = self.hwinfo.get_cpu_temperature()
        if hwinfo_temp is not None:
            from monitoring.hardware_monitor_v2 import HardwareSensor
            enhanced_sensors.append(
                HardwareSensor("CPU Temperature (HWiNFO)", hwinfo_temp, "°C", "temperature", "cpu", datetime.utcnow())
            )
        
        # Add HWiNFO CPU power if available
        hwinfo_power = self.hwinfo.get_cpu_power()
        if hwinfo_power is not None:
            from monitoring.hardware_monitor_v2 import HardwareSensor
            enhanced_sensors.append(
                HardwareSensor("CPU Power (HWiNFO)", hwinfo_power, "W", "power", "cpu", datetime.utcnow())
            )
        
        # Add core temperatures
        core_temps = self.hwinfo.get_cpu_core_temperatures()
        for i, temp in enumerate(core_temps):
            from monitoring.hardware_monitor_v2 import HardwareSensor
            enhanced_sensors.append(
                HardwareSensor(f"CPU Core {i+1} Temperature (HWiNFO)", temp, "°C", "temperature", "cpu", datetime.utcnow())
            )
        
        # Create enhanced metrics
        from monitoring.hardware_monitor_v2 import HardwareMetrics
        return HardwareMetrics("cpu", "CPU (Enhanced)", enhanced_sensors, datetime.utcnow())
    
    def get_enhanced_gpu_metrics(self):
        """Get GPU metrics enhanced with HWiNFO data"""
        base_metrics = self.base_monitor.gpu_monitor.get_metrics()
        
        if not self.hwinfo.is_available():
            return base_metrics
        
        # Enhance with HWiNFO data
        enhanced_sensors = list(base_metrics.sensors)
        
        # Add HWiNFO GPU temperature if available
        hwinfo_temp = self.hwinfo.get_gpu_temperature()
        if hwinfo_temp is not None:
            from monitoring.hardware_monitor_v2 import HardwareSensor
            enhanced_sensors.append(
                HardwareSensor("GPU Temperature (HWiNFO)", hwinfo_temp, "°C", "temperature", "gpu", datetime.utcnow())
            )
        
        # Add HWiNFO GPU power if available
        hwinfo_power = self.hwinfo.get_gpu_power()
        if hwinfo_power is not None:
            from monitoring.hardware_monitor_v2 import HardwareSensor
            enhanced_sensors.append(
                HardwareSensor("GPU Power (HWiNFO)", hwinfo_power, "W", "power", "gpu", datetime.utcnow())
            )
        
        # Create enhanced metrics
        from monitoring.hardware_monitor_v2 import HardwareMetrics
        return HardwareMetrics("gpu", "GPU (Enhanced)", enhanced_sensors, datetime.utcnow())
    
    def cleanup(self):
        """Cleanup HWiNFO monitoring"""
        if self.hwinfo:
            self.hwinfo.stop_monitoring()

# Test function
def test_hwinfo_integration():
    """Test HWiNFO integration"""
    print("Testing HWiNFO Integration...")
    print("="*50)
    
    hwinfo = HWiNFOReader()
    
    if not hwinfo.is_available():
        print("HWiNFO CSV not found - integration test skipped")
        return
    
    print("HWiNFO CSV found - testing integration...")
    
    # Start monitoring
    if hwinfo.start_monitoring():
        print("HWiNFO monitoring started")
        
        # Wait a bit for data
        time.sleep(2)
        
        # Test sensor readings
        cpu_temp = hwinfo.get_cpu_temperature()
        cpu_power = hwinfo.get_cpu_power()
        gpu_temp = hwinfo.get_gpu_temperature()
        gpu_power = hwinfo.get_gpu_power()
        
        print(f"CPU Temperature: {cpu_temp}°C" if cpu_temp else "CPU Temperature: N/A")
        print(f"CPU Power: {cpu_power}W" if cpu_power else "CPU Power: N/A")
        print(f"GPU Temperature: {gpu_temp}°C" if gpu_temp else "GPU Temperature: N/A")
        print(f"GPU Power: {gpu_power}W" if gpu_power else "GPU Power: N/A")
        
        # Test core temperatures
        core_temps = hwinfo.get_cpu_core_temperatures()
        print(f"CPU Core Temperatures: {len(core_temps)} cores detected")
        
        # Test fan speeds
        fans = hwinfo.get_fan_speeds()
        print(f"Fan Speeds: {len(fans)} fans detected")
        
        # Test voltages
        voltages = hwinfo.get_voltage_readings()
        print(f"Voltage Readings: {len(voltages)} voltages detected")
        
        # Get status
        status = hwinfo.get_status()
        print(f"HWiNFO Status: {status}")
        
        # Stop monitoring
        hwinfo.stop_monitoring()
        print("HWiNFO monitoring stopped")
        
        print("✅ HWiNFO integration test completed")
    else:
        print("❌ Failed to start HWiNFO monitoring")

if __name__ == "__main__":
    test_hwinfo_integration()
