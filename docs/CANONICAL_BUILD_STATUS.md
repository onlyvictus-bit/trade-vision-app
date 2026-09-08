# Trade Vision — Canonical Build Status

> **Purpose:** durable repository source of truth for controlled completion of Trade Vision.
>
> **Rule:** one milestone -> implement -> test -> audit -> commit -> GREEN -> lock. Do not infer milestone state from old chats, percentages, or subsystem-local tests.

**Last audited:** 2026-09-08  
**Active branch:** `m3-1-canonical-price-intelligence`  
**M3.1-B verified source head:** `404098d0ba7033977dfa4999f915bde2387b8fbe`  
**M3.1 verification workflow:** `M3.1 Canonical Price Intelligence` run `34242136190` — **SUCCESS**  
**M3.1 controlling reference:** `docs/M3_1_CANONICAL_PRICE_INTELLIGENCE_MIGRATION_PLAN_2026-09-08.md`

Historical lock references:

- M2 docs head before M3.1: `9e5047dec0d50a7089caa6a4f06c7902173c7d81`
- M2 verified source head: `105561fc4908db6c18c32f9fd1a81ae5570f680f`
- M2 workflow: `M2 DecisionContext` run `34233061074` — **SUCCESS**
- M3.1-A last verified committed head before M3.1-B: `bb7eb600af745d486157978b0d8daaa2b6f2df39`

---

## 1. Program rule

Trade Vision is being migrated into one causally traceable Decision Spine. Existing specialist engines may disagree, but no specialist may gain final-band or execution authority during migration.

Canonical principle:

> **Many brains may disagree internally. Only one decision may leave the brain.**

Locked semantic rules:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no_signal != unavailable
no_output != neutral
```

Locked authority rules:

```text
D1 outranks every predictor/reviewer
no incomplete bar authority
all M2+ evidence must be D2 causal
specialists cannot set final band
FINAL_CONFLUENCE_ARBITER / D6 remains sole final-band authority
zero execution authority
Jarvis presentation only when migrated
```

A locked milestone is reopened only for a reproducible defect, safety regression, causal/provenance violation, contract incompatibility, correctness defect, or requirement contradiction exposed by later integration.

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
SNAPSHOT FEATURE KERNEL
CALCULATE RAW FACTS ONCE
        |
  +-----+------+----------------+
  |            |                |
  v            v                v
CANDLE       LEVELS         INDICATORS
ANATOMY
  |
  +--> CANDLE CONDITION
  |
  +--> CHART REASONING
  |
  +--> MARKET STRUCTURE
                     |
                    MTF
                     |
                     v
           PRICE STRUCTURE EVIDENCE
                     |
                     v
           Stage2IntegrityReport
                     |
                     v
            DecisionContext
                     |
                     v
              CURRENT D6
               UNCHANGED
```

Central M3.1 rule:

```text
RAW FACT CALCULATED ONCE
        ↓
MANY SPECIALISTS MAY INTERPRET IT
        ↓
EVERY INTERPRETATION IS TRACEABLE
        ↓
NO SPECIALIST GETS FINAL AUTHORITY
```

---

## 3. Milestone truth

