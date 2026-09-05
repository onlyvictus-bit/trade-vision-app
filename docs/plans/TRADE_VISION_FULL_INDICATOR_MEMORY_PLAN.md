# Trade Vision Complete Market Behavior, Indicator Memory, Chart Evidence, and Kronos Alignment Plan

## 1. Purpose

This plan upgrades the current compact Trade Vision analyzer into a point-in-time
historical behavior engine that can answer:

> When the present candle structure, indicator combination, timeframe context,
> session state, and levels occurred before, what happened next, and does real
> Kronos agree?

The result remains research-only. No milestone in this plan enables broker
routing or allows Kronos to override `WAIT`, `NO_TRADE`, risk, or human veto.

## 2. Verified Starting State

- Real upstream source is installed at `external/kronos`.
- Real `NeoQuasar/Kronos-mini` and `NeoQuasar/Kronos-Tokenizer-2k` are installed
  under `apps/kronos-service/models`.
- Real GPU inference works on the RTX 5050 Laptop GPU.
- The isolated API bridge parses real Kronos output and reapplies all safety
  locks.
- Trade Vision currently exposes 71 self-indicator implementations.
- Runtime readiness exposes 94 total output groups: 71 self-indicator groups
  and 23 PTA marker groups.
- The governed replay matrix currently computes 32 rows; some are proxies.
- The existing multi-timeframe analyzer uses a compact feature vector, not the
  complete validated inventory.

## 3. Non-Negotiable Invariants

```python
assert feature.decision_time <= feature.available_time
assert higher_timeframe_bar.closed_before(decision_time)
assert feature_snapshot.hash == kronos_input_snapshot.hash
assert all(group.weight_sum <= 1.0 for group in indicator_families)
assert historical_matches.exclude_current_and_future
assert ambiguous_same_bar_target_and_sl != TARGET_HIT
assert kronos.cannot_execute_orders
assert kronos.cannot_override_no_trade
assert twin.conflict_action in {"WAIT", "NO_TRADE"}
assert live_trading_blocked
assert indicator.internal_computation_uses_only_past_and_current_bar
assert not indicator.uses_centered_window_unless_converted_to_trailing
assert pattern.confirmation_time <= decision_time
assert sequential_signal_window.max_lookback <= available_history
assert reciprocal_signal_detector.uses_only_pre_outcome_data
assert value_confluence.does_not_require_same_candle_signals
assert design_similarity.invariant_to_price_level_scaling
assert missing_required_volume_or_halt_context.blocks_trade
assert cross_market_context.reduces_coverage_or_is_explicitly_missing
assert memory_poisoning_detection.active
assert ood_detection.threshold_explicitly_defined
assert drift_detection.algorithm_explicitly_defined
```

## 4. Target Architecture

```text
Immutable OHLCV Snapshot
        |
        +--> Seven-Timeframe Closed-Bar Builder
        |       1m / 3m / 5m / 15m / 1H / Daily / Weekly
        |
        +--> Validated Indicator Runtime
        |       71 self indicators + 23 PTA groups
        |
        +--> Feature Normalization and Availability Guard
        |
        +--> Redundancy and Family Weight Controller
        |
        +--> Point-in-Time Feature Store
        |
        +--> Historical Combination Similarity
        |       candle + indicators + levels + session + regime
        |
        +--> Target/Stop Outcome Labeler
        |
        +--> Trade Vision Behavior Result
        |
        +--> Real Kronos on the exact same OHLCV snapshot
        |
        +--> Twin Arbiter
                agreement / conflict / WAIT / NO_TRADE
```

## 5. Indicator Registry

Create:

```text
apps/api/app/behavior/indicator_registry.py
apps/api/app/behavior/indicator_contracts.py
apps/api/app/behavior/indicator_runtime.py
config/behavior_indicators.yaml
```

Every indicator/output group must declare:

```text
indicator_id
display_name
implementation_path
callable_name
family
subfamily
output_columns
input_columns
minimum_bars
lookback_bars
timeframes_allowed
continuous_or_event
normalization_method
direction_semantics
closed_bar_only
point_in_time_safe
formula_hash
implementation_version
test_fixture
status = validated | proxy | blocked | retired
default_parameters_json
warmup_bars_exact
output_schema_json
pit_audit_passed_date
internal_lookahead_audit_result
centered_or_trailing
minimum_volume_policy
uses_future_pivots
confirmation_delay_bars
```

No indicator enters historical matching while its status is `proxy`,
`blocked`, or `retired`.

### 5.1 Mandatory Indicator Contract for the Four Added Stock-App Indicators

The four requested stock-app indicators must be registered explicitly before
implementation. They cannot remain only as names in the preservation register.

| Indicator ID | Function | Family | Minimum Bars | PIT Rule | Required Output Groups |
|---|---|---|---:|---|---|
| `si_sweep_inside_rr` | `sweep_inside_rr_strategy` | `breakout_retest` / `smart_money_structure` | 50 | sweep, inside setup, entry, SL, and TP become available only after the triggering candle closes | setup lines, entry line, stop line, target line, EMA, direction, confirmation state |
| `si_inside_candle_strategy` | `inside_candle_strategy` | `candlestick` / `breakout_retest` | 200 | mother candle, inside candle, SuperTrend, and EMA confirmation must use closed bars only | setup segments, trade segments, EMA9, EMA21, EMA200, SuperTrend, direction |
| `si_ichi_trend_osc` | `ichimoku_trend_oscillator` | `momentum` / `trend` | 52 | Tenkan/Kijun/cloud force must be calculated from trailing Donchian windows only | force, signal line, histogram, state, shift event, Kumo state |
| `si_fmfm300` | `fmfm300_indicator` | `market_structure` / `pattern` | 100 | pivots, zones, trendlines, FVGs, heatmap, and dynamic VWAP must record confirmation delays and cannot use future pivots at decision time | summary, EMA20, SuperTrend, dynamic VWAP, pivots, zones, FVGs, trendlines, heatmap, HTF levels |

If any of these indicators requires a future pivot to confirm a level or
pattern, the output at decision time must be labeled `FORMING` or
`DEVELOPING_NOT_DECISION_SAFE` until `confirmation_time <= decision_time`.

## 6. Indicator Families

Use family-level weighting so similar indicators cannot create fake agreement:

```text
price_structure
trend
momentum
volatility
volume_participation
vwap_value_area
support_resistance
breakout_retest
candlestick
smart_money_structure
harmonic_geometry
session_opening_range
reversal
liquidity_order_flow_proxy
statistical_distribution
risk_execution
```

Each family receives a maximum total contribution of `1.0`. Ten correlated
momentum indicators therefore cannot outvote one independent risk block.

## 7. Seven-Timeframe Computation

Create:

```text
apps/api/app/behavior/timeframe_feature_builder.py
apps/api/app/behavior/closed_bar_guard.py
apps/api/app/behavior/multitimeframe_snapshot.py
```

Required timeframes:

```text
1m, 3m, 5m, 15m, 1H, daily, weekly
```

Rules:

1. Build every higher timeframe from the same immutable 1-minute snapshot.
2. Align intraday bars to the exchange session starting at 09:15 IST.
3. Label each aggregate with its actual last source candle timestamp.
4. Never expose an incomplete 1H, daily, or weekly value to an earlier decision.
5. Persist `source_snapshot_hash`, `bar_open_time`, `bar_close_time`,
   `available_time`, and `decision_time`.
6. Corporate-action-adjusted and raw price series must have distinct data
   versions and must never be silently mixed.

## 8. Feature Store

Create:

```text
apps/api/app/behavior/feature_store.py
apps/api/app/behavior/feature_snapshot_repository.py
data/feature-store/
```

Use columnar Parquet partitions for the high-volume feature matrix:

```text
data/feature-store/
  symbol=RELIANCE/
    timeframe=5m/
      year=2026/
        month=03/*.parquet
```

Use the application database for metadata and lineage:

```sql
CREATE TABLE feature_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    decision_time_ns INTEGER NOT NULL,
    source_snapshot_hash TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    indicator_registry_version TEXT NOT NULL,
    parquet_uri TEXT NOT NULL,
    row_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(symbol, timeframe, decision_time_ns, feature_version)
);

CREATE INDEX ix_feature_snapshot_lookup
ON feature_snapshots(symbol, timeframe, decision_time_ns);
```

The stored row must include candle anatomy, levels, session, market regime,
all validated indicator outputs, availability masks, and missing-value reasons.

## 9. Missing and Sparse Indicator Rules

- `no signal` is different from `calculation failed`.
- Sparse event indicators store `event_present`, `event_direction`,
  `event_strength`, and `bars_since_event`.
- Warm-up periods remain `unavailable`; they are never replaced with zero.
- An indicator failure removes that indicator from the current family weight
  and emits a data-quality event.
- A snapshot is blocked when required safety families are unavailable.

## 10. Duplicate-Indicator Inflation Control

Create:

```text
apps/api/app/behavior/feature_redundancy.py
apps/api/app/behavior/family_weighting.py
apps/api/app/behavior/redundancy_audit.py
```

Apply these controls using training history only:

1. Group indicators by declared semantic family.
2. Calculate rolling Spearman correlation for continuous features.
3. Calculate Jaccard similarity for sparse binary events.
4. Calculate mutual information against outcome labels.
5. Cluster features with distance `1 - abs(correlation)`.
6. For clusters above `abs(rho) >= 0.90`, select a stable medoid or divide the
   cluster weight across members.
7. Cap every family contribution at `1.0`.
8. Persist selected features, rejected duplicates, cluster membership, and
   fit-period boundaries.
9. Refit only during walk-forward training, never using the evaluation period.

Required outputs:

```text
raw_feature_count
eligible_feature_count
redundancy_cluster_count
effective_independent_feature_count
family_weights
suppressed_duplicate_features
redundancy_model_version
```

Cross-family correlation audit:

```text
if average_inter_family_correlation > 0.70:
    apply cross_family_penalty or merge into shared weight budget
```

Family caps prevent same-family inflation, but they are not sufficient when
different families are mathematically redundant.

## 11. Combination Similarity

Create:

```text
apps/api/app/behavior/combination_similarity.py
apps/api/app/behavior/analog_retrieval.py
apps/api/app/behavior/similarity_explanation.py
```

Use a two-stage retrieval process:

### Stage A: Hard Context Filter

Filter historical candidates by:

```text
same symbol
same timeframe
same session phase where applicable
compatible market regime
compatible gap class
no corporate-action contamination
point-in-time-valid features
candidate timestamp before decision timestamp
outcome horizon fully available
```

### Stage B: Weighted Similarity

```text
total_similarity =
    0.20 * candle_structure_similarity
  + 0.20 * independent_indicator_similarity
  + 0.15 * trend_momentum_similarity
  + 0.15 * level_context_similarity
  + 0.10 * session_similarity
  + 0.10 * volatility_volume_similarity
  + 0.10 * regime_market_similarity
```

The weights are initial configuration values, not permanent truths. They must be
walk-forward calibrated and versioned.

Calibration procedure:

```text
method: walk_forward_optimization
folds: 5 minimum
train_size: 1 year default, configurable by market history
test_size: 3 months default
step: 1 month default
objective: analog_retrieval_precision_at_10 plus calibration error
minimum_calibration_outcomes: 500
weight_stability_threshold: cross_fold_std <= 0.05
block_if_weight_variance_exceeds: 20% relative variance
```

If calibrated probabilities are displayed:

```text
calibration_method = isotonic_regression or Platt_scaling
expected_calibration_error <= 0.05 for promotion
recalibration_trigger = recent_ECE > 0.10 over last 100 labeled outcomes
```

Return at least 30 non-overlapping historical matches. Prevent multiple adjacent
timestamps from the same setup from pretending to be independent evidence.

### Stage C: Scale-Safe Retrieval and Independence Guard

Exact Gower, DTW, Mahalanobis, Jaccard, and shape-grammar matching is not
allowed to scan millions of rows directly during realtime research. Retrieval
must use a tiered candidate funnel:

```text
1. hard context filter
2. vectorized ANN prefilter using FAISS, HNSW, or equivalent local ANN index
3. shortlist top_k_initial = 500 candidates
4. exact mixed-feature distance on the shortlist
5. DTW/design-shape refinement only on top_k_refined = 100 candidates
6. non-overlap and independence filter
7. calibrated outcome aggregation
```

The ANN vector may include only point-in-time-safe normalized continuous
features. Categorical, sparse-event, and shape-grammar evidence is applied in
the exact refinement stage.

Independence rule:

```text
minimum_match_count = 30
minimum_distinct_regimes = 3 where available
minimum_separation = max(20 bars, volatility_adjusted_event_window)
minimum_coverage_ratio = 0.001 of searchable history where data volume permits
```

If 30 matches can be reached only by relaxing essential context filters, the
result must be labeled `LOW_EVIDENCE_RELAXED_FILTERS` and cannot produce a
high-confidence recommendation.

Hubness and false-nearest-neighbor protections:

```text
track_neighbor_frequency_per_candidate
flag hub candidates above 99th percentile neighbor frequency
support local scaling or mutual proximity correction
report distance metric used in every analog explanation
use cosine only inside homogeneous continuous-feature subspaces
use Gower or mixed-distance aggregation for final cross-family similarity
```

## 12. Outcome Labeling

Create:

```text
apps/api/app/behavior/outcome_labeler.py
apps/api/app/behavior/barrier_engine.py
apps/api/app/behavior/outcome_repository.py
```

For each candidate direction and timeframe, calculate future outcomes using
entry, stop, and target barriers known at decision time.

Labels:

