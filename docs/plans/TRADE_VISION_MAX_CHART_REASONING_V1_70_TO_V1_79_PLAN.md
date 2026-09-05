# Trade Vision Max Chart Reasoning Expansion Plan v1.70-v1.75

## Purpose

This plan merges the overlapping v1.70-v1.79 chart-reasoning roadmap into the leanest buildable sequence without dropping any required reasoning layer.

The objective remains unchanged:

```text
move Trade Vision from a strong research analyst
into a safer paper-trading decision engine
that reasons from OHLCV, chart structure, indicators,
optional OI/options context, and prior outcome memory
without any live broker execution
```

## Non-Negotiable Safety Scope

- No live trading.
- No broker order route.
- No automatic OpenAlgo execution.
- No external AI override.
- No future candle leakage.
- No incomplete higher-timeframe candle usage.
- No fabricated market regime, event, OI, depth, or order-flow data.
- Any unavailable data must be marked unavailable and must cap confidence.
- Final outputs remain `WAIT`, `WATCH`, `PAPER-CANDIDATE`, or `AVOID` unless short-side logic is explicitly enabled later.

## Merged Remaining Roadmap

```text
v1.62  Research Panel Extraction
v1.63  Real MTF Pullback Engine
v1.64  Indicator Result Cache Completion
v1.65  Indicator Cache Frontend Controls
v1.66  Golden Fixture Regression Pack
v1.67  TV-PROD-RED-001 Final Red-Team Gate
v1.68  RELIANCE Full Workflow UI Proof
v1.69  Research-Release Safety Audit

v1.70  Chart Reasoning + Volatility Regime
v1.71  Market Regime + Breadth + RS + Bayesian
v1.72  Market Structure & Liquidity Engine
v1.73  Execution + Event + OI Risk Guard
v1.74  Post-Entry Lifecycle Manager
v1.75  Final Confluence Conflict Arbiter
v1.76  Full Indicator Intelligence Ontology (requirement heritage; implemented by v1.80)
v1.77  Indicator Reliability Memory (requirement heritage; implemented by v1.81)
v1.78  Sequential Indicator Causality Engine (preserve existing event_sequence_mining.py wiring)
v1.79  Indicator Conflict and Redundancy Arbiter (preserve existing redundancy/confluence wiring)
v1.80  Indicator Intelligence Contract + Ontology + Lag-Aware Voting
v1.81  Per-Indicator Reliability Memory + Outcome Labeling Bridge
```

## Merge Rationale

### v1.70 + v1.74 -> v1.70

These overlapped on:

- Hurst exponent
- fractal dimension
- fractal noise output
- chart morphology feeding volatility state

The merged version now owns all chart-shape, candle-math, and volatility/fractal regime logic.

### v1.71 + v1.76 -> v1.71

These overlapped on:

- per-stock setup memory
- relative performance and stock-specific edge
- breakout failure and VWAP respect memory
- posterior confidence adjustment

The merged version now owns market regime, breadth, RS, and adaptive per-stock confidence feedback.

### v1.72 + v1.73 -> v1.72

These overlapped on:

- acceptance/rejection zones
- liquidity geometry
- absorption concepts
- trap structure

The merged version now owns auction logic, VP/TPO/VSA, SMC, Wyckoff, and trap detection.

### v1.75 + v1.77 -> v1.73

These overlapped on:

- missing-data caps
- external risk constraints
- confidence downgrades
- target realism and fill realism

The merged version now owns execution, liquidity, events, OI, gamma, and expected-move risk caps.

### Standalone Versions

`v1.74` remains standalone because it is post-entry logic and not pre-entry reasoning.

`v1.75` remains standalone because it must consume every earlier layer and act as the final decision arbiter.

## v1.70 - Chart Reasoning + Volatility Regime

### Purpose

Create a single chart-intelligence layer that measures candle quality, structure, exhaustion, noise, contraction, and volatility regime from closed candles only.

### Features

