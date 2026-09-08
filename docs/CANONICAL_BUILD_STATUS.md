# Trade Vision — Canonical Build Status

> **Purpose:** durable repository source of truth for controlled completion of Trade Vision.
>
> **Rule:** one milestone -> implement -> test -> audit -> commit -> GREEN -> lock. Do not infer milestone state from old chats, percentages, or subsystem-local tests.

**Last audited:** 2026-09-08  
**Active branch:** `decision-spine-orchestration-v1`  
**M2 verified source head:** `105561fc4908db6c18c32f9fd1a81ae5570f680f`  
**M2 verification workflow:** `M2 DecisionContext` run `34233061074` — **SUCCESS**  
**Base main used for Decision Spine branch:** `f26546047a28df7deb3916ed0b4467d67fd9bb7b`  
**AFRE v4 merge:** PR #1 merge commit `83070628bf153557ac6f5f54a025866bd484f76d`

---

## 1. Program rule

The project already contains many useful engines, memories, ORB/AFRE paths, reviewers, Jarvis surfaces and legacy decision paths. The main engineering risk is orchestration inconsistency, duplicated authority, hidden neutral assumptions, and causal/provenance drift—not a lack of additional trading ideas.

Canonical principle:

> **Many brains may disagree internally. Only one decision may leave the brain.**

Milestone state machine:

```text
NOT STARTED
    ↓
IN BUILD
    ↓
CODE COMPLETE
    ↓
TARGETED TESTS GREEN
    ↓
INTEGRATION TESTS GREEN
    ↓
FULL REGRESSION GREEN
    ↓
SAFETY / AUTHORITY AUDIT GREEN
    ↓
COMMITTED
    ↓
MILESTONE GREEN / LOCKED
```

A locked milestone is reopened only for a reproducible defect, safety regression, causal/provenance violation, contract incompatibility, or requirement contradiction exposed by later integration.

---

## 2. Canonical target architecture

```text
VERIFIED MARKET DATA
        |
        v
D1 DATA / PIT / KILL-SWITCH SAFETY
        |
        v
D2 IMMUTABLE CLOSED-CANDLE SNAPSHOT
        |
        v
STAGE-2 ANALYSIS BRAINS
        |
        v
STAGE-2 EVIDENCE INTEGRITY
        |
        v
ONE Canonical DecisionContext
        |
   +----+-------------------------+
   |                              |
   v                              v
Price / Context / Memory     ORB / AFRE / Hypotheses
   |                              |
   +--------------+---------------+
                  |
        Derivatives / Events
                  |
           Failure / Risk
                  |
         Execution Reality
                  |
                  v
       FINAL CONFLUENCE / D6
        SOLE FINAL AUTHORITY
                  |
                  v
            FinalDecision
                  |
                  v
               JARVIS
            DISPLAY ONLY
```

M2 intentionally stops short of migrating D6 inputs:

```text
D2 approved snapshot
        ↓
current D2-native Stage-2 receipts
+ explicit inactive/unavailable inventory
        ↓
Stage2IntegrityReport
        ↓
Canonical DecisionContext
        ↓
context_hash / provenance / compact audit
        ↓
existing D6 inputs unchanged
```

---

## 3. Milestone truth

