"""
RLE_real Live Testing: Monitor actual PC hardware and compute RLE_real.

This script monitors CPU usage, temperature, and clock speed in real-time
and computes RLE_real to assess system efficiency and stress.
"""

import numpy as np
import time
from typing import List, Dict
from collections import deque
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import threading

# Import psutil in functions to avoid linter warnings
try:
    import psutil
except ImportError:
    psutil = None

# Global variables for temperature tracking
_last_cpu_temp = 35.0
_last_cpu_percent = 0.0
_temp_time = 0.0


def get_cpu_metrics() -> Dict:
    """
    Get current CPU metrics.
    
    Returns:
    --------
    dict : Dictionary with CPU metrics
    """
    global psutil
    if psutil is None:
        import psutil
    
    # CPU usage percentage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    
    # CPU frequency (in MHz)
    try:
        cpu_freq = psutil.cpu_freq().current
    except Exception:
        cpu_freq = 2500.0  # Default estimate
    
    # Number of CPU cores
    num_cores = psutil.cpu_count()
    
    # CPU temperature (may not be available on all systems)
    cpu_temp = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            # Try common sensor names
            for sensor_name in ['coretemp', 'cpu_thermal', 'k10temp']:
                if sensor_name in temps:
                    cpu_temp = temps[sensor_name][0].get('current', None)
                    if cpu_temp:
                        break
    except Exception:
        pass
    
    # If no real sensor, simulate dynamic temperature
    if cpu_temp is None:
        # Simple thermal simulation
        # Temperature rises with CPU usage, with inertia
        global _last_cpu_temp
        target_temp = 35.0 + (cpu_percent / 100.0) * 50.0  # 35-85°C range
        
        # Smooth transition with decay
        decay = 0.95  # temperature follows with inertia
        _last_cpu_temp = _last_cpu_temp * decay + target_temp * (1 - decay)
        cpu_temp = _last_cpu_temp
    
    return {
        'cpu_percent': cpu_percent,
        'cpu_freq': cpu_freq,
        'num_cores': num_cores,
        'cpu_temp': cpu_temp
    }


def estimate_power_consumption(cpu_percent: float, cpu_freq: float, base_freq: float = 2500.0,
                               idle_power: float = 30.0, max_power: float = 150.0) -> float:
    """
    Estimate power consumption based on CPU usage and frequency.
    
    Parameters:
    -----------
    cpu_percent : float
        CPU usage percentage
    cpu_freq : float
        Current CPU frequency in MHz
    base_freq : float
        Base CPU frequency in MHz
    idle_power : float
        Estimated idle power in watts
    max_power : float
        Estimated maximum power in watts
    
    Returns:
    --------
    float : Estimated power consumption in watts
    """
    # Base power
    load_factor = cpu_percent / 100.0
    
    # Frequency boost increases power consumption exponentially
    freq_boost = cpu_freq / base_freq
    freq_power_multiplier = freq_boost ** 1.5
    
    # Estimate total power
    power = idle_power + (max_power - idle_power) * load_factor * freq_power_multiplier
    
    return power


def compute_rle_real_live(
    P_useful: float,
    Q_in: float,
    P_rated: float,
    output_history: np.ndarray,
    temp_current: float,
    temp_limit: float,
    temp_history: np.ndarray,
    temp_rise_rate: float,
    window_size: int = 10
) -> Dict:
    """
    Compute RLE_real for live hardware monitoring.
    
    Parameters:
    -----------
    P_useful : float
        Useful work done (CPU load in watts)
    Q_in : float
        Total input power in watts
    P_rated : float
        Rated/safe operating power in watts
    output_history : np.ndarray
        Recent work history
    temp_current : float
        Current temperature in °C
    temp_limit : float
        Maximum safe temperature in °C
    temp_history : np.ndarray
        Recent temperature history
    temp_rise_rate : float
        Temperature rise rate in °C/s
    window_size : int
        Size of rolling window
    
    Returns:
    --------
    dict : RLE_real and intermediate values
    """
    # Limit history
    if len(output_history) > window_size:
        output_history = output_history[-window_size:]
    if len(temp_history) > window_size:
        temp_history = temp_history[-window_size:]
    
    # Compute Q_waste
    Q_waste = max(Q_in - P_useful, 0)
    
    # Energy utilization
    if Q_in > 0:
        energy_utilization = 1 - Q_waste / Q_in
    else:
        energy_utilization = 0
    
    # Stability from output history
    if len(output_history) > 1 and np.mean(output_history) != 0:
        stability_ratio = np.std(output_history) / np.mean(output_history)
        S_stability = 1 / (1 + stability_ratio)
    else:
        S_stability = 1.0
    
    # Conversion efficiency
    if Q_in > 0:
        eta_conv = P_useful / Q_in
    else:
        eta_conv = 0
    
    # Load aggressiveness
    if P_rated > 0:
        A_load = P_useful / P_rated
    else:
        A_load = 0
    
    # Time to burnout
    if temp_rise_rate > 0:
        T_sustain = (temp_limit - temp_current) / temp_rise_rate
        if T_sustain < 0:
            T_sustain = 1e-6
    else:
        T_sustain = 1e6
    
    # Burnout penalty
    burnout_penalty = 1 / T_sustain
    
    # Thermal noise
    if len(temp_history) > 1:
        N_noise = np.std(temp_history) / 5.0
    else:
        N_noise = 0
    
    # RLE_real
    numerator = energy_utilization * S_stability * eta_conv
    denominator = (A_load + burnout_penalty) * (1 + N_noise)
    
    if denominator > 0:
        RLE_real = numerator / denominator
    else:
        RLE_real = 0
    
    return {
        'RLE_real': RLE_real,
        'P_useful': P_useful,
        'Q_in': Q_in,
        'Q_waste': Q_waste,
        'energy_utilization': energy_utilization,
        'S_stability': S_stability,
        'eta_conv': eta_conv,
        'A_load': A_load,
        'T_sustain': T_sustain,
        'burnout_penalty': burnout_penalty,
        'N_noise': N_noise,
        'temp_current': temp_current,
        'temp_limit': temp_limit
    }


