# Next Build Target

Last reviewed: 2026-09-08

## Official target: M2 — Canonical DecisionContext real-pipeline construction

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
  -> M2 CANONICAL DecisionContext          <- CONTRACT BUILT; REAL CONSTRUCTION NEXT
  -> M3 specialist brain migration
  -> FINAL CONFLUENCE / D6 (SOLE FINAL AUTHORITY)
  -> FinalDecision
  -> JARVIS (DISPLAY ONLY)
```

Core rule: **Many brains may disagree internally. Only one decision may leave the brain.**

## M0 Stage-2 stabilization — COMPLETE / GREEN

Tested source commit:
`728d81d40ec8cdfe136e765ff0378118a8c1e759`

Committed-tree verification run:
`34213835837` — SUCCESS

```text
Stage-2 integrity                         15 passed
Paper Guidance v1.88                      29 passed
full apps/api/tests/test_api.py           556 passed
authority invariants                      PASS
```

M0-C `synthetic_fallback`, M0-A 9C provenance accounting, M0-B PTA probe accounting and pre-D6 Stage-2 integrity wiring are complete. Synthetic data remains non-real/non-authoritative, missing evidence remains explicit, and hard integrity failures stop before D6.

## M1 Engine Authority Registry — FOUNDATION BUILT / GREEN

Exactly one engine may set the final band:

```text
FINAL_CONFLUENCE_ARBITER
```

No registered engine may execute.

## M2 DecisionContext contract — FOUNDATION BUILT / GREEN

New contract:

```text
apps/api/app/behavior/decision_spine/decision_context.py
apps/api/tests/decision_spine/test_decision_context.py
```

Exports are wired through:
`apps/api/app/behavior/decision_spine/__init__.py`

Verification workflow:

```text
workflow: M2 DecisionContext
run:      34214606289
head:     90edc5c516324817c0e59bf56f072a63c2044e66
result:   SUCCESS
```

Exact verification:

```text
compile Decision Spine modules            PASS
DecisionContext suite                     25 passed
M0 Stage-2 integrity regression           15 passed
Paper Guidance v1.88 regression           29 passed
full apps/api/tests/test_api.py           556 passed
authority invariants                      PASS
```

### What the foundation enforces

`DecisionContext` is an immutable deterministic evidence container, not a predictor or arbiter.

It requires explicit canonical blocks for:

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

Every block carries:
- registered `source_engine`;
- D2 `source_snapshot_hash`;
- explicit availability/status;
- payload;
- observed time when applicable;
- source mode/provenance;
- evidence version;
- capability source;
- reasons/warnings;
- explicit probability/authority flags.

The builder rejects:
- missing canonical evidence fields;
- unknown extra evidence fields;
- D2 snapshot mismatch;
- future evidence;
- unregistered engine identity;
- unavailable evidence replaced by neutral defaults;
- synthetic/mock/masked/unknown evidence used for probability authority;
- proof/paper/trade authority claims;
- any pre-D6 final-band claim;
- PIT not passing;
- quarantine block;
- Stage2IntegrityReport hard block/ineligibility.

It recursively freezes payload mappings and creates a deterministic `context_hash`. Identical causal inputs produce the same hash; material evidence changes alter the hash.

Safety remains hard-coded:

```text
paper_promotion_eligible = false
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
```

## Immediate next coding target — finish M2 real-pipeline construction

The contract exists; now construct it from the actual post-M0 Paper Guidance evidence stream.

Required sequence:

```text
D2 Snapshot
   ↓
PaperGuidanceEngineReceipt[]
+ explicit availability observations
   ↓
Stage2IntegrityReport
   ↓
DecisionContext adapter/builder
   ↓
context_hash + canonical evidence object
   ↓
record/verify context in Paper Guidance
   ↓
DO NOT change D6 authority yet
```

Rules for this step:
1. Do not independently refetch market state during context construction.
2. Use only evidence already causally tied to the D2 snapshot.
3. For brains not yet active in this path, create explicit `UNAVAILABLE/SKIPPED` blocks with reasons—not neutral values.
4. Do not activate ORB/AFRE/9C/PTA merely to fill fields.
5. Do not let context construction grant paper authority.
6. Preserve current D6 behavior while the canonical context is introduced and replay-tested.
7. Full specialist migration remains M3.

## M3 — Route all brains through DecisionContext

This is where temporary neutral placeholders are removed:

```text
relative_strength_score = 0.5
indicator_signal_score  = 0.0
external_ai_score       = 0.0
weak_sector             = False
```

They become explicit availability-bearing evidence rather than invented neutral facts.

## M4 — D6 sole repository-wide final authority

D6 already has the sole-finalizer registry invariant. M4 makes every active specialist consume/report through the canonical context so no legacy arbiter/fusion/master/twin path can appear to be a competing product final.

## M5 — Canonical FinalDecision

One product output:
`WAIT | WATCH | AVOID | PAPER-CANDIDATE`
with bias, story, setup/state, alternatives, derivatives, failure states, history, entry plan, wait-for, avoid-if, blocker, confidence, PIT/data/proof/paper state and provenance.

## M6 — Jarvis read-only presentation

Jarvis displays/explains `FinalDecision`; it never upgrades it.

## M7 — contradiction / replay / safety tests

Test bullish strategy/AI evidence against hard risk/failure/liquidity veto, unavailable/stale/future evidence, replay determinism, hard-veto projection, AFRE proof gating and live-routing blocks.

## M8 — real providers + proof

Wire verified derivatives/event/risk providers into the same context, then perform train-only selection -> unseen holdout -> walk-forward -> approved playbook -> paper observation -> outcome memory -> edge-decay monitoring.

## Remaining non-M0 infrastructure issues

1. Linux CI/HSTRY fixture coverage including `RELIANCE_NSE_5m.csv`.
2. PowerShell parser verification on Ubuntu.

These do not justify weakening Decision Spine evidence semantics.

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
