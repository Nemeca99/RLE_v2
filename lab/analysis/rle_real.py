"""
RLE_real: Real-world Recursive Load Efficiency metric computation.

This module computes a metric that balances useful output vs stress,
waste, instability, and time-to-burnout in physical systems.
"""

import numpy as np
from typing import Tuple, Dict, List
from collections import deque


def compute_rle_real(
    Q_in: float,
    P_useful: float,
    P_rated: float,
    output_history: np.ndarray,
    temp_current: float,
    temp_limit: float,
    temp_history: np.ndarray,
    temp_rise_rate: float,
    window_size: int = 10
) -> Dict:
    """
    Compute RLE_real metric and all intermediate values.
    
    Parameters:
    -----------
    Q_in : float
        Total input power in watts
    P_useful : float
        Useful output power in watts
    P_rated : float
        Safe continuous output rating in watts
    output_history : np.ndarray
        Recent output power history for stability calculation
    temp_current : float
        Current temperature in °C
    temp_limit : float
        Temperature limit in °C
    temp_history : np.ndarray
        Recent temperature history for noise calculation
    temp_rise_rate : float
        Rate of temperature rise in °C/s
    window_size : int
        Size of rolling window for history
    
    Returns:
    --------
    dict : Dictionary containing RLE_real and all intermediate values
    """
    
    # Limit history to last window_size elements
    if len(output_history) > window_size:
        output_history = output_history[-window_size:]
    if len(temp_history) > window_size:
        temp_history = temp_history[-window_size:]
    
    # Compute Q_waste
    Q_waste = max(Q_in - P_useful, 0)
    
    # Compute energy_utilization
    if Q_in > 0:
        energy_utilization = 1 - Q_waste / Q_in
    else:
        energy_utilization = 0
    
    # Compute S_stability from output history
    if len(output_history) > 1 and np.mean(output_history) != 0:
        stability_ratio = np.std(output_history) / np.mean(output_history)
        S_stability = 1 / (1 + stability_ratio)
    else:
        S_stability = 1.0  # Assume stable if no variation
    
    # Compute eta_conv (conversion efficiency)
    if Q_in > 0:
        eta_conv = P_useful / Q_in
    else:
        eta_conv = 0
    
    # Compute A_load (aggressiveness of load)
    if P_rated > 0:
        A_load = P_useful / P_rated
    else:
        A_load = 0
    
    # Compute T_sustain (time to burnout)
    if temp_rise_rate > 0:
        T_sustain = (temp_limit - temp_current) / temp_rise_rate
        # Prevent negative T_sustain
        if T_sustain < 0:
            T_sustain = 1e-6  # Very small value
    else:
        # System is cooling or steady
        T_sustain = 1e6  # Very large value
    
    # Compute burnout penalty
    burnout_penalty = 1 / T_sustain
    
    # Compute N_noise (thermal instability)
    if len(temp_history) > 1:
        N_noise = np.std(temp_history) / 5.0
    else:
        N_noise = 0
    
    # Compute numerator
    numerator = energy_utilization * S_stability * eta_conv
    
    # Compute denominator
    denominator = (A_load + burnout_penalty) * (1 + N_noise)
    
    # Compute RLE_real
    if denominator > 0:
        RLE_real = numerator / denominator
    else:
        RLE_real = 0
    
    return {
        'RLE_real': RLE_real,
        'Q_in': Q_in,
        'P_useful': P_useful,
        'Q_waste': Q_waste,
        'energy_utilization': energy_utilization,
        'S_stability': S_stability,
        'eta_conv': eta_conv,
        'A_load': A_load,
        'T_sustain': T_sustain,
        'burnout_penalty': burnout_penalty,
        'N_noise': N_noise,
        'numerator': numerator,
        'denominator': denominator
    }


