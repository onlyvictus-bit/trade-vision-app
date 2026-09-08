# Trade Vision — Canonical Build Status

> **Purpose:** one durable repository source of truth for the controlled completion of Trade Vision.
>
> **Rule:** every future build/audit session starts here. Do not infer milestone state from old chats, old implementation percentages, or a subsystem's local tests.
>
> **Last audited:** 2026-09-08  
> **Active branch:** `decision-spine-orchestration-v1`  
> **Pre-update audited head:** `d8723947b078951435afe083f21e643f40ef64aa`  
> **Base main used for Decision Spine branch:** `f26546047a28df7deb3916ed0b4467d67fd9bb7b`  
> **AFRE v4 merge:** PR #1 merge commit `83070628bf153557ac6f5f54a025866bd484f76d`

---

## 1. Program rule — finish, prove, lock

The biggest current engineering risk is not lack of trading ideas. It is having many useful engines, adapters, memories, ORB/AFRE paths, reviewers, Jarvis layers, D6 logic and legacy decision surfaces that are partially connected, duplicated, or carrying neutral placeholders.

From this point onward, Trade Vision is completed as a controlled engineering program:

> **One milestone -> finish implementation -> test -> audit -> commit -> mark GREEN -> lock it. Do not reopen a locked milestone unless a later integration exposes a concrete defect.**

No jumping ahead to add another brain merely because an interesting idea appears. New work must belong to the current milestone or be recorded for the correct future milestone.

### Milestone state machine

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

A milestone is not GREEN merely because its new unit tests pass.

### Reopen rule

A locked milestone may be reopened only when a later integration produces a reproducible defect, safety regression, causal/provenance violation, contract incompatibility, or requirement contradiction. Record the reason before modifying the locked scope.

---

## 2. Canonical target architecture

Core principle:

> **Many brains may disagree internally. Only one decision may leave the brain.**

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

The immediate M2 introduction is deliberately narrower:

```text
D2 approved snapshot
        ↓
Stage-2 engine receipts
        ↓
Stage2IntegrityReport
        ↓
Canonical DecisionContext
        ↓
context_hash / provenance
        ↓
existing D6 unchanged
```

D6 does **not** consume the canonical context as its sole input until the later migration milestone.

---

## 3. Current milestone truth

| Step | Milestone | Goal | Current state | Exit condition |
|---|---|---|---|---|
| M0 | Stage-2 integrity | Fix runtime/provenance accounting and pre-D6 evidence integrity | **GREEN / LOCKED** | Runtime provenance/accounting truthful; Stage2 fail-closed gate wired; regressions green |
| M1 | Authority Registry | Define exactly what every brain may/cannot do | **FOUNDATION GREEN / SCOPE LOCKED** | Registry has one finalizer, zero execution authority, role classifications; repo-wide consumer migration is later M3/M4 |
| M2 | Canonical DecisionContext | One immutable deterministic causal input/evidence container | **CURRENT — IN BUILD** | All M2 exit gates in §5 green; Paper Guidance constructs/reports context without changing D6 behavior |
| M3 | Brain migration | Route specialist brains through canonical context | **NOT STARTED** | Active specialists consume/emit canonical evidence; legacy neutral placeholders removed; no independent causal paths |
| M4 | D6 orchestration | Make D6 the actual single final decision authority everywhere | **NOT STARTED / D6 EXISTS** | No parallel/public decision authority; D6 is repository-wide canonical consumer/finalizer |
| M5 | FinalDecision | Create the deterministic user-facing decision contract | **NOT STARTED** | Only `WAIT / WATCH / AVOID / PAPER-CANDIDATE` product action states; complete provenance/reasons/invalidation |
| M6 | Jarvis | Presentation/explanation only | **NOT STARTED** | Jarvis cannot alter, upgrade, or independently decide beyond FinalDecision |
| M7 | Contradiction & replay | Attack disagreement, stale/missing/future/bad/failure scenarios | **NOT STARTED** | Determinism and fail-closed behavior proven across contradiction/replay matrix |
| M8 | Real providers | Replace synthetic/placeholder evidence with verified NSE/OpenAlgo/official inputs | **NOT STARTED** | Proven provider identity, timestamps, freshness, PIT, normalization, provenance and fail-closed missing-data behavior |
| M9 | Historical validation | Walk-forward/regime/failure/robustness validation | **NOT STARTED** | Trading edge evidence exists independently of software unit-test success |
| M10 | Paper validation | Controlled paper observations/outcome tracking | **NOT STARTED** | Explicit paper promotion criteria satisfied with observed outcomes |
| M11 | Production hardening | Performance, observability, recovery, deployment, security, migrations | **NOT STARTED** | Operational production-readiness checks green |
| M12 | Production release gate | Final independent audit | **NOT STARTED** | Only after architecture, evidence, paper validation and operational gates pass may the system be called production-ready |

