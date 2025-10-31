#!/usr/bin/env python3
"""
AIOS-RLE Bridge: Passive Thermal Monitoring
Monitors AIOS core activity and correlates with thermal efficiency

This is a SEPARATE monitoring daemon that observes AIOS from the outside.
It does NOT modify AIOS kernel or consciousness_core.
"""

import os
import sys
import time
import psutil
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json
import csv
import argparse

# Add parent directory to path for RLE imports
sys.path.append(str(Path(__file__).parent.parent))

class AIOSProcessMonitor:
    """Monitors AIOS process activity without modifying AIOS"""
    
    def __init__(self):
        self.aios_processes = []
        self.core_activity = {}
        self.last_sample_time = None
        
    def find_aios_processes(self):
        """Find running AIOS processes"""
        aios_procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'main.py' in cmdline and 'AIOS' in cmdline:
                    aios_procs.append(proc)
                elif 'luna_chat.py' in cmdline:
                    aios_procs.append(proc)
                elif 'streamlit_app.py' in cmdline and 'AIOS' in cmdline:
                    aios_procs.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        self.aios_processes = aios_procs
        return len(aios_procs)
    
    def get_core_activity(self):
        """Detect which AIOS cores are active based on file system activity"""
        core_activity = {}
        
        # Check for AIOS directory
        aios_path = Path("L:/AIOS")
        if not aios_path.exists():
            return core_activity
        
        # Monitor core directories for recent activity
        core_dirs = [
            'luna_core', 'carma_core', 'dream_core', 'consciousness_core',
            'data_core', 'support_core', 'utils_core', 'enterprise_core',
            'rag_core', 'streamlit_core', 'backup_core', 'fractal_core',
            'game_core', 'marketplace_core', 'music_core', 'privacy_core',
            'template_core', 'main_core', 'infra_core'
        ]
        
        current_time = time.time()
        
        for core in core_dirs:
            core_path = aios_path / core
            if core_path.exists():
                # Check for recent file modifications (within last 30 seconds)
                try:
                    recent_files = []
                    for file_path in core_path.rglob('*'):
                        if file_path.is_file():
                            mtime = file_path.stat().st_mtime
                            if current_time - mtime < 30:  # Modified in last 30 seconds
                                recent_files.append(file_path)
                    
                    core_activity[core] = len(recent_files)
                except (OSError, PermissionError):
                    core_activity[core] = 0
        
        return core_activity
    
    def get_aios_metrics(self):
        """Get AIOS process metrics"""
        metrics = {
            'aios_processes': len(self.aios_processes),
            'total_cpu_percent': 0.0,
            'total_memory_mb': 0.0,
            'core_activity': self.get_core_activity()
        }
        
        for proc in self.aios_processes:
            try:
                metrics['total_cpu_percent'] += proc.cpu_percent()
                metrics['total_memory_mb'] += proc.memory_info().rss / 1024 / 1024
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return metrics