- Candle morphology.
- Wick/body/no-wick impact.
- Wick rejection index.
- Candle acceleration.
- Candle mass index.
- Micro-trend linear regression slope.
- EMA distance index.
- EMA spacing and tangled-state detection.
- Hidden bullish and bearish divergence.
- Oscillator exhaustion.
- Oscillator slope versus price slope.
- Time symmetry and Fibonacci time-window clusters.
- Hurst exponent.
- Fractal dimension.
- 20-day historical volatility.
- 1-year historical volatility percentile.
- Bollinger bandwidth percentile.
- ATR percentile using prior closed data only.
- Volatility clustering.
- VCP contraction count.
- VCP volume dry-up.
- Higher-low pivot alignment.

### Outputs

```text
trend_health
chop_risk
rejection_index
rubber_band_risk
momentum_cleanliness
mean_reversion_state
time_symmetry_cluster
fractal_noise_score
volatility_regime
hv_percentile
bb_width_percentile
vcp_state
contraction_count
volume_dryup_score
trend_persistence_score
```

### Tests

```text
MAX-001 no-wick candle sequence classified as clean momentum
MAX-002 upper-wick/body > 2 raises rejection risk
MAX-003 candle acceleration decreasing raises exhaustion risk
MAX-004 EMA tangled state blocks breakout confidence
MAX-005 Hurst < 0.5 marks mean-reverting/choppy
MAX-006 Hurst > 0.5 allows trend-following logic
MAX-007 hidden bullish divergence detected
MAX-008 no future candle enters morphology calculation
VOL-001 HV percentile uses only prior closed data
VOL-002 BB width low percentile marks compression
VOL-003 extreme ATR day triggers volatility OOD
VCP-001 30->15->5 contraction sequence detected
VCP-002 volume dry-up improves VCP quality
VCP-003 choppy non-contracting range rejects VCP
FRA-001 high fractal dimension marks noisy trend
FRA-002 Hurst regime changes breakout versus mean-reversion preference
```

## v1.71 - Market Regime + Breadth + RS + Bayesian

### Purpose

Stop analyzing the stock in isolation and add adaptive, per-stock self-correction without live weight retraining.

### Features

- NIFTY trend state.
- BANKNIFTY trend state.
- Sector trend state.
- Advance-decline ratio.
- Stock versus NIFTY rolling correlation.
- Stock versus sector relative-strength line slope.
- Relative-strength position versus 20-day range.
- Leading/lagging classification.
- Per-stock signal history.
- Per-stock setup hit rate.
- Per-stock VWAP respect score.
- Per-stock breakout failure score.
- Recent losing streak tracker.
- Bayesian posterior confidence.
- Dynamic threshold adjustment.
- Cooldown after repeated failures.

### Unavailable Data Rule

If index, breadth, or sector data is unavailable:

```text
market_context_status = unavailable
confidence_cap = WATCH max
```

### Live Update Rule

Allowed:

```text
new labels
failure memory
confidence calibration
drift alerts
analog index refresh
```

Forbidden:

```text
live model weight mutation
live LightGBM retraining
live feature selection changes
```

### Outputs

```text
market_context_status
trend_state
breadth_state
relative_strength_score
relative_strength_position
leading_lagging_state
prior_confidence
posterior_confidence
stock_specific_edge
recent_failure_penalty
dynamic_confirmation_requirement
cooldown_active
```

### Tests

```text
REG-001 stock breakout with sector weakness reduces confidence
REG-002 stock leading weak index increases RS score but still requires risk pass
REG-003 missing index data caps decision at WATCH
REG-004 A/D weak distribution day blocks PAPER-CANDIDATE
REG-005 RS line near 20-day high raises conviction
REG-006 RS laggard with bullish candle returns WAIT/WATCH
BAYES-001 low sample uses prior shrinkage
BAYES-002 3 failed signals activates cooldown
BAYES-003 stock with poor VWAP history requires extra confirmation
BAYES-004 stock with strong setup history improves confidence but cannot bypass risk
BAYES-005 feedback update changes confidence, not model weights
```

## v1.72 - Market Structure & Liquidity Engine

### Purpose

Unify every chart-only acceptance/rejection and liquidity-geometry concept into one structure layer.

### Features

Volume Profile:

```text
POC
VAH
VAL
HVN
LVN
profile shape: D / P / b / thin
```

TPO:

```text
TPO POC
TPO value area
single prints
time acceptance zones
```

VSA:

```text
high volume + narrow spread = absorption
low volume + wide spread = easy markup/down
high volume + wide spread + close near high = true demand
no demand
no supply
```

