#!/usr/bin/env python3
"""
RID Training Monitor - Original Purpose

Maps RID framework to AI model training metrics.

Original 4 training variables:
- grad_norm: Gradient magnitude
- loss: Training loss
- learning_rate: LR schedule
- epoch: Training progress

RID mapping for training domain:
- RLE (Efficiency): How efficiently is the model learning?
- LTP (Structure): Does the model have capacity to continue?
- RSR (Fidelity): Is gradient signal reliable?
- S_n: Overall training health (is training working?)

Goal: Single score that answers "Is my training working?"
Instead of staring at 4 meaningless numbers.
"""

from dataclasses import dataclass
from typing import List, Optional
import math


@dataclass
class TrainingHealthResult:
    """RID health score for model training"""
    
    # Core RID invariants (training domain)
    RLE: float  # Learning efficiency
    LTP: float  # Capacity to continue
    RSR: float  # Gradient fidelity
    S_n: float  # Training health score
    
    # Raw metrics
    grad_norm: float
    loss: float
    learning_rate: float
    epoch: int
    
    # Weights
    w_efficiency: float
    w_structure: float
    w_fidelity: float
    
    # Diagnostics
    training_state: str  # "healthy", "struggling", "failing", "diverging"
    alerts: str


class RIDTrainingMonitor:
    """
    RID framework applied to AI model training
    
    Dimensionless mapping:
    - RLE = learning efficiency (loss improvement rate)
    - LTP = structural capacity (gradient stability vs magnitude)
    - RSR = signal fidelity (gradient consistency)
    """
    
    def __init__(self,
                 expected_final_loss: float = 0.5,
                 max_grad_norm: float = 10.0,
                 initial_lr: float = 1e-4,
                 total_epochs: int = 10):
        
        self.expected_final_loss = expected_final_loss
        self.max_grad_norm = max_grad_norm
        self.initial_lr = initial_lr
        self.total_epochs = total_epochs
        
        # History for computing rates of change
        self.loss_history: List[float] = []
        self.grad_norm_history: List[float] = []
        self.epoch_history: List[int] = []
    
    def compute_health(self,
                      grad_norm: float,
                      loss: float,
                      learning_rate: float,
                      epoch: int) -> TrainingHealthResult:
        """
        Compute training health score from current metrics
        
        Args:
            grad_norm: Gradient L2 norm
            loss: Current training loss
            learning_rate: Current LR
            epoch: Current epoch number
            
        Returns:
            TrainingHealthResult with S_n and diagnostics
        """
        
        # Update histories
        self.loss_history.append(loss)
        self.grad_norm_history.append(grad_norm)
        self.epoch_history.append(epoch)
        
        # === RLE: Learning Efficiency ===
        # "How efficiently is the model learning?"
        # Higher when loss is decreasing steadily
        
        if len(self.loss_history) < 2:
            RLE = 0.5  # Neutral at start
        else:
            # Loss improvement rate
            recent_losses = self.loss_history[-5:] if len(self.loss_history) >= 5 else self.loss_history
            if len(recent_losses) >= 2:
                loss_slope = (recent_losses[-1] - recent_losses[0]) / len(recent_losses)
                # Normalize: negative slope (improving) → high RLE
                # Positive slope (degrading) → low RLE
                improvement = -loss_slope / max(recent_losses[0], 0.01)
                RLE = 1.0 / (1.0 + math.exp(-10 * improvement))  # Sigmoid
            else:
                RLE = 0.5
        
        # Clamp
        RLE = max(0.0, min(1.0, RLE))
        
        # === LTP: Structural Capacity ===
        # "Does the model have capacity to continue learning?"
        # Higher when gradients are stable (not exploding)
        
        grad_stability = 1.0 - min(1.0, grad_norm / self.max_grad_norm)
        
        # Learning rate headroom (higher LR = more capacity)
        lr_headroom = learning_rate / self.initial_lr
        
        # Epoch headroom (earlier in training = more capacity)
        epoch_progress = epoch / self.total_epochs
        epoch_headroom = 1.0 - epoch_progress
        
        # Structure = geometric mean
        LTP = (grad_stability * lr_headroom * epoch_headroom) ** (1.0/3.0)
        LTP = max(0.0, min(1.0, LTP))
        
        # === RSR: Gradient Signal Fidelity ===
        # "Is the gradient signal reliable?"
        # Higher when gradients are consistent (low variance)
        
        if len(self.grad_norm_history) < 5:
            RSR = 1.0  # Assume good at start
        else:
            recent_grads = self.grad_norm_history[-10:]
            mean_grad = sum(recent_grads) / len(recent_grads)
            variance = sum((g - mean_grad)**2 for g in recent_grads) / len(recent_grads)
            std = math.sqrt(variance)
            
            # Coefficient of variation (relative noise)
            cv = std / max(mean_grad, 1e-6)
            
            # Low CV → high fidelity
            RSR = 1.0 / (1.0 + cv)
            RSR = max(0.0, min(1.0, RSR))
        
        # === WEIGHTS (based on training intensity) ===
        
        # Efficiency weight: How much are we learning?
        w_efficiency = min(1.0, loss / 5.0)  # Higher loss = more focus on efficiency
        
        # Structure weight: How stressed are gradients?
        w_structure = min(1.0, grad_norm / self.max_grad_norm)
        
        # Fidelity weight: Always important
        w_fidelity = 0.5
        
        # Normalize
        total = w_efficiency + w_structure + w_fidelity
        w_efficiency /= total
        w_structure /= total
        w_fidelity /= total
        
        # === TRAINING HEALTH SCORE ===
        S_n = w_efficiency * RLE + w_structure * LTP + w_fidelity * RSR
        
        # === DIAGNOSTICS ===
        training_state = self._classify_training_state(S_n, RLE, LTP, RSR, grad_norm, loss)
        alerts = self._generate_alerts(S_n, RLE, LTP, RSR, grad_norm, loss)
        
        return TrainingHealthResult(
            RLE=RLE,
            LTP=LTP,
            RSR=RSR,
            S_n=S_n,
            grad_norm=grad_norm,
            loss=loss,
            learning_rate=learning_rate,
            epoch=epoch,
            w_efficiency=w_efficiency,
            w_structure=w_structure,
            w_fidelity=w_fidelity,
            training_state=training_state,
            alerts=alerts
        )
    
    def _classify_training_state(self, S_n, RLE, LTP, RSR, grad_norm, loss):
        """Classify current training state"""
        
        if S_n > 0.7:
            return "healthy"
        elif S_n > 0.5:
            if RLE < 0.5:
                return "struggling (not learning efficiently)"
            elif LTP < 0.5:
                return "struggling (gradients unstable)"
            else:
                return "struggling (signal noise)"
        elif S_n > 0.3:
            if grad_norm > self.max_grad_norm * 0.8:
                return "failing (gradient explosion)"
            elif loss > self.loss_history[0] if self.loss_history else False:
                return "failing (loss diverging)"
            else:
                return "failing (multiple issues)"
        else:
            return "diverging (abort training)"
    
    def _generate_alerts(self, S_n, RLE, LTP, RSR, grad_norm, loss):
        """Generate training alerts"""
        
        alerts = []
        
        if S_n < 0.3:
            alerts.append("ABORT: Training diverging")
        elif S_n < 0.5:
            alerts.append("WARNING: Training struggling")
        
        if RLE < 0.3:
            alerts.append("Not learning (reduce LR or check data)")
        
        if LTP < 0.3:
            alerts.append("Gradients unstable (reduce LR or clip grads)")
        
        if RSR < 0.5:
            alerts.append("Noisy gradients (increase batch size)")
        
        if grad_norm > self.max_grad_norm:
            alerts.append(f"Gradient explosion ({grad_norm:.2f} > {self.max_grad_norm})")
        
        return " | ".join(alerts) if alerts else ""


