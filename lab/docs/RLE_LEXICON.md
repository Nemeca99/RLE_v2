# RLE Lexicon: Terminology & Symbol Definitions

## Overview

This document defines every recurring symbol, term, and concept in the RLE system. It draws a clear boundary between metaphorical language and quantitative measurements, providing precise technical definitions for all RLE terminology.

## Core RLE Symbols

### Primary Formula Symbols
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `RLE` | Recursive Load Efficiency | `(η × σ) / (α × (1 + 1/τ))` | dimensionless | 0.0 - 1.0 |
| `η` | Utilization | CPU utilization percentage | dimensionless | 0.0 - 1.0 |
| `σ` | Stability | Inverse of rolling standard deviation | dimensionless | 0.1 - 10.0 |
| `α` | Load Factor | Power consumption / baseline gaming power | dimensionless | 0.5 - 2.0 |
| `τ` | Sustainability Time Constant | Thermal time constant | seconds | 10 - 1000 |

### Efficiency Components
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `E_th` | Thermal Efficiency | `σ / (1 + 1/τ)` | dimensionless | 0.0 - 1.0 |
| `E_pw` | Power Efficiency | `η / α` | dimensionless | 0.0 - 2.0 |
| `RLE_norm` | Normalized RLE | `RLE / RLE_max` | dimensionless | 0.0 - 1.0 |

## Thermal System Symbols

### Temperature Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `T` | Temperature | Current device temperature | °C | 20 - 100 |
| `T_limit` | Thermal Limit | Manufacturer-specified maximum | °C | 80 - 100 |
| `T_ambient` | Ambient Temperature | Room temperature | °C | 20 - 30 |
| `T_baseline` | Baseline Temperature | Reference gaming temperature | °C | 40 - 60 |

### Thermal Properties
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `C_th` | Thermal Capacitance | Heat storage capacity | J/K | 100 - 10000 |
| `G_th` | Thermal Conductance | Heat transfer rate | W/K | 0.1 - 10.0 |
| `τ_th` | Thermal Time Constant | `C_th / G_th` | seconds | 10 - 1000 |

## Power System Symbols

### Power Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `P` | Power | Current power consumption | W | 10 - 500 |
| `P_baseline` | Baseline Power | Reference gaming power | W | 50 - 200 |
| `P_limit` | Power Limit | Maximum allowed power | W | 100 - 500 |
| `P_useful` | Useful Power | Power converted to useful work | W | 5 - 400 |

### Power Ratios
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `α` | Load Factor | `P / P_baseline` | dimensionless | 0.5 - 2.0 |
| `η_power` | Power Efficiency | `P_useful / P` | dimensionless | 0.1 - 0.9 |

## Performance Symbols

### Utilization Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `util` | Utilization | CPU utilization percentage | % | 0 - 100 |
| `util_pct` | Utilization Percentage | `util × 100` | % | 0 - 100 |
| `η` | Normalized Utilization | `util / 100` | dimensionless | 0.0 - 1.0 |

### Frequency Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `f` | Frequency | Current operating frequency | GHz | 0.2 - 5.0 |
| `f_max` | Maximum Frequency | Maximum allowed frequency | GHz | 1.0 - 5.0 |
| `f_baseline` | Baseline Frequency | Reference gaming frequency | GHz | 2.0 - 4.0 |

## Collapse Detection Symbols

### Collapse Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `collapse` | Collapse Flag | Binary collapse indicator | boolean | 0, 1 |
| `collapse_rate` | Collapse Rate | Collapses per second | s⁻¹ | -0.01 - 0.01 |
| `rolling_peak` | Rolling Peak | Adaptive reference with decay | dimensionless | 0.0 - 1.0 |

### Detection Thresholds
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `threshold` | Collapse Threshold | 65% of rolling peak | dimensionless | 0.4 - 0.7 |
| `hysteresis` | Hysteresis | 7-second minimum duration | seconds | 5 - 10 |
| `evidence_gate` | Evidence Gate | Thermal OR power evidence required | boolean | 0, 1 |

## Scaling Model Symbols

### Scaling Exponents
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `β` | Power Scaling Exponent | Power scaling factor | dimensionless | 0.1 - 0.2 |
| `γ` | Temperature Scaling Exponent | Temperature scaling factor | dimensionless | 0.05 - 0.15 |
| `δ` | Time Scaling Exponent | Time constant scaling factor | dimensionless | 0.05 - 0.15 |

### Universal Constants
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `σ_universal` | Universal Scaling | Cross-domain RLE standard deviation | dimensionless | 0.15 - 0.20 |
| `κ` | Coupling Coefficient | Thermal coupling strength | dimensionless | 0.0 - 1.0 |
| `C_coupling` | Coupling Constant | Thermal interaction factor | dimensionless | 0.0 - 0.5 |

## Control System Symbols

### Control States
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `state` | Control State | Current control mode | enum | 0-4 |
| `throttle_level` | Throttle Level | Current throttling percentage | % | 0 - 100 |
| `fan_speed` | Fan Speed | Cooling fan speed | % | 0 - 100 |

### Control Parameters
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `K_p` | Proportional Gain | Control response gain | dimensionless | 0.1 - 2.0 |
| `K_i` | Integral Gain | Integral control gain | dimensionless | 0.01 - 0.5 |
| `K_d` | Derivative Gain | Derivative control gain | dimensionless | 0.001 - 0.1 |

## Mobile System Symbols

### Mobile-Specific Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `P_mobile` | Mobile Power | Mobile device power consumption | W | 1 - 10 |
| `T_mobile` | Mobile Temperature | Mobile device temperature | °C | 25 - 50 |
| `τ_mobile` | Mobile Time Constant | Mobile thermal time constant | seconds | 10 - 100 |