```text
TARGET_HIT_FIRST
SL_HIT_FIRST
OVERNIGHT_GAP_TARGET
OVERNIGHT_GAP_SL
GAP_THROUGH_STOP
AMBIGUOUS_BOTH_HIT_SAME_BAR
NEITHER_HIT_TIME_EXIT
PARTIAL_TARGET_THEN_SL
BREAKEVEN
FAKE_BREAKOUT
RETEST_SUCCESS
RETEST_FAIL
CHOP_NO_FOLLOWTHROUGH
NO_FILL
```

Critical rule:

> If a single OHLC bar touches both target and stop and no lower-timeframe
> sequence is available, label it `AMBIGUOUS_BOTH_HIT_SAME_BAR`. Never assume
> the profitable ordering.

Store:

```text
entry_time
entry_price
fill_model_version
target_price
stop_price
first_target_time
first_stop_time
bars_to_target
bars_to_stop
mfe_price
mae_price
mfe_atr
mae_atr
net_return_after_costs
outcome_label
outcome_horizon_end
```

### 12.1 Fill, Slippage, Cost, and Gap Model

Outcome labeling must model executable prices conservatively. A bar touching a
level is not automatically a fill at the desired level.

Fill rules:

```text
market_order: fill at next eligible bar open plus half-spread and slippage
limit_order: fill only when price reaches limit; no fill if touched only by an
             ambiguous OHLC bar without sufficient lower-timeframe evidence
stop_order: fill at stop price or worse when price gaps through the stop
partial_fill: track filled quantity and apply target/stop only to filled size
no_fill: do not count as win or loss; record opportunity cost separately
```

Gap-through-stop handling:

```text
long position:
  if next_open < stop_price:
      fill_price = next_open
short position:
  if next_open > stop_price:
      fill_price = next_open
```

If a same OHLC bar includes both target and stop:

```text
1. inspect open price first
2. if open gaps beyond target or stop, label according to executable open
3. if lower-timeframe path is unavailable, label AMBIGUOUS_BOTH_HIT_SAME_BAR
4. never assume profitable ordering
```

Initial India cost model, configurable per broker/exchange:

```text
brokerage: configurable, default 0.01% per side capped at Rs 20
STT: intraday equity sell-side default 0.025%; delivery configurable
GST: 18% on brokerage + exchange + SEBI charges
SEBI: configurable per crore
exchange_transaction_charge: NSE/BSE configurable
stamp_duty: buy-side configurable by state/product
impact_cost: f(order_size, average_daily_volume, volatility, spread)
latency_slippage: f(order_type, volatility, session_phase, data_delay_ms)
adverse_selection_penalty: f(signal_crowding, spread, time_of_day)
```

Missing volume policy:

```text
if volume is missing for a market where volume is expected:
    mark required volume context unavailable
    check halt/circuit/special-session calendar
    block trade-quality conclusion unless explicitly whitelisted
```

## 13. Exact Snapshot Contract with Kronos

Create:

```text
apps/api/app/behavior/shared_snapshot.py
apps/api/app/behavior/kronos_snapshot_adapter.py
```

One immutable `SharedAnalysisSnapshot` must feed both engines:

```text
snapshot_id
symbol
timeframe
decision_time_ns
closed_ohlcv_bars
source_snapshot_hash
corporate_action_version
calendar_version
```

Trade Vision may derive indicators from these bars. Kronos receives the same
bars directly. Both results must echo the identical:

```text
snapshot_id
source_snapshot_hash
decision_time_ns
last_bar_timestamp_ns
```

Twin comparison must fail closed when any identity differs.

### 13.1 Kronos Barrier Discretization Contract

Kronos raw forecast paths are not directly comparable to Trade Vision's
historical outcome labels. Before Twin comparison, every Kronos forecast must
be converted into the same barrier language used by Behavior.

Create:

```text
apps/api/app/behavior/kronos_barrier_adapter.py
```

Required conversion:

```text
forecast_path -> target_hit_probability
forecast_path -> stop_hit_probability
forecast_path -> time_exit_probability
forecast_path -> expected_mfe
forecast_path -> expected_mae
forecast_path -> path_chop_probability
forecast_path -> barrier_sequence_distribution
```

Twin Arbiter may compare:

```text
Behavior target/stop/time probabilities
Kronos target/stop/time probabilities
Behavior expected MFE/MAE
Kronos expected MFE/MAE
Behavior uncertainty
Kronos uncertainty
```

Twin Arbiter must not compare raw forecast tokens, raw generated candles, or
uncalibrated path direction as direct trading evidence.

Kronos agreement can increase only the research explanation score after
decorrelation and OOS reliability tests pass. Kronos disagreement reduces
confidence or produces `WAIT`; Kronos agreement never overrides risk,
`NO_TRADE`, kill switch, stale data, or human veto.

## 14. Public Contracts

Add:

```text
IndicatorDefinition
IndicatorAvailability
IndicatorFeatureValue
IndicatorFeatureSnapshot
FeatureFamilyScore
RedundancyCluster
RedundancyAuditReport
MultiTimeframeFeatureSnapshot
HistoricalAnalog
CombinationSimilarityResult
BarrierDefinition
OutcomeLabelRecord
SharedAnalysisSnapshot
KronosSnapshotReceipt
TwinSnapshotIntegrity
FullBehaviorForecast
```

## 15. APIs

```text
GET  /api/v1/behavior/indicators/registry
GET  /api/v1/behavior/indicators/readiness
POST /api/v1/behavior/features/build
GET  /api/v1/behavior/features/{snapshot_id}
POST /api/v1/behavior/redundancy/audit
POST /api/v1/behavior/analogs/search
POST /api/v1/behavior/outcomes/label
POST /api/v1/behavior/full-analysis
POST /api/v1/kronos/forecast-shared-snapshot
POST /api/v1/twin/full-analysis
```

Long-running historical builds must return `202 Accepted` with `run_id`,
progress, cancellation state, evidence hashes, and resumable partitions.

## 16. Build Order

### v0.60: Registry Lock

- Register all 94 output groups.
- Map implementations, outputs, families, warm-up, and PIT status.
- Block every proxy from production feature computation.

### v0.61: Seven-Timeframe Feature Runtime

- Compute validated indicators on all seven closed-bar streams.
- Add availability masks and deterministic output hashes.

### v0.62: Columnar Historical Feature Store

- Build partitioned Parquet writer/reader.
- Add metadata tables, lineage, resumability, and corruption checks.

### v0.63: Redundancy Control

- Add correlation/Jaccard clustering and family caps.
- Produce independent-feature and suppressed-duplicate reports.

### v0.64: Outcome Labeling

- Add target-first/SL-first, ambiguity, MFE/MAE, fill, cost, and time-exit labels.

### v0.65: Combination Similarity

- Add context filtering, weighted similarity, time decay, and non-overlap.
- Return verifiable historical dates and feature-level explanations.

### v0.66: Shared Snapshot Kronos Contract

- Feed identical bars and hashes to Trade Vision and Kronos.
- Fail closed on snapshot mismatch.

### v0.67: Full Twin Analysis

- Compare full Trade Vision memory result with real Kronos.
- Preserve risk/no-trade authority and conflict reduction.

### v0.68: Walk-Forward Validation

- Evaluate each timeframe and stock out of sample.
- Calibrate confidence, drift thresholds, and family weights.
- Publish Behavior-only, Kronos-only, and Twin performance separately.

## 17. Required Tests

```text
TV-FI-001 all 94 groups are registered
TV-FI-002 every registry entry has implementation lineage
TV-FI-003 proxy/blocked indicators cannot enter the feature store
TV-FI-004 all seven timeframes use the same source snapshot
TV-FI-005 incomplete higher-timeframe bars are unavailable
TV-FI-006 future values fail the point-in-time guard
TV-FI-007 warm-up missing is not converted to zero
TV-FI-008 sparse no-event differs from calculation failure
TV-FI-009 repeated build produces identical row hashes
TV-FI-010 family weights never exceed one
TV-FI-011 highly correlated features cannot multiply family influence
TV-FI-012 redundancy fitting excludes evaluation data
TV-FI-013 analogs are strictly historical
TV-FI-014 adjacent timestamps are de-duplicated
TV-FI-015 minimum evidence requires 30 independent matches
TV-FI-016 target before stop labels TARGET_HIT_FIRST
TV-FI-017 stop before target labels SL_HIT_FIRST
TV-FI-018 same-bar target and stop labels AMBIGUOUS
TV-FI-019 costs and slippage alter net outcome
TV-FI-020 no-fill is not counted as a win
TV-FI-021 Trade Vision and Kronos snapshot hashes match
TV-FI-022 snapshot mismatch blocks Twin
TV-FI-023 Kronos failure returns WAIT without breaking Trade Vision
TV-FI-024 Kronos cannot override Behavior NO_TRADE
TV-FI-025 risk block cannot be overridden
TV-FI-026 historical dates are present in the source dataset
TV-FI-027 walk-forward fit excludes future periods
TV-FI-028 confidence calibration is measured out of sample
TV-FI-029 feature drift quarantines stale memory
TV-FI-030 no live route or broker credential exists
```

## 18. Acceptance Criteria

The upgrade is complete only when:

1. All 94 groups have an explicit status and lineage.
2. Every validated output is computed deterministically on seven timeframes.
3. No incomplete or future bar can enter any snapshot.
4. Duplicate features cannot inflate family agreement.
5. At least 30 independent analogs are used or confidence is blocked.
6. Every analog exposes a real historical date and outcome.
7. Target/stop ordering is conservative and ambiguity-aware.
8. Trade Vision and Kronos prove identical snapshot identity.
9. Twin reports Behavior-only, Kronos-only, and combined evidence separately.
10. Walk-forward and out-of-sample tests pass before paper-trading evaluation.

## 19. External AI Review Questions

Ask reviewers to challenge:

1. Whether the redundancy controls sufficiently prevent correlated-vote inflation.
2. Whether the similarity distance is appropriate for mixed continuous, ordinal,
   and sparse-event features.
3. Whether outcome labels avoid intrabar optimism and lookahead leakage.
4. Whether Parquet partitioning and metadata indexes support one million-plus
   1-minute candles per symbol.
5. Whether snapshot identity proves both engines saw exactly the same data.
6. Whether any rule could allow Kronos to override risk or `NO_TRADE`.
7. Whether walk-forward splits protect feature selection, weighting, calibration,
   and threshold tuning from future leakage.

## 20. Complete Requirement Boundary

The example:

> At 1 PM the market is ranging, RSI is within a repeated value band, MFI is
> weak, a harmonic pattern exists on 3m, price is choppy, and the stock is not
> respecting its trendline.

is only one possible answer. It is not the complete requirement.

The complete system must answer arbitrary historical and current questions
across:

```text
symbol
exchange
asset class
trade date
decision timestamp
market session
day of week
calendar/event class
source timeframe
confirmation timeframes
market regime
price structure
candle structure
indicator values and states
support/resistance interactions
trendline interactions
VWAP/value-area interactions
volume and liquidity behavior
pattern geometry
cross-asset context
historical analogs
subsequent outcomes
execution feasibility
risk and invalidation
```

The engine must support both directions:

1. **Current-to-history:** Given the present state, find prior matching states.
2. **History-to-rule:** Given a proposed condition, discover when it occurred,
   what followed, and whether the relationship remained stable out of sample.

The engine must distinguish:

```text
observation      = directly measured fact
derived feature  = deterministic calculation from available facts
pattern          = rule-based or model-based structural classification
historical fact  = outcome recorded after a prior decision timestamp
forecast         = uncertain future distribution
recommendation   = safety-filtered research conclusion
```

No forecast, similarity percentage, pattern name, or narrative may be displayed
as a measured fact.

## 21. Behavior Investigation Questions

For any selected symbol and decision time, the system must answer all applicable
questions below.

### 21.1 Current State

- What is price doing now: trend, range, compression, expansion, reversal,
  breakout, retest, fade, accumulation, distribution, or uncertain?
- What changed during the latest candle, rolling window, session segment, day,
  and higher-timeframe bar?
- Is the state stable, newly forming, weakening, invalidated, or conflicting?
- Which observations support the classification?
- Which observations contradict it?

### 21.2 Indicator State

- What is every validated indicator's exact value?
- What is its unit, parameter set, input price, timeframe, and calculation time?
- Is the value rising, falling, flat, crossing, diverging, saturated, or stale?
- What percentile is it in relative to that stock, timeframe, session phase,
  regime, and rolling history?
- Is the indicator independently informative or redundant with another family?
- Did the indicator emit no event, or did its calculation fail?
- How old is the latest event and how long has the current state persisted?

### 21.3 Structure and Pattern

- What candle, multi-candle, swing, chart, harmonic, liquidity, and session
  patterns are present?
- Is each pattern forming, confirmed, failed, expired, or invalidated?
- What anchors, pivots, tolerances, and confidence produced the pattern?
- Does the pattern agree with price structure, indicators, volume, levels, and
  higher timeframes?

### 21.4 Exact-Time and Session Behavior

- What does this stock usually do at this exact minute or session segment?
- Does the behavior differ on Monday, Friday, expiry day, post-holiday, results
  day, RBI/Fed day, or other calendar classes?
- Is the present state typical or unusual for the stock at this time?
- At what time do similar states usually resolve?
- Which session transitions commonly alter the behavior?

### 21.5 Historical Analogs

- When did the same or sufficiently similar state occur before?
- Which exact values, states, patterns, timeframes, levels, and contexts matched?
- Which important features did not match?
- How many independent matches exist?
- What happened after each match over configurable horizons?
- Did target, stop, invalidation, or time exit occur first?
- Were results stable across recent/old history, regimes, and walk-forward folds?

### 21.6 Trading Usefulness

