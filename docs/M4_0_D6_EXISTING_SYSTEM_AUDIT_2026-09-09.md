# M4-0 — Existing D6 System Audit

Baseline: `main@7a15bfb3717d34ea75d19a6584a3ef814fae8001`

## 1. Purpose
Inventory current D6 behavior before redesign and identify every path that can affect final band, confidence, blocker state, or explanation.

## 2. Existing repository truth
Current D6 implementation is `apps/api/app/behavior/final_confluence_arbiter.py`, version `final-confluence-conflict-arbiter.v1.75`. Authority registry declares `FINAL_CONFLUENCE_ARBITER` rank 100, sole `may_set_final_band=True`, `may_execute=False`. Canonical `DecisionContext` exists but the current arbiter accepts a legacy `FinalConfluenceArbiterRequest`, not the full canonical context directly.

Current D6 pipeline:
```text
request
 -> _votes()
 -> _conflicts()
 -> sum(weighted_score) + conflict adjustments
 -> _bounded_score()
 -> _hard_block()
 -> _decision()
 -> _dominant_blocker()
 -> _confidence_interval()
 -> _reason_tree()
 -> _gates()
 -> FinalConfluenceArbiterReport
```

## 3. Good parts
- Sole final-band authority is explicit and registry-enforced.
- Hard safety/data/liquidity/post-entry invalidation gates exist.
- Execution authority is hard-disabled.
- Conflict objects and reason-tree output already exist.
- Short paper candidate exists as an explicit distinct final state.
- No-future-leakage and data-quality failures hard-block.

## 4. Problems
### 4.1 Weighted-vote core
`raw_score = sum(vote.weighted_score) + adjustment` remains the decisive center. Many lower-authority observations can still shape the final score even though narrative hierarchy says otherwise. This is incompatible with the target authority graph.

### 4.2 Authority is descriptive, not structurally enforced
Priority ranks and registry authority are not used as a generic arbitration algorithm. Conflict rules are manually enumerated. New evidence can enter a weighted score without passing a common authority-resolution contract.

### 4.3 Canonical worlds are not first-class D6 inputs
D6 does not consume M3.1/M3.2/M3.3 receipts as typed world objects. Current Paper Guidance adapter assembles `DecisionContext`, but D6 remains on a separate request schema.

### 4.4 Missingness collapses upstream
Current D6 request uses scalar values/booleans for many factors. It cannot distinguish KNOWN, UNKNOWN, UNAVAILABLE, MISSING, DEGRADED, STALE, CONTRADICTORY, OOD, QUARANTINED, INSUFFICIENT for each relevant fact.

### 4.5 Confidence is cosmetic
Confidence interval is primarily score-position plus conflict-count/evidence-count width. It does not explicitly model source quality, freshness, independence, missingness, OOD/drift, regime match, sample sufficiency, scenario stability, or counterfactual robustness.

### 4.6 Conflict engine is closed-list
Only hardcoded combinations are recognized. There is no typed conflict graph linking evidence nodes, authority, direction, severity, resolution state, and downstream consequence.

### 4.7 Failure reasoning is shallow
Failure questions are strings. No bounded failure-mode state is computed with preconditions, evidence, likelihood/severity class, invalidation triggers, or decision consequence.

### 4.8 Counterfactual robustness absent
The engine does not test removal of strongest evidence, removal of memory, loss of index alignment, resolution of contradiction against the thesis, or minimum-change-to-flip.

### 4.9 Long/short asymmetry incomplete
Short candidate requires a very negative scalar score and `short_logic_enabled`, effectively tying short reasoning to inverse score behavior. M4 must independently validate bearish continuation/reversal evidence.

### 4.10 Hidden coupling / duplicated semantics
Risk, trap, event, liquidity and post-entry state appear both as votes and conflicts/hard blocks. This duplicates semantic authority and can double-count the same fact.

## 5. Current authority paths
- `FINAL_CONFLUENCE_ARBITER`: sole final band.
- D1/data-quality style failures: represented inside D6 hard-block inputs.
- Risk engines: registry grants veto/downgrade to several legacy engines.
- Reviewers: downgrade-only; no upgrade/final authority.
- Canonical M3 memory specialists: rank 0, no propose/veto/downgrade/final/execute.

## 6. Current blockers
Explicit current hard blockers include data-quality fail, future leakage, liquidity grade C, invalidated post-entry thesis, and any conflict with severity `block`.

## 7. Current confidence path
`center=(score+7)/14`; width grows with number of conflicts and low evidence count. This is not a calibrated probability and must not be represented as one.

## 8. Compatibility dependencies
- `FinalConfluenceArbiterRequest/Report` public model contract.
- Paper Guidance expects stable final labels.
- Existing tests likely assert v1.75 gates/conflicts/bands.
- Authority registry identity must remain stable.
- Locked M3 worlds must remain untouched.

## 9. Risk ranking
1. CRITICAL — weighted score can dominate architecture.
2. CRITICAL — canonical DecisionContext not direct D6 contract.
3. HIGH — missing/unknown/degraded evidence not first-class.
4. HIGH — confidence semantics weak.
5. HIGH — short side insufficiently independent.
6. HIGH — duplicated risk semantics can double count.
7. MEDIUM — conflict taxonomy closed-list.
8. MEDIUM — reason tree is prose, not replay-grade receipt.
9. MEDIUM — no counterfactual robustness.
10. LOW — current display/research safety boundaries are strong.

## 10. Target state transition
```text
INGEST -> VALIDATE -> AUTHORITY_CLASSIFY -> EPISTEMIC_CLASSIFY
-> CONFLICT_DETECT -> FAILURE_SCAN -> SCENARIO_ANALYZE
-> COUNTERFACTUAL_CHALLENGE -> UNCERTAINTY_SYNTHESIS
-> FINAL_ARBITRATION -> RECEIPT -> PAPER_GUIDANCE
```
Every transition may fail closed; no transition may fabricate neutral evidence.

## 11. Performance / determinism / replay
Use immutable typed inputs, sorted canonical node IDs, fixed policy tables, bounded scenario/counterfactual sets, stable hashing, no ambient time/randomness, no live fetch inside D6.

## 12. Tests
- Preserve all existing v1.75 regressions via compatibility adapter.
- Add parity fixtures before changing output semantics.
- Prove weak evidence cannot override D1.
- Prove missingness cannot become zero.
- Prove identical context hash produces identical receipt hash.

## 13. Acceptance / lock
Audit is complete when all final-band mutation paths are mapped, D6 input coupling is documented, compatibility dependencies are enumerated, and no M4 production code has been introduced.

## 14. Expected implementation files
Likely new `decision_spine/m4_*` modules plus adapter changes around `final_confluence_arbiter.py` and Paper Guidance.

## 15. Forbidden casual edits
D1 integrity, D2 identity/snapshot semantics, canonical M3.1/M3.2/M3.3 calculations, memory PIT logic, authority law.