SMC / Wyckoff / Trap Geometry:

```text
equal highs and equal lows
liquidity sweep
stop hunt signature
order block
fair value gap
Break of Structure
Change of Character
Wyckoff spring
Wyckoff upthrust / UTAD
Last Point of Support
range trap
inducement move
```

### Outputs

```text
auction_state
poc_distance_atr
value_area_position
hvn_lvn_context
tpo_acceptance_state
vsa_effort_result_state
liquidity_pool_detected
sweep_direction
order_block_zone
fvg_zone
bos_choch_state
wyckoff_phase
trap_score
stop_hunt_score
```

### Tests

```text
AUC-001 POC calculated from volume bins
AUC-002 VAH/VAL contains 70 percent volume
AUC-003 LVN breakout identifies vacuum zone
AUC-004 D-shape profile marks balance
AUC-005 P-shape profile marks trend continuation risk/opportunity
AUC-006 TPO single print marks fast movement
VSA-001 high volume narrow spread flags absorption
VSA-002 no demand detected on shrinking-volume up candles
VSA-003 no supply detected on shrinking-volume down candles
VSA-004 VSA downgrade overrides raw breakout strength
SMC-001 equal highs create liquidity pool
SMC-002 sweep above equal highs then close below = stop hunt
SMC-003 order block is last opposite candle before impulse
SMC-004 FVG detected only from valid 3-candle imbalance
SMC-005 BOS continuation differs from CHoCH reversal
WYC-001 spring below support then recovery detected
WYC-002 UTAD above resistance then rejection blocks long
TRAP-001 breakout plus OBV divergence raises fakeout score
TRAP-002 break with volume below p50 raises fakeout score
TRAP-003 rejection wick > 60 percent blocks PAPER-CANDIDATE
```

## v1.73 - Execution + Event + OI Risk Guard

### Purpose

Unify all external constraint layers that cap confidence, invalidate unrealistic targets, or block fill-unfriendly setups.

### Features

Execution / Liquidity:

- Spread percent.
- Average slippage by time of day.
- Entry-zone fill probability.
- Single-tick wick risk.
- Float/market-cap class.
- Impact cost estimate.
- Liquidity grade A/B/C.

OHLCV fallback when depth is unavailable:

```text
range instability
volume percentile
wick-only level detection
gap-through-entry risk
historical slippage proxy
```

Event / Optional OI:

Use only when data exists:

```text
earnings proximity
RBI/Fed/CPI/FOMC proximity
expiry day
max pain
OI concentration
gamma wall
expected move from straddle
IV percentile
IV skew
```

### Unavailable Data Rule

```text
event_context_status = unavailable
options_context_status = unavailable
do not fabricate values
```

### Outputs

```text
fill_probability
slippage_risk
impact_cost_pct
liquidity_grade
execution_plan_status
event_risk_score
earnings_adjustment
expiry_pinning_risk
expected_move_limit
gamma_wall_context
max_pain_magnet
```

### Tests

```text
EXEC-001 single-tick wick entry becomes WATCH only
EXEC-002 high spread blocks PAPER-CANDIDATE
EXEC-003 low volume blocks position sizing
EXEC-004 impact cost > expected move blocks trade
EXEC-005 missing depth data uses OHLCV proxy and marks source
EXEC-006 no-fill scenario is not counted as winning backtest
EVENT-001 earnings within 3 days downgrades size
EVENT-002 macro event before target window caps confidence
EVENT-003 unavailable event data marked unavailable, not clean
OPT-001 expected move limits unrealistic target
OPT-002 call gamma wall above price marks resistance
OPT-003 price between gamma walls marks pinning/range risk
OPT-004 missing OI data does not block chart-only mode
```

## v1.74 - Post-Entry Lifecycle Manager

### Purpose

Handle the part that earlier plans missed completely: how the system manages the thesis after entry.

### Trade State Machine

```text
WAITING
ENTRY_READY
ENTERED
PARTIAL_EXIT
TRAILING
THESIS_WEAKENING
INVALIDATED
EXITED
```

### Post-Entry Rules

```text
move SL to breakeven after 1R
partial exit at target 1
trail by ATR / swing low / VWAP
invalidate if thesis breaks
tighten SL on divergence / trap signal
reduce size on regime flip
```