- Is there enough independent evidence to form a research conclusion?
- What entry zone, invalidation, stop, targets, expected MFE/MAE, time horizon,
  fill risk, and costs are supported by prior evidence?
- Is the setup actionable now, awaiting confirmation, too late, too illiquid,
  too uncertain, or structurally invalid?
- What would have to change to promote `WAIT` to a replay candidate?
- What would immediately invalidate the thesis?

## 22. Complete Indicator Value Contract

Every validated indicator output must return an `IndicatorObservation`, even
when unavailable:

```text
observation_id
snapshot_id
symbol
exchange
indicator_id
output_name
display_name
family
subfamily
timeframe
parameters
input_columns
input_price_type
raw_value
formatted_value
unit
normalized_value
rolling_percentile
session_percentile
regime_percentile
z_score
slope_1
slope_n
acceleration
direction
state
signal
signal_strength
crossed_reference
reference_name
reference_value
distance_from_reference
divergence_state
persistence_bars
bars_since_event
warmup_complete
available
availability_reason
quality_score
point_in_time_safe
source_bar_close_time
available_time
decision_time
formula_hash
implementation_version
```

Allowed `state` values include:

```text
RISING
FALLING
FLAT
ACCELERATING
DECELERATING
OVERBOUGHT
OVERSOLD
TRENDING
CHOPPY
COMPRESSED
EXPANDING
BULLISH_CROSS
BEARISH_CROSS
BULLISH_DIVERGENCE
BEARISH_DIVERGENCE
NO_EVENT
UNAVAILABLE
FAILED
```

The registry must support multiple outputs from one indicator. For example,
MACD line, signal line, histogram, crossover state, slope, and bars since cross
are separate outputs linked to one implementation.

## 23. Pattern and Market-Structure Taxonomy

The taxonomy must be versioned and extendable. A detector may emit zero, one,
or multiple concurrent patterns.

### 23.1 Candle Anatomy and Multi-Candle Patterns

```text
body/range strength
upper/lower wick rejection
close-location value
inside bar
outside bar
engulfing
pin bar
doji/indecision
marubozu/trend candle
morning/evening reversal sequence
three-bar continuation/reversal
wick cluster
failed follow-through
absorption-like candle
exhaustion-like candle
abnormal print
```

### 23.2 Price and Swing Structure

```text
HH/HL uptrend
LH/LL downtrend
range/balance
compression
expansion
break of structure
change of character
failed break
liquidity sweep
retest
spring/upthrust
double/triple top or bottom
head and shoulders/inverse
rounded base/top
flag/pennant/wedge/triangle/channel
```

### 23.3 Harmonic and Geometric Patterns

```text
Gartley
Bat
Butterfly
Crab
Deep Crab
Cypher
AB=CD
Three Drives
Fibonacci retracement/extension confluence
zigzag swing geometry
```

Each geometric pattern must expose:

```text
anchor timestamps and prices
ratio measurements
ratio tolerances
completion zone
invalidation zone
forming/confirmed/failed/expired state
detector version
```

### 23.4 Level Interaction

```text
VWAP hold/reclaim/rejection/cross
anchored VWAP interaction
CPR and pivot interaction
PDH/PDL and PWH/PWL interaction
opening range/ORB interaction
volume-profile POC/VAH/VAL interaction
supply/demand zone interaction
support/resistance respect
trendline respect, break, false break, and retest
gap edge and gap-fill interaction
circuit-limit proximity
```

`trendline_respect_score` must be calculated from objective evidence such as
touch count, normalized touch error, close-through count, slope stability,
recency, volume response, and post-touch excursion. The system must not call a
line "respected" merely because a line can be visually drawn.

### 23.5 Flow and Participation

```text
volume expansion/contraction
relative volume
MFI/CMF accumulation-distribution context
effort versus result
absorption proxy
exhaustion proxy
delta/volume-profile proxy
liquidity vacuum
opening auction imbalance proxy
closing drive
```

### 23.6 Universal Indicator Activity Discovery

The system must find repeated activity and outcome relationships for every
available indicator, detector, algorithm, pattern engine, and chart structure
source. This includes ordinary numeric indicators and visual/structural
algorithms.

Required coverage:

```text
trendline detectors
curve pattern detectors
harmonic pattern detectors
Fibonacci retracement/extension detectors
Elliott wave detectors
candle pattern detectors
inside/outside candle detectors
VWAP and anchored VWAP engines
Bollinger/Keltner/band engines
CPR, pivot, ORB, and volume-profile engines
support/resistance detectors
market-structure engines
liquidity/sweep/order-block/FVG engines
momentum oscillators
volume and money-flow indicators
ML/probability-grid indicators
Kronos forecast path features
```

For each source, store and analyze:

```text
activity_present
activity_type
activity_direction
activity_strength
activity_start_time
activity_end_time
activity_duration_bars
activity_price_zone
activity_timeframe
activity_parameters
activity_quality
activity_confirmation_state
activity_invalidation_state
bars_before_outcome
outcome_distribution_after_activity
```

The engine must answer:

```text
When this indicator/pattern/algorithm became active before, what happened next?
When this source disagreed with price, which side usually won?
When this source fired early versus late, did outcome quality change?
When this source repeated across timeframes, did reliability improve or weaken?
When this source gave the opposite of the final move, is it a reciprocal signal?
```

No structural detector is allowed to be treated as merely decorative. If it is
displayed on the chart, it must have a point-in-time activity record, quality
score, lineage, and outcome history before it contributes to similarity or
decision evidence.

### 23.7 Candle Body, Wick, No-Wick, and Neighbor-Candle Effect Memory

Candle anatomy must be treated as a first-class pattern source, not just a
helper feature. The engine must identify and compare exact body/wick behavior
and how nearby candles change the meaning of the current candle.

Required candle anatomy features:

```text
body_size
body_pct_of_range
upper_wick_size
lower_wick_size
upper_wick_pct_of_range
lower_wick_pct_of_range
upper_wick_to_body_ratio
lower_wick_to_body_ratio
total_wick_to_body_ratio
close_location_value
open_location_value
no_upper_wick
no_lower_wick
no_wick_full_body
large_body_no_wick
small_body_large_wick
same_direction_body_sequence
opposite_direction_body_sequence
body_expansion_sequence
body_compression_sequence
wick_expansion_sequence
wick_compression_sequence
wick_cluster_direction
nearby_candle_confirmation
nearby_candle_rejection
nearby_candle_absorption
nearby_candle_exhaustion
```

The engine must compare candle behavior over configurable local windows:

```text
previous_1_candle
previous_2_candles
previous_3_candles
previous_5_candles
next_outcome_window_for_historical_labels_only
```

Decision-time features may use only current and prior candles. Future candles
are used only for historical outcome labels after the decision timestamp.

Examples the engine must support:

```text
large no-wick bullish candle followed by tiny upper-wick candle
large no-wick bullish candle followed by immediate bearish engulfing
long lower wick near VWAP followed by higher close
long upper wick near resistance followed by failed continuation
small body with very high volume followed by reversal
three candles with shrinking bodies before expansion
wick cluster at pivot resistance before breakdown
```

Similarity must include both single-candle anatomy and neighbor-candle context:

```text
candle_shape_similarity
wick_ratio_similarity
no_wick_match
body_sequence_similarity
nearby_rejection_similarity
nearby_confirmation_similarity
local_candle_rhythm_similarity
```

The output must explain how wick/body structure affected the trend:

```text
The current candle has no lower wick and closed in the top 8% of its range,
but the next historical analog condition required follow-through within two
bars. Similar cases without follow-through reversed 58% of the time.
```

### 23.7A Prior-Candle Influence and Current-Candle Reason Chain

The engine must compare previous candle data against the current candle and
estimate whether earlier candle anatomy, indicator values, signals, or pattern
states contributed to the current candle's behavior.

This is not a guaranteed causal claim. It is a point-in-time, evidence-based
reason-chain analysis:

```text
previous candle/body ratio -> current candle expansion or rejection
previous upper wick cluster -> current bearish follow-through
previous lower wick rejection -> current bullish continuation
previous no-wick drive candle -> current pullback or exhaustion
previous volume spike with small body -> current absorption/reversal
previous indicator signal -> current candle breakout/failure
previous VWAP reclaim -> current trend continuation
previous harmonic/Fib/trendline interaction -> current rejection or acceleration
```

Required fields:

```text
prior_candle_window
prior_body_ratio_sequence
prior_wick_ratio_sequence
prior_no_wick_sequence
prior_close_location_sequence
prior_indicator_value_sequence
prior_indicator_signal_sequence
prior_pattern_state_sequence
prior_level_interaction_sequence
current_candle_response
current_candle_response_strength
influence_hypothesis
influence_confidence
historical_support_count
historical_counterexample_count
similar_prior_to_current_cases
```

The engine must answer:

```text
Did the previous candle's body/wick structure usually lead to this current candle type?
Did earlier indicator signals appear before the current candle expansion/reversal?
Did a prior buy/sell signal act as a true confirmation or a reciprocal warning?
Did the previous candle near VWAP/BB/CPR/pivot/trendline cause the current reaction?
How often did this prior-to-current sequence continue, reverse, or become range-bound?
```

Example explanation:

```text
The current bearish candle is not isolated. The previous three candles showed
upper-wick rejection near R1, shrinking bodies, and falling MFI while RSI stayed
high. In 46 similar prior-to-current sequences, the next move continued lower
57% of the time and became range-bound 28% of the time.
```

Safety rule:

```python
assert prior_influence_features.use_only_candles_before_or_at_decision_time
assert influence_hypothesis.is_labeled_as_evidence_not_proven_causality
assert counterexamples_are_displayed_with_supporting_cases
```

### 23.8 Visual Price Design Recognition Engine and Market Shape Grammar

Create:

```text
apps/api/app/behavior/visual_shape_engine.py
apps/api/app/behavior/pattern_grammar.py
apps/api/app/behavior/design_similarity.py
```

The visual engine tokenizes intraday price paths into deterministic shape
terms before continuous indicator similarity runs. It must detect:

```text
SHAPE_U_REVERSAL
SHAPE_INV_U_REJECTION
SHAPE_W_RANGE_STRUCTURE
SHAPE_M_REJECTION_STRUCTURE
SHAPE_SUDDEN_REVERSE_DRIVE
SHAPE_PULLBACK_CONTINUATION
SHAPE_GAP_UP_FADE
SHAPE_GAP_DOWN_RECOVERY
SHAPE_STAIR_STEP_TREND
SHAPE_SLOW_GRIND_TREND
SHAPE_COMPRESSION_TRIANGLE
SHAPE_RANGE_BOX
SHAPE_LIQUIDITY_SWEEP_REVERSAL
SHAPE_MORNING_FAKE_AFTERNOON_REVERSE
SHAPE_LUNCH_COMPRESSION_BREAKOUT
```

Output contract:

```text
VisualDesignRecognitionResult
design_shape_id
design_confidence
design_completion_time
anchor_candles
grammar_tokens
shape_start_time
shape_end_time
point_in_time_safe
similar_shape_count
historical_outcome_distribution
```

Grammar examples:

```text
BULLISH_RETEST_DRIVE := ANCHOR(long_green_candle) -> PULLBACK(small_descending_bodies) -> CONSOLIDATION(inside_candle) -> TRIGGER(breakout)
SWEEP_AND_DESTROY    := EXPANSE(liquidity_sweep) -> REJECTION(upper_wick_cluster) -> FAILURE(vwap_loss) -> TARGET(reversal)
FAILED_BREAK_FADE    := GAP(gap_up) -> STALL(range_box) -> TRAP(failed_high_break) -> EXECUTE(fade)
COMPRESSED_EXPANSION := SQUEEZE(compression) -> SPIKE(volume_spike) -> TRAP(fake_breakout) -> REVERSE(reversal)
```

Design similarity:

```text
Design_Similarity =
    0.30 * Shape_DTW
  + 0.30 * Grammar_Token_Match
  + 0.20 * Distance_Vector_Proximity
  + 0.20 * Session_Phase_Match
```

All weights are initial and must be walk-forward calibrated.

### 23.9 Sequential Signal Memory and Timing Window Engine

Create:

```text
apps/api/app/behavior/sequential_signal_memory.py
apps/api/app/behavior/signal_timing_window.py
```

Indicator confluence does not require every signal on the same candle. The
engine must store ordered signal sequences across a configurable window.

Example:

```text
Candle N-3: RSI bullish trigger
Candle N-2: MACD cross
Candle N-1: VWAP reclaim
Candle N: inside-bar breakout
```

Contract:

```text
SequentialSignalPattern
sequence_id
sequence_hash
ordered_indicators
ordered_states
candle_offsets
max_candle_span
completion_time
expiry_time
same_candle_required=false
historical_occurrence_count
historical_outcome_distribution
false_agreement_rate
point_in_time_safe
```

Rules:

```text
ordered_step_matching_required
max_candle_span_default = 5
expired_sequences_reset_to_neutral
same indicators in different order are different sequences
signals after outcome are never part of the sequence
```

### 23.10 Reciprocal Signal and False Agreement Detectors

Create:

```text
apps/api/app/behavior/reciprocal_signal_detector.py
apps/api/app/behavior/false_agreement_detector.py
```

The Reciprocal Signal Detector identifies indicators whose nominal bullish
signals repeatedly precede bearish outcomes, or nominal bearish signals
repeatedly precede bullish outcomes, for a specific symbol/timeframe/session.

Contract:

```text
ReciprocalSignalRecord
indicator_id
nominal_direction
observed_outcome_direction
symbol
timeframe
session_phase
regime
sample_count
inverse_outcome_ratio
confidence_interval
oos_stability
action = OBSERVE | WARN | BLOCK_CONFIDENCE
```