# === DEMO / TEST ===

if __name__ == "__main__":
    print("RID Training Monitor - Original Purpose")
    print("=" * 80)
    print()
    print("Simulating model training scenarios...")
    print()
    
    monitor = RIDTrainingMonitor(
        expected_final_loss=0.5,
        max_grad_norm=10.0,
        initial_lr=1e-4,
        total_epochs=10
    )
    
    # Simulate training scenarios
    print(f"{'Epoch':<6} {'Loss':<8} {'GradNorm':<10} {'LR':<10} | {'RLE':<6} {'LTP':<6} {'RSR':<6} {'S_n':<6} | {'State':<30}")
    print("-" * 110)
    
    # Scenario 1: Healthy training
    scenarios = [
        # Epoch, Loss, GradNorm, LR, Description
        (1, 3.5, 2.0, 1e-4, "Initial"),
        (2, 2.8, 1.8, 1e-4, "Learning"),
        (3, 2.1, 1.5, 1e-4, "Improving"),
        (4, 1.6, 1.2, 9e-5, "Converging"),
        (5, 1.2, 0.9, 8e-5, "Healthy"),
        
        # Scenario 2: Gradient explosion
        (6, 1.1, 5.0, 7e-5, "Warning"),
        (7, 1.3, 12.0, 6e-5, "Explosion"),
        
        # Scenario 3: Plateau/not learning
        (8, 1.35, 0.5, 5e-5, "Plateau"),
        (9, 1.34, 0.5, 4e-5, "Stuck"),
        (10, 1.33, 0.5, 3e-5, "Not learning"),
    ]
    
    for epoch, loss, grad_norm, lr, desc in scenarios:
        result = monitor.compute_health(grad_norm, loss, lr, epoch)
        
        print(f"{epoch:<6} {loss:<8.2f} {grad_norm:<10.2f} {lr:<10.2e} | "
              f"{result.RLE:<6.3f} {result.LTP:<6.3f} {result.RSR:<6.3f} {result.S_n:<6.3f} | "
              f"{result.training_state:<30}")
        
        if result.alerts:
            print(f"       ALERT: {result.alerts}")
    
    print()
    print("=" * 110)
    print()
    print("Interpretation:")
    print("  S_n > 0.7: Training is healthy (continue)")
    print("  S_n 0.5-0.7: Training is struggling (monitor closely)")
    print("  S_n 0.3-0.5: Training is failing (adjust hyperparameters)")
    print("  S_n < 0.3: Training is diverging (abort and restart)")
    print()
    print("This gives you ONE number to watch instead of 4 meaningless metrics.")