### Mobile Constants
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `β_mobile` | Mobile Power Scaling | Mobile power scaling exponent | dimensionless | 0.1 - 0.15 |
| `γ_mobile` | Mobile Temp Scaling | Mobile temperature scaling exponent | dimensionless | 0.05 - 0.10 |
| `σ_mobile` | Mobile Scaling | Mobile RLE standard deviation | dimensionless | 0.15 - 0.20 |

## Philosophical Symbols (From Appendices)

### Miner's Law Terms
| Symbol | Name | Definition | Status | Notes |
|--------|------|------------|--------|-------|
| `RIS` | Recursive Information System | Thermal feedback loop metaphor | Symbolic | Philosophical concept |
| `Q-RAM` | Quantum RAM | Thermal memory system concept | Symbolic | Theoretical framework |
| `Q-Storage` | Quantum Storage | Thermal storage concept | Symbolic | Theoretical framework |
| `RCF` | Recursive Feedback Constant | Feedback stabilization factor | Quantitative | Maps to hysteresis |

### Entropy Terms
| Symbol | Name | Definition | Status | Notes |
|--------|------|------------|--------|-------|
| `S` | Entropy | Thermal state disorder | Symbolic | Philosophical concept |
| `dS/dt` | Entropy Rate | Rate of thermal state change | Symbolic | Philosophical concept |
| `S_mod` | Entropy Modulation | Thermal state control | Symbolic | Philosophical concept |

## Measurement Symbols

### Sensor Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `sensor_temp` | Sensor Temperature | Raw temperature reading | °C | 0 - 150 |
| `sensor_power` | Sensor Power | Raw power reading | W | 0 - 1000 |
| `sensor_util` | Sensor Utilization | Raw utilization reading | % | 0 - 100 |

### Calibration Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `cal_temp` | Temperature Calibration | Temperature sensor calibration | °C | ±2 |
| `cal_power` | Power Calibration | Power sensor calibration | W | ±5 |
| `cal_util` | Utilization Calibration | Utilization sensor calibration | % | ±2 |

## Data Processing Symbols

### Window Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `window_size` | Window Size | Rolling window length | samples | 5 - 30 |
| `rolling_avg` | Rolling Average | Moving average over window | dimensionless | 0.0 - 1.0 |
| `rolling_std` | Rolling Standard Deviation | Moving std dev over window | dimensionless | 0.01 - 0.5 |

### Smoothing Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `smoothing_factor` | Smoothing Factor | Exponential smoothing coefficient | dimensionless | 0.1 - 0.9 |
| `decay_factor` | Decay Factor | Rolling peak decay rate | dimensionless | 0.99 - 0.999 |

## Validation Symbols

### Accuracy Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `accuracy` | Accuracy | Measurement accuracy | % | 95 - 99.9 |
| `precision` | Precision | Measurement precision | % | 90 - 99 |
| `resolution` | Resolution | Measurement resolution | bits | 8 - 16 |

### Error Terms
| Symbol | Name | Definition | Units | Range |
|--------|------|------------|-------|-------|
| `error` | Error | Measurement error | % | 0.1 - 5.0 |
| `bias` | Bias | Systematic measurement bias | % | -2.0 - 2.0 |
| `drift` | Drift | Long-term measurement drift | %/hour | -0.1 - 0.1 |

## Boundary Definitions

### Symbolic vs Quantitative
- **Symbolic**: Philosophical concepts, metaphors, theoretical frameworks
- **Quantitative**: Measurable quantities, testable predictions, empirical data

### Metaphor vs Measurement
- **Metaphor**: "Thermal breathing", "entropy modulation", "recursive feedback"
- **Measurement**: Temperature (°C), power (W), utilization (%), time (s)

### Theoretical vs Empirical
- **Theoretical**: Derived from first principles, mathematical models
- **Empirical**: Measured from real systems, validated through data

## Usage Guidelines

### Symbol Consistency
- Use Greek letters for dimensionless ratios (η, σ, α, τ)
- Use Latin letters for dimensional quantities (T, P, f)
- Use subscripts for variants (T_limit, P_baseline, f_max)

### Unit Conventions
- Temperature: Celsius (°C)
- Power: Watts (W)
- Time: Seconds (s)
- Frequency: Gigahertz (GHz)
- Ratios: Dimensionless (0.0 - 1.0)

### Precision Standards
- RLE values: 3 decimal places (0.123)
- Temperature: 1 decimal place (45.6°C)
- Power: 1 decimal place (123.4W)
- Time: 1 decimal place (12.3s)

## Conclusion

This lexicon provides precise definitions for all RLE terminology, distinguishing between symbolic concepts and quantitative measurements. It enables clear communication about RLE concepts while maintaining the philosophical depth of the original work.

Key categories:
- **Core RLE symbols**: Primary formula components
- **Thermal symbols**: Temperature and thermal properties
- **Power symbols**: Power consumption and efficiency
- **Performance symbols**: Utilization and frequency
- **Collapse detection**: Detection algorithms and thresholds
- **Scaling model**: Cross-domain scaling equations
- **Control systems**: Predictive thermal management
- **Mobile systems**: Mobile-specific adaptations
- **Philosophical symbols**: Miner's Law and entropy concepts
- **Measurement symbols**: Sensors and calibration
- **Data processing**: Windows and smoothing
- **Validation symbols**: Accuracy and error terms

This enables RLE to serve as a comprehensive thermal efficiency standard with precise terminology.

---

*For the mathematical foundations, see [RLE_MATH_FOUNDATIONS.md](RLE_MATH_FOUNDATIONS.md). For the control system specification, see [RLE_CONTROL_SPEC.md](RLE_CONTROL_SPEC.md).*
