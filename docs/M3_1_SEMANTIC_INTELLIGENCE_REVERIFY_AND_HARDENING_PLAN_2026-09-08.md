# M3.1 Semantic Intelligence Re-verification & Hardening Plan

**Date:** 2026-09-08  
**Audit branch:** `m3-1-semantic-hardening-audit`  
**Base:** `m3-2-context-intelligence` at `a97382ca133a1e72a9d7b410d3b555acc9381e32`  
**Locked predecessor:** M3.1 final documented head `20d2d7b5889b09cd593401e8f70ec53cc299c51e`

## Executive finding

M3.1 remains strong as a causal/provenance migration, but it is **not yet the final semantic intelligence design**. The largest remaining weaknesses are not missing tests or missing indicators. They are:

1. some downstream brains still recompute facts that should be calculated once in the D2 feature substrate;
2. several heuristic labels overstate what OHLCV can actually prove;
3. missing data is still converted to numeric zero in Chart Reasoning and Market Structure paths;
4. hard-coded thresholds are not instrument/session/regime adaptive;
5. some heuristic scores are named like probabilities without calibration;
6. current Condition/Level/Structure outputs sometimes contain direction-specific blocking semantics inside sensory specialists;
7. Market Structure uses approximate OHLCV proxies for volume profile/TPO/order-block/Wyckoff concepts without a strong epistemic distinction between observation and hypothesis;
8. the current D6 compatibility mapping treats directionless trend-persistence magnitude as directional, creating a potentially inverted short-side interpretation;
9. the canonical indicator runtime covers only the promoted self-indicator subset, while the locked registry describes a larger 94-output universe;
10. indicator metadata/warmup/dependency truth is split across more than one registry/adapter source.

This document proposes **M3.1.1 Semantic Hardening** as a shadow, zero-authority layer. It must not silently mutate the locked M3.1 behavior or D6 parity. New semantics should run beside the old compatibility projection until replay, calibration and M4 migration explicitly authorize adoption.

---

# 1. Required epistemic model

The project should distinguish the type of every claim:

```text
OBSERVED     = directly present in approved market data
DERIVED      = deterministic math from observed data
INFERRED     = rule/model interpretation of derived facts
HYPOTHESIS   = plausible explanation that is not directly observable
PREDICTIVE   = calibrated future-outcome distribution
DECISION     = D6-only recommendation state
```

Examples:

```text
high=2501.0                         OBSERVED
body_ratio=0.71                     DERIVED
large bullish displacement          INFERRED
possible absorption                 HYPOTHESIS
P(continuation next 3 bars)=0.58    PREDICTIVE only if calibrated
WATCH                               DECISION, D6 only
```

Terms such as `manipulated_looking`, `order_block`, `stop_hunt`, `accumulation`, `distribution`, `Wyckoff spring`, or `absorption` must never be presented as direct market facts when only OHLCV supports them. They should be typed as hypotheses/proxies with evidence and alternatives.

---

# 2. Snapshot Feature Kernel — upgrade from reusable vectors to Market Primitive Kernel

## Current strengths

- accepts approved D2 immutable closed-candle snapshots only;
- validates snapshot hash/stage/closed/PIT flags;
- rejects non-canonical ordering;
- validates OHLC geometry and finite values;
- materializes OHLCV/range/body/typical-price/return vectors once;
- reuses rolling average-range and volume windows;
- provides cumulative VWAP primitives;
- deterministic hashes and calculate-once audit.

## Remaining weaknesses

### 2.1 Price positivity is not enforced inside the kernel

Finite OHLC geometry is checked, but zero/negative prices are not explicitly rejected. Simple return calculation divides by the previous close. A malformed zero previous close can therefore produce a calculation failure rather than an epistemically clean invalid-input state.

### 2.2 `average_range` is intentionally not ATR

This is correctly documented for compatibility, but downstream code still frequently names mean range as `ATR`. The system needs two separately versioned primitives:

```text
average_candle_range_legacy
true_range
wilder_atr
```

No silent replacement.

### 2.3 Too many Level-0 facts are recalculated downstream

Chart Reasoning and Market Structure reconstruct ranges, bodies, return series, volatility statistics, EMA-like state, percentiles and other primitives independently.