### Outputs

```text
trade_state
current_thesis_status
exit_plan
partial_exit_plan
trailing_stop
invalidation_trigger
thesis_downgrade_reason
```

### Tests

```text
LIFE-001 after 1R reached SL moves to breakeven
LIFE-002 partial exit executes in simulation only
LIFE-003 VWAP loss after long marks thesis weakening
LIFE-004 UTAD after entry tightens SL
LIFE-005 regime flip reduces confidence and blocks add-on
LIFE-006 post-entry logic remains paper/simulation only
```

## v1.75 - Final Confluence Conflict Arbiter

### Purpose

Consume every upstream layer and produce the final ranked decision with explicit conflict resolution.

### Evidence Hierarchy

```text
risk/safety
data quality
liquidity
market regime
structure/levels
volume/auction
relative strength
indicators
external AI explanation
```

### Confluence Bands

```text
+5 to +7 = PAPER-CANDIDATE
+2 to +4 = WATCH
-1 to +1 = WAIT
-2 to -4 = AVOID
-5 to -7 = SHORT PAPER-CANDIDATE if short logic is explicitly enabled
```

### Conflict Rules

```text
price action/order-flow proxy > indicator signal
structure/levels > single candle
relative strength > isolated stock move
time of day modifies signal strength
event risk can downgrade all signals
liquidity can block all signals
post-entry invalidation overrides entry thesis
```

### Outputs

```text
confluence_score
evidence_votes
conflicts_detected
dominant_blocker
decision_band
confidence_interval
final_decision
human_reason_tree
```

### Tests

```text
ARB-001 bullish indicators + daily resistance = WATCH/WAIT
ARB-002 strong breakout + weak sector = confidence reduced
ARB-003 high trap score overrides analog strength
ARB-004 event risk downgrades PAPER to WATCH
ARB-005 liquidity C blocks PAPER-CANDIDATE
ARB-006 post-entry thesis break overrides original long plan
ARB-007 every final decision has reason tree
ARB-008 evidence scores sum deterministically
```

## Indicator Intelligence Contract

Every registered indicator must have a structured intelligence profile before it can move from visible/computed status into trusted reasoning status.

The contract must include:

```text
indicator_id
purpose
category
best_market_regime
bad_market_regime
best_timeframe
minimum_bars
input_columns
output_columns
signal_type
direction_meaning
lag_behavior
confirmation_delay_bars
sequential_signal_window
normalization_method
missing_policy
false_positive_conditions
conflict_rules
confirmation_rules
trade_usage
risk_usage
no_trade_usage
historical_success_rate
historical_failure_rate
per_stock_reliability
usable_for_probability
usable_for_explanation
```

Purpose of this contract:

```text
indicator exists != indicator is understood
indicator computed != indicator is trade-useful
indicator bullish != trade should be taken
```

The engine must know what every indicator is for, when it works, when it fails, and how it should affect entry, wait, no-trade, risk, target, stop, position sizing, and exit logic.

## v1.76 - Full Indicator Intelligence Ontology (Requirement Heritage)

### Purpose

Classify every indicator into a known reasoning role so Trade Vision stops treating all indicators as equal votes.

### Indicator Classes

Every indicator must be classified as one or more of:

```text
trend
momentum
volatility
volume
level
structure
trap
exhaustion
harmonic
curve
SMC
risk
```

### Indicator Purpose Map

Every indicator must answer a clear question.

Examples:

```text
RSI divergence answers exhaustion, not breakout strength.
MACD answers lagging momentum confirmation, not early entry timing.
VWAP answers value acceptance/rejection, not standalone trend certainty.
CPR answers location/context, not immediate direction by itself.
Harmonic pattern answers geometric exhaustion/reversal risk, not fill probability.
```

### Outputs

```text
indicator_id
purpose
category
best_timeframe
signal_type
direction_meaning
lag_behavior
trade_usage
risk_usage
no_trade_usage
usable_for_probability
usable_for_explanation
```

### Tests

```text
IND-ONTO-001 every registry indicator has an intelligence contract
IND-ONTO-002 every indicator has at least one ontology category
IND-ONTO-003 every indicator has purpose and direction meaning
IND-ONTO-004 proxy indicators remain explanation-only
IND-ONTO-005 future-pivot indicators require confirmation delay
IND-ONTO-006 missing purpose blocks probability promotion
```

