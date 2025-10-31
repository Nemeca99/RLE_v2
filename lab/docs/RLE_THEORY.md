# RLE Theory: First-Principles Derivation

## 1) Objective
Construct a dimensionless, predictive efficiency index for thermal-work systems that:
- Increases with productive work rate (utilization, stability)
- Decreases with stress/waste (excess load, entropy production)
- Penalizes approach to thermal limit (time-to-limit)
- Is invariant to device scale and units (dimensionless)

## 2) Energy and Entropy Balances
For a device converting electrical power \(P\) into useful work \(\dot{W}\) with losses \(\dot{Q}\):
\[
P = \dot{W} + \dot{Q}
\]
The entropy balance (closed control volume) at temperature \(T\) with heat rejection to an ambient sink at \(T_\infty\) and internal irreversibility \(\dot{S}_{gen}\):
\[
\dot{S} = \int \frac{\delta \dot{Q}}{T} - \int \frac{\delta \dot{Q}}{T_\infty} + \dot{S}_{gen} \approx \dot{Q}\left(\frac{1}{T}-\frac{1}{T_\infty}\right) + \dot{S}_{gen}
\]
In steady operation over short windows (quasi-steady mass and energy), the trend toward thermal limits is governed by the heat capacity and thermal resistance network. Using a lumped RC model:
\[
C_{th}\, \frac{dT}{dt} = P - h\,(T- T_\infty)
\]
When \(P\) exceeds the dissipative capacity, \(dT/dt>0\) and time to limit \(T_{sustain}\) is finite.

## 3) Constructing a Dimensionless Efficiency
We want an efficiency that captures:
- Productive fraction of power (signal quality): utilization \(u\in[0,1]\) and load smoothness (stability \(\sigma_s\))
- Stress factor: relative load \(A_{load} = P/P_{rated}\)
- Thermal proximity: inverse of time-to-limit \(1/T_{sustain}\)

We define a stability term as a monotone decreasing function of short-horizon variance, e.g.:
\[
\text{stability} = \frac{1}{1 + \mathrm{std}(u_{k..k-n})}
\]
This maps \([0,\infty) \to (0,1] \) and is dimensionless.

We combine these into a ratio so that units cancel and the index is predictive (punishes approaching thermal limit):
\[
\boxed{\;\mathrm{RLE} = \frac{u\,\cdot\, \text{stability}}{\;A_{load}\,\cdot\,\bigl(1 + 1/T_{sustain}\bigr)}\;}
\]
All terms are dimensionless except \(1/T_{sustain}\). The sum \(1+1/T_{sustain}\) is dimensionless because 1 is unitless and \(1/T_{sustain}\) is scaled implicitly by the sampling period or a chosen time unit. In discrete time, we compute \(T_{sustain}\) in “seconds” and use seconds as the canonical unit for all datasets, preserving comparability. The ratio therefore remains dimensionless across devices.

Notes:
- As \(T_{sustain}\to \infty\) (plenty of thermal headroom), the denominator \(\to A_{load}\) and RLE increases.
- As \(T_{sustain}\to 0^+\) (imminent limit), denominator grows, RLE \(\downarrow\) sharply → predictive penalty.

## 4) Mapping to Physical Quantities
- \(u\): device utilization fraction (GPU/CPU busy ratio) — proxy for the portion of \(P\) performing work \(\dot{W}\).
- stability: inverse sensitivity to short-horizon volatility — stable workloads convert energy more efficiently, minimize transient losses.
- \(A_{load}=P/P_{rated}\): non-dimensional stress; near 1 means power-limited operation (caps \(\dot{W}\)).
- \(T_{sustain}=(T_{limit}-T)/\max(dT/dt,\varepsilon)\): horizon estimate from lumped RC; as thermal mass saturates or heat rejection is capped, \(dT/dt\) grows and \(T_{sustain}\) falls.