### Important interpretation

M1's registry foundation being GREEN does **not** mean all old arbitration surfaces are already removed. Their migration/demotion is intentionally owned by M3/M4/M6. Do not reopen M1 to do those later milestones.

---

## 4. Verified completed foundations

### M0 Stage-2 stabilization — GREEN / LOCKED

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

Closed M0 work:
- `synthetic_fallback` contract drift repaired;
- 9C real/synthetic/unavailable/failed runtime accounting separated;
- PTA selected/probed/computed/no-signal/dependency/error/materialized accounting separated;
- Stage2IntegrityReport wired before D6;
- hard integrity block stops before D6;
- inactive 9C/PTA/ORB/AFRE are explicit SKIPPED observations rather than neutral values.

### M1 Authority Registry — foundation GREEN / scope locked

Current invariant:

```text
exactly one may_set_final_band = FINAL_CONFLUENCE_ARBITER
zero may_execute engines
presenters cannot decide
reviewers cannot finalize
```

Registration defines authority; it does not activate a brain.

### M2 contract foundation — GREEN but M2 milestone not complete

Verification workflow:

```text
workflow: M2 DecisionContext
run:      34214606289
verified head: 90edc5c516324817c0e59bf56f072a63c2044e66
result:   SUCCESS
```

```text
DecisionContext suite                     25 passed
M0 Stage-2 integrity regression           15 passed
Paper Guidance v1.88 regression           29 passed
full apps/api/tests/test_api.py           556 passed
authority invariants                      PASS
```

The contract is immutable/deterministic and prohibits proof/paper/trade/final-band authority. This is only the M2 foundation; real pipeline construction remains open.

---

## 5. M2 — current scope and mandatory exit gates

**Do not start M3 until every item below is implemented, tested, audited, committed and the M2 state is changed here to `GREEN / LOCKED`.**

### 5.1 Code/contract hardening still required

- [ ] Every `EvidenceBlock.source_engine` must be present in the **exact** `Stage2IntegrityReport.engine_states` used to build that context, not merely registered globally.
- [ ] Evidence status/source mode must be compatible with the exact Stage2 engine state; context assembly must not upgrade a Stage2 `SKIPPED/UNAVAILABLE/ERROR` engine into clean AVAILABLE evidence.
- [ ] `InputIntegrity.freshness == BLOCK` must reject context construction.
- [ ] `InputIntegrity` with `DEGRADED`, `UNKNOWN`, or `BLOCK` integrity states must carry explicit reasons appropriate to the degraded/unknown/blocking fact; no unexplained bad integrity state.
- [ ] Keep PIT non-PASS fail-closed.
- [ ] Keep quarantine BLOCK fail-closed.
- [ ] Keep future evidence, snapshot mismatch, neutral substitution and non-authoritative probability use hard-rejected.

### 5.2 Real Paper Guidance -> DecisionContext adapter

Build a dedicated adapter/assembler from the existing D2-linked Paper Guidance evidence.

Rules:
- [ ] no independent refetch during context construction;
- [ ] no specialist rerun merely to fill a context field;
- [ ] use only evidence causally tied to the approved D2 snapshot;
- [ ] map current receipt-backed evidence into canonical fields with truthful provenance;
- [ ] inactive ORB/AFRE/9C/PTA remain explicit `SKIPPED` or `UNAVAILABLE` with reasons;
- [ ] unimplemented regime/session/index/sector/relative-strength/etc. remain explicit unavailable where no valid current receipt exists;
- [ ] missing evidence is never converted to `0.0`, `0.5`, `False`, empty-safe, or another neutral assumption;
- [ ] DecisionContext itself grants no paper authority;
- [ ] existing D6 decision behavior remains unchanged during M2.

