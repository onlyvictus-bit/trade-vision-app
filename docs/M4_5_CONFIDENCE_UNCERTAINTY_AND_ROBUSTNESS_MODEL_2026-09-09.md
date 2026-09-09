# M4-5 — Confidence, Uncertainty and Robustness Model

## Purpose
Define confidence semantically from evidence quality and decision robustness rather than vote ratio or score position.

## Repository truth
Current D6 confidence interval is derived mainly from confluence score, conflict count and evidence count. M4 replaces this with explicit uncertainty dimensions.

## Confidence is not probability
M4 confidence means: **how well the final decision is supported by causal, sufficiently complete, independent, regime-relevant, non-contradictory evidence and how stable that decision remains under bounded counterfactual challenge.** It is not a forecast win probability.

## Dimensions
1. Evidence quality
2. Coverage of required evidence
3. Independent support
4. Authority strength
5. Freshness
6. Contradiction burden
7. Missingness burden
8. OOD severity
9. Drift severity
10. Memory sample sufficiency
11. Regime match
12. Counterfactual robustness
13. Scenario stability
14. Failure-risk density
15. Single-factor dependence

## Model
Each dimension is classified into an ordinal semantic state rather than free-form weighted votes:
`STRONG | ACCEPTABLE | LIMITED | WEAK | CRITICAL | UNKNOWN`.

A deterministic policy lattice produces an overall uncertainty class and maximum permissible confidence band. Critical dimensions cannot be averaged away by strong lower-priority dimensions.

## Confidence bands
- VERY_LOW: critical unknowns/conflicts, severe OOD, fragile thesis, or minimal independent support.
- LOW: material missingness/degradation or weak robustness.
- MODERATE: adequate causal coverage and independence, bounded conflicts, acceptable regime fit, thesis survives core challenges.
- HIGH: strong independent multi-domain support, low contradiction, low OOD/drift, strong robustness, no material missingness.
- VERY_HIGH: reserved; requires unusually complete, high-quality, independent and robust evidence. Never produced merely because signals agree.

## Caps
Examples:
- critical evidence MISSING/UNAVAILABLE -> confidence cap LOW/MODERATE according to domain importance.
- unresolved equal-authority contradiction -> cap LOW.
- severe OOD -> cap LOW; memory support may become explanation-only.
- insufficient independent history -> memory cannot raise above MODERATE.
- single-factor dependency -> cap MODERATE.
- D1 hard block -> confidence in actionable thesis is irrelevant; final decision forced safe.

## Independent evidence
Evidence sharing the same causal source/receipt family belongs to one `independence_group`. Multiple indicators derived from the same candles do not count as separate independent confirmations automatically.

## Missingness
Missingness penalty is importance-aware and epistemically typed. UNAVAILABLE and MISSING are not treated as bearish/neutral facts; they reduce coverage/certainty and may cap band.

## Contradiction
Conflict graph supplies severity and resolution state. Resolved low-authority disagreement may have small effect; unresolved high-authority conflict has large uncertainty effect.

## OOD/drift
Canonical M3.3 OOD/drift states govern whether historical support is admissible. Severe OOD prevents memory from increasing confidence.

## Robustness
Counterfactual results directly constrain confidence. A thesis that flips after removal of one support group is FRAGILE regardless of raw evidence count.

## Output
`M4UncertaintyReceipt`:
```text
overall_confidence_band
overall_uncertainty_state
dimension_states{}
confidence_caps[]
confidence_reasons[]
coverage_summary
independence_summary
conflict_summary
robustness_class
failure_risk_summary
```

## State transitions
`classified evidence -> dimension assessment -> hard caps -> robustness integration -> final semantic confidence`.

## Long/short behavior
Separate confidence assessment per thesis side. Confidence in long invalidity does not automatically equal confidence in short validity.

## Determinism/replay
No learned online weights, random sampling or opaque LLM scoring in final confidence. All policy tables versioned and replayable.

## Tests
Missing critical field; many correlated supports; severe OOD; tiny memory sample; resolved/unresolved conflicts; stale evidence; robust vs fragile counterfactuals; long/short asymmetry; ordering invariance.

## Acceptance
For every confidence change the receipt can answer exactly which dimension changed, why, and which cap/rule applied.

## Expected files
`m4_uncertainty.py`, `m4_confidence_policy.py`, tests.

## Forbidden casual edits
Canonical world calculations and historical memory labels/sampling rules.
