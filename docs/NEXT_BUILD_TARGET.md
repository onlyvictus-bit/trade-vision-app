# Next Build Target

Last reviewed: 2026-09-08

## Official target: M2 — Canonical DecisionContext

Active branch: `decision-spine-orchestration-v1`

Base main: `f26546047a28df7deb3916ed0b4467d67fd9bb7b`

AFRE v4 is already merged through PR #1 (`83070628bf153557ac6f5f54a025866bd484f76d`). This branch does not reopen AFRE work.

## Current architecture

```text
VERIFIED MARKET DATA
  -> D1 DATA / PIT / KILL-SWITCH SAFETY
  -> D2 IMMUTABLE CLOSED-CANDLE SNAPSHOT
  -> STAGE-2 ANALYSIS BRAINS
  -> STAGE-2 EVIDENCE INTEGRITY
  -> M2 CANONICAL DecisionContext       <- NEXT BUILD
  -> Price / Context / Memory / Hypotheses / ORB / AFRE
  -> Derivatives / Events / Failure
  -> Risk / Execution Reality
  -> FINAL CONFLUENCE / D6 (SOLE FINAL AUTHORITY)
  -> FinalDecision
  -> JARVIS (DISPLAY ONLY)
```

Core rule: **Many brains may disagree internally. Only one decision may leave the brain.**

## M0 Stage-2 stabilization — COMPLETE

Tested source commit:

`728d81d40ec8cdfe136e765ff0378118a8c1e759` — `decision-spine: stabilize Stage2 runtime contracts`

Committed-tree verification workflow:

- workflow: `M0 Stage2 Committed Verify`
- run: `34213835837`
- verified head: `9568ce951f44ea9e7c8d34b296a21b0bea0ab630`
- result: **SUCCESS**

Verification results:

```text
compile affected M0 modules                 PASS
Stage-2 integrity suite                     15 passed
Paper Guidance v1.88 suite                  29 passed
full apps/api/tests/test_api.py             556 passed
sole-D6 / zero-execution authority checks   PASS
```

The temporary self-applying patch workflow and patch scripts were removed after successful committed-tree verification. The retained verification workflow is read-only.

### M0-C — `synthetic_fallback` contract drift — FIXED

`IndicatorFeatureBlock` now preserves the same explicit `synthetic_fallback` provenance accepted by `IndicatorSequenceRecord`.

Required semantics are enforced:

```text
synthetic_fallback != real
synthetic_fallback -> explanation_only = true
synthetic_fallback -> usable_for_probability = false
synthetic_fallback -> no proof authority
synthetic_fallback -> no trade authority
```

### M0-A — 9C runtime accounting — FIXED

Runtime provenance is separated into:

```text
real_runtime_computed_count
synthetic_fallback_computed_count
runtime_unavailable_count
runtime_failed_count
runtime_accounting_pass
```

Synthetic computation is never counted as real computation.

### M0-B — PTA probe accounting — FIXED

PTA now exposes explicit accounting instead of treating selected probes as successful outputs:

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

Missing optional research dependencies remain explicit. They are not fabricated into successful signals. PTA remains explanation/availability evidence only and has no probability/trading authority.

### M0 real-pipeline Stage-2 integrity wiring — COMPLETE

Paper Guidance now evaluates Stage-2 evidence integrity after D2-native receipts and before D6.

```text
D2 Snapshot
   ↓
current Stage-2 engine receipts
+ explicit migration observations
   ↓
Stage2IntegrityReport
   ↓
PASS / DEGRADED / BLOCK
   ↓
D6 only when no hard integrity blocker
```

9C, PTA, ORB and AFRE are explicit `SKIPPED` migration observations in this Paper Guidance path until each is made D2-snapshot-native there. They are not substituted with neutral values and are not secretly re-fetched during arbitration.

A hard Stage-2 integrity failure stops before D6 and returns fail-closed `WAIT / DO_NOTHING` behavior.

## Stage status

| Area | Status | Next action |
|---|---|---|
| Stage 1 D1/D2 safe immutable snapshot | COMPLETE / STRONG | preserve; do not rebuild |
| Stage 1 -> Stage 2 snapshot identity | COMPLETE / STRONG | preserve |
| M0-C synthetic fallback contract | COMPLETE / GREEN | preserve provenance rules |
| M0-A 9C runtime accounting | COMPLETE / GREEN | use canonical evidence in M2/M3 |
| M0-B PTA probe accounting | COMPLETE / GREEN | keep explanation-only |
| Stage-2 Evidence Integrity | BUILT + WIRED / GREEN | make it the entry gate to DecisionContext |
| Engine Authority Registry | FOUNDATION BUILT / GREEN | expand only as brains migrate |
| Canonical DecisionContext | **NEXT / NOT STARTED** | M2 |
| All project brains routed through one context | NOT COMPLETE | M3 |
| Repository-wide D6-only final authority | PARTIAL | M4 after canonical wiring |
| Canonical FinalDecision | NOT STARTED | M5 |
| Jarvis display-only migration | NOT STARTED | M6 |
| Real derivatives/risk providers | PARTIAL | M8/provider work |

