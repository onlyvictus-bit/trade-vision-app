# Trade Vision — Canonical Build Status

> **Purpose:** durable repository source of truth for controlled completion of Trade Vision.
>
> **Program rule:** one milestone -> implement -> test -> adversarial/replay/parity -> full regression -> authority audit -> commit -> GREEN -> lock.

**Last audited:** 2026-09-08  
**Active branch:** `m3-1-canonical-price-intelligence`  
**Controlling M3.1 spec:** `docs/M3_1_CANONICAL_PRICE_INTELLIGENCE_MIGRATION_PLAN_2026-09-08.md`  
**M3.1 pre-documentation verified source head:** `a346ca62ddc960e0402b7df661bb3215cfa45a7b`  
**M3.1 pre-documentation verification:** `M3.1 Canonical Price Intelligence` run `34254621808` — **SUCCESS**

The workflow checks out the exact triggering `${{ github.sha }}` and verifies `git rev-parse HEAD == GITHUB_SHA`; branch-tip drift is not accepted as lock evidence.

---

## 1. Locked semantics and authority

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no_signal != unavailable
no_output != neutral

D1 outranks every predictor/reviewer
no incomplete-bar authority
all M2+ evidence is D2-causal
specialists cannot set final band
FINAL_CONFLUENCE_ARBITER / D6 is sole final-band authority
zero execution authority
RAW FACT CALCULATED ONCE; many may interpret; every interpretation traceable
```

Safety boundary remains:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
```

M3.1 is sensory/canonical evidence infrastructure. It does not prove trading edge and does not authorize live trading.

---

## 2. Milestone truth

| Step | Milestone | State | Boundary |
|---|---|---|---|
| M0 | Stage-2 integrity | **GREEN / LOCKED** | truthful evidence accounting and fail-closed pre-D6 integrity |
| M1 | Authority Registry | **FOUNDATION GREEN / SCOPE LOCKED** | exactly one final-band authority; zero execution authority |
| M2 | Canonical DecisionContext | **GREEN / LOCKED** | deterministic D2-causal context before unchanged D6 |
| M3 | Brain migration | **IN BUILD** | later specialist families remain to migrate |
| M3.1 | Canonical Price Intelligence | **GREEN / LOCKED** | A-F complete; D6 semantics unchanged |
| M3.1-A | Snapshot Feature Kernel | **GREEN / LOCKED** | immutable calculate-once D2 feature substrate |
| M3.1-B | Canonical Candle Intelligence | **GREEN / LOCKED** | one Anatomy computation; shared Condition/Chart facts |
| M3.1-C | Canonical Level Intelligence | **GREEN / LOCKED** | session VWAP, OR5/15/30, PIT-safe previous-session levels/CPR |
| M3.1-D | Canonical Indicator Intelligence | **GREEN / LOCKED** | typed indicator evidence, dependency/family/correlation metadata |
| M3.1-E | PIT-safe MTF Intelligence | **GREEN / LOCKED** | independently hashed closed-only HTF facts |
| M3.1-F | Price Evidence Fusion / DAG / parity | **GREEN / LOCKED** | bounded contradiction-preserving zero-authority price world-state |
| M3.2+ | Later brain families | **NEXT / NOT STARTED** | eligible only after this M3.1 lock; do not imply implementation |
| M4 | D6 orchestration redesign | **NOT STARTED / D6 EXISTS** | no M3.1 semantic redesign performed |
| M5-M12 | FinalDecision through independent release gate | **NOT STARTED** | later canonical program stages |

Do not reinterpret **NEXT** as started. M3.2+ work requires a new explicit milestone session.

---

## 3. Canonical M3.1 architecture now locked

```text
D1 DATA / PIT / KILL-SWITCH SAFETY
        |
        v
D2 IMMUTABLE CLOSED-CANDLE SNAPSHOT
        |
        v
SNAPSHOT FEATURE KERNEL                 M3.1-A
CALCULATE REUSABLE RAW FACTS ONCE
        |
        +--> CANDLE ANATOMY             M3.1-B
        |      +--> CONDITION
        |      +--> CHART REASONING
        |
        +--> LEVEL INTELLIGENCE          M3.1-C
        |      +--> session VWAP
        |      +--> OR5 / OR15 / OR30
        |      +--> prior-session PDH/PDL/close/CPR
        |
        +--> INDICATOR INTELLIGENCE      M3.1-D
        |      +--> typed state
        |      +--> family/dependency/correlation metadata
        |
        +--> MTF INTELLIGENCE            M3.1-E
               +--> closed-only per-TF D2 identities
               +--> independent series/snapshot hashes
        |
        v
PRICE STRUCTURE EVIDENCE / DAG          M3.1-F
preserves aligned/conflicting/unavailable facts
        |
        v
Stage2IntegrityReport
        |
        v
DecisionContext
        |
        v
CURRENT D6 / FINAL_CONFLUENCE_ARBITER
UNCHANGED SOLE FINAL-BAND AUTHORITY
```

