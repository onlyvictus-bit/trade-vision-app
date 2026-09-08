# Canonical Decision Spine Build Status — 2026-09-08

## Current status

```text
branch: decision-spine-orchestration-v1
base main: f26546047a28df7deb3916ed0b4467d67fd9bb7b
M0: COMPLETE / GREEN
M1: FOUNDATION BUILT / GREEN
M2 contract: FOUNDATION BUILT / GREEN
M2 real-pipeline construction: NEXT
```

AFRE v4 is already merged. This work is isolated from the AFRE branch.

## Architecture decision

```text
D1 DATA/PIT SAFETY
 -> D2 IMMUTABLE CLOSED-CANDLE SNAPSHOT
 -> STAGE-2 ANALYSIS BRAINS
 -> STAGE-2 EVIDENCE INTEGRITY
 -> DecisionContext
 -> specialist brains
 -> FINAL CONFLUENCE / D6
 -> FinalDecision
 -> Jarvis display only
```

Trade Vision does not need another independent BUY/SELL brain. `DecisionContext` is shared causal evidence, not another decision engine.

## Stage 1 verdict

Stage 1 is architecturally complete and should not be rebuilt. Preserve D1-before-D2 ordering, closed-candle/PIT protection, deterministic D2 snapshot/hash, bad-data/unfinished-candle/kill-switch blocking, and same-snapshot downstream identity.

## M0 Stage-2 stabilization — COMPLETE

Tested source commit:
`728d81d40ec8cdfe136e765ff0378118a8c1e759`

Verification run:
`34213835837` — SUCCESS

```text
Stage-2 integrity                 15 passed
Paper Guidance v1.88              29 passed
full test_api.py                  556 passed
authority checks                  PASS
```

### M0-C synthetic fallback — FIXED

```text
synthetic_fallback != real
explanation_only = true
usable_for_probability = false
no proof authority
no trade authority
```

### M0-A 9C accounting — FIXED

```text
real_runtime_computed_count
synthetic_fallback_computed_count
runtime_unavailable_count
runtime_failed_count
runtime_accounting_pass
```

### M0-B PTA accounting — FIXED

```text
selected_count
probe_count
computed_count
no_signal_count
dependency_unavailable_count
error_count
materialized_output_count
accounting_pass
```

PTA remains explanation/availability evidence only.

### Stage-2 integrity real wiring — COMPLETE

Paper Guidance now evaluates `Stage2IntegrityReport` after D2-native receipts and before D6. A hard integrity failure stops before D6 and returns fail-closed WAIT / DO_NOTHING behavior.

9C, PTA, ORB and AFRE remain explicit migration `SKIPPED` observations in this Paper Guidance path until their D2-native canonical wiring is implemented. Missing is not replaced by neutral.

## M1 Engine Authority Registry — FOUNDATION BUILT / GREEN

Registry invariant:

```text
only FINAL_CONFLUENCE_ARBITER may_set_final_band
all engines may_execute = false
```

Registration does not activate an engine.

## M2 Canonical DecisionContext — CONTRACT FOUNDATION BUILT / GREEN

Added:

```text
apps/api/app/behavior/decision_spine/decision_context.py
apps/api/tests/decision_spine/test_decision_context.py
```

Exports added to:
`apps/api/app/behavior/decision_spine/__init__.py`

Verification:

```text
workflow: M2 DecisionContext
run:      34214606289
head:     90edc5c516324817c0e59bf56f072a63c2044e66
result:   SUCCESS
```

Exact results:

```text
compile Decision Spine modules        PASS
DecisionContext                       25 passed
Stage-2 integrity regression          15 passed
Paper Guidance v1.88                  29 passed
full test_api.py                      556 passed
authority invariants                  PASS
```

### DecisionContext contract

Canonical required evidence fields:

```text
price_structure
candle_anatomy
levels
indicators
market_regime
session_context
index_context
sector_context
relative_strength
memory
historical_analogs
hypotheses
strategy_candidates
orb_variants
afre_scenarios
derivatives
events
failure_scenarios
execution_quality
portfolio_risk
proof_status
paper_authority
```

Each `EvidenceBlock` carries registered source engine, D2 snapshot hash, availability, payload, optional observation time, source mode, evidence version, capability source, reasons/warnings and authority/probability flags.

### M2 safety/causal rules implemented

The builder rejects:

- missing required evidence blocks;
- unknown evidence blocks;
- Stage2/D2 identity mismatch;
- per-block D2 hash mismatch;
- future evidence;
- unregistered engines;
- neutral substitution for unavailable evidence;
- synthetic/mock/masked/unknown probability authority;
- proof authority claims;
- paper authority claims;
- trade authority claims;
- pre-D6 final-band claims;
- PIT not passing;
- quarantine block;
- Stage-2 integrity hard block/ineligibility.

Payloads are recursively frozen. Serialization and `context_hash` are deterministic. Same causal inputs -> same hash. Material evidence change -> changed hash.

The context itself always preserves:

```text
paper_promotion_eligible = false
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
```

It deliberately contains no `final_band` or `final_decision`.

## M2 remaining work — real-pipeline construction

The contract is green, but M2 is not yet complete. Next:

```text
D2 Snapshot
 -> PaperGuidanceEngineReceipt[]
 -> Stage2IntegrityReport
 -> construct canonical EvidenceBlock set
 -> build DecisionContext
 -> persist/report context_hash + provenance
 -> replay/determinism checks
```

Important migration rule: inactive specialists must enter as explicit `UNAVAILABLE/SKIPPED` evidence with reasons. Do not activate ORB/AFRE/9C/PTA merely to populate the context. Do not refetch current state during context assembly.

D6 should continue using the existing safe path during this M2 introduction. Full D6 consumption of canonical context is a later M3/M4 migration after parity/replay evidence.

## Milestone status

```text
M0  Stage-2 stabilization / integrity                    COMPLETE / GREEN
M1  Engine Authority Registry                            FOUNDATION / GREEN
M2  Canonical DecisionContext contract                   FOUNDATION / GREEN
M2  Real Paper Guidance context construction             NEXT
M3  Route all specialist brains through DecisionContext NOT STARTED
M4  D6 sole repository-wide canonical consumer          PARTIAL; D6 EXISTS
M5  Canonical FinalDecision                              NOT STARTED
M6  Jarvis read-only presentation                       NOT STARTED
M7  contradiction/replay/safety integration             NOT STARTED
M8  real providers + historical/paper proof             NOT STARTED
```

## Remaining non-M0 infrastructure issues

1. Linux CI/HSTRY fixture coverage including `RELIANCE_NSE_5m.csv`.
2. PowerShell parser verification on Ubuntu.

## Safety invariants

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
missing != neutral
unknown != false
unavailable != safe
synthetic != real
external_ai != safety_authority
ORB_or_AFRE_confirmation != proof_authority
```