| Step | Milestone | State | Exit condition / next boundary |
|---|---|---|---|
| M0 | Stage-2 stabilization / evidence integrity | **GREEN / LOCKED** | truthful runtime accounting; Stage2 fail-closed gate before D6 |
| M1 | Engine Authority Registry | **FOUNDATION GREEN / SCOPE LOCKED** | exactly one final-band authority; zero execution authority |
| M2 | Canonical DecisionContext real-pipeline construction | **GREEN / LOCKED** | deterministic causal context is built in Paper Guidance before unchanged D6 |
| M3 | Brain migration | **NOT STARTED — NEXT ELIGIBLE** | migrate specialist families through canonical context and remove corresponding legacy placeholders only after replay parity |
| M4 | D6 orchestration | **NOT STARTED / D6 EXISTS** | D6 becomes repository-wide canonical consumer/finalizer; parallel public authority removed |
| M5 | FinalDecision | **NOT STARTED** | one deterministic product decision contract |
| M6 | Jarvis presentation | **NOT STARTED** | Jarvis read-only explanation/presentation |
| M7 | Contradiction / replay attack matrix | **NOT STARTED** | adversarial disagreement, stale/missing/future/tampered evidence proven fail-closed |
| M8 | Verified real providers | **NOT STARTED** | provider identity, PIT, freshness, normalization and provenance proven |
| M9 | Historical / walk-forward validation | **NOT STARTED** | edge evidence independent of unit-test success |
| M10 | Controlled paper validation | **NOT STARTED** | observed paper outcomes satisfy explicit promotion criteria |
| M11 | Operational hardening | **NOT STARTED** | performance, observability, recovery, security, deployment and migration gates |
| M12 | Independent production release gate | **NOT STARTED** | architecture + evidence + validation + operational gates independently verified |

Do **not** start M3 in an M2 verification/docs patch.

---

## 4. M0 — locked foundation

Tested source commit: `728d81d40ec8cdfe136e765ff0378118a8c1e759`  
Committed-tree verification: run `34213835837` — SUCCESS

```text
Stage-2 integrity                         15 passed
Paper Guidance v1.88                      29 passed
full apps/api/tests/test_api.py           556 passed
authority invariants                      PASS
```

Locked M0 semantics retained by M2:
- `synthetic_fallback` is never relabeled real;
- 9C real/synthetic/unavailable/failed accounting remains explicit;
- PTA selected/probed/computed/no-signal/dependency/error/materialized accounting remains explicit;
- Stage2 hard block stops before D6;
- inactive `NINE_CANDLE_MEMORY`, `PTA_MARKER_RUNTIME`, `ORB_CORE`, and `AFRE` remain explicit `SKIPPED` observations in the Paper Guidance route.

---

## 5. M1 — authority foundation locked

Current authority invariants:

```text
exactly one may_set_final_band = FINAL_CONFLUENCE_ARBITER
zero may_execute engines
presenters cannot decide
reviewers cannot finalize
```

Registration does not activate a brain.

---

## 6. M2 — GREEN / LOCKED

### 6.1 Canonical coding reference

The M2 implementation reference is:

`docs/M2_AUDIT_VERDICT_CODING_REFERENCE_2026-09-08.md`

Core interpretation:

> M2 is not another trading predictor. It is the immutable canonical world-state/evidence layer that records what is known, unknown, unavailable, skipped, degraded or erroneous at one exact D2 snapshot.

### 6.2 Contract hardening completed

`apps/api/app/behavior/decision_spine/decision_context.py` now enforces:
- exact `EvidenceBlock.source_engine` membership in the supplied `Stage2IntegrityReport`;
- exact D2 snapshot identity;
- registered + snapshot-matched + identity-matched Stage2 source state;
- monotonic evidence availability: DecisionContext may preserve/downgrade but never upgrade Stage2 evidence;
- exact Stage2 source-mode provenance; no UNKNOWN/MOCK/MASKED/SYNTHETIC source may become REAL/VERIFIED inside context;
- `freshness == BLOCK` rejects context construction;
- non-PASS PIT/freshness/quarantine integrity requires an explicit reason;
- PIT non-PASS remains fail-closed;
- quarantine BLOCK remains fail-closed;
- future evidence, neutral-default substitution and non-authoritative probability use remain rejected;
- no evidence block may claim proof, paper, trade or final-band authority;
- optional `source_output_hash` links receipt fingerprints into canonical evidence provenance;
- context remains immutable and deterministically SHA-256 hashed.

### 6.3 Real Paper Guidance adapter completed