def burn_cpu_worker(intensity, stop_event):
    """Worker thread that burns CPU at variable intensity."""
    import math
    while not stop_event.is_set():
        # Burn CPU based on intensity
        loops = int(intensity() * 500000)
        for _ in range(loops):
            _ = math.sqrt(_)
        time.sleep(0.1)


current_intensity = [0.5]

def get_intensity(elapsed):
    """Get current intensity based on elapsed time."""
    if elapsed < 15:
        return 0.5
    elif elapsed < 45:
        return 0.5 + (elapsed - 15) / 30 * 4.5
    else:
        return 5.0

def cpu_stressor(duration: float, start_time: float):
    """Generate gradually increasing CPU load using threads."""
    stop_event = threading.Event()
    
    def intensity_fn():
        elapsed = time.time() - start_time
        return get_intensity(elapsed)
    
    # Start workers on 4 cores
    workers = []
    for _ in range(4):
        t = threading.Thread(target=burn_cpu_worker, args=(intensity_fn, stop_event))
        t.daemon = True
        t.start()
        workers.append(t)
    
    # Wait for duration
    elapsed = 0
    while elapsed < duration:
        elapsed = time.time() - start_time
        time.sleep(0.5)
    
    # Stop workers
    stop_event.set()
    time.sleep(0.5)


def run_live_test(duration: int = 60, interval: float = 1.0, auto_stress: bool = True):
    """
    Run live hardware monitoring and compute RLE_real.
    
    Parameters:
    -----------
    duration : int
        Duration of test in seconds
    interval : float
        Sampling interval in seconds
    auto_stress : bool
        Automatically generate CPU load
    """
    print("Starting Live Hardware Monitoring")
    print("=" * 60)
    print("Monitoring CPU for {} seconds...".format(duration))
    
    # Start background CPU stress if requested
    stress_thread = None
    start_time_global = time.time()
    if auto_stress:
        print("\nStarting automatic CPU load generation...")
        print("Baseline (0-15s): Low idle")
        print("Ramp-up (15-45s): Gradual load increase")
        print("Peak (45-{}s): Maximum load".format(duration))
        stress_thread = threading.Thread(target=lambda: cpu_stressor(duration, start_time_global))
        stress_thread.daemon = True
        stress_thread.start()
        time.sleep(1)  # Give stress thread time to start
    
    print("\nPress Ctrl+C to stop early\n")
    
    # State variables
    output_history = deque(maxlen=10)
    temp_history = deque(maxlen=10)
    
    # Storage
    timestamps = []
    rle_values = []
    temp_values = []
    load_values = []
    cpu_percents = []
    all_metrics = []
    
    # Parameters
    P_rated = 120.0  # Rated safe operating power (watts)
    temp_limit = 85.0  # Temperature limit (°C)
    base_freq = 2500.0  # Base CPU frequency
    
    start_time = time.time()
    
    try:
        for i in range(duration):
            # Get current metrics
            metrics = get_cpu_metrics()
            cpu_percent = metrics['cpu_percent']
            cpu_temp = metrics['cpu_temp']
            cpu_freq = metrics['cpu_freq']
            
            # Manual stress should show up in CPU percent
            # No need for target_load when using background stress
            
            # Estimate power consumption
            Q_in = estimate_power_consumption(cpu_percent, cpu_freq, base_freq)
            
            # Useful power is proportional to CPU usage
            P_useful = Q_in * (cpu_percent / 100.0)
            
            # Estimate temperature rise rate based on load
            temp_rise_rate = (cpu_percent / 100.0) * 0.15  # °C/s
            if cpu_temp > 70:
                temp_rise_rate *= 1.5  # Accelerate near limit
            
            # Update histories
            output_history.append(P_useful)
            temp_history.append(cpu_temp)
            
            # Compute RLE_real
            rle_metrics = compute_rle_real_live(
                P_useful=P_useful,
                Q_in=Q_in,
                P_rated=P_rated,
                output_history=np.array(output_history),
                temp_current=cpu_temp,
                temp_limit=temp_limit,
                temp_history=np.array(temp_history),
                temp_rise_rate=temp_rise_rate
            )
            
            # Store data
            elapsed = time.time() - start_time
            timestamps.append(elapsed)
            rle_values.append(rle_metrics['RLE_real'])
            temp_values.append(cpu_temp)
            load_values.append(rle_metrics['A_load'])
            cpu_percents.append(cpu_percent)
            all_metrics.append(rle_metrics)
            
            # Print progress
            if i % 10 == 0 or i == duration - 1:
                print("t={:3d}s | CPU={:4.1f}% | Temp={:5.1f}°C | RLE={:5.3f} | A_load={:4.2f}".format(
                    i, cpu_percent, cpu_temp, rle_metrics['RLE_real'], rle_metrics['A_load']
                ))
            
            time.sleep(max(0, interval - (time.time() - start_time - i)))
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    
    # Analyze results
    print("\n" + "=" * 60)
    print("Live Test Complete!")
    print("=" * 60)
    
    if rle_values:
        max_rle = max(rle_values)
        max_idx = rle_values.index(max_rle)
        min_rle = min(rle_values)
        
        print("\nResults:")
        print("  Peak RLE_real: {:.4f} (at t={:.1f}s)".format(max_rle, timestamps[max_idx]))
        print("  Final RLE_real: {:.4f}".format(rle_values[-1]))
        print("  Minimum RLE_real: {:.4f}".format(min_rle))
        print("  Avg CPU Usage: {:.1f}%".format(np.mean(cpu_percents)))
        print("  Max Temperature: {:.1f}°C".format(max(temp_values)))
        print("  Avg Temperature: {:.1f}°C".format(np.mean(temp_values)))
        
        # Identify collapse point
        collapse_idx = None
        for i in range(len(rle_values) - 10):
            if i > max_idx and rle_values[i] < max_rle - 0.2:
                if np.mean(rle_values[i:i+5]) < max_rle - 0.2:
                    collapse_idx = i
                    break
        
        if collapse_idx and collapse_idx < len(timestamps):
            print("\n  Collapse detected at t={:.1f}s".format(timestamps[collapse_idx]))
            print("  RLE_real at collapse: {:.4f}".format(rle_values[collapse_idx]))
    
    # Plot results
    print("\nGenerating plots...")
    plot_live_results(timestamps, rle_values, temp_values, load_values, cpu_percents)
    
    return timestamps, rle_values, temp_values, load_values, all_metrics