## v1.77 - Indicator Reliability Memory (Requirement Heritage)

### Purpose

Learn which indicators work for each stock, timeframe, session phase, and regime. A strong indicator on one stock may be weak or misleading on another.

### Reliability Layers

```text
per_stock_reliability
per_timeframe_reliability
per_session_reliability
per_regime_reliability
per_pattern_reliability
historical_success_rate
historical_failure_rate
false_positive_rate
false_negative_rate
```

### Required Behavior

- Learn which stocks respect VWAP, CPR, pivots, trendlines, RSI divergence, MACD, volume profile, harmonic patterns, curve structures, SMC, and other indicator families.
- Track when indicators fail during trend, range, expiry, high-volatility, lunch chop, opening drive, and closing flow.
- Use Bayesian shrinkage for low sample counts.
- Do not allow low-sample reliability to create false confidence.

### Outputs

```text
indicator_id
symbol
timeframe
session_phase
regime_id
sample_count
historical_success_rate
historical_failure_rate
per_stock_reliability
confidence_cap
low_evidence_flag
```

### Tests

```text
IND-REL-001 low sample count caps reliability
IND-REL-002 VWAP reliability differs per stock
IND-REL-003 indicator success differs by timeframe
IND-REL-004 trend-regime reliability does not leak into range-regime reliability
IND-REL-005 repeated failures lower per-stock reliability
IND-REL-006 reliability update changes confidence, not model weights
```

## v1.78 - Sequential Indicator Causality Engine (Preserve Existing Module)

### Purpose

Track ordered indicator sequences, not only same-candle agreement. Some setups form through staged evidence: one indicator fires first, another confirms later, and price confirms after that.

### Required Sequence Logic

```text
same-candle agreement
ordered multi-candle sequence
signal freshness decay
late-confirmation penalty
reciprocal signal warning
pre-outcome-only causality
```

Example:

```text
indicator A fires at candle 1
indicator B fires at candle 3
price confirms at candle 5
outcome is labeled only after the future horizon completes
```

### Outputs

```text
sequence_id
symbol
timeframe
indicator_chain
signal_offsets
confirmation_candle
freshness_score
sequence_success_rate
sequence_failure_rate
reciprocal_signal_warning
future_leakage_detected
```

### Tests

```text
IND-SEQ-001 same-candle agreement is represented
IND-SEQ-002 ordered multi-candle sequence is represented
IND-SEQ-003 stale indicator signal is downweighted
IND-SEQ-004 late confirmation cannot create early-entry proof
IND-SEQ-005 reciprocal buy-before-downtrend warning is captured
IND-SEQ-006 future outcome data cannot enter sequence features
```

## v1.79 - Indicator Conflict and Redundancy Arbiter (Preserve Existing Modules)

### Purpose

Prevent blind indicator stacking. More indicators should not automatically mean stronger confidence.

### Problems This Version Must Solve

```text
too many indicators create false confidence
correlated indicators vote multiple times for the same thing
lagging indicators confirm after the move is already over
confirmation_delay_bars exists in the registry but is not used as a vote weight
missing indicator values create false similarity if not masked
future-pivot indicators leak if not delayed
same signal means different things in trend vs range
strong indicator on one stock may be useless on another
indicator overload slows frontend/backend
equal weighting lets weak indicators dilute strong evidence
```

### Conflict Engine Rules

Examples:

```text
RSI bullish + daily resistance + VSA absorption = downgrade
MACD buy in range/chop = late confirmation warning
4 correlated trend indicators = one trend vote, not four votes
future-pivot harmonic output = explanation-only until confirmed
missing output = masked, never zero-signal
```

### Indicator Lag-Awareness Voting

This is mandatory. The arbiter must not treat all simultaneous bullish or bearish
signals equally. Every indicator vote must be adjusted by the registry/model field
`confirmation_delay_bars`.

Reason:

```text
0-bar-delay evidence is closer to the current candle.
4-bar-delay evidence often confirms after the move.
Late confirmation must not be allowed to create false confidence.
```

Required formula:

```text
lag_weight = 1 / (1 + confirmation_delay_bars)

delay_adjusted_vote =
  raw_indicator_vote
  * lag_weight
  * per_stock_reliability
  * per_regime_reliability
  * freshness_weight
```

Required behavior:

```text
confirmation_delay_bars = 0 -> full timing value
confirmation_delay_bars = 1 -> half timing value
confirmation_delay_bars = 4 -> one-fifth timing value
confirmation_delay_bars >= sequential_signal_window -> stale/late confirmation warning
```

Hard rules:

```text
Lagging confirmation can support explanation.
Lagging confirmation can support trade management after entry.
Lagging confirmation cannot by itself promote WAIT to WATCH.
Lagging confirmation cannot by itself promote WATCH to PAPER-CANDIDATE.
Fast structural evidence outranks slow indicator confirmation when they conflict.
```

Example:

```text
Inside candle breakout and VWAP reclaim fire with 0-1 bar delay.
MACD confirms 4 bars later.
The arbiter treats MACD as late confirmation, not fresh independent evidence.
Decision remains WAIT/WATCH unless structure, levels, volume, and memory agree.
```

### Indicator-to-Trade Impact

Every indicator must say whether it supports:

```text
entry
no trade
wait
fakeout warning
stop placement
target placement
position sizing
exit/tighten SL
```

### Decision Examples

Bad blind-stacking case:

```text
RSI and MACD are bullish, but both are lagging indicators.
Price is at HVN resistance, upper wick rejection is high, VSA shows effort without result,
and this stock has failed this same setup 62% of the time.
Decision: WAIT.
```

Good aligned case:

```text
VWAP reclaim, CPR support, inside candle breakout, declining volatility,
and stock-specific memory all align.
Similar past cases continued 68% of the time.
Decision: WATCH / PAPER-CANDIDATE if risk passes.
```

### Outputs

```text
indicator_vote_groups
redundant_vote_count
independent_evidence_count
lag_adjusted_vote_score
late_confirmation_warnings
conflict_rules_triggered
dominant_indicator_blocker
indicator_trade_impact
indicator_reason_tree
decision_adjustment
```

### Tests

```text
IND-ARB-001 correlated trend indicators count as one vote group
IND-ARB-002 RSI bullish at resistance with VSA absorption downgrades decision
IND-ARB-003 MACD buy in chop is marked lagging-risk
IND-ARB-004 missing indicator values are masked and cannot match as zeros
IND-ARB-005 future-pivot indicator remains explanation-only until confirmed
IND-ARB-006 per-stock low reliability blocks probability promotion
IND-ARB-007 every indicator has trade impact fields
IND-ARB-008 final indicator reason tree is deterministic
IND-ARB-009 confirmation_delay_bars reduces late indicator vote weight
IND-ARB-010 zero-delay structural signal outranks four-bar delayed MACD confirmation
IND-ARB-011 late confirmation cannot promote WATCH to PAPER-CANDIDATE by itself
IND-ARB-012 stale confirmation beyond sequential window creates warning, not confidence
```

## v1.80 - Indicator Intelligence Contract + Ontology + Lag-Aware Voting

### Purpose

Make the engine understand every registered indicator before that indicator is allowed
to influence reasoning. This is not another indicator-computation layer. It extends the
registry contract, then feeds existing redundancy, false-agreement, reciprocal-signal,
and sequence engines.

### Version Resolution

```text
v1.76 ontology requirement -> implemented here as the concrete v1.80 contract.
v1.78 sequential causality -> do not rebuild; preserve event_sequence_mining.py.
v1.79 conflict/redundancy -> do not rebuild; wire feature_redundancy.py and false_agreement_confluence.py.
```

### Registry Contract Fields

Extend each indicator profile with safe defaults:

```text
purpose
category = trend | momentum | volatility | volume | level | structure | trap | exhaustion | harmonic | curve | smc | risk | unclassified
best_market_regime
bad_market_regime
best_timeframe
lag_behavior = leading | lagging | coincident | unknown
false_positive_conditions
confirmation_rules
conflict_rules
trade_usage
ontology_version
```

The existing `confirmation_delay_bars` field must be consumed. Do not add a duplicate
field.

Implementation rule:

```text
Use Field(default_factory=list) for list defaults.
New indicators default to unclassified/reserved, not broken.
Registry growth must not crash the engine.
```

### Required Indicator Examples

```text
RSI -> category=exhaustion, lag_behavior=lagging, not breakout strength
ADX -> category=trend, lag_behavior=lagging
VWAP -> category=level, lag_behavior=coincident
Inside candle breakout -> category=structure, lag_behavior=leading, confirmation_delay_bars=0
MACD -> category=momentum, lag_behavior=lagging, confirmation_delay_bars=4
CPR -> category=level, lag_behavior=coincident
```

### Lag-Aware Voting Engine

New implementation target:

```text
apps/api/app/behavior/indicator_lag_voting.py
```

Required formula:

```text
lag_weight = 1 / (1 + confirmation_delay_bars)

delay_adjusted_vote =
  raw_indicator_vote
  * lag_weight
  * per_stock_reliability
  * per_regime_reliability
  * freshness_weight
```

Hard rules:

```text
Lagging confirmation can support explanation and post-entry management.
Lagging confirmation cannot by itself promote WAIT -> WATCH.
Lagging confirmation cannot by itself promote WATCH -> PAPER-CANDIDATE.
Fast structural evidence outranks slow indicator confirmation on conflict.
Correlated indicators cannot vote multiple times as independent evidence.
```

### Existing Engine Wiring

```text
feature_redundancy.py
  Add category-level clustering beside family clustering.
  Same family but different category is not automatically duplicate evidence.

false_agreement_confluence.py
  Read false_positive_conditions and conflict_rules.
  Detect contract-defined false agreement, such as MACD bullish in range/chop.

reciprocal_signal_detector.py
  Consume future v1.81 reciprocal_signal_ratio.
```

### v1.80 Tests

```text
IND-ONT-001 every registry indicator carries ontology metadata
IND-ONT-002 RSI is exhaustion, not breakout strength
IND-ONT-003 category and family can differ without breaking redundancy logic
IND-ONT-004 all list defaults are factory-backed, not shared mutable defaults
IND-ONT-005 registry count/growth gate remains green
IND-ONT-006 new unclassified indicator is safe/reserved, not probability-enabled
IND-ARB-009 confirmation_delay_bars reduces late indicator vote weight
IND-ARB-010 zero-delay structural signal outranks four-bar delayed MACD confirmation
IND-ARB-011 late confirmation cannot promote WATCH to PAPER-CANDIDATE by itself
IND-ARB-012 stale confirmation beyond sequential window creates warning, not confidence
IND-ONT-009 conflict_rules trigger downgrade
IND-ONT-010 false_positive_conditions flag false agreement
```

## v1.81 - Per-Indicator Reliability Memory + Outcome Labeling Bridge

### Purpose

Learn which indicators actually work for each stock, timeframe, session, and regime.
This converts indicator profiles from static ontology into evidence-backed reliability.

### Labeling Bridge

New implementation target:

```text
apps/api/app/behavior/indicator_reliability_labeler.py
```

For every historical 9C window where an indicator fired, record:

```text
indicator_id
symbol
timeframe
signal_direction
regime
session_phase
outcome_label
mfe
mae
bars_to_target
bars_to_sl
```

Rules:

```text
Use horizons 3, 5, 9, 12, and 20 candles.
Outcome labels are attached only after the horizon completes.
Use conservative stop-first labeling when target and stop touch inside the same candle.
Unresolved outcomes never count as wins.
No future data can enter the signal feature state.
```

### Reliability Memory

New implementation target:

```text
apps/api/app/behavior/indicator_reliability_memory.py
```

Required outputs:

```text
historical_success_rate
historical_failure_rate
per_stock_reliability
per_regime_reliability
per_session_reliability
reciprocal_signal_ratio
bayesian_posterior
minimum_sample_pass
usable_for_probability
```

Rules:

```text
sample_count < 30 -> shrink toward base rate and block probability authority
OOD/regime-shift -> quarantine reliability until refreshed
reliable reciprocal behavior -> feed reciprocal_signal_detector.py
live update may append labels/reliability; live update must not mutate model weights
```

### Storage Targets

```text
indicator_ontology_profiles
indicator_signal_outcomes
indicator_reliability_memory
indicator_lag_vote_audit
indicator_conflict_events
indicator_reciprocal_signal_memory
```