def simulate_device(
    duration: int = 300,
    P_rated: float = 200.0,
    temp_limit: float = 90.0,
    temp_start: float = 40.0,
    P_useful_start: float = 50.0,
    P_useful_end: float = 260.0,
    efficiency_start: float = 0.7,
    efficiency_end: float = 0.5
) -> Tuple[List[float], List[float], List[float], List[Dict], List[float], List[int]]:
    """
    Simulate device operation over time.
    
    Returns:
    --------
    rle_values : list of RLE_real values
    temp_values : list of temperature values
    a_load_values : list of A_load values
    all_metrics : list of metric dictionaries
    times : list of time values in seconds
    collapse_points : list of indices where RLE_real collapses
    """
    
    # Initialize state
    temp_current = temp_start
    t = 0
    
    # Rolling windows
    window_size = 10
    output_history = deque(maxlen=window_size)
    temp_history = deque(maxlen=window_size)
    
    # Storage
    rle_values = []
    temp_values = []
    a_load_values = []
    all_metrics = []
    times = []
    
    while t < duration:
        # Linear ramp of useful power
        P_useful = P_useful_start + (P_useful_end - P_useful_start) * (t / duration)
        
        # Compute efficiency degradation based on temperature
        temp_factor = (temp_current - temp_start) / (temp_limit - temp_start)
        temp_factor = max(0, min(1, temp_factor))  # Clamp to [0, 1]
        efficiency = efficiency_start - (efficiency_start - efficiency_end) * temp_factor
        
        # Compute Q_in
        if efficiency > 0:
            Q_in = P_useful / efficiency
        else:
            Q_in = P_useful
        
        # Compute temp_rise_rate based on load
        # Higher load = higher temp rise
        # If A_load > 1, temp rises faster
        A_load_local = P_useful / P_rated
        base_rise_rate = 0.1  # °C/s at no load
        # Increase rise rate quadratically when past rated
        if A_load_local > 1.0:
            temp_rise_rate = base_rise_rate + 0.3 * ((A_load_local - 1.0) ** 2)
        else:
            temp_rise_rate = base_rise_rate * A_load_local + 0.01
        
        # Update temperature
        temp_current += temp_rise_rate
        
        # Update histories
        output_history.append(P_useful)
        temp_history.append(temp_current)
        
        # Convert to numpy arrays
        output_hist_arr = np.array(output_history)
        temp_hist_arr = np.array(temp_history)
        
        # Compute RLE_real
        metrics = compute_rle_real(
            Q_in=Q_in,
            P_useful=P_useful,
            P_rated=P_rated,
            output_history=output_hist_arr,
            temp_current=temp_current,
            temp_limit=temp_limit,
            temp_history=temp_hist_arr,
            temp_rise_rate=temp_rise_rate,
            window_size=window_size
        )
        
        # Store values
        rle_values.append(metrics['RLE_real'])
        temp_values.append(temp_current)
        a_load_values.append(metrics['A_load'])
        all_metrics.append(metrics)
        times.append(t)
        
        t += 1
    
    # Identify collapse point - sustained decline from peak
    collapse_points = []
    if rle_values and len(rle_values) > 20:  # Need sufficient data
        # Find peak RLE
        max_rle = max(rle_values)
        max_rle_idx = rle_values.index(max_rle)
        
        # Look for sustained drop - after peak, find where it stays below threshold
        threshold_drop = 0.3  # 30% sustained drop from max indicates collapse
        
        # Start checking well after the peak
        for i in range(max_rle_idx + 10, len(rle_values)):
            # Check if RLE has dropped significantly and stays low
            recent_values = rle_values[max(i-5, 0):i+1]
            avg_recent = np.mean(recent_values) if recent_values else 0
            
            if avg_recent < max_rle - threshold_drop and a_load_values[i] > 1.0:
                collapse_points.append(i)
                break
    
    return rle_values, temp_values, a_load_values, all_metrics, times, collapse_points


