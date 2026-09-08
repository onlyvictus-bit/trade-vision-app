# Engine Authority / Upgrade Matrix — 2026-09-08

## Purpose

Preserve useful intelligence while forcing every specialist to use one approved causal context and removing competing final-decision authority.

Migration actions:
- **KEEP** useful logic.
- **REPAIR** known contract/runtime defect.
- **WRAP** output in canonical evidence/provenance.
- **WIRE** into DecisionContext.
- **DEMOTE** remove appearance of final authority.
- **PROVIDER** connect verified upstream data.
- **PRESENTER** read-only output.
- **COMPLETE** scoped repair is verified and no longer a blocking repair task.

## Authority rule

```text
Evidence / Proposal / Warning / Downgrade / Veto
                    -> DecisionContext
                    -> FINAL_CONFLUENCE_ARBITER / D6
                       ONLY FINAL-BAND AUTHORITY
                    -> FinalDecision
                    -> Jarvis display only
```

No engine receives live execution authority.

## M0 completion evidence

Tested source commit:
`728d81d40ec8cdfe136e765ff0378118a8c1e759`

Committed-tree verification:

```text
workflow run                              34213835837
Stage-2 integrity                         15 passed
Paper Guidance v1.88                      29 passed
full apps/api/tests/test_api.py           556 passed
authority registry invariants             PASS
```

M0-C/A/B are no longer open repair items. Their next work is canonical wrapping/wiring in M2/M3.

## Engine matrix

| Brain / engine | Current role | Current issue / truth | Migration action now | Target authority |
|---|---|---|---|---|
| D1 Data Quality / PIT / Kill Switch | hard input safety | architecturally sound | KEEP | veto before D2 |
| D2 Closed-Candle Snapshot | immutable causal root | architecturally sound | KEEP | identity root only |
| Stage-2 Evidence Integrity | pre-context causal/provenance gate | built and wired before D6 in Paper Guidance | **COMPLETE M0; KEEP + make M2 entry gate** | block/degrade evidence only |
| Chart Reasoning | trend/chop/volatility evidence | only current Paper Guidance path is canonical | WRAP + WIRE M3 | evidence/downgrade |
| Candle Anatomy | body/wick/effort/result | outside complete canonical spine | WRAP + WIRE M3 | calculator only |
| Candle Condition | fakeout/chop/manipulation/continuation | not repository-wide canonical | WRAP + WIRE M3 | evidence + bounded veto |
| Level Context | VWAP/ORB/CPR/PDH/PDL/SR | duplicated across paths | WRAP + deduplicate + WIRE M3 | evidence + bounded veto |
| Snapshot Indicator Runtime | causal indicators from D2 | needs DecisionContext evidence block | WRAP + WIRE M2/M3 | evidence only |
| 9C Real Runtime | sequence/indicator memory | M0 provenance/counting repaired | **COMPLETE M0-A; WRAP + WIRE M3** | evidence/memory only |
| PTA Signal Markers | optional signal probes | M0 accounting repaired; optional deps can remain unavailable | **COMPLETE M0-B; WIRE availability evidence M3** | explanation evidence only |
| IndicatorFeatureBlock | normalized indicator block | `synthetic_fallback` contract aligned | **COMPLETE M0-C; KEEP provenance rules** | evidence only |
| MTF Confirmation | closed HTF alignment | separate worldviews possible outside P1 | WRAP + WIRE M3 | evidence/downgrade |
| Market Regime | trend/range/volatility | not consistently P1-routed | WIRE M3 | evidence/downgrade |
| Relative Strength | stock vs index/sector | neutral `0.5` placeholder remains in legacy arbitration | WIRE M3; remove neutral fallback | evidence/downgrade |
| Sector Context | sector alignment | `weak_sector=False` placeholder remains in legacy arbitration | WIRE M3; explicit availability | evidence/downgrade |
| Index Context | Nifty/index alignment | spread across paths | WRAP + WIRE M3 | evidence / bounded veto |
| Session Memory | phase/rhythm/stock DNA | separate path | WRAP + WIRE M3 | memory evidence |
| Pattern Memory | learned pattern outcomes | separate path | WRAP + WIRE M3 | memory evidence |
| Analog / Similar History | historical analogs | PIT + snapshot identity required | WRAP + WIRE M3 | memory evidence |
| 9-Candle Hybrid | sequence analog evidence | runtime stabilized; still decision-like/legacy surface | DEMOTE + WIRE M3 | memory/reviewer evidence |
| Hypothesis Engine | continuation/reversal/fakeout | needs canonical input | WIRE M3 | scenario proposal; no final |
| ORB Core | opening-range strategy | same-snapshot behavior exists but not canonical app-wide | KEEP + DEMOTE + WIRE M3 | propose/veto; no final |
| AFRE | variants + failure adaptation | merged and deterministic; provider population partial; not yet canonical app-wide | KEEP + WIRE M3 | propose/veto/downgrade; no final |
| Derivatives | VIX/IV/PCR/OI/max pain/GEX/basis/rollover/FII | calculators exist; upstream real data partial | KEEP + PROVIDER + WIRE M3/M8 | evidence/risk; no final |
| RiskContext | event/restriction/data/execution facts | real sources incomplete | KEEP + PROVIDER + WIRE M3/M8 | factual risk/veto |
| Failure Detector | observed/armed/unobservable failures | preserve unknown and same-context identity | KEEP + WIRE M3 | veto/downgrade |
| Market Structure / Liquidity | auction/trap/liquidity | currently P1-path evidence | WRAP + WIRE M3 | evidence/veto |
| Execution / Event / OI Risk | fill/slippage/event/options/depth | provider gaps remain explicit | KEEP + PROVIDER + WIRE M3/M8 | risk/veto |
| Behavior Risk | sizing/heat/loss/correlation/R:R | separate decision-era path | KEEP + WIRE M3 | hard risk gate; no final |
| Portfolio / Cooldown | heat/correlation/cooldown | needs canonical context gate | WIRE M3 | veto/downgrade |
| Behavior Decision | legacy specialist decision | overlaps future final authority | DEMOTE + WRAP M3 | specialist evidence only |
| Kronos | independent reviewer/prior | can look like second decision | DEMOTE + WIRE M3 | reviewer/downgrade only |
| Gemini | external AI | must never override safety | DEMOTE + WIRE M3 | reviewer only |
| Grok | external AI | must never override safety | DEMOTE + WIRE M3 | reviewer only |
| OpenAlgo Report | imported advisory evidence | must not imply handoff authority | DEMOTE + WIRE M3 | reviewer only |
| Twin Arbiter | Behavior vs Kronos conflict | duplicate arbitration | DEMOTE + WIRE M3 | conflict/downgrade evidence |
| Jarvis Arbiter | compatibility safety wrapper | arbitration overlap | DEMOTE M4/M6 | downgrade only |
| Jarvis Fusion | aggregation | can look like final answer | DEMOTE M4/M6 | aggregation evidence only |
| Jarvis Master Panel | combined panel | authority ambiguity | PRESENTER M6 | no decision authority |
| Final Confluence / D6 | conflict/risk finalization | sole authority invariant exists; not all brains routed through one context | KEEP + EXPAND CANONICAL INPUT M4 | **SOLE FINAL BAND** |
| DecisionContext | canonical shared evidence object | not yet built | **BUILD M2 NEXT** | no decision authority |
| FinalDecision / PaperTradeGuidance | one product decision | canonical object incomplete | BUILD M5 | canonical output only |
| Jarvis Trading Decision Output | trader-readable explanation | should not decide | PRESENTER M6 | display only |
| OpenAlgo / broker bridge | paper/transport infra | autonomous live route forbidden | KEEP BLOCKED | no live execution |

