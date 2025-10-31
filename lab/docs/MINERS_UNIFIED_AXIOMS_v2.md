# MINER’S UNIFIED AXIOMS (RLE v2)

## Axiom 0 (Dimensionless Base)
All terms are dimensionless and referenced to θ; no wall-second dependence.

## Axiom I (Temporal Invariance)
RLE_θ and collapse parity are invariant to sampling rate changes after θ-normalization.

## Axiom II (Orthogonality of Substrate)
Local variations along Ξ_i minimally perturb Φ_substrate under steady load:
∂Φ/∂Ξ_i ≈ 0 for steady spans; channels remain weakly coupled.

## Axiom III (Boundedness)
Φ_substrate ∈ [0, 1+] with narrow headroom above 1 in high-SNR regimes; Ξ_H, Ξ_C ∈ [0,1]; Ξ_E ∈ [0,2].

## Axiom IV (Substrate Consistency)
For stable systems, mean(Φ_substrate) ≈ 1 ± ε (desktop ε ≲ 0.03).

## Axiom V (Collapse Independence)
Collapse detection is strictly tied to canonical RLE_θ; substrate/envelope do not alter the detector.

## Implementation Notes
- EMA clamps, spectral/τ_eff fallback, Δθ windowing rules
- Diagnostics computed append-only; envelope optional, diagnostic-only

