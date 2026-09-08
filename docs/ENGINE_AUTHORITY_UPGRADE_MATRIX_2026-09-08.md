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

## Verified foundations

### M0

```text
source commit: 728d81d40ec8cdfe136e765ff0378118a8c1e759
verify run:    34213835837
Stage2:       15 passed
PaperGuide:   29 passed
test_api:     556 passed
```

### M2 DecisionContext contract

```text
verify run:    34214606289
verified head: 90edc5c516324817c0e59bf56f072a63c2044e66
DecisionContext: 25 passed
Stage2:          15 passed
PaperGuide:      29 passed
test_api:        556 passed
authority:       PASS
```

## Engine matrix

| Brain / engine | Current role | Current issue / truth | Migration action now | Target authority |
|---|---|---|---|---|
| D1 Data Quality / PIT / Kill Switch | hard input safety | architecturally sound | KEEP | veto before D2 |
| D2 Closed-Candle Snapshot | immutable causal root | architecturally sound | KEEP | identity root only |
| Stage-2 Evidence Integrity | pre-context causal/provenance gate | M0 built and wired before D6 | COMPLETE M0; KEEP as DecisionContext entry gate | block/degrade evidence only |
| DecisionContext | immutable canonical evidence object | contract + deterministic builder green; real Paper Guidance construction not yet wired | **FOUNDATION COMPLETE M2; WIRE REAL CONTEXT NEXT** | no decision authority |
| Chart Reasoning | trend/chop/volatility evidence | current P1 receipt exists | WRAP into real DecisionContext | evidence/downgrade |
| Candle Anatomy | body/wick/effort/result | no canonical P1 block yet | explicit unavailable first, then WIRE M3 | calculator only |
| Candle Condition | fakeout/chop/manipulation/continuation | current P1 receipt exists | WRAP into DecisionContext | evidence + bounded veto |
| Level Context | VWAP/ORB/CPR/PDH/PDL/SR | current P1 receipt exists; duplicated elsewhere | WRAP + deduplicate M3 | evidence + bounded veto |
| Snapshot Indicator Runtime | causal indicators from D2 | current P1 receipt exists | WRAP into DecisionContext | evidence only |
| 9C Real Runtime | sequence/indicator memory | M0 provenance/counting repaired; not D2-native in P1 | COMPLETE M0-A; explicit SKIPPED now; WIRE M3 | evidence/memory only |
| PTA Signal Markers | optional probes | M0 accounting repaired; optional deps may be unavailable; not D2-native in P1 | COMPLETE M0-B; explicit SKIPPED; WIRE availability M3 | explanation evidence only |
| IndicatorFeatureBlock | normalized indicator block | synthetic contract aligned | COMPLETE M0-C; KEEP provenance | evidence only |
| MTF Confirmation | closed HTF alignment | current P1 receipt exists | WRAP into DecisionContext | evidence/downgrade |
| Market Regime | trend/range/volatility | not current canonical P1 receipt | explicit unavailable first; WIRE M3 | evidence/downgrade |
| Relative Strength | stock vs index/sector | legacy neutral `0.5` placeholder | explicit unavailable in M2; remove neutral in M3 | evidence/downgrade |
| Sector Context | sector alignment | legacy `weak_sector=False` placeholder | explicit unavailable in M2; remove neutral M3 | evidence/downgrade |
| Index Context | Nifty/index alignment | separate paths | explicit unavailable/current verified evidence only; WIRE M3 | evidence / bounded veto |
| Session Memory | phase/rhythm/stock DNA | separate path | explicit unavailable first; WIRE M3 | memory evidence |
| Persisted Indicator Memory | PIT-valid indicator memory | current P1 receipt exists | WRAP into DecisionContext | memory evidence |
| Pattern Memory | learned outcomes | separate path | explicit unavailable first; WIRE M3 | memory evidence |
| Analog / Similar History | historical analogs | separate path; PIT required | explicit unavailable first; WIRE M3 | memory evidence |
| 9-Candle Hybrid | sequence analog evidence | runtime stable but legacy surface | DEMOTE + WIRE M3 | memory/reviewer evidence |
| Hypothesis Engine | continuation/reversal/fakeout | not current P1 canonical input | explicit unavailable first; WIRE M3 | proposal; no final |
| ORB Core | opening-range strategy | same-snapshot support exists elsewhere; intentionally skipped in P1 | KEEP + explicit SKIPPED; WIRE M3 | propose/veto; no final |
| AFRE | variants/failure adaptation | merged/deterministic but not P1 canonical | KEEP + explicit SKIPPED; WIRE M3 | propose/veto/downgrade; no final |
| Derivatives | VIX/IV/PCR/OI/max pain/GEX/basis/rollover/FII | calculators exist; upstream real data partial | explicit unavailable/current capability only; PROVIDER M8 | evidence/risk; no final |
| RiskContext | events/restrictions/data/execution facts | sources incomplete | WRAP available facts + explicit unknowns | factual risk/veto |
| Failure Detector | observed/armed/unobservable failures | needs canonical same-context input | explicit unavailable first; WIRE M3 | veto/downgrade |
| Market Structure / Liquidity | auction/trap/liquidity | current P1 receipt exists | WRAP into DecisionContext | evidence/veto |
| Execution / Event / OI Risk | fill/slippage/event/options/depth | current P1 receipt exists with explicit missing evidence | WRAP into DecisionContext | risk/veto |
| Behavior Risk | sizing/heat/loss/correlation/R:R | separate decision-era path | explicit unavailable first; WIRE M3 | hard risk gate; no final |
| Portfolio / Cooldown | heat/correlation/cooldown | separate path | explicit unavailable first; WIRE M3 | veto/downgrade |
| Behavior Decision | legacy specialist decision | overlaps future final authority | DEMOTE + use only if explicitly wrapped | specialist evidence only |
| Kronos | reviewer/prior | can resemble second decision | DEMOTE + WIRE M3 | reviewer/downgrade only |
| Gemini | external AI | must never override safety | DEMOTE + WIRE M3 | reviewer only |
| Grok | external AI | must never override safety | DEMOTE + WIRE M3 | reviewer only |
| OpenAlgo Report | advisory evidence | must not imply execution | DEMOTE + WIRE M3 | reviewer only |
| Twin Arbiter | Behavior vs Kronos conflict | duplicate arbitration | DEMOTE + WIRE M3 | conflict/downgrade only |
| Jarvis Arbiter | compatibility wrapper | arbitration overlap | DEMOTE M4/M6 | downgrade only |
| Jarvis Fusion | aggregation | can resemble final | DEMOTE M4/M6 | aggregation evidence only |
| Jarvis Master Panel | combined panel | authority ambiguity | PRESENTER M6 | no decision authority |
| Final Confluence / D6 | final conflict/risk authority | sole-finalizer invariant green; not yet canonical-context consumer | KEEP; M4 canonical consumer migration | **SOLE FINAL BAND** |
| FinalDecision / PaperTradeGuidance | product decision | final canonical object incomplete | BUILD M5 | canonical output only |
| Jarvis Trading Decision Output | trader explanation | should never decide | PRESENTER M6 | display only |
| OpenAlgo / broker bridge | paper/transport infra | autonomous live route forbidden | KEEP BLOCKED | no live execution |