The False Agreement Detector inspects cases where many independent indicator
families agree but history says the setup usually fails.

Contract:

```text
FalseAgreementRecord
agreement_direction
agreeing_families
agreeing_indicators
conflicting_context
historical_failure_rate
independent_sample_count
nearest_resistance_or_support
recommended_action = WARN | FAKEOUT_WARNING | NO_TRADE
```

Rule:

```text
if independent bullish agreement >= 4 families
and historical bearish/failure rate >= 0.60
and evidence_count >= minimum_sample_size:
    downgrade to FAKEOUT_WARNING or NO_TRADE
```

### 23.11 Indicator Value Confluence, Band Distance, and Value Cluster Engines

Create:

```text
apps/api/app/behavior/confluence_engine.py
apps/api/app/behavior/band_level_distance.py
apps/api/app/behavior/value_cluster_engine.py
```

The engine must form signatures from exact values, band tier, distance,
state, level proximity, pattern context, timeframe, and session.

Required distance fields:

```text
distance_to_vwap_band_1
distance_to_vwap_band_2
distance_to_vwap_band_3
distance_to_bb_upper_1
distance_to_bb_upper_2
distance_to_bb_upper_3
distance_to_bb_lower_1
distance_to_bb_lower_2
distance_to_bb_lower_3
distance_to_keltner_upper
distance_to_keltner_lower
distance_to_pivot_resistance
distance_to_pivot_support
distance_to_daily_resistance
distance_to_daily_support
distance_to_cpr_top
distance_to_cpr_bottom
cpr_width_percentile
inside_candle_height_pct
distance_to_fib_level
distance_to_harmonic_completion_zone
distance_to_trendline
```

Repeated value cluster output:

```text
RepeatedValueCluster
feature_ids
value_ranges
symbol
timeframe
session_phase
regime
outcome_distribution
sample_count
independent_sample_count
confidence_interval
multiple_testing_adjustment
walk_forward_stability
```

### 23.12 Per-Timeframe Pattern Outcome Table

Store pattern outcomes separately by timeframe and horizon. A 1m pattern edge
must not be mixed with a 15m or 1H outcome.

Table:

```sql
CREATE TABLE per_timeframe_pattern_outcomes (
    pattern_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    horizon_bars INTEGER NOT NULL,
    regime_at_trigger TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    hit_target_first INTEGER NOT NULL,
    hit_stop_first INTEGER NOT NULL,
    ambiguous_count INTEGER NOT NULL,
    no_fill_count INTEGER NOT NULL,
    avg_mfe_atr REAL NOT NULL,
    avg_mae_atr REAL NOT NULL,
    net_expectancy_after_costs REAL NOT NULL,
    model_version TEXT NOT NULL,
    PRIMARY KEY (pattern_id, symbol, timeframe, horizon_bars, regime_at_trigger)
);
```

## 24. Multi-Timeframe State and Conflict Engine

For every decision, create a matrix for:

```text
1m, 3m, 5m, 15m, 1H, daily, weekly
```

Each timeframe must include:

```text
bar_close_time
bar_completeness
market_state
trend_state
momentum_state
volatility_state
volume_state
level_context
active_patterns
indicator_family_scores
quality_score
confidence
```

The engine must identify:

```text
full alignment
lower-timeframe pullback inside higher-timeframe trend
lower-timeframe breakout into higher-timeframe resistance
higher-timeframe reversal with lower-timeframe continuation lag
timeframe compression conflict
timeframe data unavailable
```

No unfinished higher-timeframe candle may be treated as confirmed. A developing
bar may be displayed visually with a `DEVELOPING_NOT_DECISION_SAFE` label but
cannot enter historical matching or calibrated probability.

### 24.1 Realtime Regime Shift Detector

Create:

```text
apps/api/app/behavior/regime_shift_detector.py
```

Triggers:

```text
1H ATR > 3 standard deviations above its 20-day mean
intraday realized volatility > 99th percentile of recent comparable sessions
index/sector drawdown exceeds configured shock threshold
volume spike + spread expansion + failed liquidity score
news/event shock flag when available
```

Actions:

```text
quarantine WARM memory
prefer COLD crisis archetypes
block high-confidence continuation claims
force recalibration queue
emit REGIME_SHIFT_WARNING
require fresh evidence before re-enabling WARM memory
```

The detector is research/paper-simulation safety infrastructure. It does not
route orders.

## 25. Time, Session, Calendar, and Cross-Market Memory

Memory keys must support:

```text
exact minute bucket
session segment
minutes since open
minutes to close
day of week
week of month
monthly/weekly expiry
first/last trading day
post-holiday session
earnings/results day
major macro-event day
special trading session
market regime
gap class
overnight global context
```

The default Indian cash-market segments are configurable, not hard-coded:

```text
09:15-09:30 opening auction reaction
09:30-10:15 opening confirmation
10:15-11:30 morning continuation/fade
11:30-13:30 midday/lunch behavior
13:30-14:30 afternoon transition
14:30-15:15 closing drive
15:15-15:30 square-off/closing noise
```

Cross-market context may include, when point-in-time data is licensed and
available:

```text
NIFTY/BANKNIFTY/sector index
GIFT Nifty
Nikkei/Hang Seng/Asian indices
DXY
major FX pairs
Indian and US yields
oil
gold
S&P 500/Nasdaq/Dow prior close and futures
volatility indices
```

Missing cross-market data must reduce context coverage. It must never be
silently interpreted as neutral.

## 26. Similarity and Correlation Research Engine

The engine must support four different questions and must not mix their results:

1. **Nearest analog retrieval:** Which prior states look most like now?
2. **Conditional outcome analysis:** What happened after a declared condition?
3. **Association discovery:** Which feature combinations are associated with an
   outcome?
4. **Causal research:** Does a relationship survive causal assumptions and
   refutation tests?

### 26.1 Mixed-Feature Similarity

Similarity must combine:

```text
continuous distances
ordinal state agreement
categorical pattern agreement
sparse event agreement
path/shape similarity
time/session compatibility
level-relative distances
availability overlap
```

No global cosine score alone is sufficient. The implementation must support:

```text
robust-scaled Euclidean or Mahalanobis distance
Gower distance for mixed data
DTW or shape-based distance for paths
Jaccard distance for sparse events
family-level weighted aggregation
learned metric only after walk-forward validation
```

### 26.2 Value-Band Discovery

For indicators such as RSI, MFI, ADX, MACD, ATR, or custom outputs, discover
historically stable value bands without hand-picking a profitable interval from
the evaluation data.

Return:

```text
feature_id
candidate_band
sample_count
independent_sample_count
outcome_distribution
confidence_interval
regime_stability
recent_stability
multiple_testing_adjustment
walk_forward_result
```

### 26.3 Combination Discovery

The engine may investigate combinations such as:

```text
13:00 session
+ 3m choppy state
+ RSI within stock-specific range
+ MFI weakening
+ harmonic pattern forming
+ trendline respect low
+ 15m at resistance
```

It must also report whether each condition adds incremental information. Adding
more conditions must not automatically increase confidence.

Controls:

```text
minimum evidence
maximum rule depth
cross-validation
false-discovery-rate correction
bootstrap confidence intervals
stability across folds
recent-versus-old comparison
regime stratification
holdout confirmation
```

### 26.4 Match Explanation

Every analog must show:

```text
matched date and timestamp
symbol and timeframe
overall similarity
family-level similarities
matched values and tolerances
matched states and patterns
important mismatches
missing features
context differences
outcome path
MFE/MAE
target/stop ordering
net result after costs
source snapshot and replay link
```

## 27. Stock DNA and Adaptive Memory

Stock DNA is not one static profile. It is a versioned collection of conditional
behavior memories:

```text
session personality
day-of-week behavior
gap behavior
level respect
trendline respect
VWAP behavior
breakout/fakeout tendency
retest behavior
volatility response
volume response
event-day behavior
regime behavior
time-to-resolution
best/worst trading windows
failure archetypes
indicator value-band reliability
pattern reliability
```

Memory tiers:

```text
HOT     recent sessions and live replay cache
WARM    current-regime behavior
COLD    compressed long-history archetypes
ARCHIVE immutable snapshots and reproducible outcomes
```

Memory updates must be blocked or quarantined for:

```text
bad data
corporate-action contamination
abnormal print
manipulated-looking/illiquid behavior
unresolved outcome
OOD regime
model drift
insufficient provenance
```

Time decay must be configurable by feature family and regime. Old crisis
archetypes must not disappear merely because they are old; they move to
archetype memory instead of receiving ordinary recency weighting.

### 27.1 Memory Poisoning, OOD, and Drift Detection

Create:

```text
apps/api/app/behavior/memory_poisoning_detector.py
apps/api/app/behavior/ood_detector.py
apps/api/app/behavior/drift_detector.py
```

Memory poisoning triggers:

```text
outcome_distribution_changes_more_than_2_sigma_in_7_days
same_direction_outcomes_exceed_80_percent_in_20_sample_window
abnormal_print_cluster_detected
corporate_action_date_within_window
halt_or_circuit_event_within_window
manual_data_quality_flag
```

Actions:

```text
quarantine_period
recompute_dna_without_suspect_window
flag_human_review
preserve immutable raw data
write decision_audit_log
```

OOD detection:

```text
primary_method: Mahalanobis distance from training distribution
secondary_methods: isolation forest, autoencoder reconstruction error, local density score
threshold: above 95th percentile of historical OOD scores
action: block confidence, emit OOD warning, reduce similarity weight to 0.5 or zero by family
```

Drift detection:

```text
primary_method: population_stability_index
threshold: PSI > 0.25
secondary_method: Kolmogorov-Smirnov p < 0.01
feature_mean_shift_threshold: > 2 sigma
action: quarantine memory, trigger rebuild plan, notify operator, demote stale clusters
```

New detectors enter these states:

```text
observation_only: visible, not weighted
beta: visible and tracked, not used for calibrated probabilities
validated: weighted only after 100+ labeled outcomes and stable OOS behavior
```

## 28. Recommendation and Reasoning Contract

The engine may emit:

```text
NO_TRADE
WAIT
WATCH_ONLY
BUY_BREAKOUT_RESEARCH
SELL_BREAKDOWN_RESEARCH
BUY_RETEST_RESEARCH
SELL_RETEST_RESEARCH
BUY_FADE_RESEARCH
SELL_FADE_RESEARCH
FAKEOUT_WARNING
AVOID_CHOP
DATA_BLOCKED
LOW_EVIDENCE
CONFLICT
```

Every result must separate:

```text
observed_facts
derived_states
historical_evidence
forecast_evidence
supporting_reasons
contradicting_reasons
safety_blocks
required_confirmations
invalidation_conditions
uncertainties
```

Required recommendation fields:

```text
decision
decision_time
direction
entry_status
best_entry_zone
entry_trigger
invalidation_level
stop_loss
target_1
target_2
target_3
expected_mfe
expected_mae
expected_resolution_time
risk_reward_after_costs
position_size_research_estimate
evidence_count
evidence_quality
calibrated_probability
probability_interval
uncertainty_score
no_trade_reasons
reason_tree
```

Price levels are research estimates until an external, separately governed
paper/live execution system validates tick size, quantity, margin, liquidity,
spread, and current order-book state.

## 29. Human-Readable Explanation Specification

The explanation engine must generate three synchronized views:

1. **Plain-language summary** for rapid understanding.
2. **Structured reason tree** for audit and machine consumption.
3. **Evidence table** with exact values, timestamps, formulas, and source links.

Example format only:

```text
At 13:00 IST, RELIANCE is classified as RANGE/CHOPPY on 3m.

Observed:
- RSI(14) = 47.2 and has remained within 44-52 for 11 bars.
- MFI(14) = 42.8 and is falling.
- ADX(14) = 16.9, below this stock's 3m trend threshold.
- Price crossed VWAP four times during the current segment.
- Trendline respect score = 0.24 because two recent closes broke through it.
- A bearish harmonic candidate is FORMING, not confirmed.

Historical evidence:
- 37 independent prior matches after filtering.
- 62% remained range-bound for the next 12 bars.
- 21% broke upward and 17% broke downward.
- Median MFE = 0.31 ATR; median MAE = 0.28 ATR.

Conflicts:
- 15m structure is mildly bullish.
- Current volume quality is below the matched-history median.

Conclusion:
- WAIT / AVOID CHOP.
- Promote only after a closed 3m breakout, rising participation, and successful
  VWAP retest.
```

The system must use `insufficient evidence`, `unavailable`, or `not confirmed`
instead of inventing a value or pattern.

## 30. Complete Frontend Workspace

The production frontend must provide a dense, resizable workspace rather than a
single fixed chart or a collection of decorative cards.

### 30.1 Global Controls

```text
symbol/exchange selector
date and decision-time selector
live/replay cursor
timeframe and confirmation-timeframe selector
session/event/regime filters
snapshot selector
data mode watermark
data quality status
kill switch status
Kronos availability
layout save/reset
```

### 30.2 Chart Workbench

Required chart capabilities:

```text
candlestick/OHLC display
volume pane
indicator pane creation/removal
multi-axis scaling
overlay selection from registry
pattern and candle annotations
support/resistance and supply/demand zones
VWAP/anchored VWAP/CPR/pivots/ORB/value profile
trendline anchors and respect evidence
harmonic anchors and ratio labels
entry/stop/target/invalidation overlays
historical analog ghost paths
Kronos forecast fan/ghost path
replay play/pause/step/seek/speed
crosshair synchronized across panes/timeframes
selected-candle inspector
snapshot/export evidence link
```

The chart must never silently draw unavailable indicators. Each layer displays:

