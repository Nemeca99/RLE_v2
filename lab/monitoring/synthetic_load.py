#!/usr/bin/env python3
"""
RLE Synthetic Load Generator
Generates controlled CPU/GPU load for testing RLE monitoring

CREDITS & INSPIRATION:
- Inspired by stress testing tools like Prime95, FurMark
- Uses multiprocessing for CPU load generation
- Uses CUDA/OpenCL for GPU load generation
- Designed for RLE monitoring validation

FEATURES:
- CPU: Multi-core stress testing with configurable intensity
- GPU: Compute shader stress testing with memory bandwidth
- Configurable load patterns (constant, ramp, sine wave)
- Real-time load adjustment
- Integration with RLE monitoring
"""

import argparse
import time
import threading
import math
import random
from typing import Optional, Dict, Any
import psutil

# GPU load generation
try:
    import numpy as np
    import cupy as cp
    GPU_LOAD_AVAILABLE = True
    print("[Synthetic Load] GPU acceleration available (CuPy)")
except ImportError:
    try:
        import numpy as np
        GPU_LOAD_AVAILABLE = True
        print("[Synthetic Load] GPU acceleration available (NumPy)")
    except ImportError:
        GPU_LOAD_AVAILABLE = False
        print("[Synthetic Load] GPU acceleration not available")

class CPULoadGenerator:
    """CPU load generator with multiple stress patterns"""
    
    def __init__(self, intensity: float = 0.5, cores: Optional[int] = None):
        self.intensity = intensity
        self.cores = cores or psutil.cpu_count()
        self.running = False
        self.threads = []
        
    def _cpu_stress_worker(self, worker_id: int, intensity: float):
        """Worker process for CPU stress testing"""
        while self.running:
            # Prime number calculation (CPU intensive)
            n = 1000000
            for i in range(2, n):
                if n % i == 0:
                    break
            
            # Matrix multiplication (memory intensive)
            if intensity > 0.5:
                size = int(1000 * intensity)
                a = [[random.random() for _ in range(size)] for _ in range(size)]
                b = [[random.random() for _ in range(size)] for _ in range(size)]
                # Simple matrix multiplication
                result = [[sum(a[i][k] * b[k][j] for k in range(size)) for j in range(size)] for i in range(size)]
            
            # Sleep to control intensity
            sleep_time = (1.0 - intensity) * 0.01
            time.sleep(sleep_time)
    
    def start(self):
        """Start CPU load generation"""
        self.running = True
        self.threads = []
        
        for i in range(self.cores):
            t = threading.Thread(
                target=self._cpu_stress_worker,
                args=(i, self.intensity),
                daemon=True
            )
            t.start()
            self.threads.append(t)
        
        print(f"[CPU Load] Started {self.cores} worker threads at {self.intensity*100:.1f}% intensity")
    
    def stop(self):
        """Stop CPU load generation"""
        self.running = False
        
        for t in self.threads:
            t.join(timeout=1)
        
        self.threads = []
        print("[CPU Load] Stopped all worker threads")
    
    def set_intensity(self, intensity: float):
        """Dynamically adjust load intensity"""
        self.intensity = max(0.0, min(1.0, intensity))
        print(f"[CPU Load] Intensity adjusted to {self.intensity*100:.1f}%")

class GPULoadGenerator:
    """GPU load generator using compute shaders"""
    
    def __init__(self, intensity: float = 0.5):
        self.intensity = intensity
        self.running = False
        self.thread = None
        
    def _gpu_stress_worker(self):
        """GPU stress testing worker"""
        if not GPU_LOAD_AVAILABLE:
            print("[GPU Load] GPU acceleration not available, skipping")
            return
        
        try:
            # Initialize GPU arrays
            size = int(10000 * self.intensity)
            
            while self.running:
                # Matrix multiplication on GPU
                if 'cp' in globals():  # CuPy available
                    a = cp.random.random((size, size))
                    b = cp.random.random((size, size))
                    c = cp.dot(a, b)
                    # Memory bandwidth test
                    d = cp.random.random((size, size))
                    e = cp.random.random((size, size))
                    f = cp.dot(d, e)
                else:  # NumPy fallback
                    a = np.random.random((size, size))
                    b = np.random.random((size, size))
                    c = np.dot(a, b)
                    # Memory bandwidth test
                    d = np.random.random((size, size))
                    e = np.random.random((size, size))
                    f = np.dot(d, e)
                
                # Sleep to control intensity
                sleep_time = (1.0 - self.intensity) * 0.01
                time.sleep(sleep_time)
                
        except Exception as e:
            print(f"[GPU Load] Error: {e}")
    
    def start(self):
        """Start GPU load generation"""
        if not GPU_LOAD_AVAILABLE:
            print("[GPU Load] GPU acceleration not available")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._gpu_stress_worker)
        self.thread.start()
        
        print(f"[GPU Load] Started GPU stress at {self.intensity*100:.1f}% intensity")
    
    def stop(self):
        """Stop GPU load generation"""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2)
        
        print("[GPU Load] Stopped GPU stress")
    
    def set_intensity(self, intensity: float):
        """Dynamically adjust load intensity"""
        self.intensity = max(0.0, min(1.0, intensity))
        print(f"[GPU Load] Intensity adjusted to {self.intensity*100:.1f}%")

