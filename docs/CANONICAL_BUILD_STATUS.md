# Trade Vision — Canonical Build Status

> **Purpose:** durable repository source of truth for controlled completion of Trade Vision.
>
> **Rule:** one milestone -> implement -> test -> audit -> commit -> GREEN -> lock. Do not infer milestone state from old chats, percentages, or subsystem-local tests.

**Last audited:** 2026-09-08  
**Active branch:** `m3-1-canonical-price-intelligence`  
**M3.1-C verified source head before documentation consolidation:** `98428df2fa20b9e2079f222a6ea7563b02fa17c1`  
**M3.1-C verification workflow:** `M3.1 Canonical Price Intelligence` run `34246032835` — **SUCCESS**  
**M3.1 controlling reference:** `docs/M3_1_CANONICAL_PRICE_INTELLIGENCE_MIGRATION_PLAN_2026-09-08.md`

Historical lock references:

- M2 docs head before M3.1: `9e5047dec0d50a7089caa6a4f06c7902173c7d81`
- M2 verified source head: `105561fc4908db6c18c32f9fd1a81ae5570f680f`
- M2 workflow: `M2 DecisionContext` run `34233061074` — **SUCCESS**
- M3.1-A last verified committed head before M3.1-B: `bb7eb600af745d486157978b0d8daaa2b6f2df39`
- M3.1-B lock commit: `a3223327df0c2e49456440c7f99ac2c3565bbf13`
- M3.1-B final lock workflow: `M3.1 Canonical Price Intelligence` run `34242730545` — **SUCCESS**

---

## 1. Program rules

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

Locked safety boundary:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
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
| M3.1-B | Canonical Candle Intelligence | **GREEN / LOCKED** | Anatomy once; Condition + Chart consume same facts; canonical receipt/context; D6 parity |
| M3.1-C | Canonical Level Intelligence | **GREEN / LOCKED** | session-aware VWAP/OR/PDH/PDL/CPR; explicit missingness; D2 provenance; D6 parity |
| M3.1-D | Canonical Indicator Intelligence | **NEXT CURRENT SUB-MILESTONE** | normalized typed indicator evidence; dependency/family/correlation metadata; explicit missing/error states |
| M3.1-E | PIT-safe MTF | **NOT STARTED** | only completed HTF candles with independent causal identities |
| M3.1-F | Price Evidence Fusion / DAG / parity | **NOT STARTED** | composer, dependency DAG, contradiction preservation, parity/performance audit |
| M3.2+ | Later brain migration families | **NOT STARTED** | not eligible until M3.1 A-F are GREEN / LOCKED |
| M4 | D6 orchestration redesign | **NOT STARTED / D6 EXISTS** | repository-wide canonical finalizer after specialist migration |
| M5-M12 | FinalDecision through independent release gate | **NOT STARTED** | follow canonical staged plan |

Do **not** jump to M3.2. Finish M3.1 A-F first.

---

## 4. Locked foundation retained

M0, M1 and M2 remain locked. M3.1-A/B/C did not weaken their contracts.

Historical M2 verification:

```text
Workflow: M2 DecisionContext
Run:      34233061074
Result:   SUCCESS
```

M2 still guarantees:

- immutable canonical DecisionContext;
- Stage2 evidence integrity before context/D6;
- exact snapshot identity and receipt provenance;
- explicit unavailable/skipped evidence instead of neutral fabrication;
- deterministic context hashing;
- fail-closed contract behavior;
- sole D6 final-band authority;
- zero execution authority.

The byte-preserved pre-M2 implementation remains in:

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

Any future true-ATR correction must be explicit, versioned, tested, parity-audited and impact-reviewed. It must never be hidden inside an orchestration refactor.

---

## 6. M3.1-B — Canonical Candle Intelligence — GREEN / LOCKED

M3.1-B removed duplicate Candle Anatomy computation from the normal Paper Guidance route.

```text
D2
 ↓
SNAPSHOT FEATURE KERNEL       build_count = 1
 ↓
CANDLE_ANATOMY                compute_count = 1
 ↓
one CandleAnatomyResult
 ↓
CANDLE_ANATOMY receipt
 ├─> CANDLE_CONDITION
 └─> CHART_REASONING
```

Locked B guarantees:

- Condition and Chart consume the same already-computed Anatomy facts;
- successful `CANDLE_ANATOMY` receipt binds to the D2 snapshot and deterministic output hash;
- Condition and Chart summaries carry the Anatomy upstream receipt hash;
- `DecisionContext.candle_anatomy` is bounded receipt-backed evidence;
- full candle history/DataFrames/large arrays are not copied into DecisionContext;
- `feature_kernel_build_count == 1`;
- `candle_anatomy_compute_count == 1`;
- `decision_context_build_count == 1`;
- Anatomy/Condition/Chart failure injection stops before D6;
- error does not become a neutral score;
- standalone legacy compatibility remains where existing public callers require it;
- D6 semantic behavior remains unchanged;
- no specialist gains final or execution authority.

