# Source-to-code coverage: 30 failure cases + 20 controller cases

Statuses distinguish observed price rules, policy/accounting contracts and unobservable external mechanisms. A row is not a calibrated predictor or a promise that this failure cannot occur.

| ID | Scenario | Implemented treatment / limit | Code |
|---|---|---|---|
| A01 | Chop day | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| A02 | VIX coma | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| A03 | VIX spike | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| A04 | Gap exhaustion | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| A05 | News shock | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| B01 | False breakout (trap) | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| B02 | OR too wide | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| B03 | OR too narrow | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| B04 | First-bar contamination | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| B05 | Level staleness | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| B06 | Double-stop whipsaw | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| C01 | Result-day whipsaw | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| C02 | RBI MPC ~10:00 | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| C03 | Budget/election | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| C04 | Ex-dividend misread | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| D01 | Circuit lock | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| D02 | ASM/GSM/T2T | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| D03 | Illiquidity/slippage | MODELED_ECONOMIC_GUARD_DEPTH_UNAVAILABLE | `execution.py` |
| D04 | F&O ban | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| E01 | Feed lag / bad ticks | OBSERVED_PRICE_CLOCK_RULE_NOT_CAUSE_PREDICTOR | `features.py`, `controller.py` |
| E02 | Order rejection / broker square-off | BROKER_EXCLUDED_CLOCK_ACCOUNTING_IMPLEMENTED | `execution.py`, `wake.py` |
| E03 | PIT violation (lookahead) | CAUSAL_GUARD_IMPLEMENTED | `features.py`, `contracts.py`, `adapters.py` |
| E04 | Backtest/live mismatch (E3) | AFRE_PARITY_IMPLEMENTED_LEGACY_UNCHANGED | `runtime.py`, `execution.py`, `research.py` |
| F01 | Expiry pinning | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| F02 | Gamma squeeze | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| F03 | OI wall rejection | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| F04 | Rollover distortion | EXTERNAL_MECHANISM_UNOBSERVABLE_NO_PROVIDER_CONNECTOR | `registry.py`, `contracts.py` |
| G01 | Edge decay | MATURED_OUTCOME_REVIEW_CODE_NO_REAL_HISTORY | `monitor.py` |
| G02 | Overfit | REGISTERED_TEMPORAL_SELECTION_GUARDS | `research.py`, `store.py`, `governance.py` |
| G03 | Small sample | SUPPORT_AND_NULL_ESTIMATE_GUARDS | `forecasting.py`, `value.py` |
| X01 | Expected fakeout becomes accepted continuation | Registered reclaim/acceptance can refute fade; not a probability guarantee. | `controller.py` |
| X02 | Healthy pullback mistaken for failed break | Retest and actual-inside-close rules are distinct; still unvalidated on real paths. | `features.py` |
| X03 | Correct failure diagnosis but losing fade | Independent geometry and losing-fade fixture; a detector is not a profit proof. | `execution.py` |
| X04 | PDC touches before approval or fill | Sticky feature-prefix PDC touch and next-open PDC checks invalidate original fade. | `runtime.py` |
| X05 | Waiting destroys entry economics | Fresh proposal geometry/envelope, expiry and cost/risk gates. | `execution.py` |
| X06 | Correlated tags counted as independent evidence | Shared immutable event family; no multiplication of candle likelihoods. | `controller.py` |
| X07 | Detection reported as advance forecast | Issued-at and positive-lead-time label checks; matured-only scoring. | `forecasting.py` |
| X08 | Forecast horizon substitution | Event/horizon/rules identities; four action-dependent numerical estimators remain unavailable. | `forecasting.py` |
| X09 | Both sides crossed within one bar | Conservative ambiguity accounting; no inferred intrabar event chronology. | `execution.py` |
| X10 | Native 3m versus 5m disagreement | Explicit availability and nested source resolution; no 5m-to-3m conversion. | `adapters.py` |
| X11 | Unsupported context extrapolation | Unsupported cells/universe/code/time return null; no supported real model bundled. | `forecasting.py` |
| X12 | Absent external input treated as neutral | Required capability blocks; disabled external mechanisms remain unobservable. | `features.py` |
| X13 | Endless self-agreement loop | Duplicate receipts and bounded pure evaluator; timer journals only due events. | `runtime.py` |
| X14 | Simultaneous approvals | Atomic account/day transaction tested across threads and local processes. | `store.py` |
| X15 | Unproved switching among proved leaves | Full-controller/code/model/budget/universe binding; no inherited BEL proof. | `governance.py` |
| X16 | New opposite trade after a filled loss | Permanent filled token; further opportunities are shadow-only. | `runtime.py` |
| X17 | Shadow alternatives inflate real sample size | Session-date treatment and synthetic gating; complete-policy evidence still required. | `value.py` |
| X18 | Local watchlist called market breadth | NOT IMPLEMENTED; no market-wide breadth inference. | `registry.py` |
| X19 | Corrected bars erase original forecasts | Conflicts quarantine and retain original receipts; no automated corrected-history migration. | `runtime.py` |
| X20 | Novel shock outside named taxonomy | UNKNOWN branch remains; finite contracts cannot cover every future path. | `controller.py` |
