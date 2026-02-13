# RID for Model Training - Integration Guide

**Purpose**: Monitor AI training health with single score instead of 4 meaningless metrics

---

## The Problem You're Solving

**During model training, you see**:
```
Epoch 5/10
loss: 2.341
grad_norm: 3.52
learning_rate: 0.0001
```

**You think**: "Is this good? Is training working? Should I stop?"

**You don't know** because these numbers are meaningless without context.

---

## The Solution (RID)

**One number**: `S_n = 0.76` → "Training is healthy, continue"

**Interpretati on**:
- S_n > 0.7: ✅ Healthy (keep going)
- S_n 0.5-0.7: ⚠️ Struggling (monitor)
- S_n 0.3-0.5: 🚨 Failing (adjust hyperparameters)
- S_n < 0.3: 🛑 Diverging (abort now)

---

## Integration with Your Training Code

### Option 1: Live Monitoring (During Training)

```python
from lab.monitoring.rid_training_monitor import RIDTrainingMonitor

# Initialize monitor
rid = RIDTrainingMonitor(
    expected_final_loss=0.5,
    max_grad_norm=10.0,
    initial_lr=1e-4,
    total_epochs=10
)

# Inside your training loop
for epoch in range(num_epochs):
    for batch in dataloader:
        # ... your training code ...
        
        # Compute gradients
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=10.0)
        
        # Update with optimizer
        optimizer.step()
        
        # === RID MONITORING ===
        health = rid.compute_health(
            grad_norm=float(grad_norm),
            loss=float(loss.item()),
            learning_rate=optimizer.param_groups[0]['lr'],
            epoch=epoch
        )
        
        # Check if training should stop
        if health.S_n < 0.3:
            print(f"🛑 ABORT: {health.training_state}")
            print(f"   {health.alerts}")
            break  # Stop training
        
        # Log single number
        print(f"Epoch {epoch}, Batch {i}: S_n={health.S_n:.3f} ({health.training_state})")
```

### Option 2: Post-Training Analysis (From Logs)

```python
from lab.monitoring.rid_training_monitor import RIDTrainingMonitor
import pandas as pd

# Load your training logs
df = pd.read_csv('training_log.csv')

# Initialize monitor
rid = RIDTrainingMonitor()

# Compute health for each step
health_scores = []

for _, row in df.iterrows():
    health = rid.compute_health(
        grad_norm=row['grad_norm'],
        loss=row['loss'],
        learning_rate=row['lr'],
        epoch=row['epoch']
    )
    health_scores.append(health.S_n)

# Plot
import matplotlib.pyplot as plt
plt.plot(health_scores)
plt.axhline(y=0.7, color='g', linestyle='--', label='Healthy')
plt.axhline(y=0.5, color='y', linestyle='--', label='Warning')
plt.axhline(y=0.3, color='r', linestyle='--', label='Critical')
plt.ylabel('Training Health (S_n)')
plt.xlabel('Step')
plt.legend()
plt.savefig('training_health.png')
```

---

## What It Tells You

### When S_n Drops

**RLE drops** → Not learning efficiently
- **Action**: Reduce learning rate or check data quality

**LTP drops** → Gradients unstable or out of headroom
- **Action**: Clip gradients, reduce LR, or check architecture

**RSR drops** → Noisy/inconsistent gradients
- **Action**: Increase batch size or add gradient smoothing

---

## Real Use Case

**Your Unsloth training**:
```python
# Add to your training script
from lab.monitoring.rid_training_monitor import RIDTrainingMonitor

rid = RIDTrainingMonitor()

# Inside Unsloth training callback
def training_step_callback(grad_norm, loss, lr, epoch):
    health = rid.compute_health(grad_norm, loss, lr, epoch)
    
    # Log to CSV
    log_training_health(epoch, health.S_n, health.training_state)
    
    # Early stopping
    if health.S_n < 0.3:
        raise TrainingDivergenceError(health.alerts)
    
    return health.S_n
```

---

## Validation (What You Need to Do)

**Test on your actual Unsloth training runs**:

1. Add RID monitoring to training loop
2. Run 5-10 training experiments
3. Check if S_n correctly identifies:
   - ✅ Good runs (S_n stays > 0.7)
   - 🚨 Bad runs (S_n drops < 0.5)
   - 🛑 Diverging runs (S_n < 0.3 before explosion)

**If it does** → Framework works for original purpose

**If it doesn't** → Adjust metric mappings

---

## This is What RID Was For

Not thermal monitoring. Not universal geometry.

**Model training health monitoring.**

"Is my AI training working?" → S_n = 0.76 → "Yes, continue."

That's it. Simple. Practical. Dimensionless.

---

**Ready to test when you have real training logs.**