Target kernel v2 should calculate reusable primitive blocks once:

```text
OHLCV geometry
simple returns
log returns
true range
Wilder ATR
rolling mean/variance
robust median/MAD
rolling extrema
close-location
body/wick ratios
session-relative volume baseline
raw volume z-score
realized volatility
rolling EMA primitives
rolling slope primitives
prefix VWAP sums
session index map
missingness masks
source-quality masks
```

### 2.4 Volume seasonality is absent

Raw rolling volume z-score treats naturally high opening/closing volume as anomalous. A real intraday intelligence engine needs both:

```text
raw_local_volume_z
session_time_normalized_rvol_z
```

The second requires M3.2/M3.3 historical session memory and must remain unavailable until real evidence exists.

### 2.5 No market-microstructure normalization

Future source contract should allow:

```text
tick_size
spread
trade_count
turnover
quote_age
depth/order-book identity
auction/circuit state
corporate-action adjustment state
```

When those sources are absent, the kernel must say unavailable, not estimate them from candle shape.

### 2.6 Performance

Current small rolling windows are acceptable, but future many-window expansion should use prefix sums / incremental rolling state instead of repeated slicing so updates can approach O(delta) per new bar.

---

# 3. Candle Anatomy — from heuristic labels to high-resolution morphology

## Current strengths

- compute-once reuse of Snapshot Feature Kernel;
- deterministic geometry;
- explicit missing volume z-score;
- inside/outside/rejection/compression/expansion/follow-through facts;
- bounded canonical receipt.

## Weaknesses

### 3.1 `range_atr` is semantically misleading

It is average candle range, not Wilder ATR. Keep compatibility field, but add canonical names:

```text
range_to_average_range
range_to_true_atr
```

### 3.2 Static thresholds do not generalize

Examples such as 65% body, 45% wick, 1.1x range, 0.4% gap are fixed across:

- RELIANCE vs low-price/high-beta stocks;
- opening drive vs lunch session;
- low-VIX vs high-VIX days;
- 1m vs 15m bars.

The better design is a two-layer model:

```text
raw continuous morphology facts
        ↓
context-conditioned interpretation thresholds
```

Do not hard-code context into anatomy itself.

### 3.3 Adjacent-bar gap is not the same as session gap

`gap_pct` currently compares each bar open to the previous bar close. That is a valid discontinuity fact but should not be interpreted as morning gap context. Rename:

```text
bar_open_discontinuity_pct
```

Session gap belongs in M3.2/session context using prior-session close.

### 3.4 `body_to_volume_efficiency` and `effort_vs_result` are proxies

These formulas are useful heuristic transforms but they are not direct order-flow efficiency. Preserve as proxy-derived features with versioned formulas, not as microstructure truth.

### 3.5 Follow-through should be path-aware

Current follow-through is mostly a contiguous directional candle count. A stronger state should track:

```text
extension beyond prior extreme
close progression
retracement depth
range decay/expansion
volume participation
level distance
bars since trigger
failure/reclaim state
```

### 3.6 Add morphology dimensions

Recommended canonical continuous facts:

```text
body/range
upper-wick/range
lower-wick/range
close-location
open-location relative prior range
overlap ratio with prior bar
range expansion ratio
body expansion ratio
directional efficiency
close-to-close return in ATR units
bar displacement in ATR units
wick asymmetry
range percentile
session-normalized volume participation
micro-gap/discontinuity
inside/outside depth
```

These should be facts. Pattern names remain interpretations.

---

# 4. Candle Condition — major semantic redesign required

## Current strengths

- consumes shared anatomy in the canonical route;
- multiple condition tags are preserved;
- deterministic rules are explainable;
- structural uncertainty exists;
- can block obviously poor legacy patterns.

## Critical weaknesses

### 4.1 Missing volume still becomes neutral in several rules

Patterns such as distribution/accumulation/manipulated-looking and absorption use `volume_z or 0.0`; aggregate volume helper also returns `0.0` when no volume observations exist.

This violates the project rule:

```text
missing != neutral
```

M3.1.1 must return `UNKNOWN/UNAVAILABLE` for volume-dependent interpretations.