```text
status
parameters
timeframe
last value
last update
quality
source
```

### 30.3 Required Analysis Panels

```text
Current Market State
Multi-Timeframe Matrix
Candle Anatomy
Indicator Matrix
Indicator Detail and History
Indicator Family Agreement
Session Rhythm
Exact-Time Memory
Day-of-Week/Calendar Memory
Stock DNA
Support/Resistance Memory
Trendline Respect
VWAP/Value-Area Context
Harmonic/Geometry Inspector
Flow and Participation
Gap Context
Relative Strength
Index/Sector/Cross-Market Context
Market Regime
News/Event Context
Similar Historical Cases
Analog Detail and Replay
Outcome Distribution
Failure Pattern Library
Confidence Calibration
Model Drift/OOD
Data Quality/Lookahead Guard
Execution Cost and Liquidity
Risk/Position/Portfolio Heat
Trade Lifecycle
Reason Tree
Kronos Forecast
Twin Comparison
Benchmark/Walk-Forward Report
Audit and Lineage
```

### 30.3A Panel Organization, Lazy Loading, and Streaming

The frontend must not render all analysis panels synchronously. Panels are
organized into five workspaces:

```text
Chart_Primary:
  candlestick, volume, primary overlays, current state, crosshair

Indicators_Evidence:
  indicator matrix, indicator detail, family agreement, candle anatomy,
  band/level distances, value clusters

Memory_Research:
  stock DNA, similar cases, analog replay, visual shape, sequential signals,
  pattern memory, session rhythm

Risk_Execution:
  risk sizing, execution cost, trade lifecycle, portfolio heat, paper fills

Forecast_Twin:
  Kronos forecast, Twin comparison, confidence calibration, conflict explorer
```

Panel priority:

```text
priority 1 = always visible or loaded on snapshot open
priority 2 = collapsible/sidebar and lazy-loaded
priority 3 = modal/drilldown and loaded only on request
```

Each panel contract must include:

```text
panel_group
panel_priority
data_loading_mode = initial | lazy | stream | drilldown
worker_required
virtualized_list_required
stream_endpoint
last_successful_snapshot_id
```

Realtime panel updates must use Server-Sent Events or WebSocket streams for
high-frequency state changes instead of REST polling loops. Large tables must
be virtualized. Indicator calculations in the browser, if any, must run in Web
Workers and remain advisory only; backend contracts remain the source of truth.

### 30.3B Responsive Layout, Shortcuts, Exports, Alerts, and Accessibility

Responsive behavior:

```text
desktop: full five-workspace layout with resizable panels
tablet: three-workspace stacked layout with chart-first navigation
mobile: single-column chart-first layout with swipe/timeframe navigation
```

Keyboard shortcuts:

```text
Space: play/pause replay
Left/Right: step replay backward/forward
1-7: select timeframe
S: symbol search
C: crosshair toggle
R: run current analysis
F: focus similar-case search
Esc: close modal or cancel pending panel request
```

Exports:

```text
CSV: indicator values, analog matches, outcome labels, confluence records
PNG: chart screenshot with overlays and mode watermark
PDF: full analysis report with reason tree, evidence, limitations, and hashes
JSON: machine-readable immutable evidence bundle
```

Alerts:

```text
pattern_detected
high_similarity_analog_found
false_agreement_warning
reciprocal_signal_warning
regime_shift_warning
stale_data_freeze
kronos_behavior_conflict
data_quality_block
```

Alert delivery in early milestones is in-app/WebSocket only. Email/SMS or
external notification channels are reserved until user permissions, throttling,
audit logging, and abuse-prevention rules are defined.

Theme and accessibility:

```text
dark_theme
light_theme
high_contrast_theme
color_blind_safe_palette
deuteranopia_safe_chart_colors
protanopia_safe_chart_colors
non_color_shape_markers_for_buy_sell_warning_states
```

Chart evidence must not rely on color alone. Critical states such as
`NO_TRADE`, `FAKEOUT_WARNING`, stale data, or low evidence require text labels
and shape/icon markers.

### 30.4 Indicator Matrix Columns

The matrix must support filtering, sorting, grouping, pinning, and exporting:

```text
indicator
family
timeframe
parameters
current value
unit
state
direction
slope
percentile
signal
signal age
quality
availability
historical matched band
match contribution
redundancy cluster
formula version
```

### 30.5 Similar Cases Table

```text
date/time
session
regime
similarity
independent evidence flag
matched conditions
mismatched conditions
next move
MFE/MAE
target/stop result
time to resolution
net result
replay button
```

### 30.6 Empty, Loading, and Failure States

- No data: explain which input is required.
- Warm-up incomplete: show required and available bars.
- Indicator failure: isolate the failed indicator and preserve other panels.
- Insufficient analogs: show match count and relaxed-filter preview, but do not
  promote the relaxed result to calibrated evidence.
- Backend/Kronos offline: remain usable in Behavior-only safe mode.
- Snapshot mismatch: block Twin comparison and show both hashes.
- Stale data: freeze recommendation and mark it stale.

## 31. Frontend-to-Backend Panel Contract

Every panel must declare:

```text
panel_id
display_name
contract_name
endpoint
required_fields
optional_fields
required_capabilities
refresh_policy
maximum_staleness
loading_state
empty_state
error_state
offline_fallback
mode_permissions
audit_event
```

No frontend panel may derive a trading probability independently from raw API
fields. Calibrated probabilities and safety decisions must come from versioned
backend contracts.

## 32. Extended Storage Model

In addition to `feature_snapshots`, add:

```text
indicator_definitions
indicator_observations
multitimeframe_snapshots
market_state_records
pattern_detections
pattern_anchors
level_definitions
level_interactions
session_context_records
calendar_context_records
cross_market_context_records
analog_search_runs
analog_matches
conditional_research_runs
outcome_labels
stock_dna_profiles
stock_dna_components
memory_quarantine_records
calibration_records
drift_events
ood_events
recommendation_records
reason_tree_nodes
kronos_forecasts
twin_comparisons
chart_annotations
decision_audit_logs
visual_design_detections
sequential_signal_patterns
signal_timing_windows
reciprocal_signal_records
false_agreement_records
indicator_value_confluence_records
band_level_distance_snapshots
per_timeframe_pattern_outcomes
market_shape_grammar_rules
repeated_value_clusters
design_similarity_scores
```

Common indexes:

```text
(symbol, decision_time_ns)
(symbol, timeframe, decision_time_ns)
(indicator_id, timeframe, decision_time_ns)
(symbol, session_phase, day_of_week)
(pattern_type, pattern_state, decision_time_ns)
(snapshot_id)
(source_snapshot_hash)
(run_id)
(model_version, feature_version, data_version)
```

High-volume observations belong in Parquet/Arrow-compatible storage. Relational
storage holds identity, metadata, lineage, workflow state, and frequently
queried summaries.

Retention:

```text
raw immutable source snapshots     archive indefinitely where licensing allows
derived feature partitions         versioned; superseded versions retained
live transient cache               bounded by memory and replay requirements
audit/recommendation records       immutable
failed temporary build artifacts   purge after 7 days
```

## 33. Extended APIs

Add versioned endpoints:

```text
POST /api/v1/behavior/investigate
GET  /api/v1/behavior/investigations/{run_id}
GET  /api/v1/behavior/investigations/{run_id}/status
POST /api/v1/behavior/investigations/{run_id}/cancel

GET  /api/v1/behavior/snapshots/{snapshot_id}/state
GET  /api/v1/behavior/snapshots/{snapshot_id}/timeframes
GET  /api/v1/behavior/snapshots/{snapshot_id}/indicators
GET  /api/v1/behavior/snapshots/{snapshot_id}/patterns
GET  /api/v1/behavior/snapshots/{snapshot_id}/levels
GET  /api/v1/behavior/snapshots/{snapshot_id}/context
GET  /api/v1/behavior/snapshots/{snapshot_id}/explanation

POST /api/v1/behavior/analogs/query
GET  /api/v1/behavior/analogs/{run_id}/matches
GET  /api/v1/behavior/analogs/{run_id}/matches/{match_id}
GET  /api/v1/behavior/analogs/{run_id}/matches/{match_id}/replay

POST /api/v1/behavior/research/conditional
GET  /api/v1/behavior/research/conditional/{run_id}

GET  /api/v1/behavior/stocks/{symbol}/dna
GET  /api/v1/behavior/stocks/{symbol}/session-memory
GET  /api/v1/behavior/stocks/{symbol}/level-memory
GET  /api/v1/behavior/stocks/{symbol}/pattern-memory

GET  /api/v1/behavior/chart/{snapshot_id}
GET  /api/v1/behavior/chart/{snapshot_id}/annotations
GET  /api/v1/behavior/chart/{snapshot_id}/indicator/{indicator_id}
POST /api/v1/behavior/visual-design/recognize
POST /api/v1/behavior/grammar/parse-shape
GET  /api/v1/behavior/shape-grammar/rules
POST /api/v1/behavior/sequential-signals/search
POST /api/v1/behavior/signal-timing/analyze
POST /api/v1/behavior/reciprocal-signals/detect
POST /api/v1/behavior/false-agreement/detect
POST /api/v1/behavior/confluence/analyze
GET  /api/v1/behavior/bands/distances
POST /api/v1/behavior/value-clusters/discover
GET  /api/v1/behavior/patterns/by-timeframe
POST /api/v1/behavior/design-similarity/score
```

`POST /investigate` accepts:

```text
symbol
exchange
decision_time
primary_timeframe
confirmation_timeframes
requested_indicator_ids or families
requested_pattern_types
analog_horizons
target/stop policy
session/calendar filters
market-context requirements
maximum_matches
explanation_detail
```

All long-running calls return `202`, `run_id`, progress, stage, ETA range,
resumability, cancellation support, and evidence hash.

## 34. Configuration and Add-On Architecture

Future indicators, pattern detectors, markets, models, and panels must be added
through registries rather than central conditional blocks.

Plugin contracts:

```text
IndicatorPlugin
PatternDetectorPlugin
ContextProviderPlugin
OutcomePolicyPlugin
SimilarityMetricPlugin
ForecastProviderPlugin
ChartLayerPlugin
ExplanationContributorPlugin
```

Every plugin must declare:

```text
plugin_id
semantic_version
inputs
outputs
minimum_history
supported_timeframes
point_in_time_guarantee
determinism guarantee
resource budget
failure isolation
tests
capability status
```

An add-on cannot become `beta` until deterministic replay, point-in-time,
lineage, failure isolation, and output-contract tests pass.

For v0.60 through v0.68, prefer a static YAML/Python registry for the 94
baseline indicators. The generic plugin architecture is reserved for v0.70+
unless an add-on cannot be represented safely in the static registry.

Cross-market providers are optional context providers in early milestones.
Missing cross-market context must reduce coverage and be visible, but it must
not block core Behavior Engine operation unless the user explicitly requests a
cross-market-dependent analysis.

## 35. Pipeline and Concurrency Model

```text
1. Validate request and permissions
2. Resolve immutable source snapshot
3. Validate data quality and corporate actions
4. Build closed bars for requested timeframes
5. Compute indicators by dependency DAG
6. Detect structures, patterns, and levels
7. Build session/calendar/cross-market context
8. Persist feature snapshot and lineage
9. Run hard-context analog filter
10. Run similarity and conditional research
11. Label/retrieve outcomes
12. Calculate evidence quality and calibration
13. Apply risk, liquidity, drift, OOD, and no-trade gates
14. Optionally request Kronos on identical snapshot
15. Run Twin comparison
16. Build reason tree and chart annotations
17. Persist immutable recommendation/audit record
18. Stream panel-ready result
```

Realtime research/paper-simulation flow:

```text
Live/Replay 1m feed
-> immutable snapshot
-> data-quality + PIT guard
-> closed 1m/3m/5m/15m/1H/D/W bars
-> 94 indicator runtime
-> visual shape + sequential signal memory
-> level/band distance engine
-> historical analog search
-> outcome/trust table
-> risk/no-trade gates
-> optional Kronos same-snapshot forecast
-> Twin comparison
-> WAIT / NO_TRADE / FAKEOUT_WARNING / BUY-SELL research candidate
-> chart evidence + immutable audit record
```

Required realtime modules:

```text
RealtimeMarketDataAdapter
ImmutableSnapshotBuilder
ClosedBarRuntime
IndicatorRegistryRuntime
VisualPriceDesignEngine
SequentialSignalMemoryEngine
BandLevelDistanceMemory
FalseAgreementDetector
RealtimeDecisionGate
ChartEvidenceWorkbench
KronosSharedSnapshotService
TwinConflictEngine
PaperModeSimulator
OpenAlgoExternalAdapter
```

`OpenAlgoExternalAdapter` remains disabled for live execution until separate
paper-mode, human-veto, kill-switch, exchange-reconciliation, and approval
gates pass.

Concurrency:

- Parallelize independent indicator families after shared prerequisites exist.
- Serialize operations that mutate the same snapshot identity.
- Deduplicate identical in-flight requests by request hash.
- Use bounded worker pools; never spawn one worker per indicator.
- Cancel descendants when a hard data-quality or lookahead gate fails.
- Kronos runs in an isolated process/service and cannot block the core result.

## 36. Performance Budgets

Initial budgets, subject to measured revision:

```text
cached current snapshot API p95          <= 250 ms
uncached seven-timeframe state p95       <= 2 s
single-symbol analog query p95           <= 3 s
chart initial payload                    <= 2 MB
chart pan/zoom cached response p95       <= 200 ms
frontend interaction main-thread block   <= 50 ms
Kronos timeout                           configurable, default 15 s
Behavior result when Kronos unavailable  must still complete
```