New module:

`apps/api/app/behavior/decision_spine/paper_guidance_decision_context_adapter.py`

Responsibilities are deliberately narrow:
- no I/O;
- no provider fetch;
- no database/history read;
- no specialist rerun;
- no indicator recomputation;
- no ORB/AFRE execution;
- no AI call;
- no probability computation;
- no D6/final authority.

It:
1. builds O(1) receipt and Stage2 indexes;
2. maps current D2-native receipts into 22 canonical fields;
3. represents inactive specialists explicitly as `UNAVAILABLE`/`SKIPPED` with reasons;
4. keeps freshness and quarantine `UNKNOWN` where no canonical assessor exists rather than fabricating PASS;
5. carries receipt `output_hash` into evidence provenance;
6. constructs the immutable DecisionContext;
7. returns only a compact audit projection to normal Paper Guidance output.

### 6.4 Canonical 22-field evidence inventory

Current M2 truth is deliberately conservative:

```text
receipt-backed now:
  price_structure        <- MARKET_STRUCTURE_LIQUIDITY
  levels                 <- LEVEL_CONTEXT
  indicators             <- SNAPSHOT_INDICATOR_RUNTIME
  memory                 <- PERSISTED_INDICATOR_MEMORY
  events                 <- EXECUTION_EVENT_OI_RISK
  execution_quality      <- EXECUTION_EVENT_OI_RISK

explicit unavailable/skipped until M3 migration:
  candle_anatomy
  market_regime
  session_context
  index_context
  sector_context
  relative_strength
  historical_analogs
  hypotheses
  strategy_candidates
  orb_variants
  afre_scenarios
  derivatives
  failure_scenarios
  portfolio_risk
  proof_status
  paper_authority
```

Locked semantic rule:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
```

### 6.5 Paper Guidance runtime wiring completed

Public compatibility facade:
`apps/api/app/behavior/paper_guidance_spine.py`

M2 implementation:
`apps/api/app/behavior/paper_guidance_spine_m2_impl.py`

Byte-preserved pre-M2 implementation for parity/rollback:
`apps/api/app/behavior/paper_guidance_spine_legacy.py`

Runtime:

```text
D1
 ↓
D2
 ↓
current D2-native Stage2 engines
 ↓
receipts
 + explicit canonical inactive inventory
 + locked M0 9C/PTA/ORB/AFRE skipped inventory
 ↓
Stage2IntegrityReport
 ↓
if BLOCK -> WAIT / DO_NOTHING / no DecisionContext / no D6
 ↓ eligible
DecisionContext
 ↓
if contract failure -> WAIT / DO_NOTHING / no D6
 ↓ valid
compact context audit
 ↓
legacy D6 request UNCHANGED
 ↓
FINAL_CONFLUENCE_ARBITER
```

The public facade preserves historical monkeypatch/fault-injection hooks used by the regression suite.

### 6.6 D6 parity explicitly proven

M2 does not reinterpret legacy D6 placeholders yet. These remain migration debt owned by M3:

```python
relative_strength_score = 0.5
indicator_signal_score  = 0.0
external_ai_score       = 0.0
weak_sector             = False
```

Direct integration test compares M2 output against the byte-preserved pre-M2 implementation and asserts equality of:
- snapshot hash;
- guidance ID;
- final band;
- confidence cap;
- next action;
- arbiter summary;
- engine receipts.

Thus M2 adds canonical evidence truth/auditability without changing current D6 decision behavior.

### 6.7 Determinism / causal identity proven

Tests prove:
- same request + same approved D2 state -> same snapshot hash;
- same evidence set -> same Stage2 integrity hash;
- same Stage2/evidence -> same DecisionContext hash;
- same request -> same legacy guidance result;
- changed legitimate closed candle -> changed D2 and context hashes;
- typed context-integrity failure stops before D6;
- Stage2 BLOCK stops before context/D6;
- exact Stage2 source membership is mandatory;
- missing specialist data stays explicit instead of becoming a neutral score.

### 6.8 Compact audit output

`risk_summary["decision_context"]` contains only replay/audit metadata:

```text
adapter_version
context_version
context_hash
snapshot_hash
stage2_integrity_hash
integrity:
  data_quality
  pit_status
  freshness
  quarantine_status
  reasons