class AIOSRLEBridge:
    """Bridge between AIOS monitoring and RLE thermal analysis"""
    
    def __init__(self, sample_hz=1.0, duration=None):
        self.sample_hz = sample_hz
        self.duration = duration
        self.end_time = None
        
        # Initialize monitors
        self.aios_monitor = AIOSProcessMonitor()
        # Hardware monitoring will be done separately
        
        # Data storage
        self.bridge_data = []
        self.csv_file = None
        
    def setup_logging(self):
        """Setup CSV logging for bridge data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.csv_file = f"sessions/recent/aios_rle_bridge_{timestamp}.csv"
        
        # Ensure directory exists
        os.makedirs("sessions/recent", exist_ok=True)
        
        # CSV headers
        headers = [
            'timestamp', 'aios_processes', 'aios_cpu_percent', 'aios_memory_mb',
            'active_cores', 'core_activity_json', 'rle_cpu', 'rle_gpu',
            'cpu_temp', 'gpu_temp', 'cpu_power', 'gpu_power',
            'cpu_collapse', 'gpu_collapse', 'cpu_util', 'gpu_util'
        ]
        
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        print(f"[SUCCESS] Bridge logging to: {self.csv_file}")
    
    def sample_bridge_data(self):
        """Sample both AIOS and RLE data simultaneously"""
        timestamp = datetime.now().isoformat()
        
        # Get AIOS metrics
        aios_metrics = self.aios_monitor.get_aios_metrics()
        
        # Get latest RLE data (we'll need to modify hardware_monitor to expose current metrics)
        # For now, we'll get basic hardware metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        # Get temperature (simplified - would need proper sensor access)
        try:
            import wmi
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            cpu_temp = 0
            gpu_temp = 0
            for sensor in w.Sensor():
                if sensor.SensorType == 'Temperature':
                    if 'CPU' in sensor.Name:
                        cpu_temp = sensor.Value
                    elif 'GPU' in sensor.Name:
                        gpu_temp = sensor.Value
        except:
            cpu_temp = 0
            gpu_temp = 0
        
        # Count active cores
        active_cores = sum(1 for count in aios_metrics['core_activity'].values() if count > 0)
        
        # Store bridge data
        bridge_sample = {
            'timestamp': timestamp,
            'aios_processes': aios_metrics['aios_processes'],
            'aios_cpu_percent': aios_metrics['total_cpu_percent'],
            'aios_memory_mb': aios_metrics['total_memory_mb'],
            'active_cores': active_cores,
            'core_activity_json': json.dumps(aios_metrics['core_activity']),
            'rle_cpu': 0.0,  # Placeholder - would need RLE calculation
            'rle_gpu': 0.0,  # Placeholder - would need RLE calculation
            'cpu_temp': cpu_temp,
            'gpu_temp': gpu_temp,
            'cpu_power': 0.0,  # Placeholder
            'gpu_power': 0.0,  # Placeholder
            'cpu_collapse': 0,  # Placeholder
            'gpu_collapse': 0,  # Placeholder
            'cpu_util': cpu_percent,
            'gpu_util': 0.0  # Placeholder
        }
        
        self.bridge_data.append(bridge_sample)
        
        # Log to CSV
        if self.csv_file:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    bridge_sample['timestamp'],
                    bridge_sample['aios_processes'],
                    bridge_sample['aios_cpu_percent'],
                    bridge_sample['aios_memory_mb'],
                    bridge_sample['active_cores'],
                    bridge_sample['core_activity_json'],
                    bridge_sample['rle_cpu'],
                    bridge_sample['rle_gpu'],
                    bridge_sample['cpu_temp'],
                    bridge_sample['gpu_temp'],
                    bridge_sample['cpu_power'],
                    bridge_sample['gpu_power'],
                    bridge_sample['cpu_collapse'],
                    bridge_sample['gpu_collapse'],
                    bridge_sample['cpu_util'],
                    bridge_sample['gpu_util']
                ])
        
        return bridge_sample
    
    def run_bridge_monitoring(self):
        """Run the bridge monitoring loop"""
        print("="*70)
        print("AIOS-RLE BRIDGE: PASSIVE THERMAL MONITORING")
        print("="*70)
        print("Monitoring AIOS core activity and correlating with thermal efficiency")
        print("This is a SEPARATE daemon - does NOT modify AIOS")
        print()
        
        # Setup logging
        self.setup_logging()
        
        # Find AIOS processes
        aios_count = self.aios_monitor.find_aios_processes()
        print(f"[INFO] Found {aios_count} AIOS processes")
        
        if aios_count == 0:
            print("[WARNING] No AIOS processes found. Start AIOS first:")
            print("  cd L:/AIOS")
            print("  python main.py --luna --message 'Hello'")
            print()
        
        # Set end time if duration specified
        if self.duration:
            self.end_time = time.time() + self.duration
            print(f"[INFO] Monitoring for {self.duration} seconds")
        
        print("[INFO] Starting bridge monitoring...")
        print("Press Ctrl+C to stop")
        print()
        
        sample_interval = 1.0 / self.sample_hz
        start_time = time.time()
        sample_count = 0
        
        try:
            while True:
                loop_start = time.time()
                
                # Sample bridge data
                sample = self.sample_bridge_data()
                sample_count += 1
                
                # Print status
                elapsed = time.time() - start_time
                print(f"[{elapsed:6.1f}s] AIOS: {sample['aios_processes']} procs, "
                      f"{sample['active_cores']} cores, "
                      f"CPU: {sample['aios_cpu_percent']:5.1f}%, "
                      f"Temp: {sample['cpu_temp']:3.0f}°C")
                
                # Check if duration expired
                if self.end_time and time.time() >= self.end_time:
                    print(f"\n[INFO] Duration completed ({self.duration}s)")
                    break
                
                # Sleep until next sample
                sleep_time = sample_interval - (time.time() - loop_start)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            print(f"\n[INFO] Monitoring stopped by user")
        
        # Final summary
        elapsed = time.time() - start_time
        print(f"\n[SUCCESS] Bridge monitoring complete:")
        print(f"  Duration: {elapsed:.1f} seconds")
        print(f"  Samples: {sample_count}")
        print(f"  Sample rate: {sample_count/elapsed:.2f} Hz")
        print(f"  Data saved: {self.csv_file}")
        
        return self.bridge_data

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AIOS-RLE Bridge: Passive Thermal Monitoring')
    parser.add_argument('--sample-hz', type=float, default=1.0, help='Sampling frequency (Hz)')
    parser.add_argument('--duration', type=int, help='Duration in seconds')
    
    args = parser.parse_args()
    
    # Create and run bridge
    bridge = AIOSRLEBridge(sample_hz=args.sample_hz, duration=args.duration)
    bridge.run_bridge_monitoring()

if __name__ == "__main__":
    main()