### 4.2 `trap_probability` is not a calibrated probability

It is a hand-added rule score. Rename it now in the semantic layer:

```text
trap_heuristic_score
```

Only M3.3-calibrated, holdout-tested outputs may use probability terminology.

### 4.3 Directional asymmetry

Opening-drive continuation is explicitly bullish in the current rule. Reversal logic emphasizes upper-wick rejection. The condition ontology must be symmetric:

```text
bullish opening drive
bearish opening drive
bullish reversal/reclaim
bearish reversal/rejection
```

### 4.4 A single dominant condition loses information

Priority ordering can collapse:

```text
breakout + high rejection + absorption + compression release
```

into one label.

Replace the intelligence representation with a **hypothesis set**:

```text
hypothesis_id
state
supporting_evidence
contradicting_evidence
quality
confirmation_needed
invalidation
```

The old dominant label may remain as a compatibility projection only.

### 4.5 Semantic overclaim

Rename intent-like states:

```text
manipulated_looking        -> abnormal_wick_range_volume_signature
accumulation               -> lower_rejection_high_participation_candidate
distribution               -> upper_rejection_high_participation_candidate
absorption                 -> effort_result_absorption_candidate
```

Intent cannot be known from OHLCV alone.

### 4.6 No temporal belief state

One candle can flip the class. Add state-transition/hysteresis concepts:

```text
FORMING
CONFIRMED
WEAKENING
INVALIDATED
EXPIRED
```

and track `bars_since_confirmation`.

---

# 5. Chart Reasoning — strongest opportunity for higher intelligence

## Current strengths

- trend persistence, volatility state, Hurst/fractal proxy, EMA geometry, VCP, rejection, exhaustion, chop and mean-reversion concepts already exist;
- no order authority;
- shared Anatomy prevents one major duplicate calculation.

## Critical weaknesses

### 5.1 Missing volume becomes zero

The current chart path converts missing volume to `0.0`, which can falsely create volume-dry-up/VCP evidence.

Must become:

```text
volume_state = UNAVAILABLE
vcp_volume_confirmation = UNAVAILABLE
```

### 5.2 Mean candle range is labeled current ATR

Chart Reasoning currently derives `current_atr` from mean high-low ranges. Build separate true ATR/legacy average-range fields.

### 5.3 Intraday historical volatility annualization is not timeframe-correct

The current HV calculation multiplies bar-return volatility by `sqrt(252)` regardless of bar duration. For intraday bars, level interpretation is not an annualized volatility estimate.

Use:

```text
realized_vol_per_bar
realized_vol_per_session
annualized_realized_vol only with timeframe-aware sessions-per-year scaling
```

### 5.4 Insufficient history can become neutral 50th percentile

Percentile helper returns 50 when no history exists. That is a useful computational fallback but an invalid epistemic statement.

Canonical state must be:

```text
percentile = null
availability = INSUFFICIENT_HISTORY
```

### 5.5 Hurst default 0.5 is not evidence

Insufficient samples return 0.5. Canonically this should be unavailable/low-confidence, not neutral memorylessness.

### 5.6 Hurst on raw close levels is fragile

Use multiple estimators/diagnostics only as secondary evidence; never let a short-window Hurst proxy dominate regime decisions.

### 5.7 VCP logic is too local and session-volume-blind

Contraction plus falling raw volume can be caused by the normal intraday U-curve. VCP should use session-normalized volume and structural swing contraction, not only consecutive bar ranges.

### 5.8 Trend persistence needs direction separated from magnitude

Required canonical fields:

```text
trend_direction       bearish | neutral | bullish | unavailable
trend_persistence     0..1
trend_strength        0..1
trend_efficiency      0..1
trend_acceleration    signed
trend_change_risk     0..1 or uncalibrated score
```

Do not encode direction by multiplying a directionless persistence score downstream.

---

# 6. Critical D6 compatibility wiring defect

Current D6 compatibility helper approximately does:

```text
score = trend_persistence_score * 2 - 1
if requested direction == short:
    score *= -1
```

But current Chart Reasoning builds persistence from components including absolute micro-slope and absolute EMA distance. Therefore persistence is primarily magnitude, not bullish direction.

