# Trade Vision — Canonical Build Status

> Durable source of truth. Repository code + tests + exact-head CI are temporary truth when documentation lags.
>
> Program law: implement -> targeted/adversarial/replay tests -> locked regressions -> full tree -> authority audit -> exact-head CI -> GREEN -> lock.

**Last audited:** 2026-09-09  
**Active branch:** `m3-2-context-intelligence`  
**Controlling M3.2 spec:** `docs/M3_2_CANONICAL_CONTEXT_INTELLIGENCE_ANALYSIS_AND_BUILD_PLAN_2026-09-08.md`

## Locked authority and safety law

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
future != causal
unfinished != closed
stale != fresh
ambiguous mapping != valid mapping
unknown adjustment basis != comparable series

D1 outranks every predictor/reviewer
all active M2+ evidence is causal to D2
FINAL_CONFLUENCE_ARBITER / D6 is sole final-band authority
all M3.2 may_execute = false
RAW FACT CALCULATED ONCE -> MANY INTERPRETATIONS -> EVERY INTERPRETATION TRACEABLE

trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
```

## Milestone truth

| Step | Milestone | State |
|---|---|---|
| M0 | Stage-2 integrity | **GREEN / LOCKED** |
| M1 | Authority Registry | **FOUNDATION GREEN / SCOPE LOCKED** |
| M2 | Canonical DecisionContext | **GREEN / LOCKED** |
| M3 | Brain migration | **IN BUILD** |
| M3.1 | Canonical Price Intelligence | **GREEN / LOCKED** |
| M3.1-A | Snapshot Feature Kernel | **GREEN / LOCKED** |
| M3.1-B | Canonical Candle Intelligence | **GREEN / LOCKED** |
| M3.1-C | Canonical Level Intelligence | **GREEN / LOCKED** |
| M3.1-D | Canonical Indicator Intelligence | **GREEN / LOCKED** |
| M3.1-E | PIT-safe MTF Intelligence | **GREEN / LOCKED** |
| M3.1-F | Price Evidence Fusion / DAG / parity | **GREEN / LOCKED** |
| M3.2 | Canonical Context Intelligence | **IN BUILD** |
| M3.2-A | Context Source Contract | **GREEN / LOCKED** |
| M3.2-B | Canonical Session Intelligence | **GREEN / LOCKED** |
| M3.2-C | Canonical Index/Sector Context | **GREEN / LOCKED** |
| M3.2-D | Canonical Relative Strength | **ACTIVE / IN BUILD** |
| M3.2-E | Canonical Market Regime | **NOT STARTED** |
| M3.2-F | Context Fusion / Wiring / Parity | **NOT STARTED** |
| M3.3 | Canonical Memory Intelligence | **DESIGN STAGED / RUNTIME NOT ACTIVE** |
| M4 | D6 orchestration redesign | **NOT STARTED / D6 EXISTS** |

## Locked predecessor evidence

### M3.1

```text
verified source head: a346ca62ddc960e0402b7df661bb3215cfa45a7b
workflow: M3.1 Canonical Price Intelligence
run: 34254621808 — SUCCESS
```

M3.1 calculations and D6 compatibility semantics remain locked.

### M3.2-B

```text
verified source head: 5c944ac0f727767f5494af4c23b9334366860a8d
workflow: M3.2 Canonical Context Intelligence
run: 34321289260 — SUCCESS
```

Passed compile, M3.2-A/B, cache-isolation regression, locked M3.1/M2/M0, Paper Guidance, `tests/test_api.py`, full API tree and sole-D6/zero-execution audit.

### M3.2-C — Canonical Index + Sector Context — GREEN / LOCKED

```text
verified source head: 64eaa47f5ecf02c18aa3b3422ef1e0cab9b489e6
workflow: M3.2 Canonical Context Intelligence
run: 34323060143 — SUCCESS
```

Primary production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_market_context.py
apps/api/tests/decision_spine/test_m3_2_market_context.py
```

Locked C guarantees:

- effective-dated versioned `stock -> sector -> broad-index` mapping;
- missing, overlapping and ambiguous mappings fail closed;
- provider/contract/timeframe freshness policy identity is explicit;
- stale, delayed, clock-skewed and unproven sources degrade rather than become neutral;
- explicit price-basis/corporate-action lineage; adjusted data is never fabricated;
- independently hashed index and sector observations;
- wrong benchmark identity and suspicious source-hash collision are exposed;
- index/sector contradictions and missingness remain visible;
- deterministic bounded receipts;
- zero probability/proposal/veto/downgrade/final-band/execution authority;
- locked regressions, full API tree and authority audit passed at exact head.

## M3.2-D — Canonical Relative Strength — ACTIVE

Build relative strength only from canonical causal observations, never arbitrary caller scalars. Preserve absolute returns and relative relationships separately:

```text
stock_return
sector_return
index_return
stock_vs_sector
stock_vs_index
sector_vs_index
```

Every measurement must carry a versioned window, exact start/end, source hashes and compatible price basis. Missing sector/index remains unavailable; incompatible price basis degrades/fails closed. Classifications may describe leadership, lagging, alignment, divergence or idiosyncratic strength, but must not become trade authority.

Required D verification includes leadership, laggard, negative absolute/relative outperformance, index-sector contradiction, missing source, future/unfinished/stale source, mapping transitions, price-basis mismatch, duplicates, source-order independence, replay determinism, bounded receipt, performance guard and authority invariants.

## Known limitations that remain explicit

Software verification does not establish an authoritative NSE holiday/special-session calendar, authoritative live benchmark registry artifact, universal corporate-action provenance, or trading edge/profitability. Provider truth must be versioned and proven; otherwise evidence remains degraded/unavailable.

## Next boundary

Do not begin M3.2-E until M3.2-D is exact-head GREEN / LOCKED. M3.2 does not authorize D6 redesign or live execution.
