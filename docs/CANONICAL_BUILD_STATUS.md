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
| M3.2 | Canonical Context Intelligence | **GREEN / LOCKED** |
| M3.2-A | Context Source Contract | **GREEN / LOCKED** |
| M3.2-B | Canonical Session Intelligence | **GREEN / LOCKED** |
| M3.2-C | Canonical Index/Sector Context | **GREEN / LOCKED** |
| M3.2-D | Canonical Relative Strength | **GREEN / LOCKED** |
| M3.2-E | Canonical Market Regime | **GREEN / LOCKED** |
| M3.2-F | Context Fusion / Wiring / Parity | **GREEN / LOCKED** |
| M3.3 | Canonical Memory Intelligence | **NEXT / DESIGN STAGED / RUNTIME NOT ACTIVE** |
| M4 | D6 orchestration redesign | **NOT STARTED / D6 EXISTS** |

## Exact M3.2 lock evidence

```text
M3.2-B source: 5c944ac0f727767f5494af4c23b9334366860a8d
M3.2-B run:    34321289260 — SUCCESS

M3.2-C source: 64eaa47f5ecf02c18aa3b3422ef1e0cab9b489e6
M3.2-C run:    34323060143 — SUCCESS

M3.2-D source: 576ca58e5b4f62aeb4925a02e056680923cc4f22
M3.2-D run:    34325190554 — SUCCESS

M3.2-E source: 1a03a0888ea3fdd92593c358fa30ed50da789627
M3.2-E run:    34325585040 — SUCCESS

M3.2-F / overall source: 4a98058357e6cddc8b3cb0aac225171933881479
M3.2-F / overall run:    34326793497 — SUCCESS
workflow:                M3.2 Canonical Context Intelligence
```

The exact-head M3.2-F run passed:

```text
exact checkout identity                              PASS
compile M3.2 + locked Decision Spine modules         PASS
M3.2-A context source contract                       PASS
M3.2-B session intelligence                          PASS
M3.2-C index / sector context                        PASS
M3.2-D relative strength                             PASS
M3.2-E market regime                                 PASS
M3.2-F context fusion                                PASS
final release audit cache-isolation regression       PASS
locked M3.1 price-intelligence regressions           PASS
locked M2 DecisionContext regressions                PASS
locked M0 Stage2 integrity regressions               PASS
Paper Guidance regression                            PASS
historical tests/test_api.py                         PASS
entire apps/api/tests tree                           PASS
sole-D6 / zero-execution authority audit             PASS
```

## M3.2-A — Context Source Contract — GREEN / LOCKED

Primary production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_context_intelligence.py
apps/api/tests/decision_spine/test_m3_2_context_contract.py
```

It freezes independently sourced context observations with explicit provider identity, source hashes, close-time/available-at causality, freshness, clock-skew, synthetic identity and explicit missingness. It cannot propose, set final band or execute.

## M3.2-B — Canonical Session Intelligence — GREEN / LOCKED

Primary production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_session_intelligence.py
apps/api/tests/decision_spine/test_m3_2_session.py
```

It consumes the approved D2/M3.1 closed-bar world and rejects unfinished candles. Without an authoritative versioned NSE calendar artifact, calendar authority remains degraded rather than fabricated.

## M3.2-C — Canonical Index + Sector Context — GREEN / LOCKED

Primary production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_market_context.py
apps/api/tests/decision_spine/test_m3_2_market_context.py
```

Locked guarantees:

- effective-dated versioned `stock -> sector -> broad-index` mapping;
- missing, overlapping and ambiguous mappings fail closed;
- provider/contract/timeframe freshness policy identity is explicit;
- stale, delayed, clock-skewed and unproven sources degrade rather than become neutral;
- explicit price-basis/corporate-action lineage; adjusted data is never fabricated;
- independently hashed index and sector observations;
- wrong benchmark identity and suspicious source-hash collision are exposed;
- index/sector contradictions and missingness remain visible;
- deterministic bounded receipts and zero authority.

## M3.2-D — Canonical Relative Strength — GREEN / LOCKED

Primary production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_relative_strength.py
apps/api/tests/decision_spine/test_m3_2_relative_strength.py
```

Locked guarantees:

- stock/sector/index returns are derived from causal canonical observations, not arbitrary caller scalars;
- versioned windows bind start/end time, source-series identity and price basis;
- `stock_vs_sector`, `stock_vs_index`, `sector_vs_index` remain unavailable when their required source is missing or incompatible;
- absolute direction and relative leadership are preserved independently;
- contradictory cases are exposed before leadership labels can flatten them;
- incompatible price bases degrade rather than generate fake relative values;
- deterministic/replay-safe bounded zero-authority receipt.

## M3.2-E — Canonical Market Regime — GREEN / LOCKED

Primary production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_market_regime.py
apps/api/tests/decision_spine/test_m3_2_regime.py
```

Locked guarantees:

- regime evidence spans trend, volatility, liquidity, breadth, index alignment, sector alignment, relative strength and session phase;
- confidence may be HIGH/MEDIUM/LOW/UNKNOWN/CONFLICTING/OOD/INSUFFICIENT_EVIDENCE;
- index/sector and breadth contradictions stay explicit;
- failure-risk evidence includes volatility shock, liquidity failure, trend exhaustion and session-transition risk where supported;
- OOD/novelty reduces confidence;
- hysteresis uses explicitly supplied history/hash rather than hidden mutable process-global state, preserving replay/restart determinism;
- no regime specialist has final decision or execution authority.

## M3.2-F — Context Fusion / Wiring / Parity — GREEN / LOCKED

Primary production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_context_world.py
apps/api/app/behavior/decision_spine/m3_2_context_wiring.py
apps/api/tests/decision_spine/test_m3_2_context_world.py
```

Locked guarantees:

- SESSION + INDEX + SECTOR + RELATIVE_STRENGTH + MARKET_REGIME compose into one deterministic bounded canonical context world;
- component D2 snapshot hashes and decision times must agree exactly;
- supporting facts, contradictions, missing/degraded facts, failure risks, reason codes and warnings remain independently visible;
- OOD and conflicting evidence dominate confidence appropriately rather than being averaged away;
- component/source hashes are independently retained for counterfactual and multi-hypothesis-ready downstream reasoning;
- canonical context receipts carry zero probability/proposal/veto/downgrade/final-band/execution authority;
- Stage2 wiring replaces only the deferred M3.2 context slots and prevents duplicate legacy/canonical context receipts;
- D6 remains the sole final-band authority and M3.2 introduces no weighted trading score.

## Known limitations that remain explicit

M3.2 software verification does not establish:

- authoritative NSE holiday/special-session/Muhurat calendar data;
- authoritative live benchmark-registry artifact or constituent history;
- universal corporate-action adjustment provenance across every provider;
- empirical trading edge, profitability or future prediction correctness;
- literal AGI.

Provider and calendar truth must remain versioned and proven; otherwise evidence degrades or remains unavailable.

## Next boundary

M3.2 is complete and locked. The next eligible milestone is M3.3 Canonical Memory Intelligence, governed by:

```text
docs/M3_3_CANONICAL_MEMORY_INTELLIGENCE_ANALYSIS_AND_BUILD_PLAN_2026-09-08.md
docs/M3_INTELLIGENCE_UPGRADE_REFERENCE_2026-09-08.md
```

M3.3 must preserve delayed-label PIT safety, exact corpus hashes, independent episode counts, replay-safe retrieval, OOD/drift/decay/quarantine and zero live-execution authority. Do not redesign D6 until the later authorized M4 stage.