| Step | Milestone | State | Exit condition / next boundary |
|---|---|---|---|
| M0 | Stage-2 integrity | **GREEN / LOCKED** | truthful runtime accounting; fail-closed Stage2 gate before D6 |
| M1 | Authority Registry | **FOUNDATION GREEN / SCOPE LOCKED** | exactly one final-band authority; zero execution authority |
| M2 | Canonical DecisionContext | **GREEN / LOCKED** | deterministic D2-causal context before unchanged D6 |
| M3 | Brain migration | **IN BUILD** | migrate specialist families through canonical evidence without authority drift |
| M3.1 | Canonical Price Intelligence | **IN BUILD** | complete A-F before M3.2 |
| M3.1-A | Snapshot Feature Kernel | **GREEN / LOCKED** | immutable D2 feature substrate; calculate-once foundation |
| M3.1-B | Canonical Candle Intelligence | **GREEN / LOCKED** | Anatomy calculated once; shared into Condition + Chart; canonical receipt/context; parity/safety green |
| M3.1-C | Level Intelligence | **NEXT CURRENT SUB-MILESTONE** | session-aware VWAP/OR/PDH/PDL/CPR with D2 identity |
| M3.1-D | Indicator Intelligence | **NOT STARTED** | normalized typed indicator evidence and dependency metadata |
| M3.1-E | PIT-safe MTF | **NOT STARTED** | only completed HTF candles with independent causal identities |
| M3.1-F | Price Evidence Fusion / DAG / parity | **NOT STARTED** | composer, dependency DAG, contradiction preservation, parity/performance audit |
| M3.2+ | Later brain migration families | **NOT STARTED** | not eligible until M3.1 A-F are GREEN / LOCKED |
| M4 | D6 orchestration redesign | **NOT STARTED / D6 EXISTS** | repository-wide canonical finalizer after specialist migration |
| M5-M12 | FinalDecision through independent release gate | **NOT STARTED** | follow canonical staged plan |

Do **not** jump to M3.2. Finish M3.1 A-F first.

---

## 4. M0 / M1 / M2 locked foundation

M0, M1, and M2 remain locked. M3.1-B did not weaken their contracts.

Historical M2 verification:

```text
Workflow: M2 DecisionContext
Run:      34233061074
Result:   SUCCESS
```

M2 still provides:

- immutable canonical DecisionContext;
- Stage2 evidence integrity before context/D6;
- exact snapshot identity and receipt provenance;
- explicit unavailable/skipped evidence rather than neutral fabrication;
- deterministic context hashing;
- fail-closed contract behavior;
- sole D6 final-band authority;
- zero execution authority.

The pre-M2 implementation remains preserved in:

`apps/api/app/behavior/paper_guidance_spine_legacy.py`

for compatibility/parity reference.

---

## 5. M3.1-A — Snapshot Feature Kernel — GREEN / LOCKED

Implementation:

`apps/api/app/behavior/decision_spine/snapshot_feature_kernel.py`

M3.1-A established the immutable D2 feature substrate and calculate-once primitives used by later price specialists.

Locked facts:

- input is the verified D2 closed-candle snapshot;
- canonical identity includes D2 snapshot identity;
- closed-bar vectors are immutable;
- reusable average-range and volume-window facts are deterministic;
- no incomplete/future candle is granted authority;
- kernel carries bounded audit/provenance identity;
- no trading/final/execution authority is introduced.

Important mathematical preservation:

`candle-anatomy.v0.15` field `range_atr` historically uses a rolling arithmetic **mean candle range**, not Wilder true-range ATR. M3.1 preserves this existing behavior explicitly through the kernel's `average_range` feature.

Any future true-ATR correction must be explicit, versioned, tested, parity-audited and impact-reviewed. It must never be hidden inside orchestration optimization.

---

## 6. M3.1-B — Canonical Candle Intelligence — GREEN / LOCKED

### 6.1 Problem removed

Before M3.1-B, the normal Paper Guidance route could calculate Candle Anatomy independently inside both Candle Condition and Chart Reasoning.

M3.1-B now uses:

```text
D2 CLOSED-CANDLE SNAPSHOT
        |
        v
SNAPSHOT FEATURE KERNEL          build_count = 1
        |
        v
CANDLE_ANATOMY                   compute_count = 1
        |
        v
one CandleAnatomyResult
        |
        v
CANDLE_ANATOMY receipt
        |
   +----+-------------------+
   |                        |
   v                        v
CANDLE_CONDITION       CHART_REASONING
same anatomy facts     same anatomy facts
```

The canonical route does not permit Condition or Chart to independently recompute Anatomy.

Standalone compatibility remains: direct specialist callers may still construct Anatomy automatically where the historical public API requires it.

### 6.2 Canonical Candle Anatomy receipt

A real `CANDLE_ANATOMY` receipt now enters Stage2.

Successful canonical identity:

