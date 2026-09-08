# Next Build Target

Last reviewed: 2026-09-08

## Official target: Canonical Decision Spine / Brain Orchestration

Active branch: `decision-spine-orchestration-v1`

Base main: `f26546047a28df7deb3916ed0b4467d67fd9bb7b`

AFRE v4 is already merged through PR #1 (`83070628bf153557ac6f5f54a025866bd484f76d`). This branch does not reopen AFRE work.

## Why this is next

Trade Vision already has enough specialist intelligence. The engineering problem is that many brains still behave like separate decision layers. The next architecture forces every specialist to consume the same approved causal evidence and report through one final authority.

```text
VERIFIED MARKET DATA
  -> D1 DATA / PIT / KILL-SWITCH SAFETY
  -> D2 IMMUTABLE CLOSED-CANDLE SNAPSHOT
  -> STAGE-2 ANALYSIS BRAINS
  -> STAGE-2 EVIDENCE INTEGRITY
  -> ONE DecisionContext
  -> Price / Context / Memory / Hypotheses / ORB / AFRE
  -> Derivatives / Events / Failure
  -> Risk / Execution Reality
  -> FINAL CONFLUENCE / D6 (SOLE FINAL AUTHORITY)
  -> FinalDecision
  -> JARVIS (DISPLAY ONLY)
```

Core rule: **Many brains may disagree internally. Only one decision may leave the brain.**

## Stage status

| Area | Status | Action |
|---|---|---|
| Stage 1 D1/D2 safe immutable snapshot | COMPLETE / STRONG | preserve; do not rebuild |
| Stage 1 -> Stage 2 snapshot identity | COMPLETE / STRONG | preserve |
| Core Stage-2 Paper Guidance chain | BUILT / WORKING | preserve and wrap |
| All project brains routed through one context | NOT COMPLETE | migrate through DecisionContext |
| 9C/PTA runtime contracts | NEED REPAIR | M0 |
| Stage-2 Evidence Integrity | STARTED | first new Decision Spine gate |
| Engine Authority Registry | FOUNDATION ADDED | validate during migration |
| Canonical DecisionContext | NOT STARTED | M2 |
| Repository-wide D6-only final authority | PARTIAL | D6 exists, not every brain routed yet |
| Canonical FinalDecision | NOT STARTED | M5 |
| Jarvis display-only migration | NOT STARTED | M6 |
| Real derivatives/risk providers | PARTIAL | later provider work |

## Ordered build sequence

### M0 — Stage-2 stabilization / evidence integrity — IN PROGRESS

First code:

```text
apps/api/app/behavior/decision_spine/authority_registry.py
apps/api/app/behavior/decision_spine/stage2_integrity.py
apps/api/tests/decision_spine/test_stage2_integrity.py
```

Focused local verification before commit: **14 passed, 0 failed**.

The integrity gate checks same D2 snapshot identity, registered engine identity, explicit availability, future leakage, synthetic/mock/masked provenance, neutral substitution, final-authority limits, deterministic hashing, and fail-closed empty evidence. It can only PASS/DEGRADE/BLOCK evidence. It cannot grant paper authority or execute.

### M0-A — 9C runtime provenance/counting

Repair the inherited `real_runtime_computed_count` ambiguity. Do not relabel deterministic synthetic fallback data as real merely to satisfy a counter. Separate runtime computation from real-market-data provenance; synthetic fallback stays explanation-only/non-authoritative.

### M0-B — PTA probe/output semantics

The PTA registry contains 23 marker slots, but optional dependencies can leave many unavailable. Separate selected/probed/computed-no-signal/dependency-unavailable/error counts. Never fabricate 23 successful outputs when dependencies are missing. PTA remains excluded from trade/probability authority.

### M0-C — `synthetic_fallback` contract drift

`IndicatorSequenceRecord` already accepts `synthetic_fallback`; downstream `IndicatorFeatureBlock` must preserve that provenance while forcing explanation-only and probability-disabled semantics.

### M1 — Engine Authority Registry

Foundation added. Each engine is classified by module, classification, propose/veto/downgrade/finalize/execute rights, authority rank, consumer and lifecycle. Only `FINAL_CONFLUENCE_ARBITER` may set the final band. No engine may execute.

### M2 — Canonical DecisionContext

Build one PIT-safe evidence object with identity/snapshot hash, input integrity, price structure, candles, levels, regime, session, index/sector/relative strength, indicators, memory/analogs, hypotheses, strategies, ORB/AFRE, derivatives/events/failures, execution/portfolio risk, blockers/warnings, proof/paper authority, and provenance.

### M3 — Route all brains through DecisionContext

Remove temporary neutral placeholders such as `relative_strength_score=0.5`, `indicator_signal_score=0.0`, `external_ai_score=0.0`, and `weak_sector=False`. Missing must become explicit AVAILABLE/DEGRADED/UNAVAILABLE evidence, not neutral data.

### M4 — D6 as sole repository-wide final authority

ORB, AFRE, Hypothesis, Behavior Decision, Kronos, Gemini, Grok, Twin and Jarvis layers may produce evidence/proposals/downgrades/vetoes according to the registry but cannot emit a competing product final.

### M5 — Canonical FinalDecision

One output contract: `WAIT | WATCH | AVOID | PAPER-CANDIDATE`, bias, market story, primary setup/state, alternatives, derivatives, failures, history, entry plan, wait-for, avoid-if, main blocker, confidence, data/PIT/proof/paper status, reasons, warnings and engine provenance. Live routing stays blocked.

### M6 — Jarvis read-only presentation

Jarvis displays/explains the canonical FinalDecision and never independently upgrades it.

### M7 — contradiction / replay / safety tests

Test bullish strategy/AI evidence versus hard risk/failure/liquidity veto, unavailable evidence, stale/future evidence, replay determinism, hard-veto projection, AFRE proof gating and live-routing blocks.

### M8 — real providers + proof

Wire verified derivatives/event/risk providers into the same context, then run train-only selection -> unseen holdout -> expanding/repeated walk-forward -> approved playbook -> paper observation -> outcome memory -> edge-decay monitoring.

## Known inherited baseline failures

1. 9C real-runtime computed-count/provenance mismatch — M0-A
2. PTA marker selected/output-count mismatch — M0-B
3. `IndicatorFeatureBlock.synthetic_fallback` contract mismatch — M0-C
4. missing HSTRY `RELIANCE_NSE_5m.csv` fixture on Linux CI — data/CI task
5. PowerShell parser check on Ubuntu — platform/CI task

The first three must be repaired without hiding or reclassifying missing/synthetic evidence as real/clean.

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
```

Related status files:
- `docs/DECISION_SPINE_BUILD_STATUS_2026-09-08.md`
- `docs/ENGINE_AUTHORITY_UPGRADE_MATRIX_2026-09-08.md`
- `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`
- `docs/AFRE_V4_MERGE_STATUS_2026-09-08.md`