def plot_live_results(timestamps: List[float], rle_values: List[float], 
                       temp_values: List[float], load_values: List[float],
                       cpu_percents: List[float]):
    """Plot the live monitoring results."""
    fig, axes = plt.subplots(4, 1, figsize=(12, 12))
    
    # Plot 1: RLE_real
    axes[0].plot(timestamps, rle_values, linewidth=2, color='blue', label='RLE_real')
    axes[0].axhline(y=max(rle_values), color='green', linestyle='--', alpha=0.5, 
                    label='Peak: {:.3f}'.format(max(rle_values)))
    axes[0].set_xlabel('Time (s)')
    axes[0].set_ylabel('RLE_real')
    axes[0].set_title('RLE_real Over Time - Live Hardware Test')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    # Plot 2: CPU Temperature
    axes[1].plot(timestamps, temp_values, linewidth=2, color='red', label='CPU Temp')
    axes[1].axhline(y=85, color='orange', linestyle='--', alpha=0.5, label='Limit: 85°C')
    axes[1].set_xlabel('Time (s)')
    axes[1].set_ylabel('Temperature (°C)')
    axes[1].set_title('CPU Temperature Over Time')
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    # Plot 3: A_load
    axes[2].plot(timestamps, load_values, linewidth=2, color='purple', label='A_load')
    axes[2].axhline(y=1.0, color='orange', linestyle='--', alpha=0.5, label='Rated Load')
    axes[2].set_xlabel('Time (s)')
    axes[2].set_ylabel('A_load')
    axes[2].set_title('Load Aggressiveness Over Time')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()
    
    # Plot 4: CPU Usage
    axes[3].plot(timestamps, cpu_percents, linewidth=2, color='teal', label='CPU %')
    axes[3].set_xlabel('Time (s)')
    axes[3].set_ylabel('CPU Usage (%)')
    axes[3].set_title('CPU Usage Over Time')
    axes[3].grid(True, alpha=0.3)
    axes[3].legend()
    
    plt.tight_layout()
    
    filename = 'rle_real_live_{}.png'.format(datetime.now().strftime('%Y%m%d_%H%M%S'))
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print("Plot saved to: {}".format(filename))
    
    return fig


if __name__ == '__main__':
    # Check if psutil is available
    try:
        import psutil
    except ImportError:
        print("Error: psutil is not installed.")
        print("Please install it using: pip install psutil")
        sys.exit(1)
    
    # Run live test
    run_live_test(duration=60, interval=1.0)