evidence:
  available_count
  degraded_count
  unavailable_count
  skipped_count
  error_count
  field_count
safety:
  paper_promotion_eligible = false
  trade_allowed = false
  order_routing_enabled = false
  live_trading_blocked = true
```

The full world-state is not duplicated in normal API responses and DecisionContext is not exposed as a second product decision.

### 6.9 Final M2 committed-tree verification

Verified source head:
`105561fc4908db6c18c32f9fd1a81ae5570f680f`

Workflow:
`M2 DecisionContext`

Run:
`34233061074`

Result:
**SUCCESS**

```text
compile affected M2 modules                    PASS
DecisionContext contract                       34 passed
Paper Guidance DecisionContext adapter         13 passed
M2 real-pipeline integration + D6 parity       10 passed
M0 Stage2 integrity regression                 15 passed
Paper Guidance v1.88 regression                29 passed
full apps/api/tests/test_api.py                556 passed
authority registry / sole-D6 / zero-execution PASS
```

Warnings remain known dependency/deprecation warnings; no test failures were present.

### 6.10 M2 lock decision

All mandatory M2 exit gates are satisfied. M2 is therefore:

> **GREEN / LOCKED**

A later milestone may reopen M2 only under the formal reopen rule.

---

## 7. M3 — next eligible milestone, NOT STARTED

Do not code M3 as part of the M2 lock commit.

Recorded migration order:

```text
M3.1 price / candle / levels / indicators / MTF
M3.2 regime / session / index / sector / relative strength
M3.3 memory / historical analogs / 9C / PTA
M3.4 hypotheses / strategy candidates / ORB / AFRE
M3.5 derivatives / events / failure scenarios
M3.6 execution quality / behavior risk / portfolio/cooldown
M3.7 reviewer evidence: Kronos / Gemini / Grok / OpenAlgo / Twin
```

For every family:
1. consume the same D2-causal DecisionContext identity;
2. emit explicit availability/provenance;
3. remove only the corresponding legacy placeholder/path after replay parity;
4. add contradiction/adversarial tests;
5. never create a parallel public final decision;
6. preserve D6 as sole final-band authority.

---

## 8. Later milestone boundaries

### M4 — D6 orchestration
Make D6 the repository-wide canonical consumer/finalizer. Demote old Behavior/Twin/Jarvis arbitration surfaces to evidence, compatibility or presentation roles.

### M5 — FinalDecision
Build one deterministic user-facing decision contract with `WAIT / WATCH / AVOID / PAPER-CANDIDATE`, bias, market story, alternatives, failure checks, evidence/proof state, entry plan when authorized, invalidation, blockers and replay provenance.

### M6 — Jarvis
Presentation/explanation only. Jarvis may not independently upgrade/downgrade or change the final action.

### M7 — contradiction/replay attack matrix
Test bullish specialist agreement against risk/failure/liquidity blocks; missing/stale/future/tampered evidence; malformed/unfinished candles; snapshot mismatch; duplicate receipts; synthetic authority attempts; engine exceptions; and same-input replay.

### M8 — verified real providers
Provider adapters must preserve source identity, exchange/instrument identity, observation/receive timestamps, session/expiry, freshness/TTL, completeness, normalization version, provenance/content hash and PIT compatibility. Missing/invalid data stays fail-closed.

### M9 — historical validation
Train-only selection, unseen holdout, rolling/expanding walk-forward, regime/failure splits, cost/slippage realism, sensitivity, sample guards, multiple-testing controls and edge-decay monitoring.

### M10 — paper validation
Controlled paper-only observations, outcome labeling, drift monitoring, replayable decision/evidence IDs and explicit promotion criteria. Human approval remains mandatory.

### M11 — operational hardening
Performance/latency budgets, observability, provider outage recovery, persistence/replay recovery, idempotency, concurrency, schema/version migration, deployment, rollback, secrets/security, rate limits and disaster recovery.

### M12 — independent production release gate
Only after architecture, provider provenance, historical/paper evidence and operational gates pass may the system be described as production-ready.

---

## 9. Production-ready code != proven trading edge

> **Production-ready software** means architecture, contracts, tests, operations, security and recovery are engineered to production standards.
>
> **Production-ready trading intelligence** additionally requires credible historical/walk-forward evidence, paper observations, robustness and explicit promotion gates.

M2 being GREEN does **not** prove a market edge and grants no paper/live authority.

---

## 10. Safety and truth invariants

Never weaken these to make a milestone pass:

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
merge_success != edge_proof
unit_tests_green != trading_edge_proven
```