## DecisionContext contract now available

`apps/api/app/behavior/decision_spine/decision_context.py` provides:

- `DecisionIdentity`
- `InputIntegrity`
- `EvidenceBlock`
- `DecisionProvenance`
- `DecisionContext`
- `build_decision_context()`
- `unavailable_evidence()`

Required evidence status/provenance prevents neutral fallback substitution.

```text
missing != 0.0
missing != 0.5
unknown != false
unavailable != clean
synthetic_fallback != real
```

The context cannot grant:

```text
proof authority
paper authority
trade authority
final band
execution authority
```

## Immediate engine upgrade sequence

### Finish M2

Construct the real `DecisionContext` from the existing D2-linked Paper Guidance evidence without changing D6 behavior yet.

Current receipt-backed blocks should be wrapped first. Missing specialists should be represented as explicit unavailable/skipped blocks.

### M3

Migrate active specialist engines one family at a time into real context evidence:

1. price/candle/levels/indicators/MTF;
2. regime/session/index/sector/relative strength;
3. memory/analogs/9C/PTA;
4. hypotheses/ORB/AFRE;
5. derivatives/events/failures;
6. execution/portfolio risk;
7. reviewer evidence (Kronos/Gemini/Grok/OpenAlgo/Twin).

Every migration needs replay parity and contradiction tests before legacy decision surfaces are demoted further.

## Authority registry

`apps/api/app/behavior/decision_spine/authority_registry.py` remains the authority source of truth.

```text
exactly one finalizer = FINAL_CONFLUENCE_ARBITER
zero execution-authorized engines
presenters cannot decide
reviewers cannot finalize
```

## Safety state

```text
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
paper_promotion_eligible = false at DecisionContext construction
```