### 5.3 Determinism / causal identity gates

- [ ] same request + same approved D2 state -> same D2 snapshot hash;
- [ ] same D2 evidence set -> same `Stage2IntegrityReport.output_hash`;
- [ ] same Stage2 report + same evidence -> same `DecisionContext.context_hash`;
- [ ] changed closed candle -> changed D2 snapshot hash and changed context hash;
- [ ] unfinished/unapproved candle never enters D2/DecisionContext;
- [ ] Stage2 BLOCK -> no DecisionContext object is constructed;
- [ ] future evidence -> no DecisionContext;
- [ ] evidence from another snapshot -> no DecisionContext.

### 5.4 Audit/provenance output

- [ ] add `context_hash` to Paper Guidance audit/provenance/debug output;
- [ ] include `stage2_integrity_hash` and context evidence/provenance identity needed for replay;
- [ ] do not expose DecisionContext as a second user-facing decision;
- [ ] do not let audit output imply paper/proof/trade authority.

### 5.5 Tests required before M2 can be GREEN

At minimum add/retain tests for:
- [ ] exact Stage2 engine-membership enforcement;
- [ ] Stage2 availability/source-mode compatibility;
- [ ] freshness BLOCK rejection;
- [ ] degraded/unknown integrity requires reasons;
- [ ] explicit skipped/unavailable specialist blocks;
- [ ] no neutral fallback for missing specialist evidence;
- [ ] same-request replay determinism through D2 -> Stage2 -> DecisionContext;
- [ ] changed closed candle changes D2/context hash;
- [ ] Stage2 BLOCK prevents adapter/context construction;
- [ ] D6 output parity before vs after introducing context audit path;
- [ ] existing sole-D6 and zero-execution authority invariants.

Then run:

```text
1. compile affected Decision Spine / Paper Guidance modules
2. DecisionContext targeted suite
3. Stage-2 integrity suite
4. Paper Guidance integration suite
5. affected adapter tests
6. full apps/api/tests/test_api.py
7. authority/safety invariant checks
```

### 5.6 M2 commit/lock gate

Only after all tests and audits are green:

1. commit the M2 implementation;
2. record commit SHA and CI run here;
3. change M2 to `GREEN / LOCKED` here;
4. change M3 to `CURRENT — IN BUILD` only when M3 actually begins;
5. do not continue coding into M3 in the same unverified M2 patch.

---

## 6. M2 code re-audit findings at 2026-09-08

These findings were reverified against repository code before creating this canonical tracker.

### Finding A — exact Stage2 membership is not yet enforced

Current `build_decision_context()` checks that each evidence engine exists in the global authority registry. It does **not** currently require that the same engine appear in the supplied `Stage2IntegrityReport.engine_states`.

This means a registered engine can currently appear in DecisionContext even when that engine was never part of the exact Stage2 report used for this context. This must be closed in M2.

### Finding B — freshness BLOCK is not yet rejected

Current construction explicitly rejects PIT non-PASS and quarantine BLOCK, but has no equivalent `freshness == BLOCK` rejection. This must be closed in M2.

### Finding C — degraded/unknown integrity reason contract is incomplete

`InputIntegrity` normalizes the `reasons` tuple but does not currently require reasons for degraded/unknown/blocking integrity states. M2 must make bad/unknown input state explainable and auditable.

### Finding D — real Paper Guidance context assembly is not wired

Paper Guidance currently builds Stage2 integrity and, when eligible, proceeds to the existing `FinalConfluenceArbiterRequest`. No real `DecisionContext` is assembled in that path yet.

### Finding E — known legacy neutral placeholders still feed D6

Current Paper Guidance still supplies legacy placeholders including:

```python
relative_strength_score = 0.5
indicator_signal_score  = 0.0
external_ai_score       = 0.0
weak_sector             = False
```

Do **not** remove or reinterpret them inside M2 in a way that changes D6 behavior. M2 must first represent the corresponding canonical evidence honestly as unavailable/skipped and prove D6 parity. Their actual removal/replacement belongs to M3 migration.