Potential consequence:

```text
strong bearish trend
trend_persistence = high

LONG request  -> positive regime score
SHORT request -> negative regime score
```

This can invert the meaning of a strong downtrend.

## Required handling

Do **not** hot-fix this inside locked M3.1 and destroy parity evidence.

Instead:

1. add a shadow signed-trend evidence field now;
2. add a regression fixture proving bearish trend semantics;
3. mark current D6 helper as compatibility debt;
4. migrate the signed directional regime meaning only under the authorized M4 D6 redesign;
5. compare old-vs-new decisions over replay before promotion.

This is a P0 semantic issue for future D6 redesign.

---

# 7. Market Structure & Liquidity — requires canonicalization, not cosmetic tuning

## Current strengths

- volume-profile/TPO proxy concepts;
- VSA effort/result;
- equal-high/low pools;
- sweep candidates;
- FVG/order-block candidates;
- BOS/CHOCH;
- trap/stop-hunt warnings;
- research-only safety.

## Critical weaknesses

### 7.1 Missing volume is converted to zero

Both volume-profile and VSA paths use `bar.volume or 0.0`.

Required behavior:

```text
volume-dependent structure = UNAVAILABLE
price-only structure may remain AVAILABLE
```

### 7.2 Current volume profile is not true volume-at-price

All of a candle's volume is assigned to its typical-price bin. With OHLCV only, intrabar volume distribution is unknowable.

Rename canonical output:

```text
bar_typical_price_volume_profile_proxy
```

Only tick/trade/volume-at-price data may claim true volume profile.

### 7.3 Current TPO is an OHLC-range proxy

Every price bin touched by a bar range is counted. It is useful, but not exchange-grade TPO. Mark its source method explicitly.

### 7.4 Profile scope is ambiguous

The engine builds profiles from all supplied bars. A multi-session D2 snapshot can mix sessions without labeling the result as session/composite/anchored.

Need independent profiles:

```text
current_session_profile
previous_session_profile
rolling_N_session_composite
anchored_event_profile
```

### 7.5 Fixed bin-count instability

When high/low range expands, bin centers move and POC/VAH/VAL can shift because the coordinate system changed, not because the market meaningfully changed.

Prefer stable tick/ATR-based bin width with explicit profile identity.

### 7.6 Order block is a candidate, not institutional truth

`last opposite candle before impulse` is a deterministic pattern definition. Call it:

```text
order_block_candidate_v1
```

Track lifecycle:

```text
fresh
first_touch
mitigated
invalidated
expired
```

### 7.7 FVG needs lifecycle and minimum significance

Add:

```text
gap_size_ticks
gap_size_atr
age_bars
fill_pct
mitigated
invalidated
```

### 7.8 BOS/CHOCH should use hierarchical confirmed swings

Current short fixed lookback is not enough for robust structure. Build causal swing hierarchy:

```text
micro swing
intraday swing
session swing
HTF swing
```

with confirmation delay explicitly recorded.

### 7.9 Wyckoff/stop-hunt semantics overclaim intent

Use observable naming:

```text
spring_candidate
upthrust_candidate
liquidity_sweep_rejection_signature
```

Intent becomes a hypothesis only when other independent evidence supports it.

### 7.10 Real microstructure should be a separate future brain

When data becomes available:

```text
bid/ask spread
book imbalance
order-flow imbalance
aggressor imbalance
depth depletion
quote/trade intensity
market impact proxy
```

should live in an independently sourced microstructure brain, not be reverse-engineered from OHLCV candle shapes.

---

# 8. M3.1-C Level Intelligence — strong foundation, needs Level Graph v2

## Current strengths

- session-aware VWAP;
- missing volume fails closed;
- OR5/15/30 explicitly tiled;
- incomplete OR is PENDING;
- missing OR bars are UNAVAILABLE;
- prior session must be observed and complete;
- CPR provenance is explicit;
- causal level hash;
- D6 compatibility projection isolated.

## Weaknesses

### 8.1 No official exchange calendar identity

Static NSE 09:15–15:30 regular-session semantics cannot prove holidays, special sessions, Muhurat trading, exceptional schedules or future rule changes.

