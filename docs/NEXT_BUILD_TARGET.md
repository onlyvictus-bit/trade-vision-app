# Next Build Target

Last reviewed: 2026-09-08

> **Canonical status source:** `docs/CANONICAL_BUILD_STATUS.md`
>
> Do not advance milestone state in this file independently. Every coding/audit session starts from the canonical status document and the controlling M3.1 plan.

## Current truth

```text
M0      Stage-2 integrity                    GREEN / LOCKED
M1      Authority Registry                   FOUNDATION GREEN / SCOPE LOCKED
M2      Canonical DecisionContext            GREEN / LOCKED
M3      Brain migration                      IN BUILD
M3.1    Canonical Price Intelligence         IN BUILD
M3.1-A  Snapshot Feature Kernel              GREEN / LOCKED
M3.1-B  Canonical Candle Intelligence        GREEN / LOCKED
M3.1-C  Canonical Level Intelligence         GREEN / LOCKED
M3.1-D  Canonical Indicator Intelligence     NEXT CURRENT SUB-MILESTONE
M3.1-E  PIT-safe MTF                         NOT STARTED
M3.1-F  Price Evidence Fusion / DAG / parity NOT STARTED
M3.2+                                         NOT STARTED
```

## M3.1-C lock evidence

Verified source head before documentation consolidation:

`98428df2fa20b9e2079f222a6ea7563b02fa17c1`

Verification workflow:

`M3.1 Canonical Price Intelligence`

Run:

`34246032835` — **SUCCESS**

```text
M3.1-A Snapshot Feature Kernel                    15 passed
M3.1-B Canonical Candle Pipeline                  13 passed
M3.1-C Canonical Level Intelligence               15 passed
Locked M2 DecisionContext                         34 passed
Locked M2 Paper Guidance integration / parity     10 passed
Locked M0 Stage2 integrity                        15 passed
Paper Guidance v1.88 regression                   29 passed
Full API regression                               556 passed
Authority / sole-D6 / zero-execution               PASS
```

M3.1-C guarantees now locked:

```text
same D2 SnapshotFeatureKernel object reused
canonical level calculation exactly once
explicit Asia/Kolkata regular-session identity
session VWAP does not leak prior-session bars
VWAP ±1/±2/±3 weighted-deviation bands
OR5 / OR15 / OR30 use explicit time windows
no canonical bars[:3] opening-range assumption
incomplete OR = PENDING/UNAVAILABLE, not partial authority
complete prior observed session -> PDH / PDL / previous close
CPR derived from complete prior observed session
missing volume != zero
incomplete prior session != fabricated levels
LEVEL_CONTEXT receipt is bounded and D2-causal
DecisionContext.levels source_output_hash == LEVEL_CONTEXT receipt output hash
actual level-engine error blocks before D6
legacy level semantics isolated as compatibility projection only
D6 semantic behavior remains unchanged
no specialist gains final-band authority
zero execution authority
```

Current session semantics are explicitly versioned as observed-bar NSE cash regular-hours semantics (`Asia/Kolkata`, 09:15-15:30). They do **not** claim official exchange holiday/special-session/half-day calendar authority. Verified calendar/provider provenance remains future provider hardening; incomplete observed windows fail closed.

---

# NEXT — M3.1-D: Canonical Normalized Indicator Intelligence

M3.1-D is now the next eligible sub-milestone. It has **NOT** been started by the M3.1-C lock work.

Controlling reference:

`docs/M3_1_CANONICAL_PRICE_INTELLIGENCE_MIGRATION_PLAN_2026-09-08.md`

Do not start M3.1-E, M3.2, ORB redesign, derivatives migration, or D6 redesign before M3.1-D is independently GREEN / LOCKED.

## Required M3.1-D target

Migrate indicator evidence into one normalized deterministic canonical layer without creating another decision brain.

Target shape:

```text
D2 CLOSED-CANDLE SNAPSHOT
        |
        v
SNAPSHOT FEATURE KERNEL
        |
        v
EXISTING VERIFIED INDICATOR RUNTIME(S)
        |
        v
CANONICAL INDICATOR NORMALIZATION
        |
        +--> typed indicator identity
        +--> family metadata
        +--> dependency metadata
        +--> correlation/redundancy metadata
        +--> normalized signal/value state
        +--> explicit missing / unavailable / error state
        +--> source snapshot/hash provenance
        |
        v
bounded INDICATOR receipt / canonical evidence
        |
        v
Stage2IntegrityReport
        |
        v
DecisionContext.indicators
        |
        v
CURRENT D6 COMPATIBILITY
UNCHANGED UNTIL AUTHORIZED MIGRATION
```

## Non-negotiable M3.1-D requirements

1. **Normalize once** — do not recompute the same indicator merely for another specialist.
2. **D2 causality** — active indicator evidence must bind to the approved D2 identity.
3. **Typed states** — distinguish AVAILABLE, DEGRADED, UNAVAILABLE and ERROR truthfully within the compatible contract.
4. **Missing != zero** — absent/error indicator values must never become a fabricated neutral numeric signal.
5. **Family metadata** — trend, momentum, volatility, volume, structure/pattern or another verified family must be explicit rather than inferred downstream.
6. **Dependency metadata** — inputs/prerequisites and unavailable dependency reasons must be traceable.
7. **Correlation/redundancy metadata** — highly related indicators must not masquerade as independent evidence merely because they have different names.
8. **No arbitrary AI/ML** — M3.1-D remains deterministic sensory normalization, not a new predictor.
9. **Bounded DecisionContext** — no full indicator arrays/history/DataFrames in canonical context.
10. **No future candle authority** — indicator calculations may use only approved closed bars.
11. **No authority drift** — indicators cannot set final band, paper authority or execution authority.
12. **D6 parity** — do not silently replace the locked `indicator_signal_score = 0.0` placeholder until the appropriate migration gate explicitly authorizes that D6 change.
13. **Fault injection** — runtime/dependency/calculator failures must remain explicit and cannot turn into neutral scores.
14. **Replay/metamorphic proof** — same D2 and same runtime facts must reproduce the same canonical evidence/hash; legitimate changed closed-bar inputs must affect only causally dependent evidence.
15. **Performance proof** — calculate/normalize/map/hash once and keep bounded anti-pathology latency tests.

## Required verification discipline

```text
READ
 ↓
UNDERSTAND every active indicator path and current runtime contract
 ↓
DESIGN smallest compatibility-safe canonical normalization layer
 ↓
IMPLEMENT
 ↓
TARGETED TESTS
 ↓
ADVERSARIAL / DEPENDENCY / MISSINGNESS TESTS
 ↓
REPLAY / METAMORPHIC / D6 PARITY
 ↓
LOCKED M0/M2/M3.1-A/B/C REGRESSIONS
 ↓
FULL API REGRESSION
 ↓
AUTHORITY / SAFETY AUDIT
 ↓
PERFORMANCE AUDIT
 ↓
DOCUMENT
 ↓
GREEN / LOCK
```

Do not claim M3.1-D GREEN until every gate has evidence.

## Safety boundary remains unchanged

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
```

Software verification remains separate from market-edge proof. Historical/walk-forward validation, realistic costs/slippage, controlled paper observations and promotion gates remain later M9/M10 work.