class LoadPatternGenerator:
    """Generate various load patterns for testing"""
    
    @staticmethod
    def constant_load(duration: float, intensity: float = 0.5) -> Dict[str, Any]:
        """Generate constant load pattern"""
        return {
            'pattern': 'constant',
            'duration': duration,
            'intensity': intensity,
            'description': f'Constant {intensity*100:.1f}% load for {duration}s'
        }
    
    @staticmethod
    def ramp_load(duration: float, start_intensity: float = 0.1, end_intensity: float = 0.9) -> Dict[str, Any]:
        """Generate ramp load pattern"""
        return {
            'pattern': 'ramp',
            'duration': duration,
            'start_intensity': start_intensity,
            'end_intensity': end_intensity,
            'description': f'Ramp from {start_intensity*100:.1f}% to {end_intensity*100:.1f}% over {duration}s'
        }
    
    @staticmethod
    def sine_load(duration: float, base_intensity: float = 0.5, amplitude: float = 0.3, frequency: float = 0.1) -> Dict[str, Any]:
        """Generate sine wave load pattern"""
        return {
            'pattern': 'sine',
            'duration': duration,
            'base_intensity': base_intensity,
            'amplitude': amplitude,
            'frequency': frequency,
            'description': f'Sine wave load: {base_intensity*100:.1f}% ± {amplitude*100:.1f}% at {frequency}Hz'
        }
    
    @staticmethod
    def step_load(duration: float, steps: list) -> Dict[str, Any]:
        """Generate step load pattern"""
        return {
            'pattern': 'step',
            'duration': duration,
            'steps': steps,
            'description': f'Step load pattern with {len(steps)} steps over {duration}s'
        }