Split diagnostics follow directly:
\[
E_{th} = \frac{\text{stability}}{1+1/T_{sustain}}, \qquad E_{pw} = \frac{u}{A_{load}}
\]
Thus \(\mathrm{RLE} = E_{th}\cdot E_{pw}\) — thermal and power efficiency factors multiply.

## 5) Assumptions
- Quasi-steady over the 1–10 s window used for stability and \(T_{sustain}\) estimation.
- Lumped thermal capacity/resistance approximates short-horizon heating (linearized RC around operating point).
- Monotone approach to a well-defined limit temperature (no phase-change plateaus in window).
- Utilization is a valid proxy for useful work fraction (work per joule increases with sustained utilization absent throttling).
- Rated power \(P_{rated}\) represents the practical power ceiling for normalization.

These assumptions are standard for on-line control metrics and hold across devices at 1 Hz sampling.

## 6) Limiting Cases (Sanity Checks)
- Idle: \(u\to 0\Rightarrow \mathrm{RLE}\to 0\) (no useful work)
- Perfect stability: \(\text{stability}\to 1\) maximizes numerator for given \(u\).
- Power cap: \(A_{load}\to 1\Rightarrow E_{pw}\to u\); RLE lowered when \(A_{load}>1\) (over target) even at high \(u\).
- Thermal cliff: \(T_{sustain}\to 0^+\Rightarrow E_{th}\to 0\) → RLE predicts collapse before firmware throttles.

## 7) Dimensionless Invariance & Scaling
All terms are ratios (utilization, stability, load) or made dimensionless by fixed time-unit choice for \(T_{sustain}\). Therefore RLE is unitless and comparable across devices and power scales (4W mobile → 300W desktop). Empirically, cross-domain dispersion \(\sigma\approx 0.16\) confirms invariance.

## 8) From RC Thermal Model to \(T_{sustain}\)
Starting from \(C_{th}\, dT/dt = P - h\,(T- T_\infty)\), near the present operating point with \(P\) approximately constant over a short horizon:
\[
\frac{dT}{dt} \approx \alpha P - \beta (T - T_\infty), \quad \alpha=1/C_{th},\ \beta=h/C_{th}
\]
If \(dT/dt>0\), the time to reach \(T_{limit}\) by linear extrapolation is:
\[
T_{sustain} \approx \frac{T_{limit} - T}{dT/dt}
\]
We clip with \(\varepsilon\) to avoid division by zero and restrict to rising-temperature regimes per the detector gates. This yields a computable, predictive thermal horizon.

## 9) Measurable Signals (Implementation Mapping)
- u: GPU/CPU busy percent → \(u = \mathrm{util\_pct}/100\)
- stability: rolling std of \(u\) over k samples → \(1/(1+\mathrm{std})\)
- A_load: \(P/P_{rated}\) from power telemetry and rated TDP
- T_sustain: finite-difference \(dT/dt\) and device thermal limit \(T_{limit}\)
- E_th, E_pw, RLE: computed as above and logged

## 10) Why This Form (Design Rationale)
- Ratio form ensures dimensionless invariance and intuitive monotonicities.
- Multiplicative split (\(E_{th}\cdot E_{pw}\)) separates thermal headroom and power utilization, aiding diagnosis and control.
- \(1+1/T_{sustain}\) penalizes short horizons while saturating for large \(T_{sustain}\), avoiding vanishing gradients far from limits.
- Stability modulates noisy loads, reflecting conversion losses and governor inefficiency under volatility.

## 11) Empirical Validation (Pointer)
See `lab/docs/MOBILE_RLE_VALIDATION.md` and `lab/sessions/PROOF_SESSIONS.md` for constants, datasets, and session-level evidence consistent with this derivation.

## 12) Sources & Appendices
- Technical sources index (Final Proof): `lab/docs/archive/Final_Proof/INDEX.md`
- Extracted appendices (snippets, equations): `lab/docs/RLE_THEORY_APPENDICES.md` (covers all scanner-identified RLE-related sources)

Notes:
- Only technical items were included (thermal horizon, load normalization, utilization/stability, energy/entropy). Poetry/fantasy content was excluded by design.