Hard architecture rules:
- D1 outranks every predictor/strategy/reviewer;
- no unfinished candle receives decision authority;
- all M2+ evidence remains D2-causal;
- missing/unknown data remains explicit;
- no external AI may override risk/data blocks;
- no specialist may claim final-band authority;
- no hidden live broker route may be introduced;
- D6 is the sole final-band authority;
- Jarvis becomes read-only presentation;
- FinalDecision becomes the only product-facing decision contract after M5.

---

## 11. Known remaining debt and ownership

```text
legacy relative_strength_score = 0.5
legacy indicator_signal_score  = 0.0
legacy external_ai_score       = 0.0
legacy weak_sector             = False
canonical real freshness assessor not yet wired
canonical quarantine assessor not yet wired
multiple older decision/arbiter/fusion presentation surfaces
partial verified real derivatives/event/OI/depth providers
Linux CI/HSTRY fixture coverage including RELIANCE_NSE_5m.csv
PowerShell parser verification on Ubuntu
```

Ownership:
- specialist evidence and neutral-placeholder removal -> M3;
- parallel authority demotion -> M4/M6;
- verified provider/freshness completeness -> M8;
- edge proof -> M9/M10;
- infrastructure/operational hardening -> M11 unless it blocks an earlier milestone’s truth.

---

## 12. Future-session start procedure

```text
1. Read docs/CANONICAL_BUILD_STATUS.md.
2. Verify active branch and current head.
3. Read only source/tests for the CURRENT milestone.
4. Confirm locked milestones have no integration defect exposed by current work.
5. Do not reopen locked work for cleanup/refactoring without a concrete defect.
6. Implement only the current milestone exit gates.
7. Run targeted -> integration -> full regression -> safety/authority checks.
8. Commit only after green verification.
9. Update this file with commit/run/results and advance exactly one milestone.
10. Update architecture/engine docs only if ownership, authority, data contract or wiring materially changed.
```

If repository truth conflicts with this document, code/tests win temporarily and this document must be corrected before continuing.

---

## 13. Supporting references

- `docs/M2_AUDIT_VERDICT_CODING_REFERENCE_2026-09-08.md` — controlling M2 implementation reference;
- `docs/NEXT_BUILD_TARGET.md` — short next-milestone pointer;
- `docs/DECISION_SPINE_BUILD_STATUS_2026-09-08.md` — dated Decision Spine snapshot;
- `docs/ENGINE_AUTHORITY_UPGRADE_MATRIX_2026-09-08.md` — per-engine migration/authority matrix;
- `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md` — architecture/wiring reference;
- `docs/SAFETY_INVARIANTS.md` — safety rules;
- `docs/plans/FINAL_REQUIRED_FLOW.md` — product-spine requirements.

This file is the **canonical milestone/build-status source of truth**.