## M2 priority: canonical evidence contract

Before broad M3 routing, build a shared immutable `DecisionContext` with explicit blocks for:

```text
identity + D2 snapshot
input integrity
price/candle/levels
indicators
market/session/index/sector/relative-strength
memory/analogs
hypotheses
ORB/AFRE
Derivatives/events/failure
execution/portfolio risk
blockers/warnings
proof/paper status
provenance
```

Every material evidence block must carry at least:

```text
status: AVAILABLE | DEGRADED | UNAVAILABLE | SKIPPED | ERROR
source_engine
source_snapshot_hash
observed_at / freshness where applicable
source_mode / provenance
reason when unavailable/degraded
payload
```

## Neutral placeholders to remove in M3

Temporary legacy values such as:

```text
relative_strength_score = 0.5
indicator_signal_score  = 0.0
external_ai_score       = 0.0
weak_sector             = False
```

must become explicit availability-bearing evidence with source, D2 snapshot identity and unavailability reason.

Rules:

```text
missing != 0.0
missing != 0.5
unknown != false
unavailable != clean
synthetic_fallback != real
```

## Registry foundation

`apps/api/app/behavior/decision_spine/authority_registry.py` records engine ID, module, classification, proposal/veto/downgrade/final/execute permissions, authority rank, consumer, lifecycle and notes.

Import/runtime verification enforces:

```text
exactly one finalizer = FINAL_CONFLUENCE_ARBITER
zero execution-authorized engines
presenters cannot decide
reviewers cannot finalize
```

Registration is not activation: migration-listed engines remain dormant until wired and integration-tested.

## Stage-2 integrity status

`apps/api/app/behavior/decision_spine/stage2_integrity.py` is now a real pre-D6 Paper Guidance guard and the required M2 entry gate. It blocks wrong/malformed snapshot identity, duplicate/unregistered engines, future leakage, identity mismatch, neutral substitution for unavailable evidence, synthetic/mock/masked/unknown probability authority, and non-D6 final-band claims.

Current safety state remains:

```text
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
paper_promotion_eligible = false
```

The next code target is the M2 `DecisionContext` contract, not another prediction engine.
