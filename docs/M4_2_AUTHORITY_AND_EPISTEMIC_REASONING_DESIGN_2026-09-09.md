# M4-2 — Authority and Epistemic Reasoning Design

## Purpose
Make evidence authority and knowledge-state explicit before any directional reasoning.

## Repository truth
Authority registry already defines engine permissions and ranks. M4 must turn that registry from descriptive metadata into enforced orchestration policy without granting new authority to specialists.

## Authority classes
```text
T0 D1 hard safety / causal-integrity facts
T1 structural impossibility / execution-quality / market-safety vetoes
T2 canonical M3.1/M3.2/M3.3 facts
T3 strategy/hypothesis interpretation
T4 historical/reliability support
T5 reviewer/heuristic challenge
T6 presentation-only
D6 sole final-band authority above all output assignment
```
Actual engine rank/permissions remain sourced from registry. Tier is an M4 orchestration grouping, not a competing registry.

## Permission semantics
- T0: veto/downgrade; cannot be upgraded by lower tiers.
- T1: bounded veto/downgrade when its canonical preconditions are proven.
- T2: may support/oppose a thesis; cannot set final band.
- T3: may propose strategy thesis; cannot bypass T0/T1.
- T4: may modify robustness/uncertainty only within bounded policy; never creates trade validity alone.
- T5: explanation/challenge/downgrade only; never upgrade a hard block.
- T6: no decision influence.
- D6: assigns final band after all higher-level constraints are resolved.

## Epistemic states
- KNOWN: causal, valid, quality acceptable.
- UNKNOWN: value genuinely unknown.
- UNAVAILABLE: source could not supply evidence.
- MISSING: evidence expected by contract but absent.
- DEGRADED: present, but quality/reliability impaired.
- STALE: outside accepted decision-time freshness.
- CONTRADICTORY: trustworthy evidence disagrees.
- OUT_OF_DISTRIBUTION: present state materially outside trusted historical support.
- QUARANTINED: excluded for integrity concerns.
- INSUFFICIENT: evidence exists but support/sample is too weak.

## Resolution law
Evidence is classified first by authority, then epistemic state, then side relevance. Numeric payload is considered only after those gates.

## Downgrade rules
Downgrade when important evidence is degraded/stale/contradictory/insufficient, when scenario fragility is high, when memory is OOD/drifting, or when thesis depends on one low-independence evidence group.

## Veto rules
Veto for D1 hard block, future leakage, identity mismatch, forbidden execution authority, quarantined critical input, structural impossibility, or policy-defined high-severity risk whose canonical preconditions are proven.

## Upgrade restrictions
No lower-authority evidence can erase a higher-authority veto. Reviewers cannot upgrade. Memory cannot independently promote. Missing/unknown evidence never upgrades. M4 may promote only when all required authority gates pass and positive evidence survives conflict/failure/counterfactual checks.

## State machine
```text
UNCLASSIFIED
 -> AUTHORITY_BOUND
 -> EPISTEMIC_BOUND
 -> SIDE_BOUND
 -> ADMISSIBLE | LIMITED | EXCLUDED | HARD_BLOCK
```

## Failure behavior
Unknown registry engine, self-claimed authority, inconsistent timestamps, invalid epistemic transition, or unsupported authority mutation fail closed and generate audit reason codes.

## Long/short behavior
Side is explicit. A bullish fact may be irrelevant to a bearish reversal thesis rather than automatically opposing it. Risks can be side-specific or symmetric.

## Determinism / replay
Authority table is versioned and immutable per decision. Epistemic classification rules are pure functions of canonical receipt + policy version.

## Tests
- 100 weak T5 supports cannot overpower one T0 block.
- reviewer upgrade attempt rejected.
- canonical memory final-band attempt rejected.
- missing and unavailable preserve distinct states.
- stale remains stale after serialization.
- same evidence shuffled yields same authority graph/hash.

## Acceptance / lock
Every decision-affecting node has authority class, allowed actions and epistemic state; forbidden authority changes are mechanically impossible.

## Files expected
`m4_authority.py`, `m4_epistemic.py`, policy tables, tests.

## Forbidden casual edits
`authority_registry.py` permissions unless a separately reviewed authority migration explicitly requires it; locked D1/D2/M3 calculations.