Historical feature builds are asynchronous and report throughput, memory, CPU,
GPU, failed partitions, retries, and estimated completion.

## 37. Error, Degradation, and Retry Rules

```text
invalid OHLC                    reject snapshot
duplicate timestamp             reject or deterministic dedupe by configured rule
missing volume                  disable dependent features; never substitute zero
missing optional context        reduce coverage and confidence
missing required context        block affected conclusion
indicator exception             isolate indicator; emit failure record
feature partition corruption    quarantine and rebuild
analog index unavailable        fall back to bounded exact search or return unavailable
Kronos timeout/OOM              Behavior-only result; no confidence boost
drift/OOD threshold breach      quarantine memory contribution
stale source data               freeze recommendation
snapshot identity mismatch      block Twin
```

Retries:

- Pure deterministic calculations: up to two retries for transient worker
  failures.
- Data downloads: provider-specific exponential backoff with jitter and
  idempotent resume.
- Validation failures: never retry automatically.
- Kronos OOM: one lower-batch retry; then fail closed to Behavior-only.

## 38. Security and Research Safety

- No browser-secret, cookie, token, or hidden-session capture.
- No frontend-held signing secret.
- No direct broker credentials in Trade Vision.
- Narrative, chart, similarity, Kronos, and Twin services cannot create orders.
- Every export includes mode, snapshot ID, expiry, evidence hash, safety gates,
  and human-readable limitations.
- Uploaded files are size-limited, content-validated, stored outside executable
  paths, and assigned immutable hashes.
- Formula/model/plugin changes require version changes and reproducibility tests.

## 39. Extended Test Matrix

Add these tests to the existing `TV-FI-001` through `TV-FI-030` suite:

```text
TV-FI-031 every indicator output exposes value/unit/parameters/timeframe
TV-FI-032 no-event and calculation-failure are distinct
TV-FI-033 indicator percentile uses training history only
TV-FI-034 exact-time memory never includes later timestamps
TV-FI-035 session boundaries follow exchange calendar
TV-FI-036 developing HTF bar cannot confirm a pattern
TV-FI-037 multi-timeframe conflict is explicitly reported
TV-FI-038 trendline respect score uses objective touch/break evidence
TV-FI-039 harmonic anchors and ratios are reproducible
TV-FI-040 forming harmonic cannot be labeled confirmed
TV-FI-041 missing MFI input cannot become neutral MFI
TV-FI-042 missing cross-market context reduces coverage
TV-FI-043 mixed-feature similarity handles unavailable values
TV-FI-044 analog explanation lists matches and mismatches
TV-FI-045 every displayed analog date exists and precedes decision time
TV-FI-046 overlapping analog episodes are not double-counted
TV-FI-047 value-band discovery applies multiple-testing correction
TV-FI-048 added conditions cannot increase confidence without incremental evidence
TV-FI-049 conditional research passes walk-forward holdout
TV-FI-050 unstable condition is marked non-generalizing
TV-FI-051 stock DNA memory is versioned and time-decayed
TV-FI-052 crisis archetypes survive ordinary time decay
TV-FI-053 quarantined memory cannot affect a recommendation
TV-FI-054 chart hides unavailable values and explains why
TV-FI-055 crosshair synchronizes chart panes and timeframes
TV-FI-056 replay cursor reproduces the same visible state hash
TV-FI-057 frontend shows exact indicator values and calculation times
TV-FI-058 frontend shows historical match dates and outcomes
TV-FI-059 frontend distinguishes observed/derived/forecast information
TV-FI-060 stale data freezes the recommendation
TV-FI-061 empty evidence returns LOW_EVIDENCE, not zero probability
TV-FI-062 relaxed analog filters are visibly uncalibrated
TV-FI-063 recommendation contains supporting and contradicting reasons
TV-FI-064 invalidation is tied to measurable price/structure
TV-FI-065 costs can convert apparent positive expectancy to NO_TRADE
TV-FI-066 same request and versions produce identical reason tree
TV-FI-067 plugin failure cannot crash unrelated analysis
TV-FI-068 unvalidated plugin cannot enter beta capability
TV-FI-069 panel contract declares loading/empty/error/offline states
TV-FI-070 no panel calculates an independent trading probability
TV-FI-071 Behavior completes when Kronos times out
TV-FI-072 Twin blocks mismatched decision timestamps
TV-FI-073 exported evidence contains all version and hash fields
TV-FI-074 no narrative or forecast endpoint can route an order
TV-FI-075 exact 13:00 query can be replayed from source data
TV-FI-076 3m choppy classification exposes its threshold evidence
TV-FI-077 RSI/MFI bands expose sample counts and confidence intervals
TV-FI-078 harmonic and trendline evidence may contradict one another
TV-FI-079 user-selected indicator combination is point-in-time validated
TV-FI-080 all required frontend panels are mapped to contracts
TV-FI-081 every displayed structural indicator has activity records and outcome history
TV-FI-082 trendline/curve/harmonic/Fib/Elliott activity can be searched as analog evidence
TV-FI-083 no-wick and wick/body-ratio candle features are computed point-in-time
TV-FI-084 neighbor-candle rhythm changes similarity and is explained in the reason tree
TV-FI-085 every indicator has explicit parameter defaults in registry
TV-FI-086 every indicator implementation is audited for internal lookahead
TV-FI-087 centered moving averages are blocked or converted to trailing equivalents
TV-FI-088 no two analogs are within the configured minimum separation window
TV-FI-089 cross-market context reduces coverage but is never silently neutral
TV-FI-090 sequential signal patterns are point-in-time safe
TV-FI-091 reciprocal signals use only pre-outcome data
TV-FI-092 value confluence supports non-same-candle signals
TV-FI-093 design similarity score is invariant to price-level scaling
TV-FI-094 false agreement detector uses independent historical evidence
TV-FI-095 ANN prefilter returns deterministic candidate IDs for same snapshot/version
TV-FI-096 exact mixed-distance refinement runs only after ANN/hard-context shortlist
TV-FI-097 hub candidates above neighbor-frequency threshold are flagged
TV-FI-098 overnight gap through stop uses executable open price
TV-FI-099 same-bar target/stop checks open price before ambiguity labeling
TV-FI-100 missing expected volume blocks trade-quality conclusion unless whitelisted
TV-FI-101 Kronos raw path is discretized into target/stop/time-exit probabilities before Twin
TV-FI-102 Kronos agreement cannot boost confidence before decorrelation/OOS checks
TV-FI-103 regime shift detector quarantines WARM memory after configured shock trigger
TV-FI-104 OOD score above threshold blocks calibrated confidence
TV-FI-105 PSI drift above threshold quarantines stale memory
TV-FI-106 memory poisoning detector quarantines suspect windows and preserves raw data
TV-FI-107 panel priority/lazy loading prevents synchronous rendering of all panels
TV-FI-108 SSE/WebSocket streaming handles realtime panel updates without REST polling loops
TV-FI-109 paper simulator labels all execution outputs as SIMULATION_ESTIMATE
TV-FI-110 no live broker route is enabled by realtime feed or OpenAlgo adapter milestones
TV-FI-111 prior-candle body/wick sequences are compared to current-candle response
TV-FI-112 prior indicator signals can be linked to current candle behavior without future leakage
TV-FI-113 prior-to-current influence explanations show supporting and counterexample cases
```

## 40. Extended Milestone Order

Continue after v0.68:

### v0.69: Complete Observation Contracts

- Implement `IndicatorObservation`, multi-output indicators, availability,
  percentile, slope, persistence, event age, formula lineage, and API schemas.

### v0.70: Structure and Pattern Registry

- Implement the candle, swing, chart, harmonic, level, trendline, flow, and
  pattern lifecycle contracts.

### v0.71: Exact-Time and Session Memory

- Implement minute/session/day/calendar behavior profiles with exchange-calendar
  boundaries and independent evidence counts.

### v0.72: Multi-Timeframe Conflict Engine

- Implement the seven-timeframe state matrix, developing-bar handling, alignment,
  and conflict explanations.

### v0.73: Complete Analog and Conditional Research

- Implement mixed-distance retrieval, value-band discovery, conditional rules,
  incremental evidence, false-discovery controls, and match explanations.

### v0.74: Adaptive Stock DNA

- Implement versioned DNA components, memory tiers, quarantine, time decay,
  crisis archetypes, and drift response.

### v0.75: Full Chart Evidence Workbench

- Implement selectable registry overlays, synchronized panes, pattern/level
  evidence, analog replay, and visible unavailable/degraded states.

### v0.76: Full Investigation Workspace

- Implement all panel contracts, dense layouts, filters, exact-time inspection,
  similar-case tables, reason trees, audit lineage, and offline states.

### v0.77: Performance and Scale

- Implement dependency-DAG scheduling, bounded concurrency, caching, indexing,
  resumable builds, profiling, and published performance evidence.

### v0.78: Research Validation Release

- Run walk-forward, OOS, calibration, false-discovery, drift, OOD, costs,
  usability, and deterministic replay validation.
- Publish Behavior-only, Kronos-only, and Twin results independently.

### v0.79: Realtime Feed Shell

- Add read-only realtime/replay feed adapter, heartbeat, stale-data freeze, and
  immutable snapshot creation.
- Keep `live_trading_blocked=true`, `broker_credentials_present=false`, and
  `order_routing_enabled=false`.

### v0.80: Paper-Simulation Cockpit

- Add simulated fills, costs, slippage, partial fills, no-fill, and gap-through
  behavior.
- Label every execution output `SIMULATION_ESTIMATE`.

### v0.81: External Adapter Review Gate

- Add OpenAlgo adapter review only as a signed intent-preview boundary.
- No live execution until independent approval, kill switch, human veto,
  exchange reconciliation, and paper-validation gates pass.

## 41. Definition of Done

This plan is complete only when a user can select any supported stock, date,
decision time, and timeframe and receive:

1. A synchronized chart built from the exact immutable snapshot.
2. Exact values and states for every requested validated indicator.
3. Candle, structure, level, trendline, harmonic, flow, session, calendar, and
   market-context evidence.
4. Multi-timeframe agreement and conflict details.
5. Independent historical analogs with real dates and replay links.
6. A feature-by-feature explanation of why each analog matched or differed.
7. Conservative target/stop/time outcomes with costs, ambiguity, and no-fill.
8. Calibrated probabilities only when sample, stability, and OOS gates pass.
9. A plain-language conclusion, reason tree, required confirmations, and exact
   invalidation.
10. Separate Behavior, Kronos, and Twin evidence with identical snapshot proof.
11. Explicit unavailable, stale, low-evidence, drift, OOD, and failure states.
12. No live order capability, broker dependency, or narrative override.

The desired product is therefore not merely an indicator dashboard. It is a
point-in-time, stock-specific, multi-timeframe market behavior investigation
and memory system whose conclusions can always be traced back to data,
calculations, comparable historical episodes, and safety gates.

## 42. Exact Migrated Indicator Preservation Register

The following 94 output groups are the current migration baseline. An
implementation may add new groups or retire a broken group through governance,
but it may not silently remove, rename, merge, or treat a proxy as validated.

### 42.1 Self-Indicator Groups (71)

```text
si_adaptive_flow
si_bahai
si_bb_break
si_bos
si_cdl
si_cdl_mb
si_chandelier
si_choch
si_cm_strg_pivt
si_cpr
si_cpr_v4
si_ctz_gann
si_curve
si_dark_cloud
si_dbl
si_delta_vp
si_dual_ma_osc
si_fib
si_fmfm300
si_flowscope
si_fractal
si_fvg
si_har_zz
si_harmonic
si_hourly_pvt
si_hs
si_hyb_opening_range_rev
si_hybrid_ml
si_hybrid_ml_cpr
si_ichi_trend_osc
si_ichimoku
si_impulse
si_inside_candle_strategy
si_inside_out
si_kc_pyti
si_liq_intelg
si_liquidity_entry
si_lrb
si_macd_ta
si_mk_inside
si_mp_va
si_nbar
si_ob
si_opening_range_rev
si_outside_rev
si_problty_grid
si_pta_cdl
si_rev_radar
si_rsi_div
si_rsi_div_auto
si_rsi_ss
si_sar_tapy
si_sbs
si_sfb_hybrid
si_sfp
si_st_talipp
si_strg_pivt
si_swing_break
si_swing_str
si_sweep_inside_rr
si_three_inside
si_three_inside_filtered
si_trend_sig
si_trendln
si_twin_range
si_vol_exh
si_vwap_bb_ml_conf
si_vwap_conf
si_vwap_super
si_wekly_pivot
si_zz_swing
```

### 42.2 Pandas-TA Marker Groups (23)

```text
pta_amat
pta_aroon_sig
pta_chop
pta_cmf
pta_drawdown
pta_dsp
pta_ebsw
pta_entropy
pta_fisher_sig
pta_hlc3
pta_kdj
pta_kurtosis
pta_log_ret
pta_long_run
pta_mfi_sig
pta_rsx
pta_short_run
pta_skew
pta_squeeze
pta_tsi
pta_ttm
pta_vortex
pta_zscore
```

### 42.3 Preservation Rules

```python
assert len(SELF_INDICATOR_GROUPS) == 71
assert len(PTA_MARKER_GROUPS) == 23
assert len(ALL_MIGRATED_OUTPUT_GROUPS) == 94
assert set(ALL_MIGRATED_OUTPUT_GROUPS) == set(PRESERVATION_REGISTER)
assert all(item.status in {"validated", "proxy", "blocked", "retired"} for item in registry)
assert not any(item.status == "proxy" and item.used_for_probability for item in registry)
```

An empty event list is not a calculation failure. The registry must preserve
the distinction among:

```text
event not present on this sample
warm-up incomplete
input unavailable
calculation failed
output blocked by governance
implementation retired
```

### 42.4 Newly Added Stock-App Indicator Additions

These four indicators were explicitly requested before implementation and are
now part of the preservation baseline:

| Indicator ID | Display Name | Source Function | Family | Frontend Treatment |
|---|---|---|---|---|
| `si_sweep_inside_rr` | `SWEP+INSD` | `sweep_inside_rr_strategy` | pattern / breakout-retest | trade-line overlay, entry/SL/target evidence, research-only |
| `si_inside_candle_strategy` | Inside Candle Strategy | `inside_candle_strategy` | pattern / candle structure | inside-candle setup, breakout segments, EMA/SuperTrend confirmation |
| `si_ichi_trend_osc` | Ichimoku Trend Oscillator | `ichimoku_trend_oscillator` | momentum / trend | oscillator pane, force/histogram/state/shift events |
| `si_fmfm300` | FMFM300 | `fmfm300_indicator` | pattern / market structure | canvas overlay, dynamic VWAP, zones, pivots, trendlines, FVGs, heatmap |

Governance:

```python
assert "si_sweep_inside_rr" in PRESERVATION_REGISTER
assert "si_inside_candle_strategy" in PRESERVATION_REGISTER
assert "si_ichi_trend_osc" in PRESERVATION_REGISTER
assert "si_fmfm300" in PRESERVATION_REGISTER
assert all(indicator.live_trading_blocked for indicator in requested_additions)
assert all(indicator.point_in_time_checked_before_similarity for indicator in requested_additions)
```

These indicators are copied into the Trade Vision legacy mirror for migration
reference only. The production runtime must still wrap them through the
versioned indicator registry, point-in-time guard, availability reporting,
deterministic replay tests, and family weighting before they are allowed to
contribute to calibrated probabilities.

## 43. Explicit Assumptions and Decisions

```text
ASSUMPTION: "MMF" in the example means Money Flow Index (MFI). If MMF refers
to a separate custom indicator, it must be registered as a distinct plugin
with its own formula, parameters, lineage, and tests.

ASSUMPTION: The initial exchange calendar and session examples target NSE/BSE
cash-market behavior in Asia/Kolkata time. Calendars and sessions remain
exchange-configurable.

ASSUMPTION: Historical recommendations are research evidence, not proof that
the same future outcome will occur.

ASSUMPTION: All probabilities are blocked until minimum evidence, independence,
calibration, walk-forward, and point-in-time gates pass.

ASSUMPTION: True order flow is unavailable when only OHLCV is supplied. Any
absorption, delta, liquidity, or hidden-pressure result is explicitly labeled
as an OHLCV proxy.

ASSUMPTION: News, fundamentals, options, order book, and cross-market features
are optional context providers. Their absence is visible and lowers coverage.

ASSUMPTION: The frontend may display a developing candle for observation, but
decision logic consumes only data available under the declared decision-time
policy.

ASSUMPTION: Entry, stop, target, sizing, and profitability outputs remain
simulation/research estimates until validated by an external execution system.

ASSUMPTION: Kronos is a forecast prior and scenario generator. Trade Vision
Behavior Intelligence remains the memory, risk, and no-trade authority.
```

## 44. Requirement Traceability Checklist

Every implementation milestone and pull request must update a machine-readable
traceability table with these columns:

```text
requirement_id
requirement_name
plan_section
contract
service/module
API endpoint
database/parquet fields
frontend panel
unit tests
integration tests
replay fixture
capability status
known limitations
```

Minimum traced capabilities:

| Requirement ID | Capability | Plan Sections |
|---|---|---|
| TV-REQ-001 | Exact indicator values, states, parameters, and lineage | 5, 22, 42 |
| TV-REQ-002 | Seven closed-bar timeframes | 7, 24 |
| TV-REQ-003 | Exact-time/session/day/calendar memory | 21, 25 |
| TV-REQ-004 | Candle and multi-candle recognition | 23.1 |
| TV-REQ-005 | Swing/chart structure recognition | 23.2 |
| TV-REQ-006 | Harmonic and geometric recognition | 23.3 |
| TV-REQ-007 | S/R, trendline, VWAP, pivot, ORB, value-area memory | 23.4 |
| TV-REQ-008 | Volume, MFI/CMF, absorption, and participation context | 23.5 |
| TV-REQ-009 | Universal indicator, detector, and algorithm activity discovery | 23.6 |
| TV-REQ-010 | Candle wick/body/no-wick and neighbor-candle effect memory | 23.7 |
| TV-REQ-011 | Prior-candle and prior-indicator influence on current candle behavior | 23.7A |
| TV-REQ-012 | Multi-timeframe alignment and conflict | 24 |
| TV-REQ-013 | Stock-specific adaptive DNA | 27 |
| TV-REQ-014 | Similar historical dates and replay | 11, 26 |
| TV-REQ-015 | Indicator-value and condition-combination discovery | 26.2, 26.3 |
| TV-REQ-016 | Conservative future outcome labels | 12 |
| TV-REQ-017 | Entry, invalidation, stop, target, MFE/MAE, and costs | 12, 28 |
| TV-REQ-018 | Human-readable and machine-readable explanations | 29 |
| TV-REQ-019 | Full chart and evidence workspace | 30 |
| TV-REQ-020 | Data-quality, lookahead, sparse-data, drift, and OOD safety | 3, 9, 27, 37 |
| TV-REQ-021 | Same-snapshot Behavior/Kronos/Twin analysis | 13 |
| TV-REQ-022 | Future indicator/pattern/context/model add-ons | 34 |
| TV-REQ-023 | Determinism, performance, auditability, and no-live-order safety | 35-41 |

CI must fail when a required capability disappears from the traceability table,
its public contract, or its preservation test without an approved architecture
decision record.

## 45. External Review Corrections Accepted

The following corrections from external architecture review are accepted as
mandatory before implementation proceeds beyond registry/runtime work:

```text
P0-A: four added indicators require explicit registry contracts and PIT rules
P0-B: similarity retrieval requires ANN/HNSW/FAISS-style prefilter before DTW/Gower
P0-C: pattern confirmation requires confirmation_time <= decision_time
P0-D: outcome labels require overnight gap, gap-through-stop, open-price-first, cost, slippage, and partial-fill logic
P0-E: visual shape, sequential signal, reciprocal signal, false agreement, confluence, distance, and design-similarity engines are core requirements
P0-F: missing expected volume in Indian market context is a hard safety concern, not a silent neutral value
P1-A: frontend panels require grouping, lazy loading, virtualization, and streaming update contracts
P1-B: Kronos must be discretized into barrier probabilities before Twin comparison
P1-C: WARM memory must be quarantined during abrupt regime shifts
P1-D: OOD, drift, memory poisoning, hubness, and false-nearest-neighbor defenses require explicit algorithms and thresholds
P1-E: plugin architecture is deferred until static registry and baseline indicators are stable
```

Implementation readiness status:

```text
architecture/spec readiness: high after these corrections
full behavior-engine build readiness: phased only
realtime research readiness: after v0.79
paper-simulation readiness: after v0.80
live-trading readiness: blocked, separate future approval path
```

Non-negotiable final interpretation:

```text
Trade Vision is first a realtime market behavior memory and evidence engine.
It may produce WAIT, NO_TRADE, FAKEOUT_WARNING, or research candidates.
It does not become a live trading bot inside this plan.
```


---

## 46. Official v0.71-v0.77 Brain-Plan Roadmap Preservation

This section is inserted verbatim from the Codex Brain-plan attachment and is the controlling roadmap for v0.71 through v0.77. It must not be summarized away during implementation. If this section conflicts with earlier broad roadmap text, this section wins for the listed version range and for the exact items named below: TV-PROD-RED-001, indicator_result_cache schema, ICACHE-001 through ICACHE-020, real MTF pullback replacing fake/hash MTF, volatility-OOD before analogs, GAP10 through GAP17, 25 missed scenarios, phase-by-phase test matrix, cache artifact JSON, no hardcoded 184 rule, speed assertions, and the final manipulated-wick red-team test.