No M3.1 composer may propose, veto, downgrade, set the final band or execute.

---

## 4. M3.1-A — Snapshot Feature Kernel — GREEN / LOCKED

Primary implementation:

`apps/api/app/behavior/decision_spine/snapshot_feature_kernel.py`

Locked facts:

- immutable D2 identity and closed-bar vectors;
- reusable average-range / volume / anchored feature primitives;
- no future/incomplete bar authority;
- deterministic hashes and bounded audit metadata;
- feature-kernel build count is one in the migrated Paper Guidance route.

Mathematical preservation: historical `candle-anatomy.v0.15` `range_atr` is an arithmetic mean candle range, not Wilder true-range ATR. M3.1 preserves that behavior explicitly as `average_range`. Any future true-ATR correction must be separately versioned and parity-reviewed.

---

## 5. M3.1-B — Canonical Candle Intelligence — GREEN / LOCKED

Locked guarantees:

- Candle Anatomy calculated once from the shared feature kernel;
- Condition and Chart consume that exact Anatomy result;
- causal upstream hashes are recorded;
- `DecisionContext.candle_anatomy` is bounded receipt-backed evidence;
- engine failure blocks rather than becoming neutral D6 input;
- D6 behavior remains unchanged.

Historical B lock reference:

`a3223327df0c2e49456440c7f99ac2c3565bbf13`

---

## 6. M3.1-C — Canonical Level Intelligence — GREEN / LOCKED

Primary implementation:

`apps/api/app/behavior/decision_spine/canonical_level_intelligence.py`

Versioned semantics include:

```text
canonical-level-intelligence.v1
nse-cash-regular-session.v1
Asia/Kolkata
regular observed session 09:15-15:30
```

Locked guarantees:

- session VWAP resets to current observed regular session and does not mix prior-session volume;
- VWAP weighted-deviation ±1/±2/±3 bands;
- OR5/15/30 use explicit 09:15-to-window-end time semantics, never global `bars[:3]`;
- incomplete OR is PENDING/UNAVAILABLE, not partial authority;
- complete prior observed session yields PDH/PDL/previous close and CPR with source hash;
- missing volume and incomplete prior session stay explicit missingness;
- exact shared M3.1-A kernel object reused;
- canonical levels calculate once and receipts are hashed only after final summary/status/warnings are complete;
- old D6-facing level semantics remain an isolated compatibility projection.

Known boundary: this is observed-bar regular-session semantics, not an authoritative NSE holiday/special-session/half-day calendar provider.

---

## 7. M3.1-D — Canonical Indicator Intelligence — GREEN / LOCKED

Primary implementation:

`apps/api/app/behavior/real_indicator_adapter.py`

Canonical evidence version:

`indicator-evidence.v1`

Typed states distinguish:

```text
COMPUTED
NO_SIGNAL
NO_OUTPUT
INSUFFICIENT_WARMUP
DEPENDENCY_UNAVAILABLE
SLOW_BLOCKED
ERROR
UNSUPPORTED
```

Locked guarantees:

- ERROR/no-output/warmup/dependency failure is never canonical numeric zero;
- one DataFrame is built for a batch and normalization does not recompute an indicator merely to represent it;
- cache identity includes calculation version, exact input-window hash, indicator id and parameter hash;
- family, dependency-family and correlation-group metadata are explicit;
- correlated indicator names are not represented as independent-vote authority;
- normalized evidence is bounded and D2-provenanced on the migrated route;
- operational latency/cache telemetry is separated from deterministic evidence identity;
- `indicator_signal_score = 0.0` in current D6 remains unchanged until a later authorized D6 migration.

Historical D verification reference:

`5a6245a9e2ab540baac6bf2f1220f52e8387be1b`, workflow run `34251758325` — **SUCCESS**.

---

## 8. M3.1-E — PIT-safe MTF Intelligence — GREEN / LOCKED

Primary implementation:

`apps/api/app/behavior/decision_spine/canonical_mtf_intelligence.py`

Canonical version:

`mtf-confirmation.v2`

Locked guarantees:

- each timeframe carries its own source snapshot hash and source-series hash;
- only fully closed bars at `decision_time_ns` may enter causal MTF state;
- incomplete/future bars may be audit metadata but cannot perturb the causal MTF hash;
- an unfinished 15m/30m/1H/daily bar has zero evidence authority;
- duplicate timeframe inputs are UNAVAILABLE instead of last-write-wins;
- symbol mismatch, non-monotonic closed source clocks and D2-freeze failure fail closed;
- partial/missing HTF facts remain explicit degradation;
- current D6 confirmation compatibility behavior is retained.