### Finding F — M2 tests do not yet cover the open hardening gates

The current DecisionContext suite verifies deterministic hashing, required fields, snapshot identity, future rejection, unregistered engine rejection, neutral substitution rejection, synthetic probability rejection, downstream-authority prohibition, Stage2 hard-block rejection, PIT and quarantine rules, immutability and provenance. It does not yet test exact Stage2 membership, freshness BLOCK, or bad-integrity reason requirements.

---

## 7. M3 migration order — recorded now, not started

Once M2 is GREEN/LOCKED, migrate specialist families one at a time:

```text
M3.1 price / candle / levels / indicators / MTF
M3.2 regime / session / index / sector / relative strength
M3.3 memory / historical analogs / 9C / PTA
M3.4 hypotheses / strategy candidates / ORB / AFRE
M3.5 derivatives / events / failure scenarios
M3.6 execution quality / behavior risk / portfolio/cooldown
M3.7 reviewer evidence: Kronos / Gemini / Grok / OpenAlgo / Twin
```

For each family:
1. use the same D2-causal context;
2. emit explicit availability/provenance;
3. remove only the corresponding legacy placeholder/path after replay parity;
4. add contradiction tests;
5. never create a new public final decision;
6. preserve D6 as sole final-band authority.

---

## 8. M4-M12 boundaries

### M4 — D6 orchestration

Make D6 the repository-wide canonical consumer/finalizer. Demote old Behavior/Twin/Jarvis arbitration surfaces to evidence, compatibility or presentation roles. No specialist may publish a competing product final.

### M5 — FinalDecision

Build one deterministic user-facing contract containing, at minimum:

```text
identity: symbol / time / timeframe / decision_context_hash
action: WAIT / WATCH / AVOID / PAPER-CANDIDATE
bias: LONG / SHORT / NEUTRAL
market_story
primary_setup + state
alternative_scenarios
derivatives_summary
failure_check: OBSERVED / ARMED / NOT_OBSERVED / UNOBSERVABLE
historical_evidence
entry_plan: side / entry / trigger / stop / targets / invalidation / RR / size_hint
wait_for
avoid_if
main_blocker
evidence_confidence
data_quality
PIT_status
proof_status
paper_authority
reason_for
reason_against
warnings
hard_blockers
engines_run
next_action: DO_NOTHING / OFFER_PAPER_TICKET
```

Safety remains:

```text
live_trading_blocked = true
order_routing_enabled = false
```

### M6 — Jarvis presentation only

Jarvis may summarize/explain/compare evidence but cannot upgrade, downgrade independently, change the final action, or become another final authority. External AI remains reviewer evidence only.

### M7 — contradiction/replay/safety attack matrix

Deliberately test situations such as:
- ORB/indicators/Kronos/Gemini bullish while risk/failure/liquidity block;
- missing sector/index/derivatives/events;
- stale/future/tampered evidence;
- malformed/unfinished candles;
- snapshot mismatches;
- repeated engine receipt / duplicate identity;
- non-authoritative synthetic evidence attempting probability/final authority;
- engine exception/degradation;
- unavailable data wrongly presented as neutral;
- same-input replay determinism;
- hard-veto projection through every public surface.

Expected behavior remains fail-closed.

### M8 — real providers

Verified provider adapters must preserve:
- provider/source identity;
- exchange/instrument identity;
- observation timestamp;
- receive timestamp;
- session/expiry;
- freshness/TTL;
- completeness;
- normalization version;
- provenance/content hash;
- PIT compatibility;
- explicit missing/invalid/fail-closed state.

Target flow:

```text
OpenAlgo / official feeds / verified providers
  -> provider adapters
  -> canonical option/futures/VIX/FII/event/restriction snapshots
  -> DerivativesSnapshot / RiskContextSnapshot
  -> existing calculators
  -> Capability[]
  -> SAME DecisionContext / D6 path
```

Do not add a parallel derivatives decision engine.

### M9 — historical validation

Architecture/unit tests cannot prove market edge. Required validation includes train-only selection, unseen holdout, expanding/rolling walk-forward, regime splits, failure-scenario splits, sensitivity/robustness checks, transaction-cost/slippage realism, sample-size guards, multiple-testing/overfit controls and edge-decay monitoring.