```text
engine_id             = CANDLE_ANATOMY
engine_version        = candle-anatomy.v0.15
source_snapshot_hash  = D2 snapshot hash
output_hash           = deterministic receipt output hash
identity_match        = true
used_for_probability  = false
final authority       = false
execution authority   = false
```

Dependent receipt summaries carry the exact Anatomy receipt hash as:

```text
upstream_candle_anatomy_hash
```

for both `CANDLE_CONDITION` and `CHART_REASONING`.

Full DAG validation remains owned by M3.1-F; M3.1-B introduces the smallest deterministic compatible upstream identity needed for this dependency.

### 6.3 DecisionContext.candle_anatomy activated

`DecisionContext.candle_anatomy` is no longer the M2 explicit-unavailable placeholder on the normal successful M3.1 route.

It is receipt-backed canonical evidence with:

```text
source_engine       = CANDLE_ANATOMY
source_snapshot_hash= D2 snapshot hash
source_output_hash  = CANDLE_ANATOMY receipt output_hash
status              = AVAILABLE on successful computation
used_for_probability= false
claims_trade_authority = false
```

The payload is deliberately bounded. It contains only compact facts such as:

- latest candle direction/body/wicks/close location/range ratio/volume z/follow-through/structure types;
- recent-window bullish/bearish/doji/rejection/compression/expansion/inside/outside counts;
- source bar count and calculation version;
- explicit missing-volume count;
- feature-kernel and snapshot provenance;
- calculation audit counters.

It does **not** place full candle history, DataFrames, large arrays, or 400-bar payloads into DecisionContext.

### 6.4 Calculate-once proof

Canonical audit/tests prove:

```text
feature_kernel_build_count   == 1
candle_anatomy_compute_count == 1
decision_context_build_count == 1
```

Tests also monkeypatch the specialist-local Anatomy builders to raise if Chart or Condition attempts a second Anatomy calculation while a canonical result is supplied.

### 6.5 Failure semantics

M3.1-B explicitly prevents specialist failures from becoming neutral D6 inputs.

Current `PaperGuidanceEngineReceipt` compatibility contract supports `completed / degraded / skipped`; it does not yet expose an `error` receipt literal. Therefore a calculator exception is represented truthfully as degraded receipt evidence with the explicit exception warning, and the M3.1 candle dependency guard blocks canonical context/D6 when any of these required candle-chain specialists did not complete:

```text
CANDLE_ANATOMY
CANDLE_CONDITION
CHART_REASONING
```

Failure result:

```text
WAIT
DO_NOTHING
no D6 arbitration
no neutral substitution
```

This preserves:

```text
error != zero
error != neutral
unavailable != safe
```

without broad receipt-schema churn during the B migration. Any later receipt-status expansion must be separately versioned and tested.

### 6.6 Edge and metamorphic coverage

Targeted M3.1-B tests cover:

- deterministic replay: same D2 -> same Anatomy hash;
- legitimate changed closed candle -> changed Anatomy evidence/hash when relevant;
- calculate once;
- same Anatomy dependency for Condition and Chart;
- canonical receipt identity;
- bounded DecisionContext evidence;
- missing volume remains explicit;
- zero-range candle safety;
- doji correctness;
- trend candle;
- rejection candle;
- inside bar;
- outside bar;
- expansion;
- compression;
- failed follow-through;
- Anatomy failure injection;
- Condition failure injection;
- Chart failure injection;
- no error-to-neutral conversion;
- no D6 authority drift;
- no execution authority;
- bounded fixture latency regression check.

### 6.7 D6 parity preserved

M3.1 is specialist migration, not D6 redesign. The current D6 placeholders remain unchanged:

```python
relative_strength_score = 0.5
indicator_signal_score  = 0.0
external_ai_score       = 0.0
weak_sector             = False
```

The migration adds a new canonical Anatomy receipt/provenance, so the overall guidance receipt list/hash is expected to change. The locked parity requirement is semantic D6 input/output behavior, and the integration suite verifies the final arbiter behavior remains equivalent to the preserved legacy route where applicable.