### API Targets

```text
GET /api/v1/behavior/indicators/{indicator_id}/ontology
GET /api/v1/behavior/indicators/{indicator_id}/reliability/{symbol}
GET /api/v1/behavior/indicators/intelligence-summary/{symbol}
```

The summary endpoint must show trader-useful output:

```text
top supporting indicators
top warning indicators
late/lagging confirmations
false agreement warnings
per-stock reliability
per-regime reliability
reciprocal signal warnings
usable_for_probability
reason
```

All endpoints must return:

```text
live_trading_blocked=True
trade_allowed=False
no_future_leakage=True
used_for_probability gated by evidence
```

### v1.81 Tests

```text
IND-REL-001 signal-to-outcome bridge records indicator outcomes
IND-REL-002 per-stock reliability differs by symbol
IND-REL-003 per-regime reliability differs between trend/range/high-volatility
IND-REL-004 Bayesian shrinkage keeps low-sample reliability near base rate
IND-REL-005 reliability cannot pass probability gate below minimum sample
IND-REL-006 unresolved outcomes are not counted as wins
IND-REL-007 conservative stop-first labeling is applied
IND-REL-008 point-in-time guard prevents future leakage
IND-REL-009 reciprocal signal ratio is captured
IND-REL-010 reciprocal reliability feeds reciprocal_signal_detector.py
IND-REL-011 OOD/regime-shift quarantines reliability
IND-REL-012 reliability update changes confidence, not model weights
IND-REL-013 intelligence-summary is deterministic for same input
IND-REL-014 live_trading_blocked remains true on every route
IND-REL-015 no broker/order route is created
```

## Final Pipeline

```text
OHLCV / frontend chart data / indicators
  ↓
Data Quality + PIT Guard
  ↓
Indicator Result Cache
  ↓
Indicator Intelligence Contract + Ontology
  ↓
Indicator Reliability Memory
  ↓
Sequential Indicator Causality Engine
  ↓
Indicator Conflict and Redundancy Arbiter
  ↓
9-Candle DNA + All Indicator Feature Bank
  ↓
MTF Pullback + HTF Closed Candle Context
  ↓
Chart Reasoning + Volatility Regime
  ↓
Market Regime + Breadth + Relative Strength + Bayesian Feedback
  ↓
Market Structure & Liquidity Engine
  ↓
Historical Analog Memory + Winner/Failure Index
  ↓
Bayesian Feedback + Calibration
  ↓
Execution + Event + OI Risk Guard
  ↓
Post-Entry Lifecycle Manager
  ↓
Final Confluence Conflict Arbiter
  ↓
WAIT / WATCH / PAPER-CANDIDATE / AVOID
```

## Mandatory Preservation List

These items must not be dropped during implementation:

```text
Volume Profile: POC, VAH, VAL, HVN, LVN
TPO: time POC, TPO value area, single prints
VSA: effort vs result, no demand, no supply
SMC: liquidity sweeps, OB, FVG, BOS, CHoCH
Wyckoff: spring, UTAD, LPS
Candle morphology: acceleration, wick/body, mass index, micro slope
Fractal: Hurst, fractal dimension
EMA geometry: distance index, spacing, tangled state
Hidden divergence and oscillator exhaustion
VCP contraction math
Time symmetry and Fibonacci time windows
Market regime and breadth
Relative strength vs index/sector
Volatility percentile and BB width percentile
Execution probability and liquidity guard
Adaptive Bayesian per-stock feedback
Event risk and optional OI/gamma/max-pain
Formal confluence/conflict score
Post-entry lifecycle management
Indicator intelligence contract for every indicator
Indicator ontology and purpose map
Indicator failure map
Sequential indicator signal memory
Per-stock and per-regime indicator reliability
Indicator conflict and redundancy arbiter
Indicator lag-awareness voting using confirmation_delay_bars
Indicator-to-trade impact mapping
```

## Final Release Meaning

After v1.79, Trade Vision should be considered:

```text
research-release ready
paper-decision ready
not live-trading ready
```

Live trading remains blocked until a separate broker/executor safety program proves deterministic replay, risk preflight, manual approval, broker reconciliation, slippage realism, and live kill-switch behavior.