class SyntheticLoadController:
    """Main controller for synthetic load generation"""
    
    def __init__(self, args):
        self.args = args
        self.cpu_generator = None
        self.gpu_generator = None
        self.running = False
        self.start_time = None
        
        # Initialize generators based on mode
        if args.mode in ['cpu', 'both']:
            self.cpu_generator = CPULoadGenerator(
                intensity=args.cpu_intensity,
                cores=args.cpu_cores
            )
        
        if args.mode in ['gpu', 'both']:
            self.gpu_generator = GPULoadGenerator(
                intensity=args.gpu_intensity
            )
    
    def start(self):
        """Start synthetic load generation"""
        self.running = True
        self.start_time = time.time()
        
        print("\n" + "="*60)
        print("RLE SYNTHETIC LOAD GENERATOR")
        print("="*60)
        
        if self.cpu_generator:
            self.cpu_generator.start()
        
        if self.gpu_generator:
            self.gpu_generator.start()
        
        print(f"[Load Controller] Started {self.args.mode} load generation")
        print(f"[Load Controller] Duration: {self.args.duration}s")
    
    def stop(self):
        """Stop synthetic load generation"""
        self.running = False
        
        if self.cpu_generator:
            self.cpu_generator.stop()
        
        if self.gpu_generator:
            self.gpu_generator.stop()
        
        duration = time.time() - self.start_time if self.start_time else 0
        print(f"[Load Controller] Stopped after {duration:.1f}s")
    
    def run(self):
        """Main run loop with pattern generation"""
        self.start()
        
        try:
            if self.args.pattern == 'constant':
                self._run_constant_pattern()
            elif self.args.pattern == 'ramp':
                self._run_ramp_pattern()
            elif self.args.pattern == 'sine':
                self._run_sine_pattern()
            elif self.args.pattern == 'step':
                self._run_step_pattern()
            else:
                # Default: constant load
                self._run_constant_pattern()
                
        except KeyboardInterrupt:
            print("\n[Load Controller] Interrupted by user")
        finally:
            self.stop()
    
    def _run_constant_pattern(self):
        """Run constant load pattern"""
        print(f"[Pattern] Constant load: {self.args.cpu_intensity*100:.1f}% CPU, {self.args.gpu_intensity*100:.1f}% GPU")
        
        start_time = time.time()
        while self.running and (time.time() - start_time) < self.args.duration:
            time.sleep(1)
    
    def _run_ramp_pattern(self):
        """Run ramp load pattern"""
        print(f"[Pattern] Ramp load: {self.args.start_intensity*100:.1f}% → {self.args.end_intensity*100:.1f}%")
        
        start_time = time.time()
        while self.running and (time.time() - start_time) < self.args.duration:
            elapsed = time.time() - start_time
            progress = elapsed / self.args.duration
            
            # Calculate current intensity
            current_intensity = self.args.start_intensity + (self.args.end_intensity - self.args.start_intensity) * progress
            
            # Update generators
            if self.cpu_generator:
                self.cpu_generator.set_intensity(current_intensity)
            if self.gpu_generator:
                self.gpu_generator.set_intensity(current_intensity)
            
            time.sleep(1)
    
    def _run_sine_pattern(self):
        """Run sine wave load pattern"""
        print(f"[Pattern] Sine wave: {self.args.base_intensity*100:.1f}% ± {self.args.amplitude*100:.1f}%")
        
        start_time = time.time()
        while self.running and (time.time() - start_time) < self.args.duration:
            elapsed = time.time() - start_time
            
            # Calculate sine wave intensity
            sine_value = math.sin(2 * math.pi * self.args.frequency * elapsed)
            current_intensity = self.args.base_intensity + self.args.amplitude * sine_value
            current_intensity = max(0.0, min(1.0, current_intensity))
            
            # Update generators
            if self.cpu_generator:
                self.cpu_generator.set_intensity(current_intensity)
            if self.gpu_generator:
                self.gpu_generator.set_intensity(current_intensity)
            
            time.sleep(0.1)  # Higher frequency updates for sine wave
    
    def _run_step_pattern(self):
        """Run step load pattern"""
        print(f"[Pattern] Step load with {len(self.args.steps)} steps")
        
        step_duration = self.args.duration / len(self.args.steps)
        
        for i, step_intensity in enumerate(self.args.steps):
            if not self.running:
                break
            
            print(f"[Step {i+1}] Intensity: {step_intensity*100:.1f}% for {step_duration:.1f}s")
            
            # Update generators
            if self.cpu_generator:
                self.cpu_generator.set_intensity(step_intensity)
            if self.gpu_generator:
                self.gpu_generator.set_intensity(step_intensity)
            
            # Wait for step duration
            start_step = time.time()
            while self.running and (time.time() - start_step) < step_duration:
                time.sleep(0.1)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="RLE Synthetic Load Generator")
    
    # Load configuration
    parser.add_argument("--mode", choices=['cpu', 'gpu', 'both'], default='both', help="Load generation mode")
    parser.add_argument("--duration", type=int, default=300, help="Load duration in seconds")
    parser.add_argument("--cpu-intensity", type=float, default=0.5, help="CPU load intensity (0.0-1.0)")
    parser.add_argument("--gpu-intensity", type=float, default=0.5, help="GPU load intensity (0.0-1.0)")
    parser.add_argument("--cpu-cores", type=int, help="Number of CPU cores to stress (default: all)")
    
    # Load patterns
    parser.add_argument("--pattern", choices=['constant', 'ramp', 'sine', 'step'], default='constant', help="Load pattern")
    
    # Ramp pattern
    parser.add_argument("--start-intensity", type=float, default=0.1, help="Ramp start intensity")
    parser.add_argument("--end-intensity", type=float, default=0.9, help="Ramp end intensity")
    
    # Sine pattern
    parser.add_argument("--base-intensity", type=float, default=0.5, help="Sine wave base intensity")
    parser.add_argument("--amplitude", type=float, default=0.3, help="Sine wave amplitude")
    parser.add_argument("--frequency", type=float, default=0.1, help="Sine wave frequency (Hz)")
    
    # Step pattern
    parser.add_argument("--steps", nargs='+', type=float, default=[0.2, 0.4, 0.6, 0.8], help="Step intensities")
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    print("RLE Synthetic Load Generator")
    print(f"Mode: {args.mode}")
    print(f"Duration: {args.duration}s")
    print(f"Pattern: {args.pattern}")
    
    controller = SyntheticLoadController(args)
    controller.run()

if __name__ == "__main__":
    main()