M3.1-B final lock commit:

`a3223327df0c2e49456440c7f99ac2c3565bbf13`

Final lock workflow:

`M3.1 Canonical Price Intelligence` run `34242730545` — **SUCCESS**

---

## 7. M3.1-C — Canonical Level Intelligence — GREEN / LOCKED

### 7.1 Migration strategy

M3.1-C did **not** delete or broadly rewrite `behavior/context_engines.py`. That file also contains unrelated context/HTF/gap behavior and a giant rewrite would create unnecessary regression risk.

A dedicated production module now owns canonical session/level truth:

`apps/api/app/behavior/decision_spine/canonical_level_intelligence.py`

Stable Decision Spine exports are provided through:

`apps/api/app/behavior/decision_spine/__init__.py`

Architecture:

```text
D2 CLOSED-CANDLE SNAPSHOT
        |
        v
SNAPSHOT FEATURE KERNEL
same object already built for M3.1-A/B
        |
        v
CANONICAL LEVEL INTELLIGENCE
        |
        +--> explicit regular-session identity
        +--> session-aware VWAP
        |      +1σ / -1σ
        |      +2σ / -2σ
        |      +3σ / -3σ
        +--> OR5
        +--> OR15
        +--> OR30
        +--> previous observed complete-session PDH
        +--> previous observed complete-session PDL
        +--> previous observed complete-session close
        +--> CPR
        +--> explicit missing / pending states
        |
        v
bounded LEVEL_CONTEXT receipt
        |
        v
Stage2IntegrityReport
        |
        v
DecisionContext.levels
        |
        v
CURRENT D6 COMPATIBILITY PROJECTION
UNCHANGED
```

### 7.2 Explicit session identity

Canonical level calculation uses versioned session semantics:

```text
SESSION_SEMANTICS_VERSION = nse-cash-regular-session.v1
timezone                  = Asia/Kolkata
regular open              = 09:15
regular close             = 15:30
```

The result records a typed immutable `SessionIdentity` including:

- session id/date;
- timezone;
- local open/close semantics;
- open/close timestamps;
- first/last observed current-session bar;
- source bar count;
- whether the bounded history starts at the explicit session open;
- whether bars are contiguous from session open.

Canonical VWAP is withheld when the current observed session does not start at 09:15 or contains timestamp gaps. Partial data is not silently treated as a complete session.

### 7.3 Session-aware VWAP

Canonical VWAP no longer consumes every supplied bar across previous sessions.

It reuses the exact already-built `SnapshotFeatureKernel` and its anchored VWAP primitive for the current explicit regular-session slice.

Rules:

```text
current session starts at 09:15         required
session bars contiguous                 required
all authoritative VWAP volumes present required
zero denominator                        unavailable
missing volume                          unavailable, not zero
```

The canonical result also records weighted standard deviation and deterministic ±1/±2/±3 bands.

A test deliberately gives the previous session much larger volume and very different prices, proving canonical VWAP resets to the current session instead of leaking prior-session volume into the result.

### 7.4 OR5 / OR15 / OR30 semantics

The pre-canonical engine used the global first three supplied bars. M3.1-C removes that assumption from canonical evidence.

Opening ranges are now defined by explicit session time windows from 09:15:

```text
OR5   = closed bars tiling [09:15, 09:20)
OR15  = closed bars tiling [09:15, 09:30)
OR30  = closed bars tiling [09:15, 09:45)
```

Rules:

- the source timeframe must exactly tile the requested OR window;
- OR is `PENDING` until its complete window has closed;
- missing expected bars make that OR `UNAVAILABLE`;
- partial opening ranges have no authority;
- no future/incomplete candle may enter the feature kernel or level result.

Timeframe-aware tests prove the implementation is not hardcoded to three bars. For example, with 15-minute source bars:

```text
OR5   = UNAVAILABLE (15m cannot exactly represent 5m)
OR15  = 1 source bar
OR30  = 2 source bars
```

### 7.5 PIT-safe previous-session PDH / PDL / CPR

Canonical previous-session levels are derived from the nearest earlier **observed complete regular session** present in the D2 snapshot.

The previous session must exactly cover its regular-hours timeline for the source timeframe with no gaps. Otherwise:

```text
previous_session.status = UNAVAILABLE
PDH                      = unavailable
PDL                      = unavailable
previous close           = unavailable
CPR                      = unavailable
PDH/PDL states           = unknown
```

When complete, the previous session carries a deterministic source hash. CPR carries that same source-session identity/hash.

CPR remains the existing correct arithmetic:

```text
pivot = (PDH + PDL + previous_close) / 3
BC    = (PDH + PDL) / 2
TC    = pivot + (pivot - BC)
```

with the lower/upper ordering normalized deterministically.

### 7.6 Explicit missingness and truthful degradation

Canonical Level Intelligence distinguishes usable facts from missing or pending facts.

Examples:

- missing volume -> canonical session VWAP `UNAVAILABLE`, value `None`;
- incomplete previous session -> PDH/PDL/CPR `UNAVAILABLE`;
- not-yet-closed OR window -> `PENDING`;
- source timeframe cannot tile an OR -> `UNAVAILABLE`;
- timestamp gap -> affected canonical level withheld;
- actual engine exception -> no canonical completion marker and context construction blocks before D6.

This preserves:

```text
missing != zero
unknown != false
unavailable != neutral
pending != available
error != neutral
```

A `LEVEL_CONTEXT` receipt may therefore be `degraded` when the canonical engine ran correctly but some bounded source facts are unavailable. That truthful degradation does **not** mean the engine crashed.

A real level-engine exception is different: it lacks the canonical completion marker, and the M3.1 dependency guard stops before D6 with `WAIT / DO_NOTHING` rather than letting an error become a neutral D6 input.

### 7.7 Provenance and calculate-once behavior

Canonical Level Intelligence records:

```text
calculation_version          = canonical-level-intelligence.v1
source_snapshot_hash         = exact D2 snapshot hash
source_feature_kernel_hash   = exact shared kernel feature hash
source_feature_kernel_version
canonical_level_hash         = deterministic canonical level facts hash
```

The Paper Guidance route reuses the exact feature-kernel object already built in M3.1-A/B. Request-local binding uses `ContextVar` and is cleared in `finally`, avoiding shared mutable per-request state.

Targeted tests prove:

```text
feature_kernel build count       == 1
canonical level compute count    == 1
feature_kernel_reused            == true
session partition pass count     == 1
canonical VWAP compute count     == 1
opening-range compute count      == 3
previous-session compute count   == 1
```

The `LEVEL_CONTEXT` receipt is minted only **after** the final canonical summary/status/warnings are known. Its `output_hash` therefore fingerprints the exact final bounded payload that DecisionContext receives; no post-hash summary mutation is permitted.

### 7.8 DecisionContext.levels activated as richer canonical evidence

`DecisionContext.levels` remains compact and receipt-backed:

```text
source_engine        = LEVEL_CONTEXT
source_snapshot_hash = D2 snapshot hash
source_output_hash   = LEVEL_CONTEXT receipt output hash
used_for_probability = false
claims_trade_authority = false
```

The bounded payload contains only canonical level/session facts, quality, provenance, calculation audit and explicit compatibility metadata. It does **not** embed full candle histories, DataFrames or large arrays.

### 7.9 D6 parity and compatibility isolation

M3.1-C is sensory migration, not D6 redesign.

The old `analyze_level_context()` behavior is preserved as an explicitly isolated compatibility projection for current D6 inputs:

```text
legacy all-supplied-bar VWAP
legacy first-three-supplied-bars OR
legacy optional numeric PDH/PDL/CPR inputs
legacy flags / level respect score
```

Those legacy semantics are **not** presented as canonical level truth. They are compatibility debt retained only so current D6 semantics remain unchanged until the authorized D6 migration milestone.

Integration tests compare the migrated Paper Guidance route with the byte-preserved legacy route and keep final D6 behavior equivalent where applicable.

The existing D6 placeholders remain unchanged:

```python
relative_strength_score = 0.5
indicator_signal_score  = 0.0
external_ai_score       = 0.0
weak_sector             = False
```

### 7.10 Adversarial / replay / performance coverage

Dedicated M3.1-C tests cover:

1. session VWAP reset at 09:15;
2. OR5/OR15/OR30 explicit time windows;
3. PIT-derived complete previous-session PDH/PDL/close/CPR;
4. missing-volume explicit unavailability;
5. incomplete previous session withholding PDH/PDL/CPR;
6. OR pending until complete window closure;
7. future/incomplete bar rejection;
8. deterministic replay and changed-closed-candle metamorphic hash behavior;
9. exact legacy compatibility projection parity;
10. shared-kernel reuse and calculate-once proof;
11. bounded receipt-backed `DecisionContext.levels` evidence;
12. level-engine failure injection blocking before D6;
13. deterministic receipt/provenance identity;
14. timeframe-aware OR behavior that proves no three-bar assumption;
15. bounded performance and zero authority.