Wire a versioned exchange-calendar source through M3.2.

### 8.2 Level tolerance is fixed

A fixed ~0.1% tolerance is not adequate across instruments/volatility/spread/tick sizes.

Use:

```text
tolerance = max(
    k_tick * tick_size,
    k_spread * spread,
    k_atr * ATR,
    k_noise * local_realized_noise
)
```

with bounded versioned parameters.

### 8.3 Level lines should become zones

Real interaction is rarely an exact one-price event. Add:

```text
zone_low
zone_high
distance_ticks
distance_atr
distance_bps
```

### 8.4 Level lifecycle is missing

Track:

```text
origin
age
first_touch
number_of_touches
rejection_count
reclaim_count
break_count
role_flip
last_interaction
freshness
invalidated
```

### 8.5 Level clustering/confluence is missing

A PDH, ORH, VWAP band and pivot within a small dynamic tolerance should form a `level_cluster`, with independent-source accounting so derived duplicates do not fake confluence.

### 8.6 Corporate actions are not verified

PDH/PDL/close and gap logic can be misleading on ex-dividend/split/bonus/other adjustment days. Explicit adjustment provenance is required.

### 8.7 `quality.available=True` conflicts with degraded sub-facts

The bounded receipt currently can report `quality.available=True` while also carrying `missing_reasons`, with outer orchestration separately marking the receipt DEGRADED.

Make the canonical v2 quality state internally consistent.

### 8.8 Directionless `blocks_trade` is semantically wrong

For example, `below_session_vwap` can be bearish support rather than a universal blocker.

A sensory level brain should instead emit:

```text
long_supporting_facts
long_conflicting_facts
short_supporting_facts
short_conflicting_facts
```

or preferably direction-neutral facts plus a later interpretation brain.

---

# 9. M3.1-D Indicator Intelligence — strong transport layer, incomplete intelligence layer

## Current strengths

- one DataFrame build per call;
- D2 snapshot/timeframe provenance;
- deterministic source-window hash;
- parameter hash;
- bounded canonical evidence;
- explicit COMPUTED/NO_SIGNAL/NO_OUTPUT/WARMUP/DEPENDENCY/ERROR/SLOW states;
- unavailable/error not converted to numeric zero;
- deterministic cache independent of operational latency;
- family/dependency/correlation labels;
- zero final authority.

## Major remaining weaknesses

### 9.1 The 94-output registry and canonical runtime are not one truth source

The locked behavior registry describes 94 output groups, including exact warmup/PIT/lag/confirmation metadata. The canonical real adapter currently promotes a smaller self-indicator allowlist and separately derives family/dependency/correlation/warmup metadata.

Target:

```text
ONE CANONICAL INDICATOR CONTRACT REGISTRY
```

Every runtime must use the registry's:

```text
formula hash
implementation version
exact warmup
lookback
confirmation delay
future-pivot policy
input dependencies
output schema
family
correlation group
PIT audit state
status validated/proxy/blocked
```

No second heuristic metadata truth.

### 9.2 Runtime coverage is incomplete

The canonical self-indicator allowlist is smaller than the 94-output registry; PTA marker runtime remains separately probed/skipped in the current Paper Guidance Stage2 path.

Create a coverage matrix:

```text
REGISTERED
VALIDATED
CANONICAL_RUNTIME_SUPPORTED
PIT_VERIFIED
REAL_DATA_EMITTING
PERFORMANCE_PASS
CANONICALIZED
M3.3_RELIABILITY_AVAILABLE
D6_ELIGIBLE
```

### 9.3 Generic output normalization can lose semantics

Different indicators produce scalars, series, marker lists, zones, multi-field structures or overlays. A generic `value/direction/strength` extractor cannot preserve all meaning safely.

Use per-indicator-family canonical adapters:

```text
scalar oscillator adapter
trend-state adapter
event-marker adapter
level/zone adapter
structure-event adapter
multi-output overlay adapter
```

### 9.4 Exact warmup is more than max parameter

Composite indicators may need more history for nested smoothing, EMA convergence, pivot confirmation or delayed events. Use registry-defined exact warmup plus confirmation delay and convergence policy.

### 9.5 Correlation group is not enough