## M2 — Canonical DecisionContext — NEXT

Build one immutable, deterministic, PIT-safe shared evidence object. It must not become another decision engine.

Target structure:

```text
DecisionContext
├─ identity
│  ├─ symbol
│  ├─ timeframe
│  ├─ decision_time
│  ├─ snapshot_hash
│  └─ universe_watermark
├─ input_integrity
│  ├─ data_quality
│  ├─ PIT_status
│  ├─ freshness
│  └─ quarantine_status
├─ price_structure
├─ candle_anatomy
├─ levels
├─ indicators
├─ market_regime
├─ session_context
├─ index_context
├─ sector_context
├─ relative_strength
├─ memory
├─ historical_analogs
├─ hypotheses
├─ strategy_candidates
├─ orb_variants
├─ afre_scenarios
├─ derivatives
├─ events
├─ failure_scenarios
├─ execution_quality
├─ portfolio_risk
├─ blockers
├─ warnings
├─ proof_status
├─ paper_authority
└─ provenance
   ├─ engines_run[]
   ├─ evidence_versions[]
   └─ capability_sources[]
```

### M2 required invariants

1. One symbol/timeframe/decision time/D2 snapshot identity.
2. Every evidence block carries explicit availability and provenance.
3. Missing evidence is never converted to `0`, `0.5`, `False`, bullish, bearish, clean, or safe.
4. Synthetic/mock/masked evidence remains non-authoritative unless an explicitly approved contract says otherwise.
5. No engine may fetch hidden current-state data during DecisionContext assembly.
6. Shared calculations are computed once upstream and reused.
7. Context construction is deterministic for identical D2 + evidence inputs.
8. Context hashing is deterministic and changes on material evidence changes.
9. Context cannot grant paper authority by itself.
10. Context cannot place orders or enable live routing.
11. D6 remains the only final-band authority.
12. M2 must preserve the M0 integrity gate rather than bypass it.

## M3 — Route all brains through DecisionContext

Remove temporary neutral placeholders such as:

```text
relative_strength_score = 0.5
indicator_signal_score  = 0.0
external_ai_score       = 0.0
weak_sector             = False
```

They must become availability-bearing evidence with source, timestamp, D2 identity and explicit unavailability reason.

## M4 — D6 sole repository-wide final authority

ORB, AFRE, Hypothesis, Behavior Decision, Kronos, Gemini, Grok, Twin and Jarvis layers may produce evidence/proposals/downgrades/vetoes according to the authority registry but cannot emit a competing product final.

## M5 — Canonical FinalDecision

One output contract:

`WAIT | WATCH | AVOID | PAPER-CANDIDATE`

with bias, market story, primary setup/state, alternatives, derivatives, failure states, historical evidence, entry plan, wait-for, avoid-if, main blocker, confidence, PIT/data/proof/paper status, reasons, warnings and engine provenance.

Live routing remains blocked.

## M6 — Jarvis read-only presentation

Jarvis displays/explains the canonical `FinalDecision` and never independently upgrades it.

## M7 — contradiction / replay / safety tests

Test bullish strategy/AI evidence versus hard risk/failure/liquidity veto, unavailable evidence, stale/future evidence, replay determinism, hard-veto projection, AFRE proof gating and live-routing blocks.

## M8 — real providers + proof

Wire verified derivatives/event/risk providers into the same DecisionContext path, then run train-only selection -> unseen holdout -> expanding/repeated walk-forward -> approved playbook -> paper observation -> outcome memory -> edge-decay monitoring.

## Remaining non-M0 baseline infrastructure issues

1. Linux CI real-data fixture / HSTRY coverage (`RELIANCE_NSE_5m.csv`).
2. PowerShell parser verification on Ubuntu runner.

These are not reasons to weaken the Decision Spine or mark unavailable evidence as clean.

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

Related status files:
- `docs/DECISION_SPINE_BUILD_STATUS_2026-09-08.md`
- `docs/ENGINE_AUTHORITY_UPGRADE_MATRIX_2026-09-08.md`
- `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`
- `docs/AFRE_V4_MERGE_STATUS_2026-09-08.md`