Performance guard:

- 50 canonical level builds on a representative bounded fixture must complete under a deliberately loose 2-second anti-pathology ceiling;
- bounded receipt summary must remain under 20 KB in the fixture;
- this is a regression guard, not a production latency SLO and not trading-edge evidence.

### 7.11 Important bounded session-calendar limitation

M3.1-C does **not** fabricate an official exchange trading calendar.

Current session identity is deliberately versioned as observed-bar NSE cash regular-hours semantics (`Asia/Kolkata`, 09:15-15:30). It proves local session separation, regular-hours tiling, completeness and PIT causality from the bars present in D2.

It does **not** yet prove from an official exchange calendar that a given civil date is a trading day, holiday, special session, or shortened/exception session. Official exchange-calendar/provider identity, holiday/special-session provenance and freshness belong to the verified-provider hardening path (M8 or an earlier explicitly versioned provider milestone if required).

Until then the implementation fails closed on incomplete observed windows and must not claim official-calendar authority.

### 7.12 Final M3.1-C verification

Verified code head before documentation consolidation:

`98428df2fa20b9e2079f222a6ea7563b02fa17c1`

Workflow:

`M3.1 Canonical Price Intelligence`

Run:

`34246032835`

Result:

**SUCCESS**

```text
Compile M3.1 + locked Decision Spine modules          PASS
M3.1-A Snapshot Feature Kernel                        15 passed
M3.1-B Canonical Candle Pipeline                      13 passed
M3.1-C Canonical Level Intelligence                   15 passed
Locked M2 DecisionContext                             34 passed
Locked M2 Paper Guidance integration / D6 parity      10 passed
Locked M0 Stage2 integrity                            15 passed
Paper Guidance v1.88 regression                       29 passed
Full API regression                                   556 passed
Authority registry / sole-D6 / zero-execution         PASS
```

Known dependency/deprecation/vendor warnings remain surfaced by the regression suite; they did not cause test failures.

### 7.13 M3.1-C lock decision

All required C gates passed:

```text
implementation                       GREEN
explicit session identity            GREEN
session-aware VWAP                   GREEN
OR5 / OR15 / OR30                    GREEN
PDH / PDL / CPR PIT derivation       GREEN
explicit missing/pending states      GREEN
calculate-once / shared kernel       GREEN
causal hashes / receipt identity     GREEN
fault injection                      GREEN
replay / metamorphic                 GREEN
legacy D6 semantic parity            GREEN
M0/M2 locked regressions              GREEN
full API regression                   GREEN
authority / safety audit              GREEN
bounded performance gate              GREEN
documentation                         GREEN
```

M3.1-C is therefore:

> **GREEN / LOCKED**

Do not reopen it unless the formal reopen rule is met.

---

## 8. Next eligible build — M3.1-D Canonical Indicator Intelligence

M3.1-D is the next eligible sub-milestone. It is **NOT STARTED** by the M3.1-C lock work.

Required boundary from the controlling M3.1 plan includes:

```text
canonical normalized indicator evidence
typed AVAILABLE / DEGRADED / UNAVAILABLE / ERROR semantics
indicator family metadata
dependency metadata
correlation / redundancy metadata
explicit missingness and no-error-to-zero behavior
D2 causal identity
calculate once / normalize once / map once / hash once
bounded DecisionContext evidence
D6 parity until its authorized migration point
zero specialist final/execution authority
```

Do not start M3.1-E until D is independently GREEN / LOCKED.

---

## 9. Complete M3.1 order

```text
M3.1-A  Snapshot Feature Kernel                  GREEN / LOCKED
   ↓
M3.1-B  Canonical Candle Intelligence            GREEN / LOCKED
   ↓
M3.1-C  Session-aware Level Intelligence         GREEN / LOCKED
   ↓
M3.1-D  Normalized Indicator Intelligence        NEXT / NOT STARTED
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

Do not start M3.2 until A-F are all GREEN / LOCKED.

---

## 10. Production-ready software != proven trading edge

A green M3.1-C proves software contracts, causal behavior, replayability, compatibility and safety invariants for this migration stage. It does **not** prove a profitable market edge.

```text
unit tests green != trading edge proven
merge success != edge proof
ORB confirmation != proof authority
AFRE confirmation != proof authority
```

Trading-intelligence promotion still requires later historical validation, walk-forward validation, regime/failure testing, realistic costs/slippage, controlled paper observations, edge-decay monitoring and explicit promotion gates.