`	ext
Brain-plan for Codex. Base: D:\Projects\trading-platforms\stock-app\trade-vision-app. Tests: pytest+FastAPI TestClient, test_9c_NNN_*, double-call SHA determinism, no_future_leakage asserts, golden fixtures. Storage=SQLite (storage.py sqlite3+json+hashlib). Models in apps/api/app/models.py ~6449+. Scope: real runtime + GAP 1-9 + Indicator Result Persistence (your spec, verbatim) + GAP 10-17 + red-team test + 25 missed scenarios. All required. Rule+LightGBM calibrator.

§0 INVARIANTS (every phase)
I1 use_real_indicators=False default/mock never deleted · I2 no future data in any output · I3 live blocked, only WAIT/WATCH/PAPER-CANDIDATE · I4 94-slot frozen · I5 deterministic double-call · I6 latency asserted · I7 no exception escapes→missing-mask/WAIT · I8 no NaN. Accuracy: A1-A7 (distance≥0; zone strength 1-5; probs sum=1.0±0.001; calibrated≠raw; OOD from 95th-pct not hardcoded; stop-first; no NaN). Speed: S1-S6 (<500ms/<800ms/<150ms/<2s/cache<50ms/single-pass/vectorized). Future: F1-F6 (versioned, growth-safe count==registry.total, model pinned, graceful degrade, SHA regression, NO hardcoded "184").

PHASE 1 — REAL S/R RUNTIME + PROXIMITY (GAP1) + CONFLUENCE (GAP2)
CREATE: indicator_runtime_bridge.py, level_proximity.py, level_confluence.py. 1A: import compute_selected/indicator_metadata from legacy/.../self_indc.py. Map S/R+structure families (indicator_registry callable_name)→compute_selected(df,keys). Closed CandleSeries→pandas OHLCV→per-candle last-9. Shape-extractor per visual_type. Missing-mask on raise/empty/warmup/NaN. Cache by (symbol,decision_time,manifest_version). Flag use_real_indicators→mock fallback. 1B(GAP1): extends context_engines.analyze_level_context (lines 27-70; only VWAP has price_vs_vwap_pct line 54). LevelProximity: level_name,level_price,latest_close,distance_pct,distance_atr,side,freshness,within_atr_band. 1C(GAP2): cluster levels within 0.5 ATR→ConfluenceZone: zone_id,zone_price(median),zone_type,contributing_levels,contributing_count,zone_strength(1-5),zone_freshness,net_agreement. Routes: /9c-dna/level-proximity/{symbol}, /9c-dna/confluence/{symbol} (?use_real_indicators=true). Tests: prox_001-004, conf_001-004, calc_001-006, perf_001-003, robust_001-002, flag_001, det_001, pit_001, routing_001.

PHASE 2 — LEVEL-AGE (GAP4) + REGIME (GAP6) + MULTI-HYPOTHESIS (GAP3) + MTF PULLBACK (GAP9) + VOL-BOOST (GAP13)
CREATE: level_memory_extended.py, regime_gate.py, hypothesis_engine.py, mtf_aggregator.py, mtf_trend_reader.py, mtf_pullback_classifier.py. 2A(GAP4): age_bars,touch_count,hold_count,break_count,last_test_result,strength_trend. 2B(GAP6): condition_classifier market_state (14 labels, lines 281-301) as regime key. 2C(GAP3): continuation/reversal/fakeout. Hypothesis: id,direction,thesis,rule_score(0-1),supporting[],opposing[],invalidation_level,confirmation_trigger,analog_evidence,raw_probability. Sum-to-one. 2D REAL MTF (GAP9) — YOUR SPEC, REPLACES HASH MTF. Fixes: multi_timeframe_conflict._direction_for_timeframe (lines 216-223)=(seed+index)%3 RANDOM; timeframe_feature_builder._source_rows=random.Random(seed) FAKE; aggregation (155-167) counts but NOT aggregates OHLCV; conflict (136-148)=BLOCK=opposite of trader logic. Reuse proven context_engines._htf_record (409-431) real slope_pct+bias. 3 files: mtf_aggregator (real 1m→3m/5m/15m/1H: open=first,high=max,low=min,close=last,vol=sum; drop incomplete developing; reuse TIMEFRAME_TO_SOURCE_MINUTES lines 23-31); mtf_trend_reader (direction,strength,structure,pullback_phase,maturity; real indicators via Phase1 bridge); mtf_pullback_classifier (aligned_continuation/pullback_in_trend/trend_resumption/true_conflict/range_no_trend — THE "3m-down=pullback-inside-15m-up"; outputs classification,confidence,pullback_depth_atr,at_htf_confluence,htf_structure_intact). 2E(GAP13): boost=base×vol_dampening. Low=full, high=reduced, extreme=inverted to penalty. Routes: /9c-dna/hypotheses, /9c-dna/regime, /9c-dna/mtf-trend, /9c-dna/mtf-pullback. Tests: mtf_001-022 (incl YOUR scenario: 15m-up+3m-pullback→pullback_in_trend NOT conflict), hyp_001-006, levelage_001-004, calc/logic/pit/perf/safety.

PHASE 3 — HISTORY + PATH ANALOGS (GAP5) + SHAPE-OOD (GAP7) + RECENCY (GAP8) + VOL-OOD (GAP11) + VOL-BUCKET (GAP12)
CREATE: nine_candle_history.py, path_similarity.py, out_of_distribution.py, volatility_regime_gate.py. 3A: slide 9-window across RELIANCE CSV→vector+path_descriptor(step_returns[9],volume_curve[9],range_progression[9]). Forward-label (3/5/9/12/20) via outcome_learning, stop-first. Winner/failure separate, regime-tagged, volatility-bucketed (GAP12). 3B(GAP5): replaces build_analogs hardcoded 184. DTW+cosine on path descriptor. Real counts. Scoped regime+vol-bucket. 3C OOD TWO AXES: Shape-OOD(GAP7) k-NN on 9C, 95th-pct, gate 9C-G013. Vol-Magnitude-OOD(GAP11) today ATR vs history, top-decile→volatility_ood=True, RUNS FIRST, gate 9C-G016. Both pass. 3D(GAP8): recency weight (recent×1.0→old×0.6), per-week cap, temporal_diversity_score. Routes: /9c-dna/path-analogs, /9c-dna/ood-status. Tests: path_001-003, ood_001-004 (vol-top-decile→WAIT-before-analogs, magnitude-wins-over-shape), recency_001-002, volbucket_001-002, calc_012-016, perf<2s+single-pass, robust, pit/routing/flag.

PHASE 4 — CALIBRATOR + PAPER-CANDIDATE + GAP10/15/16/17
CREATE: hypothesis_calibration.py, reasoning_arbiter.py, decision_audit.py, calibration_drift_monitor.py. 4A LightGBM calibrator: one model per outcome, trained 3A windows. Inputs=rule-scores+regime+proximity+confluence→isotonic. CALIBRATOR ONLY. model pinned (F3). 4B PAPER gate 9C-G014: PAPER when primary calibrated≥threshold AND winner≥min_sample AND shape-OOD=False AND vol-OOD=False AND regime match AND HTF confirms AND arbiter no override. Execution blocked. 4C Arbiter (GAP10): condition_classifier manipulated_looking/fake_breakout/high trap_probability (206-223)→continuation OVERRIDE to WAIT regardless analog strength. Safety spine outranks. 4D Disagreement (GAP15): subsystem disagreement→confidence drops. 4E Audit (GAP16): record what each subsystem said + arbiter overrides. Auditable when wrong. 4F Drift (GAP17): rolling predicted-vs-realized; exceed→demote calibrator to rule-only. Gate 9C-G018. Tests: cal_001-004, paper_001-003, arbiter_001-003 (manipulated→WAIT-even-with-strong-analogs, fakeout-overrides-pullback, no-fabricated-direction), disagree_001-002, audit_001-002, drift_001-002, perf<100ms, det/pit/routing/flag.

INDICATOR RESULT PERSISTENCE — YOUR SPEC, VERBATIM + GAP14
CREATE: apps/api/app/behavior/indicator_result_cache.py; SQLite table in data/trade_vision_state.db; artifacts data/indicator_result_cache/. Purpose: operator option to save calculated indicator results per symbol+timeframe+snapshot+registry version to reuse instead of recalc. Default: in-memory same-session; NEW persistent=SQLite+compressed JSON. Research-only, cannot enable probability/trading. Reuse ONLY when source candle hash+timeframe+registry version+manifest version+indicator param hash match EXACTLY. DB TABLE indicator_result_cache (BUILD EXACT): cache_id TEXT PK; symbol NOT NULL; timeframe NOT NULL; source_snapshot_hash NOT NULL; source_snapshot_id; candle_start_time; candle_end_time; candle_count INTEGER NOT NULL; indicator_registry_version NOT NULL; feature_manifest_version NOT NULL; promoted_indicator_hash NOT NULL; indicator_id NOT NULL; runtime_status NOT NULL; output_present INTEGER NOT NULL; used_for_probability INTEGER DEFAULT 0; trade_allowed INTEGER DEFAULT 0; order_routing_enabled INTEGER DEFAULT 0; live_trading_blocked INTEGER DEFAULT 1; artifact_uri NOT NULL; artifact_sha256 NOT NULL; latency_ms REAL NOT NULL; created_at NOT NULL. INDEXES: (symbol,timeframe,source_snapshot_hash); (symbol,timeframe,indicator_id); (indicator_registry_version,feature_manifest_version); (created_at DESC). Module: deterministic cache_id; save one row per indicator output; artifact JSON canonical sorted keys; validate artifact hash before read; cache hit ONLY when all identity fields match; missing/stale never error→recalc. cache_id=sha256(symbol|timeframe|source_snapshot_hash|indicator_id|indicator_registry_version|feature_manifest_version|promoted_indicator_hash). Artifact payload: {cache_schema_version:"indicator-result-cache.v1", symbol, timeframe, source_snapshot_hash, indicator_id, runtime_status, payload:{}, telemetry:{}, safety:{used_for_probability:false,trade_allowed:false,order_routing_enabled:false,live_trading_blocked:true}}. API: POST /indicator-cache/save/{symbol}; GET /indicator-cache/status/{symbol}; GET /indicator-cache/results/{symbol}; DELETE /indicator-cache/{cache_id}. Params: timeframe,use_real_indicators,force_recompute. Save returns saved_count,reused_count,failed_count,slow_indicator_count,cache_size_bytes,cache_hit_rate. ALWAYS trade_allowed=false,order_routing_enabled=false,live_trading_blocked=true. Runtime: request→check cache→exact match+hash verify→use→else compute→save when user clicks Save. Default NO auto-save. "Save Indicator Results" button in Jarvis/Research. Frontend panel: symbol/timeframe, saved count, latest timestamp, hit/miss, stored/slow indicators, artifact hash status, safety state. Buttons: Save/Reload/Force Recompute/Clear. Efficiency: first computes; repeat reads stored; heavy (si_fmfm300) benefit most; do NOT reuse if candle hash/timeframe/registry version/manifest version/promoted list/hash changed; stale visible not trusted. Safety HARD: used_for_probability=false,trade_allowed=false,order_routing_enabled=false,live_trading_blocked=true. Cache=speed not authority. Corrupt→ignore+recompute+cache_integrity_status="failed". Missing→cache_status="miss"+compute. Runtime fails→telemetry only if output_present=false, no usable vector. GAP14 quarantine: refuses persist if flagged by GAP10/11→cache_status="anomalous_snapshot_quarantined". Load anomalous artifact→reference_only, cannot seed 9C. SHA mismatch→recompute+log. Tests: ICACHE-001..012 (your spec) + ICACHE-013 quarantine/014 reference-only/015 SHA-mismatch/016 version-mismatch/017 disk-full/018 vector-reproducible/019 wrong-vol-stale/020 force-recompute-anomalous.

PHASE 5 — GOLDEN FIXTURES + FRONTEND + REGRESSION
5A golden (SHA): clean-breakout, fake-breakout, vwap-rejection, choppy, gap-up-continuation, low-volume, htf-lookahead-trap, near-confluence-support, near-confluence-resistance, ood-unknown, mtf-pullback-in-uptrend, mtf-true-conflict, mtf-range-no-edge, regime-shift-liquidation. 5B frontend: Proximity/Confluence map, Hypothesis board, Path-analog timeline, OOD shield, MTF pullback view, Arbiter view, Indicator Cache panel. 5C regression every phase: leak sweep all endpoints, gate dict 9C-G013/014/016/017/018/019, count==registry.total, live blocked.

RED-TEAM TEST (TV-PROD-RED-001) — FINAL GATE
2.4×ATR manipulated-wick day: vol_ood True (GAP11 fires first) · "manipulated_looking" in arbiter consulted_flags (GAP10) · matched_after_vol_bucketing<raw_match_count (GAP12) · continuation boost≤0.0 (GAP13) · decision in {WAIT,WATCH} · paper_candidate_allowed False · cache_status="anomalous_snapshot_quarantined" (GAP14) · live_trading_blocked True.

25 MISSED SCENARIOS (all tests)
Vol(1-6): ATR2×→vol-OOD, mid-session spike, low-vol-vs-high, log-guard, zero-ATR, extreme-gap. Disagree(7-11): manip-vs-analog→WAIT, fakeout-vs-pullback→penalty, vol-vs-shape→magnitude wins, 2-of-3 conflict, all-neutral. OOD(12-15): top-decile→refuse, first-ever-regime, degenerate→safe, novel-combo→flag. Cache(16-20): quarantine, reference-only, SHA-mismatch, version-mismatch, disk-full. Cache+reason(21-23): reproducible, wrong-vol→stale, force-recompute-anomalous. Resilience(24-25): CSV NaN→mask, latency-exceeded→degrade.

BUILD SEQUENCE
P1→P2(needs1B/1C)→P3(needs1A)→P4(needs2C+3A)→Cache(needs1+GAP10/11)→P5(all). No phase starts till prior matrix green. TV-PROD-RED-001 final gate.

CODEX RULES
1 phase-by-phase, matrix green before next. 2 missing-mask/no-exception/no-NaN. 3 every route live_trading_blocked=True,trade_allowed=False,no_future_leakage=True. 4 assert ranges+sum-to-one. 5 NEVER delete build_indicator_sequences/build_analogs/mock/hash MTF—add real behind flag. 6 double-call byte-identical+SHA. 7 build Cache DB table+artifact EXACTLY as spec (columns,indexes,cache_id,JSON). 8 TV-PROD-RED-001 must pass.

## 47. Official Indicator Intelligence Roadmap v1.80-v1.81 Preservation

This section preserves the missing full-indicator-awareness roadmap. It complements the detailed plan in `docs/plans/TRADE_VISION_MAX_CHART_REASONING_V1_70_TO_V1_79_PLAN.md` and must not be skipped when moving beyond registry-level indicator visibility.

Roadmap resolution:

```text
The original v1.76-v1.79 indicator roadmap remains preserved as requirement history.
The concrete implementation is now merged into two versions:

v1.80 Indicator Intelligence Contract + Ontology + Lag-Aware Voting
v1.81 Per-Indicator Reliability Memory + Outcome Labeling Bridge

Reason:
Sequential causality already exists as event_sequence_mining.py.
Conflict/redundancy already exists as feature_redundancy.py and false_agreement_confluence.py.
The missing pieces are indicator understanding, lag-aware weighting, and evidence-backed reliability.
```

Current project state:

```text
indicator exists != indicator is understood
indicator computed != indicator is trade-useful
indicator bullish != trade should be taken
```

Every registered indicator must receive an Indicator Intelligence Contract before it can be trusted as reasoning evidence.

Required contract fields:

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

Required versions:

```text
v1.80 Indicator Intelligence Contract + Ontology + Lag-Aware Voting
  Classify every indicator as trend, momentum, volatility, volume, level, structure, trap, exhaustion, harmonic, curve, SMC, or risk.
  Define what each indicator is meant to answer. RSI divergence answers exhaustion, not breakout strength.
  Extend the registry contract with purpose, category, market-regime fit, timeframe fit, lag behavior, false-positive conditions, confirmation rules, conflict rules, trade usage, and ontology version.
  Consume the existing confirmation_delay_bars field as a vote weight.
  Wire feature_redundancy.py and false_agreement_confluence.py instead of rebuilding conflict logic.

v1.81 Per-Indicator Reliability Memory + Outcome Labeling Bridge
  Learn which indicators each stock respects.
  Track per-stock, per-timeframe, per-session, and per-regime reliability.
  Use Bayesian shrinkage so low sample counts cannot create false confidence.
  Connect indicator signals to forward outcomes across 3/5/9/12/20-candle horizons.
  Outcome labels must be attached only after the future horizon completes.
  Feed reciprocal_signal_ratio into reciprocal_signal_detector.py.

Preserved existing modules
  v1.78 sequential behavior is preserved through event_sequence_mining.py.
  v1.79 conflict and redundancy behavior is preserved through feature_redundancy.py and false_agreement_confluence.py.
```

Indicator lag-awareness voting rule:

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

Required tests:

```text
IND-ONT-001 every registry indicator carries ontology metadata
IND-ONT-002 RSI is exhaustion, not breakout strength
IND-ONT-003 category and family can differ without breaking redundancy logic
IND-ONT-004 list defaults are factory-backed, not shared mutable defaults
IND-ONT-005 registry count/growth gate remains green
IND-ONT-006 new unclassified indicator is safe/reserved, not probability-enabled
IND-ARB-009 confirmation_delay_bars reduces late indicator vote weight
IND-ARB-010 zero-delay structural signal outranks four-bar delayed MACD confirmation
IND-ARB-011 late confirmation cannot promote WATCH to PAPER-CANDIDATE by itself
IND-ARB-012 stale confirmation beyond sequential window creates warning, not confidence
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

Risk rules:

```text
too many indicators create false confidence
correlated indicators vote multiple times for the same thing
lagging indicators can confirm after the move is already over
confirmation_delay_bars must be consumed as vote weight, not stored as unused metadata
missing indicator values can create false similarity if not masked
future-pivot indicators can leak future data if not delayed
same signal means different things in trend vs range
a strong indicator on one stock may be useless on another
indicator overload can slow frontend/backend
equal weighting lets weak indicators dilute strong evidence
```

Decision examples to preserve:

```text
RSI and MACD are bullish, but both are lagging indicators.
Price is at HVN resistance, upper wick rejection is high, VSA shows effort without result,
and this stock has failed this same setup 62% of the time.
Decision: WAIT.

VWAP reclaim, CPR support, inside candle breakout, declining volatility,
and stock-specific memory all align.
Similar past cases continued 68% of the time.
Decision: WATCH / PAPER-CANDIDATE if risk passes.
```

SAFETY PRESERVED + HONEST CAVEAT
No live/paper (PAPER=research flag). No mock deleted. No PIT bypass. No 94 change. ML=calibrator-only. No hardcoded counts/thresholds. No NaN. Arbiter ensures safety spine ALWAYS outranks reasoning. Caveat: no plan eliminates being wrong in markets; this makes the system correctly uncertain when it should be — refusing to promote on regime-shift days rather than confident-wrong. That is the research-demo→production-safe difference.
` 