The intelligence layer needs a dependency graph:

```text
RSI and RSI-derived signals share source transform
VWAP variants share VWAP/volume dependency
EMA-cross and MACD share moving-average information
FVG/OB/BOS indicators overlap Market Structure
```

Do not count correlated derivatives as independent evidence.

### 9.6 `NO_SIGNAL` needs event-state history

For event indicators, absence of an event on the latest bar is different from:

```text
bullish event 2 bars ago still valid
bullish event expired
opposite event invalidated
no event in current state
```

Add event lifecycle and `bars_since_event`.

### 9.7 Indicator reliability belongs to M3.3

M3.1-D should stay sensory. M3.3 should attach PIT-safe learned metadata:

```text
per-stock reliability
per-timeframe reliability
per-regime reliability
per-session reliability
sample count
confidence interval
drift state
recent-vs-old degradation
```

No indicator votes just because it exists.

### 9.8 Performance upgrade

Longer-term target is an indicator DAG:

```text
shared EMA/SMA/ATR/RSI/VWAP primitives calculated once
       ↓
indicator-specific transforms
       ↓
canonical adapters
```

This can remove repeated vendor calculations and reduce latency while keeping formula/version identity explicit.

---

# 10. Replace score soup with an Evidence Graph

The intelligent target should not be:

```text
anatomy_score + condition_score + chart_score + structure_score + indicator_score
```

because most of these are transformations of the same OHLCV bars and are not independent evidence.

Use a causal evidence DAG:

```text
D2 BAR FACTS
  |
  +-> morphology facts
  +-> level facts
  +-> volatility facts
  +-> structure facts
  +-> indicator facts

Each derived claim stores:
  upstream hashes
  epistemic type
  dependency family
  correlation group
  availability
  quality
  contradiction links
  confirmation requirement
  invalidation rule
```

Then reason over **independent evidence families**, not raw indicator count.

---

# 11. AGI-like market reasoning: scientific hypothesis loop

The project should emulate disciplined scientific reasoning, not human-like certainty.

For each decision time generate competing hypotheses:

```text
H1 continuation trend
H2 breakout failure / trap
H3 balance / chop
H4 mean reversion
H5 volatility expansion without direction
H6 news/exogenous shock
H7 liquidity sweep then reclaim
H8 exhaustion / reversal
```

Each hypothesis contains:

```text
prior state
supporting evidence
contradicting evidence
missing required evidence
expected next observations
invalidation conditions
time horizon
calibration state
```

Example:

```text
H1: genuine bullish breakout
EXPECT:
  hold above ORH
  positive close progression
  VWAP hold
  no immediate return inside OR
  participation not collapsing
  index/sector alignment

FALSIFY:
  close back inside OR
  failed retest
  volume/participation collapse
  benchmark divergence
  high rejection + adverse structure shift
```

On every newly closed candle:

```text
observe -> compare expectation -> update hypothesis -> preserve contradictions
```

This produces a truth-seeking engine rather than a label generator.

---

# 12. Probabilistic intelligence must be calibrated

No heuristic score should be called probability.

M3.3 should evaluate predictive outputs with:

```text
Brier score
log loss
calibration error
reliability diagrams
regime-specific calibration
coverage of prediction intervals
walk-forward holdout
purge/embargo
multiple-testing correction
recent-vs-old performance
OOD performance
```

For nonstationary markets, future predictive uncertainty should be able to widen or abstain under regime change rather than preserve a precise point estimate.

---

# 13. Recommended new architecture

```text
VERIFIED D2 CLOSED-CANDLE SNAPSHOT
               |
               v
MARKET PRIMITIVE KERNEL v2
CALCULATE OBSERVABLES ONCE
               |
  +------------+-------------+-------------+-------------+
  |            |             |             |             |
  v            v             v             v             v
MORPHOLOGY   LEVEL GRAPH   VOL/STATE   STRUCTURE     INDICATOR DAG
FACTS        FACTS         FACTS       PROXIES       FACTS
  |            |             |             |             |
  +------------+-------------+-------------+-------------+
               |
               v
        EPISTEMIC EVIDENCE GRAPH
 OBSERVED / DERIVED / INFERRED / HYPOTHESIS
               |
               +--------------------+
               |                    |
               v                    v
       M3.2 CONTEXT WORLD      M3.3 MEMORY WORLD
       session/index/sector    reliability/analogs
       regime/RS              calibration/drift
               |                    |
               +---------+----------+
                         |
                         v
              HYPOTHESIS / FALSIFICATION ENGINE
                         |
                         v
           SCENARIO DISTRIBUTION + UNCERTAINTY
                         |
                         v
                    D6 ARBITER ONLY
                         |
                         v
                 WAIT / WATCH / PAPER
```

