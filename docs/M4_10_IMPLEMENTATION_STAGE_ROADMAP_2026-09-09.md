# M4-10 — Implementation Stage Roadmap

## Purpose
Break M4 into independently testable, lockable stages with explicit dependencies and rollback seams.

## Stage sequence
### M4-A — Canonical input contract + receipt validator
Build immutable M4 evidence nodes and DecisionContext adapter. No decision behavior change.
Acceptance: identity/PIT/hash/authority/missingness validation green.

### M4-B — Authority graph + epistemic state
Enforce authority permissions and KNOWN/UNKNOWN/UNAVAILABLE/MISSING/DEGRADED/STALE/CONTRADICTORY/OOD/QUARANTINED/INSUFFICIENT states.
Acceptance: authority attacks and state-transition tests green.

### M4-C — Conflict graph
Implement typed conflicts and deterministic authority resolution without numeric penalties.
Acceptance: all conflict fixtures and ordering replay green.

### M4-D — Failure/risk reasoner
Map canonical risk/failure facts into explicit failure modes, vetoes and caps.
Acceptance: false breakout/event/liquidity/expiry/OOD/etc. fixtures green.

### M4-E — Scenario + counterfactual robustness
Implement bounded thesis/scenario/counterfactual engine and adversarial anti-thesis.
Acceptance: <=12 scenarios, <=8 counterfactuals/thesis, deterministic robustness receipt.

### M4-F — Confidence/uncertainty synthesis
Implement semantic uncertainty dimensions, caps and confidence bands.
Acceptance: no vote-ratio/score-position dependency; reason for every cap is auditable.

### M4-G — Deterministic D6 arbitration
Implement sole final-band state machine and remove weighted-score dependence from new path.
Acceptance: exactly one final-band assignment path; weak evidence cannot override hard authority.

### M4-H — Reason tree + decision receipt
Create lineage-complete machine receipt and human renderer.
Acceptance: decision hash/replay/serialization tests green.

### M4-I — Compatibility wiring
Wire canonical DecisionContext/Paper Guidance through M4 behind compatibility seam; preserve public contracts.
Acceptance: existing Paper Guidance/API regressions green; legacy adapter fail-closed.

### M4-J — Replay/adversarial verification
Run full authority/temporal/data/market/statistical/strategy/counterfactual matrices.
Acceptance: all golden laws proven.

### M4-K — Full regression + performance hardening
Run full API tree, multi-symbol benchmarks, cache/concurrency tests, memory bounds.
Acceptance: no locked regression failure; bounded latency/no uncontrolled loops.

### M4-L — Authority audit + exact-head CI + lock
Audit every code path capable of band change, safety flags and authority. Update canonical docs. Run exact-head CI.
Acceptance: M4 GREEN / LOCKED only after exact-head workflow success.

## Dependency graph
```text
A -> B -> C -> D -> E -> F -> G -> H -> I -> J -> K -> L
          \-------- failure/scenario policy can be built in parallel --------/
```
C and D may develop in parallel after B, but E waits for both. No final arbitration before A-F are locked locally.

## Implementation file map
Expected new modules under `apps/api/app/behavior/decision_spine/`:
- `m4_evidence.py`
- `m4_input_contract.py`
- `m4_authority.py`
- `m4_epistemic.py`
- `m4_conflict_graph.py`
- `m4_conflict_policy.py`
- `m4_thesis.py`
- `m4_failure_reasoner.py`
- `m4_scenario_reasoner.py`
- `m4_counterfactual.py`
- `m4_uncertainty.py`
- `m4_arbiter.py`
- `m4_receipt.py`
- `m4_reason_tree.py`
- `m4_compatibility.py`

Existing files potentially touched only at integration stages:
- `final_confluence_arbiter.py`
- `decision_context.py` only for additive contract extension if unavoidable
- `paper_guidance_decision_context_adapter.py`
- response models/serializers
- authority registry only if a separately reviewed M4 engine inventory extension is required, never to weaken authority.

## Files forbidden from casual modification
D1 integrity code, D2 snapshot/identity semantics, locked M3.1/M3.2/M3.3 calculators, memory PIT/label timing, safety boundaries, existing locked test expectations without explicit migration justification.

## Test sequence per stage
`unit -> property/invariant -> adversarial -> replay -> affected regressions -> full regression at integration milestones`.

## Performance requirements
- pure in-memory D6 decision path;
- no live data fetch;
- no unbounded historical scans;
- canonical worlds computed once;
- bounded node/scenario/counterfactual counts;
- stable cache key from context/policy versions;
- safe concurrent evaluation across symbols.

## Rollback strategy
A-I remain additive until cutover. Final authority switches through one compatibility seam. Rollback reselects locked v1.75 finalizer without reverting M3 worlds.

## Documentation lock sequence
After each implementation stage update this roadmap and canonical status only with verified facts. Never mark GREEN before exact-head verification.

## First implementation target
**M4-A Canonical Input Contract + Receipt Validator.** It creates the foundation needed for every later reasoner while leaving current D6 production behavior unchanged.
