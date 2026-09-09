# M4-4 — Scenario, Failure and Counterfactual Reasoning

## Purpose
Model bounded ways the thesis can fail and measure whether the conclusion survives plausible evidence perturbations.

## Scope
Structured risk/scenario reasoning only. No speculative price-path generation, no recursive agent loop, no future-data use.

## Scenario lattice
Bounded canonical branches:
- follow-through
- immediate breakout failure
- retest then resume
- index reversal
- volatility expansion
- liquidity deterioration
- event/news shock
- derivatives wall/pinning distortion
- historical analog failure
- OOD/regime break
- chop/whipsaw persistence

Each branch contains: trigger evidence, thesis preconditions, invalidation observations, severity, side relevance, decision consequence and reason codes.

## Failure-mode model
Required reusable failure classes include false breakout, late breakout, exhausted gap, wide/narrow OR, first-bar contamination, stale level, insufficient liquidity, index/sector divergence, abnormal volatility, event shock, feed degradation, OI wall, expiry pinning, gamma squeeze risk, result-day instability, regime mismatch, small sample, overfit signature, edge decay, correlated evidence, conflicting worlds and whipsaw.

M4 reuses canonical evidence; it does not recalculate ATR, OI, regime, gap or locked M3 facts.

## Thesis contract
A thesis declares:
```text
thesis_id
side
mode: continuation|reversal|no_trade|ambiguous
required_truths[]
supporting_nodes[]
opposing_nodes[]
invalidation_conditions[]
critical_missing_nodes[]
```

## Counterfactual tests
Fixed bounded suite:
1. remove strongest supporting independent evidence group;
2. remove memory world support;
3. remove index/sector alignment;
4. degrade volume/quality evidence;
5. resolve strongest contradiction against thesis;
6. remove strongest blocker;
7. force OOD severe when memory-dependent;
8. minimum policy-valid evidence change that flips/caps band.

Counterfactuals operate on already-classified evidence state, never mutate source facts.

## Robustness classes
- ROBUST: conclusion survives required counterfactual set.
- MODERATELY_ROBUST: survives most; limited dependencies.
- FRAGILE: one plausible evidence change materially downgrades.
- SINGLE_FACTOR_DEPENDENT.
- BLOCKER_DEPENDENT.
- MEMORY_DEPENDENT.
- REGIME_DEPENDENT.
- UNRESOLVED.

## Adversarial self-challenge
Before D6 arbitration, construct anti-thesis from strongest opposing high-authority evidence, hidden missingness, stale/degraded facts, correlation, OOD/drift, event risk, side asymmetry and sample weakness. Decision-affecting challenge rules are deterministic; reviewer/LLM output may explain only.

## State transitions
```text
THESIS -> FAILURE_SCAN -> SCENARIO_LATTICE -> COUNTERFACTUAL_SUITE
-> ADVERSARIAL_CHALLENGE -> ROBUSTNESS_RECEIPT
```

## Fail-closed behavior
If required scenario inputs are invalid/missing, mark scenario UNKNOWN/UNAVAILABLE and increase uncertainty; do not assume benign outcome. If a critical failure mode is proven active, emit veto/band-cap according to authority policy.

## Long/short behavior
Separate thesis sets for bullish continuation, bullish reversal, bearish continuation and bearish reversal. No `short = inverse(long)` transformation.

## Performance budget
Maximum scenarios: 12. Maximum counterfactuals: 8 per active thesis. No nested recursive scenario generation. No historical database calls from D6.

## Determinism/replay
Scenario ordering, participant sets and counterfactual IDs are canonical and hashed. Same input/policy => same robustness receipt.

## Tests
False-breakout, event shock, expiry pinning, gap exhaustion, OOD memory, weak sample, correlated confirmation, missing derivatives, hostile context, stable setup, long/short divergent outcomes, bounded runtime.

## Acceptance
Every candidate thesis can state how it can fail, what would invalidate it, most dangerous failure class, missing evidence preventing confidence, and whether final conclusion is robust or fragile.

## Expected files
`m4_thesis.py`, `m4_failure_reasoner.py`, `m4_scenario_reasoner.py`, `m4_counterfactual.py`, tests.

## Forbidden casual edits
ORB/AFRE/derivatives calculators, M3 canonical facts, memory retrieval internals.