---

# 14. Priority order

## P0 — semantic correctness before adding intelligence

1. Record the D6 trend-persistence directional mismatch as M4 compatibility debt.
2. Eliminate missing-volume-to-zero semantics in Chart Reasoning, Condition and Market Structure canonical paths.
3. Stop calling uncalibrated heuristic scores probabilities.
4. Add epistemic typing: fact vs inference vs hypothesis.
5. Canonicalize Market Structure before allowing richer use downstream.

## P1 — calculate once / reliability

6. Build Market Primitive Kernel v2 as a shadow extension.
7. Add true range/Wilder ATR separately from legacy average range.
8. Add direction + persistence separately in Chart Reasoning.
9. Convert levels to dynamic-tolerance zones with lifecycle.
10. Unify indicator registry/runtime metadata.

## P2 — stronger intelligence

11. Direction-symmetric Condition v2.
12. Multi-hypothesis state instead of one dominant label.
13. Structure swing hierarchy + zone lifecycle.
14. Indicator dependency DAG and redundancy control.
15. Session-normalized volume/RVOL once M3.2/M3.3 historical support exists.

## P3 — predictive intelligence

16. M3.3 reliability/calibration.
17. OOD/drift/change-point state.
18. scenario/path probabilities rather than single next-direction prediction.
19. hypothesis falsification loop.
20. calibrated uncertainty / abstention.

## P4 — optional higher-information sources

21. real order-flow/depth/imbalance data if legally and operationally available;
22. derivatives context;
23. event/news/calendar context;
24. corporate-action adjusted levels;
25. cross-market source snapshots.

---

# 15. How to modify the repository safely

Do not rewrite the locked M3.1 files in-place first.

Recommended shadow additions:

```text
apps/api/app/behavior/decision_spine/market_primitive_kernel_v2.py
apps/api/app/behavior/decision_spine/canonical_candle_morphology_v2.py
apps/api/app/behavior/decision_spine/canonical_chart_state_v2.py
apps/api/app/behavior/decision_spine/canonical_structure_intelligence.py
apps/api/app/behavior/decision_spine/canonical_level_graph_v2.py
apps/api/app/behavior/decision_spine/canonical_indicator_contracts_v2.py
apps/api/app/behavior/decision_spine/evidence_graph.py
apps/api/app/behavior/decision_spine/hypothesis_state.py
```

Run them in shadow mode with:

```text
used_for_probability=false
may_set_final_band=false
may_execute=false
```

Compare old vs new on replay. Promote only under explicit later migration gates.

---

# 16. Definition of semantic hardening success

M3.1.1 is successful when:

- every value is typed as observed/derived/inferred/hypothesis/predictive;
- missing never becomes neutral/zero unless zero is truly observed;
- trend direction and persistence are separate;
- all price/volume primitive calculations are calculate-once where practical;
- no heuristic score is called probability without calibration;
- OHLCV proxies are visibly labeled proxies;
- Market Structure has source quality and zone lifecycle;
- Level Intelligence has dynamic tolerance and level lifecycle;
- all 94 registered indicator outputs have an explicit runtime coverage state;
- indicator runtime metadata uses one canonical registry;
- correlated indicators cannot inflate independent evidence count;
- replay demonstrates no future leakage;
- new shadow intelligence remains zero-authority until M4/M3.3 proof gates;
- D6 remains the sole final-band authority;
- no execution authority is introduced.

M3.1 remains GREEN/LOCKED for its verified migration contract. This hardening plan does **not** claim M3.1 was wrong; it distinguishes infrastructure correctness from semantic/predictive completeness.