### M10 — paper validation

Use controlled paper-only observations, outcome labeling, drift monitoring, replayable decision/evidence IDs and explicit promotion criteria. Human approval remains required.

### M11 — operational production hardening

Cover performance/latency budgets, observability, metrics/logging/tracing, data/provider outage recovery, persistence/replay recovery, idempotency, concurrency, schema/version migration, deployment, rollback, secrets/security, rate limits, dependency failure and disaster recovery.

### M12 — production release gate

Independent final audit must verify:
- architecture/wiring matches canonical docs;
- all milestone locks are supported by commits/tests;
- no bypass/parallel public decision remains;
- real-provider provenance/PIT/freshness is proven;
- historical and paper evidence gates are satisfied;
- operational hardening is complete;
- research/paper/live safety boundary is explicit.

Only then may Trade Vision be described as production-ready.

---

## 9. Production-ready software != proven trading intelligence

This distinction is mandatory:

> **Production-ready code** means the architecture, contracts, tests, operations, security and recovery are engineered to production standards.
>
> **Production-ready trading intelligence** additionally requires credible historical/walk-forward evidence, paper observations, robustness and explicit promotion gates.

A beautiful, deterministic, fully tested architecture must still return `WAIT` when proof is insufficient.

Unit-test success, merge success, or AFRE/ORB confirmation is never market-edge proof.

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
- all M2+ evidence must remain D2-causal;
- missing/unknown data remains explicit;
- no external AI may override risk/data blocks;
- no specialist may claim final-band authority;
- no hidden live broker route may be introduced;
- D6 is the sole final-band authority;
- Jarvis becomes read-only presentation;
- FinalDecision is the only product-facing decision contract after M5.

---

## 11. Known remaining architecture debt — track, do not randomly patch

These are not permission to leave M2 scope:

```text
legacy relative_strength_score = 0.5
legacy indicator_signal_score  = 0.0
legacy external_ai_score       = 0.0
legacy weak_sector             = False
multiple older decision/arbiter/fusion presentation surfaces
partial verified real derivatives/event/OI/depth providers
Linux CI/HSTRY fixture coverage including RELIANCE_NSE_5m.csv
PowerShell parser verification on Ubuntu
```

Ownership:
- neutral placeholder removal -> M3;
- parallel authority demotion -> M4/M6;
- real provider completeness -> M8;
- edge proof -> M9/M10;
- infrastructure/operational hardening -> M11 unless it blocks an earlier milestone's test truth.

---

## 12. Future-session start procedure

Every new coding/audit session should do this before editing:

```text
1. Read docs/CANONICAL_BUILD_STATUS.md.
2. Verify active branch and current head.
3. Read only the source/tests for the CURRENT milestone.
4. Confirm previously GREEN milestones still have no integration defect exposed by current work.
5. Do not reopen locked milestones for cleanup/refactoring without a concrete defect.
6. Implement only the CURRENT milestone exit gates.
7. Run targeted -> integration -> full regression -> safety/authority checks.
8. Commit only after green verification.
9. Update this file with commit/run/results and advance exactly one milestone state.
10. Update architecture/engine docs only if ownership, authority, data contract or wiring materially changed.
```

If repository truth conflicts with this document, **code/tests win temporarily**, and this document must be corrected in the same audit before continuing.

---

## 13. Supporting references — not competing status sources

Use these for detail/history, but advance milestone status only in this file:

- `docs/NEXT_BUILD_TARGET.md` — short pointer to the current target;
- `docs/DECISION_SPINE_BUILD_STATUS_2026-09-08.md` — dated historical Decision Spine snapshot;
- `docs/ENGINE_AUTHORITY_UPGRADE_MATRIX_2026-09-08.md` — per-engine migration/authority matrix;
- `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md` — architecture/brain ownership and wiring reference;
- `docs/SAFETY_INVARIANTS.md` — safety rules;
- `docs/plans/FINAL_REQUIRED_FLOW.md` — product-spine requirements;
- `docs/IMPLEMENTATION_STATUS.md` — broader historical ship log.

This file is the **canonical milestone/build-status source of truth** from 2026-09-08 onward.
