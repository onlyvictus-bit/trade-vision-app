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
M3.1-C  Level Intelligence                   NEXT CURRENT SUB-MILESTONE
M3.1-D  Indicators                           NOT STARTED
M3.1-E  MTF                                  NOT STARTED
M3.1-F  Price Evidence Fusion / DAG / parity NOT STARTED
M3.2+                                         NOT STARTED
```

## M3.1-B lock evidence

Verified source head:

`404098d0ba7033977dfa4999f915bde2387b8fbe`

Verification workflow:

`M3.1 Canonical Price Intelligence`

Run:

`34242136190` — **SUCCESS**

```text
M3.1-A Snapshot Feature Kernel                    15 passed
M3.1-B Canonical Candle Pipeline                  13 passed
Locked M2 DecisionContext                         34 passed
Locked M2 Paper Guidance integration / parity     10 passed
Locked M0 Stage2 integrity                        15 passed
Paper Guidance v1.88 regression                   29 passed
Full API regression                               556 passed
Authority / sole-D6 / zero-execution               PASS
```

M3.1-B guarantees now locked:

```text
feature kernel built exactly once
Candle Anatomy calculated exactly once
same Anatomy facts feed Candle Condition
same Anatomy facts feed Chart Reasoning
CANDLE_ANATOMY receipt is D2-causal
DecisionContext.candle_anatomy is bounded receipt-backed evidence
Condition + Chart carry Anatomy upstream receipt hash
required candle-chain failures stop before D6
error does not become a neutral D6 score
D6 semantic behavior remains unchanged
no specialist gains final-band authority
zero execution authority
```

The historical `range_atr` behavior of `candle-anatomy.v0.15` remains unchanged: it uses rolling arithmetic mean candle range, not a silently substituted Wilder ATR.

---

# NEXT — M3.1-C: Session-aware Level Intelligence

Do not start M3.1-D, M3.2, ORB redesign, derivatives migration, or D6 redesign before M3.1-C is independently GREEN / LOCKED.

Controlling reference:

`docs/M3_1_CANONICAL_PRICE_INTELLIGENCE_MIGRATION_PLAN_2026-09-08.md`

## Required M3.1-C target

Build one D2-causal canonical level-intelligence path that removes hidden session assumptions while preserving legacy decision behavior until parity is proven.

Required semantics include:

```text
D2 CLOSED-CANDLE SNAPSHOT
        |
        v
SNAPSHOT FEATURE KERNEL / SESSION IDENTITY
        |
        v
LEVEL INTELLIGENCE
        |
        +--> SESSION-AWARE VWAP
        +--> OR5
        +--> OR15
        +--> OR30
        +--> PDH
        +--> PDL
        +--> CPR
        |
        v
LEVEL_CONTEXT receipt / bounded canonical evidence
        |
        v
Stage2IntegrityReport
        |
        v
DecisionContext
        |
        v
CURRENT D6 UNCHANGED
```

## Non-negotiable M3.1-C requirements

1. **Explicit session identity** — no implicit slicing that can mix sessions.
2. **Session-aware VWAP** — never accumulate across an unintended previous session.
3. **Timeframe-aware opening range** — OR5 / OR15 / OR30 must have explicit semantics.
4. **No `bars[:3]` assumption** — opening range must be selected by time/session semantics, not an incidental bar count.
5. **PDH / PDL** — previous-day identity must be PIT-safe and explicit.
6. **CPR** — previous-session source and missingness must be explicit.
7. **Missing != zero** — an unavailable level cannot be fabricated as `0.0` or a safe neutral state.
8. **D2 causal identity** — every active level result/receipt must bind to the same approved snapshot identity or a separately explicit PIT-safe prior-session identity where required.
9. **No future candle authority** — incomplete/current-future bars never enter authoritative level construction.
10. **No authority drift** — level specialists cannot set final band or execute.
11. **D6 parity** — migration plumbing must not silently change current final-arbiter semantics.
12. **Bounded context** — no large history/DataFrames/arrays inside DecisionContext.

## Required M3.1-C verification discipline

```text
READ
 ↓
UNDERSTAND current level/session math
 ↓
DESIGN smallest compatibility-safe patch
 ↓
IMPLEMENT
 ↓
TARGETED TESTS
 ↓
ADVERSARIAL / SESSION-BOUNDARY TESTS
 ↓
REPLAY / PARITY
 ↓
LOCKED M0/M2 REGRESSIONS
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

Do not claim M3.1-C GREEN until every gate has evidence.

## Safety boundary remains unchanged

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
```

Software verification is not trading-edge proof. Historical/walk-forward validation, cost/slippage realism, paper observations and promotion gates remain later M9/M10 work.
