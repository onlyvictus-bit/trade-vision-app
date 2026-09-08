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

| Brain / engine | Current role | Main issue | Migration action | Target authority |
|---|---|---|---|---|
| D1 Data Quality / PIT / Kill Switch | hard input safety | none architecturally | KEEP | veto before D2 |
| D2 Closed-Candle Snapshot | immutable causal root | none architecturally | KEEP | identity root only |
| Chart Reasoning | trend/chop/volatility evidence | only one Stage-2 path | WRAP + WIRE | evidence/downgrade |
| Candle Anatomy | body/wick/effort/result | outside complete canonical spine | WRAP + WIRE | calculator only |
| Candle Condition | fakeout/chop/manipulation/continuation | not repository-wide canonical | WRAP + WIRE | evidence + bounded veto |
| Level Context | VWAP/ORB/CPR/PDH/PDL/SR | duplicated across paths | WRAP + deduplicate | evidence + bounded veto |
| Snapshot Indicator Runtime | causal indicators from D2 | incomplete common contract | WRAP + WIRE | evidence only |
| 9C Real Runtime | sequence/indicator memory | provenance/count ambiguity | REPAIR M0-A | evidence/memory only |
| PTA Signal Markers | 23 optional probes | selected/probed/output conflated | REPAIR M0-B | explanation evidence only |
| IndicatorFeatureBlock | normalized indicator block | rejects `synthetic_fallback` | REPAIR M0-C | evidence only |
| MTF Confirmation | closed HTF alignment | separate worldviews possible | WRAP + WIRE | evidence/downgrade |
| Market Regime | trend/range/volatility | not consistently P1-routed | WIRE | evidence/downgrade |
| Relative Strength | stock vs index/sector | neutral `0.5` placeholder | WIRE; remove neutral fallback | evidence/downgrade |
| Sector Context | sector alignment | `weak_sector=False` placeholder | WIRE; explicit availability | evidence/downgrade |
| Index Context | Nifty/index alignment | spread across paths | WRAP + WIRE | evidence / bounded veto |
| Session Memory | phase/rhythm/stock DNA | separate path | WRAP + WIRE | memory evidence |
| Pattern Memory | learned pattern outcomes | separate path | WRAP + WIRE | memory evidence |
| Analog / Similar History | historical analogs | PIT + snapshot identity required | WRAP + WIRE | memory evidence |
| 9-Candle Hybrid | sequence analog evidence | inherited defects; decision-like surface | REPAIR + DEMOTE + WIRE | memory/reviewer evidence |
| Hypothesis Engine | continuation/reversal/fakeout | needs canonical input | WIRE | scenario proposal; no final |
| ORB Core | opening-range strategy | can look standalone | KEEP + DEMOTE + WIRE | propose/veto; no final |
| AFRE | variants + failure adaptation | provider population partial | KEEP + WIRE | propose/veto/downgrade; no final |
| Derivatives | VIX/IV/PCR/OI/max pain/GEX/basis/rollover/FII | upstream data partial | KEEP + PROVIDER + WIRE | evidence/risk; no final |
| RiskContext | event/restriction/data/execution facts | real sources incomplete | KEEP + PROVIDER + WIRE | factual risk/veto |
| Failure Detector | observed/armed/unobservable failures | preserve unknown and same context | KEEP + WIRE | veto/downgrade |
| Market Structure / Liquidity | auction/trap/liquidity | P1 path only | WRAP + WIRE | evidence/veto |
| Execution / Event / OI Risk | fill/slippage/event/options/depth | provider gaps | KEEP + PROVIDER + WIRE | risk/veto |
| Behavior Risk | sizing/heat/loss/correlation/R:R | separate decision-era path | KEEP + WIRE | hard risk gate; no final |
| Portfolio / Cooldown | heat/correlation/cooldown | needs canonical gate | WIRE | veto/downgrade |
| Behavior Decision | legacy specialist decision | overlaps future final authority | DEMOTE | specialist evidence only |
| Kronos | independent reviewer/prior | can look like second decision | DEMOTE + WIRE | reviewer/downgrade only |
| Gemini | external AI | must never override safety | DEMOTE + WIRE | reviewer only |
| Grok | external AI | must never override safety | DEMOTE + WIRE | reviewer only |
| OpenAlgo Report | imported advisory evidence | must not imply handoff authority | DEMOTE + WIRE | reviewer only |
| Twin Arbiter | Behavior vs Kronos conflict | duplicate arbitration | DEMOTE + WIRE | conflict/downgrade evidence |
| Jarvis Arbiter | compatibility safety wrapper | arbitration overlap | DEMOTE | downgrade only |
| Jarvis Fusion | aggregation | can look like final answer | DEMOTE | aggregation evidence only |
| Jarvis Master Panel | combined panel | authority ambiguity | PRESENTER | no decision authority |
| Final Confluence / D6 | conflict/risk finalization | not all brains routed yet | KEEP + EXPAND CANONICAL INPUT | **SOLE FINAL BAND** |
| FinalDecision / PaperTradeGuidance | one product decision | canonical object incomplete | BUILD | canonical output only |
| Jarvis Trading Decision Output | trader-readable explanation | should not decide | PRESENTER | display only |
| OpenAlgo / broker bridge | paper/transport infra | autonomous live route forbidden | KEEP BLOCKED | no live execution |

## Neutral placeholders to remove

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

`apps/api/app/behavior/decision_spine/authority_registry.py` records engine ID, module, classification, proposal/veto/downgrade/final/execute permissions, authority rank, consumer, lifecycle and notes. Import-time validation enforces unique IDs, exactly one finalizer (`FINAL_CONFLUENCE_ARBITER`), zero execution-authorized engines, no presenter decision authority and no reviewer final authority.

Registration is not activation: migration-listed engines remain dormant until wired and integration-tested.

## Stage-2 integrity foundation

`apps/api/app/behavior/decision_spine/stage2_integrity.py` is a pre-DecisionContext guard, not a predictor. It blocks wrong/malformed snapshot identity, duplicate/unregistered engines, future leakage, identity mismatch, neutral substitution for unavailable evidence, synthetic/mock/masked/unknown probability authority, and non-D6 final-band claims. Completed engines containing unavailable evidence are downgraded rather than treated as clean.

Safety state remains:

```text
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
paper_promotion_eligible = false
```