Known provider limits are explicit, not fabricated: official exchange calendar verification, corporate-action adjustment provenance and external feed freshness/clock-skew proof are not yet wired.

Historical E verification reference:

`473b960ec21fcba02a92e312e3e4d65f626548cc`, workflow run `34252695299` — **SUCCESS**.

---

## 9. M3.1-F — Price Evidence Fusion / DAG / parity — GREEN / LOCKED

Primary implementation:

`apps/api/app/behavior/decision_spine/price_structure_evidence.py`

Orchestration guard:

`apps/api/app/behavior/paper_guidance_spine_m3_1_impl.py`

DecisionContext integration:

`apps/api/app/behavior/decision_spine/paper_guidance_decision_context_adapter.py`

Locked guarantees:

- builds a bounded `PRICE_STRUCTURE_EVIDENCE` world-state; no weighted price score is introduced;
- local structure and MTF hashes are preserved independently;
- aligned, conflicting and unavailable facts remain visible simultaneously;
- upstream receipt hashes and exact D2 snapshot identity are traceable;
- DAG validation rejects mismatched snapshots, unknown dependencies, duplicate nodes, cycles and future authority;
- epistemic availability/quality/completeness/warnings stay explicit;
- composer authority is fixed to:

```text
may_propose = false
may_veto = false
may_downgrade = false
may_set_final_band = false
may_execute = false
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
```

- standalone locked-M2 adapter callers do not fabricate later M3.1 upstream receipts: F activates only when canonical Level and MTF provenance markers plus local upstream receipts are genuinely present;
- malformed migrated F provenance blocks before D6;
- current D6 final outputs remain parity-equal to the preserved pre-M2/legacy route in the locked integration test.

F targeted coverage on the M3.1 pre-documentation gate:

```text
Price evidence fusion                     5 passed
Replay / metamorphic                      4 passed
Adversarial DAG                           8 passed
```

---

## 10. M3.1 pre-documentation lock evidence

Exact verified source head:

`a346ca62ddc960e0402b7df661bb3215cfa45a7b`

Workflow:

`M3.1 Canonical Price Intelligence`

Run:

`34254621808` — **SUCCESS**

Observed counts:

```text
M3.1-A Snapshot Feature Kernel                         15 passed
M3.1-B Canonical Candle Pipeline                       13 passed
M3.1-C Canonical Level Intelligence                    15 passed
M3.1-D Canonical Indicator Intelligence                12 passed
M3.1-E PIT-safe MTF Intelligence                       11 passed
M3.1-F Price Evidence Fusion                            5 passed
M3.1-F Replay / Metamorphic                             4 passed
M3.1-F Adversarial DAG                                  8 passed
Locked M2 DecisionContext                              34 passed
Locked M2 standalone DecisionContext adapter           13 passed
Locked M2 Paper Guidance integration / D6 parity       10 passed
Locked M0 Stage2 integrity                             15 passed
Paper Guidance v1.88                                   29 passed, 2 warnings
Historical tests/test_api.py                          556 passed, 11 warnings
Entire apps/api/tests tree                           1060 passed, 5 skipped, 11 warnings
Authority / sole-D6 / zero-execution                   PASS
Exact triggering-commit checkout                       PASS
```

The five full-tree skips are environment/resource dependent rather than M3.1 logic substitutions: existing external fixture/tool-dependent tests skip only when their required resource is genuinely absent. In particular, the HSTRY real-data invariant remains strict when its read-only CSV fixtures exist, and the PowerShell parser test remains strict when `powershell`/`pwsh` exists.

D6 semantic parity requirement is **zero diff** for the locked integration outputs:

```text
snapshot_hash
final_band
confidence_cap
next_action
arbiter_summary
```

No frontend files changed during M3.1 completion, so frontend typecheck/build was not an applicable gate for this diff.

---

## 11. Remaining epistemic caveats

M3.1 software verification does not establish:

- official NSE holiday, special-session or half-day calendar authority;
- authoritative corporate-action adjustment provenance across every provider;
- external market-feed freshness / clock-skew proof;
- empirical trading edge, profitability, walk-forward robustness or realistic-cost performance.

Those remain explicit future-provider / validation work. They must not be inferred from green unit/integration/CI gates.

---

## 12. Next boundary

M3.1 A-F are complete and locked. The next eligible program work is **M3.2+ later brain-family migration**, but it is **NOT STARTED** by this lock.

Do not use M3.1 completion as permission to start M4/D6 redesign, ORB redesign, derivatives migration or execution work without the controlling milestone explicitly authorizing it.