No test was weakened to permit a trading/safety regression. One old v1.88 fixed-engine-order assertion was updated because the new required `CANDLE_ANATOMY` receipt legitimately adds one engine to the canonical order.

### 6.8 Final M3.1-B verification

Verified source head:

`404098d0ba7033977dfa4999f915bde2387b8fbe`

Workflow:

`M3.1 Canonical Price Intelligence`

Run:

`34242136190`

Result:

**SUCCESS**

```text
Compile M3.1 + locked Decision Spine modules          PASS
M3.1-A Snapshot Feature Kernel                        15 passed in 0.98s
M3.1-B Canonical Candle Pipeline                      13 passed in 1.09s
Locked M2 DecisionContext                             34 passed in 0.88s
Locked M2 Paper Guidance integration / D6 parity      10 passed in 1.12s
Locked M0 Stage2 integrity                            15 passed in 0.81s
Paper Guidance v1.88 regression                       29 passed in 4.22s
Full API regression                                   556 passed in 67.00s
Authority registry / sole-D6 / zero-execution         PASS
```

Known warnings were dependency/deprecation/vendor warnings already surfaced by the suite; there were no test failures.

Performance evidence at this milestone is deliberately modest:

- the dedicated M3.1-B suite completes in about one second on hosted CI;
- a canonical fixture has a loose `<500 ms` anti-pathology regression ceiling;
- this is not a production latency SLO and is not evidence of trading edge.

### 6.9 M3.1-B lock decision

All required B gates passed:

```text
implementation            GREEN
calculate-once proof       GREEN
causal/upstream identity   GREEN
fault injection            GREEN
replay/metamorphic         GREEN
M2 semantic D6 parity      GREEN
M0/M2 locked regressions   GREEN
full API regression        GREEN
authority/safety audit     GREEN
bounded performance gate   GREEN
documentation              GREEN
```

M3.1-B is therefore:

> **GREEN / LOCKED**

Do not reopen it unless the formal reopen rule is met.

---

## 7. Next eligible build — M3.1-C Level Intelligence

M3.1-C is the next current sub-milestone. It has **not** been started by the M3.1-B lock work.

Required boundary includes:

```text
session-aware VWAP
timeframe-aware opening range
explicit session identity
OR5 / OR15 / OR30 semantics
no bars[:3] assumption
PDH / PDL
CPR
missing != zero
D2 causal identity
```

M3.1-C must repeat the same discipline:

```text
READ
UNDERSTAND
DESIGN
IMPLEMENT
TEST
ADVERSARIAL TEST
REPLAY/PARITY
FULL REGRESSION
AUTHORITY AUDIT
PERFORMANCE AUDIT
COMMIT
GREEN / LOCK
```

Do not start M3.1-D until C is locked. Do not start M3.2 until all M3.1 A-F gates are locked.

---

## 8. Complete M3.1 order

```text
M3.1-A  Snapshot Feature Kernel                  GREEN / LOCKED
   ↓
M3.1-B  Canonical Candle Intelligence            GREEN / LOCKED
   ↓
M3.1-C  Session-aware Level Intelligence         NEXT / NOT STARTED
   ↓
M3.1-D  Normalized Indicator Intelligence        NOT STARTED
   ↓
M3.1-E  PIT-safe MTF                             NOT STARTED
   ↓
M3.1-F  Price Evidence Fusion / DAG / parity     NOT STARTED
   ↓
FULL REGRESSION
AUTHORITY AUDIT
PERFORMANCE AUDIT
   ↓
M3.1 GREEN / LOCKED
```

---

## 9. Safety and trading-proof boundary

Every current route remains research-only:

```text
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human approval remains required for any later paper workflow
```

A green software milestone does not prove a market edge.

```text
unit tests green != trading edge proven
merge success != edge proof
ORB confirmation != proof authority
AFRE confirmation != proof authority
```

Production-ready trading intelligence additionally requires historical validation, walk-forward validation, regime/failure testing, realistic cost/slippage assumptions, paper observations, edge-decay monitoring and explicit promotion gates in later milestones M9/M10.