def plot_results(
    rle_values: List[float],
    temp_values: List[float],
    a_load_values: List[float],
    times: List[float],
    collapse_points: List[int],
    save_path: str = 'rle_real_simulation.png'
):
    """
    Plot simulation results.
    
    Parameters:
    -----------
    rle_values : list of RLE_real values
    temp_values : list of temperature values
    a_load_values : list of A_load values
    times : list of time values
    collapse_points : list of indices where collapse occurs
    save_path : path to save the plot
    """
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # Plot 1: RLE_real over time
    axes[0].plot(times, rle_values, linewidth=2, color='blue')
    axes[0].axhline(y=max(rle_values), color='green', linestyle='--', alpha=0.5, label=f'Peak: {max(rle_values):.3f}')
    if collapse_points:
        collapse_idx_rle = collapse_points[0]
        axes[0].axvline(x=times[collapse_idx_rle], color='red', linestyle='--', alpha=0.7, linewidth=2)
        axes[0].plot(times[collapse_idx_rle], rle_values[collapse_idx_rle], 'ro', markersize=10, label=f'Collapse: t={times[collapse_idx_rle]:.0f}s')
    axes[0].set_xlabel('Time (s)')
    axes[0].set_ylabel('RLE_real')
    axes[0].set_title('RLE_real Over Time - Identifying Peak and Collapse')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    # Plot 2: Temperature over time
    axes[1].plot(times, temp_values, linewidth=2, color='red')
    axes[1].axhline(y=90, color='orange', linestyle='--', alpha=0.5, label='Temp Limit: 90°C')
    if collapse_points:
        collapse_idx_temp = collapse_points[0]
        axes[1].axvline(x=times[collapse_idx_temp], color='red', linestyle='--', alpha=0.7)
        axes[1].plot(times[collapse_idx_temp], temp_values[collapse_idx_temp], 'ro', markersize=10)
    axes[1].set_xlabel('Time (s)')
    axes[1].set_ylabel('Temperature (°C)')
    axes[1].set_title('Temperature Over Time')
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    # Plot 3: A_load over time
    axes[2].plot(times, a_load_values, linewidth=2, color='purple')
    axes[2].axhline(y=1.0, color='orange', linestyle='--', alpha=0.5, label='Rated Load: 1.0')
    if collapse_points:
        collapse_idx_load = collapse_points[0]
        axes[2].axvline(x=times[collapse_idx_load], color='red', linestyle='--', alpha=0.7)
        axes[2].plot(times[collapse_idx_load], a_load_values[collapse_idx_load], 'ro', markersize=10)
    axes[2].set_xlabel('Time (s)')
    axes[2].set_ylabel('A_load (relative to P_rated)')
    axes[2].set_title('Load Aggressiveness Over Time')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print("Plot saved to: {}".format(save_path))
    
    return fig


if __name__ == '__main__':
    print("Running RLE_real simulation...")
    print("=" * 60)
    
    # Run simulation
    rle_vals, temp_vals, a_load_vals, all_mets, times_vals, collapse_pts = simulate_device()
    
    # Print summary statistics
    print("\nSimulation Summary:")
    print("  Duration: {} seconds".format(len(times_vals)))
    print(f"  Peak RLE_real: {max(rle_vals):.4f} (at t={times_vals[rle_vals.index(max(rle_vals))]:.0f}s)")
    print(f"  Final RLE_real: {rle_vals[-1]:.4f}")
    print(f"  Maximum Temperature: {max(temp_vals):.2f}°C")
    print(f"  Maximum A_load: {max(a_load_vals):.4f}")
    
    if collapse_pts:
        collapse_idx = collapse_pts[0]
        print(f"\n  Collapse detected at t={times_vals[collapse_idx]:.0f}s")
        print(f"  RLE_real at collapse: {rle_vals[collapse_idx]:.4f}")
        print(f"  Temperature at collapse: {temp_vals[collapse_idx]:.2f}°C")
        print(f"  A_load at collapse: {a_load_vals[collapse_idx]:.4f}")
    else:
        print("\n  No significant collapse detected.")
    
    # Generate and save plots
    plot_results(rle_vals, temp_vals, a_load_vals, times_vals, collapse_pts)
    
    print("\nSimulation complete!")

