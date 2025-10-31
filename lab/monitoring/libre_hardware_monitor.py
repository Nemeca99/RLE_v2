#!/usr/bin/env python3
"""
LibreHardwareMonitor Python Wrapper
Uses Python.NET to access compiled C# DLL
"""
import os
from pathlib import Path

LIBREHM_AVAILABLE = False
Hardware = None

try:
    import clr
    
    # Load the built DLL
    dll_path = Path(__file__).parent.parent.parent / "LibreHardwareMonitor-0.9.4" / "bin" / "Release" / "net8.0" / "LibreHardwareMonitorLib.dll"
    if dll_path.exists():
        clr.AddReference(str(dll_path))
        import LibreHardwareMonitor as LHM
        Hardware = LHM.Hardware
        LIBREHM_AVAILABLE = True
        print(f"[LibreHM] Successfully loaded DLL from {dll_path}")
    else:
        print(f"[LibreHM] DLL not found at {dll_path}")
except ImportError as e:
    print(f"[LibreHM] Python.NET not installed. Run: pip install pythonnet. Error: {e}")
except Exception as e:
    print(f"[LibreHM] Failed to load: {e}")

class LibreHardwareMonitor:
    """Wrapper for LibreHardwareMonitorLib"""
    
    def __init__(self):
        if not LIBREHM_AVAILABLE:
            raise RuntimeError("LibreHardwareMonitor not available")
        
        self.computer = Hardware.Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.Open()
        
        self.update_visitor = self._create_update_visitor()
        
    def _create_update_visitor(self):
        # Create a visitor class that implements IVisitor
        class UpdateVisitor(Hardware.IVisitor):
            def __init__(self):
                self._context = None
                
            def VisitComputer(self, computer):
                computer.Traverse(self)
                
            def VisitHardware(self, hardware):
                hardware.Update()
                for sub in hardware.SubHardware:
                    sub.Accept(self)
                    
            def VisitSensor(self, sensor):
                pass
                
            def VisitParameter(self, parameter):
                pass
        
        return UpdateVisitor()
    
    def update(self):
        """Update all sensor readings"""
        self.computer.Accept(self.update_visitor)
    
    def get_cpu_temperature(self):
        """Get CPU temperature from sensors"""
        self.update()
        
        for hardware in self.computer.Hardware:
            if hardware.HardwareType == Hardware.HardwareType.Cpu:
                for sensor in hardware.Sensors:
                    if sensor.SensorType == Hardware.SensorType.Temperature:
                        return sensor.Value
            # Check subhardware too
            for sub in hardware.SubHardware:
                if sub.HardwareType == Hardware.HardwareType.Cpu:
                    for sensor in sub.Sensors:
                        if sensor.SensorType == Hardware.SensorType.Temperature:
                            return sensor.Value
        return None
    
    def get_gpu_temperature(self):
        """Get GPU temperature from sensors"""
        self.update()
        
        for hardware in self.computer.Hardware:
            if hardware.HardwareType == Hardware.HardwareType.GpuNvidia or \
               hardware.HardwareType == Hardware.HardwareType.GpuAmd or \
               hardware.HardwareType == Hardware.HardwareType.GpuIntel:
                for sensor in hardware.Sensors:
                    if sensor.SensorType == Hardware.SensorType.Temperature and sensor.Name == "GPU Core":
                        return sensor.Value
        return None
    
    def close(self):
        """Cleanup"""
        self.computer.Close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()

