# Trade Vision — Kronos Hardening and Integration Reference

**Status:** CANONICAL ENGINEERING REFERENCE / LIVING DOCUMENT  
**Repository:** `onlyvictus-bit/trade-vision-app`  
**Primary planning branch:** `m4-d6-orchestration-redesign`  
**Created:** 2026-09-11  
**Purpose:** Preserve the Kronos audit, weaknesses, target architecture, hardening plan, proof requirements, and implementation rules for all future Kronos coding and editing work.

---

## 0. How future coding sessions must use this document

This document is a **reference and implementation contract**, not a claim that every listed weakness remains present forever.

Before changing Kronos code, every future coding session must:

1. Verify the current branch head and exact repository state.
2. Read the current implementation before editing, especially:
   - `apps/kronos-service/main.py`
   - `apps/kronos-service/kronos_runtime.py`
   - `apps/api/app/behavior/kronos_proxy.py`
   - canonical snapshot / PIT / market-calendar modules
   - relevant tests and workflows.
3. Compare current code against the requirements in this document.
4. Do not blindly re-implement an item that has already been fixed.
5. Preserve all Trade Vision safety and epistemic invariants.
6. Add adversarial, replay, causality, determinism, availability, performance, and authority tests for every material change.
7. Do not mark a Kronos capability trusted merely because code exists; require evidence and OOS proof.
8. Do not give Kronos execution authority or let it bypass D6.
9. Update this document when a material Kronos design decision changes.

The original audit was performed against an earlier branch snapshot. At the time this reference was saved, the branch had advanced further. Therefore **repository truth always outranks this document's historical current-state observations**.

---

# 1. Permanent Trade Vision safety and epistemic laws

Kronos is a research forecasting specialist only.

Permanent safety contract:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true

Kronos cannot execute orders.
Kronos cannot override NO-TRADE.
Kronos cannot override risk.
Kronos cannot become final-band authority.
D6 remains the final decision authority unless the architecture is explicitly and separately redesigned.
```

Permanent epistemic rules:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no_signal != unavailable
no_output != neutral
missing volume != zero volume
```

Permanent causal law:

```text
No incomplete candle may have authority.
No future information may enter an earlier decision.
Every M2+ evidence object must be point-in-time causal.
Every canonical forecast must be traceable to its exact input snapshot.
```

Core architecture law:

```text
RAW FACT CALCULATED ONCE
        ↓
MANY BRAINS INTERPRET
        ↓
EVERY INTERPRETATION TRACEABLE
```

Kronos must remain a **bounded predictive hypothesis provider**, not a hidden decision-maker.

---

# 2. What Kronos is and why it belongs in Trade Vision

Official upstream project: `shiyu-coder/Kronos`.

Kronos is an open-source foundation model for financial candlestick / K-line sequences. The upstream authors report training on more than 12 billion K-line records from 45 exchanges.

Relevant public model family:

| Model | Approx. parameters | Maximum context | Intended Trade Vision role |
|---|---:|---:|---|
| Kronos-mini | 4.1M | 2048 candles | Warm primary research model |
| Kronos-small | 24.7M | 512 candles | Optional challenger after benchmarking |
| Kronos-base | 102.3M | 512 candles | Heavier challenger |
| Kronos-large | not publicly released | — | Excluded |

The existing architecture correctly uses the real upstream model classes rather than creating a fake Kronos-like algorithm:

```text
Kronos
  ↓
KronosTokenizer
  ↓
KronosPredictor
```

The isolated-service architecture is also correct:

```text
Trade Vision main API
        │
        │ HTTP / bounded contract
        ▼
isolated Kronos service
        │
        ▼
PyTorch + upstream Kronos
```

Heavy ML dependencies should remain outside the main Decision Spine process.

---

# 3. Audit baseline and why the previous score was only about 6.5/10

The integration was judged strong in architecture and safety but incomplete scientifically.

Historical audit scorecard:

| Area | Historical score | Strong target |
|---|---:|---:|
| Architecture / isolation | 9/10 | 9–10/10 |
| Correct use of real upstream Kronos | 8/10 | 9+/10 |
| Safety / zero execution authority | 10/10 | 10/10 |
| Forecast capability utilisation | 6/10 | 9/10 |
| Uncertainty / calibration quality | 3–4/10 | 9/10 |
| PIT / epistemic correctness | 5–6/10 | 9.5/10 |
| Runtime efficiency for many stocks | 5/10 | 8.5–9/10 |
| Real-model validation / proof | 4–5/10 | 9/10 |

The main problem was **not** that Kronos was fake or incorrectly placed.

The problem was that Trade Vision was using a powerful model through a relatively weak scientific adapter:

```text
CURRENT / WEAK FORM

good Kronos engine
      ↓
basic adapter
      ↓
one forecast path
      ↓
hand-written confidence-like numbers
      ↓
Trade Vision
```

Target form:

```text
STRONG FORM

good Kronos engine
      ↓
canonical closed/PIT data
      ↓
exact provenance
      ↓
model-aware context
      ↓
many sampled futures
      ↓
empirical distribution
      ↓
real uncertainty
      ↓
walk-forward OOS calibration
      ↓
regime-specific reliability
      ↓
bounded predictive evidence
      ↓
M4
      ↓
D6
```

---

# 4. Historical implementation weaknesses that must be checked before future edits

At audit time, the following weaknesses were identified. Future work must re-check whether each still exists.

| Area | Historical implementation | Problem |
|---|---|---|
| Sampling | `sample_count=1` | Uses one possible future instead of a useful forecast distribution |
| Mini context | request cap `<=512` | Under-uses mini's 2048-candle maximum context |
| Uncertainty | ATR-like synthetic bands | Not true Kronos forecast dispersion |
| Continuation/reversal/range values | return-based formulas | Not empirically calibrated probabilities |
| Forecast confidence | hand-written formula | Must not be presented as calibrated confidence |
| Missing volume | `None -> 0.0` | Violates `missing != zero` |
| Point-in-time | `decision_time_ns` optional | Too weak for canonical no-lookahead claims |
| Closed candle | incomplete check not truly bar-close proof | Can misrepresent insufficient history as incomplete-bar validation |
| Timeframes | incomplete mapping for `30m` / `4H` and fallback behavior | Timestamp semantics can silently become wrong |
| Market calendar | generic business-day behavior | Must use canonical NSE calendar / sessions |
| Provenance | `MODEL_REVISION = "local-snapshot"` | Not enough for exact replay |
| Real-model CI | contract tests mainly mocked bridge | Does not prove installed inference artifacts work |
| Throughput | global inference lock | Safe but serial at scale |
| Model switching | one runtime swaps mini/base | Reload cost and GPU churn |
| High uncertainty | real path historically did not automatically discard high-uncertainty cases | Less conservative than desired |
| ATR naming | average high-low proxy used in places | Must not be confused with canonical true range / ATR |
| Determinism | seeds set but environment not fully pinned/deterministic | `deterministic=true` can overstate reproducibility |
| Amount | no explicit amount input in service path | Upstream may synthesize; synthetic must be marked synthetic |

The future implementation must solve these at the **root semantic level**, not only change labels.

---

# 5. Forecast capability utilisation — target 9/10

## 5.1 Root cause of the low score

Kronos supports stochastic generation, but the audited service requested a single sample.

Conceptually:

```text
sample_count = 1
```

asks:

> Give one possible future.

Trade Vision needs to ask:

> Show a set of plausible futures, preserve their disagreement, and tell us what can and cannot be inferred from that distribution.

A second under-use was context. Kronos-mini can accept substantially more history than the service-level request contract historically allowed.

## 5.2 Required improvements

### A. Multi-path forecasting

Support an explicitly versioned sampling configuration including:

```text
seed set
sample count
T / temperature
top_p
forecast horizon
context length
model identity
```

For research and calibration, retain individual forecast paths rather than only their average.

If upstream `sample_count=N` returns an aggregated path and does not expose individual paths, Trade Vision may use repeated deterministic single-sample calls with recorded distinct seeds, or create a thin upstream-compatible sampler adapter that exposes the raw paths without changing the underlying model semantics.

### B. Multi-horizon evaluation

At minimum benchmark horizons such as:

```text
+1 bar
+3 bars
+5 bars
+6 bars
+10 bars
+12 bars
+24 bars
```

Do not infer that a model good at +1 is good at +12.

Reliability must be horizon-specific.

### C. Model-aware context

Do not impose one universal history cap.

Suggested research grid:

| Timeframe | Candidate contexts |
|---|---|
| 5m | 64, 128, 256, 512, 1024, 2048 |
| 15m | 64, 128, 256, 512, 1024 |
| 1H | 64, 128, 256, 512 |
| Daily | 32, 64, 128, 256, 512 |

These are experiment candidates, not mandatory production settings.

More context is not automatically better. Select context only from OOS evidence.

### D. Model challengers

Use mini as the warm primary candidate because it is small and has long context.

Evaluate small/base separately. Do not assume a bigger model is better.

Promotion requires demonstrated incremental value net of latency and resource cost.

### E. Optional future upstream capabilities

Do not use every Kronos feature merely because it exists.

```text
price forecast
   → predictive research candidate

volatility-related forecast
   → separate evidence family
   → only after calibration

synthetic candle generation
   → stress testing / adversarial replay only
   → NEVER real market evidence

fine-tuning
   → research laboratory
   → separately versioned challenger
   → OOS promotion only
```

---

# 6. Uncertainty and calibration — target 9/10

This was the weakest historical area.

## 6.1 What must not happen

Do not manufacture a single path and then call ATR-shaped bands "Kronos uncertainty".

Do not calculate:

```text
continuation_probability
reversal_probability
range_probability
forecast_confidence
```

from hand-written return formulas and present them as if Kronos generated or calibrated those probabilities.

Before calibration, use honest names such as:

```text
raw_bullish_sample_fraction
raw_bearish_sample_fraction
raw_sideways_sample_fraction
heuristic_continuation_score
path_dispersion
```

## 6.2 Build an empirical forecast distribution

For example, generate 16/32/64 independent research paths where latency budget permits.

From those paths derive at least:

```text
P10 / P25 / P50 / P75 / P90 close path
return distribution
directional sample fractions
path-to-path dispersion
maximum favorable excursion distribution
maximum adverse excursion distribution
tail-risk statistics
path agreement / disagreement
cross-horizon agreement
```

Example conceptual output:

```text
Current price = 2900
32 Kronos paths

P10 = 2871
P25 = 2889
P50 = 2918
P75 = 2941
P90 = 2969

UP samples        = 21/32
DOWN samples      = 8/32
SIDEWAYS samples  = 3/32
```

`21/32` is a raw sample fraction. It is **not automatically a 65.6% calibrated market probability**.

## 6.3 Historical calibration

Calibration asks:

> When the model gives a certain raw belief/score, how often does the event actually occur out of sample?

Example:

```text
Raw bullish fraction near 0.70
Actual bullish frequency = 0.52
```

Then Trade Vision must learn that this region is overconfident.

Only after calibration may the system expose a field such as:

```text
calibrated_probability = 0.53
calibration_sample_count = 2847
calibration_error = 0.031
calibration_scope = {...}
```

## 6.4 Required calibration metrics

Use metrics appropriate to the output being evaluated, including where applicable:

```text
Brier score
log loss
Expected Calibration Error (ECE)
reliability diagrams
quantile coverage
pinball loss
CRPS / distributional score
prediction-interval coverage
prediction-interval width
directional accuracy
RankIC / rank metrics where justified
MAE / path MAE / terminal-close MAE
MFE / MAE calibration
```

Do not use a metric simply because it is popular; the metric must match the prediction contract.

## 6.5 Abstention is a feature

A strong Kronos integration must be able to return:

```text
UNKNOWN
UNAVAILABLE
INSUFFICIENT_HISTORY
INSUFFICIENT_CALIBRATION
HIGH_UNCERTAINTY
OUT_OF_DISTRIBUTION
STALE
CONFLICTED
```

The strongest system is not the one that always produces a confident direction.

---

# 7. PIT and epistemic hardening — target 9.5/10

## 7.1 Mandatory canonical binding

Any Kronos output eligible to enter M4 must be bound to an exact causal snapshot.

Canonical request should require or inherit:

```text
decision_time_ns
snapshot_id
snapshot_hash
source snapshot provenance
last_closed_bar_timestamp
bar-close semantics
timeframe identity
instrument identity
data availability state
```

A canonical result must be able to prove:

```text
last_authoritative_input_bar_close <= decision_time
```

Do not set `no_future_leakage=true` merely because generic validation passed.

The proof must be explicit.

## 7.2 Closed-candle law

Example at 10:17:32 for 5-minute candles:

```text
10:15–10:20 bar = FORMING → reject for canonical authority
10:10–10:15 bar = CLOSED  → may be used
```

`len(bars) < minimum_history` is an insufficient-history condition.

It is **not** an incomplete-candle test.

These must be separate fields and separate failure reasons.

## 7.3 Missing volume and amount

Never silently transform:

```text
volume = None
```

into:

```text
volume = 0.0
```

At the Trade Vision evidence layer, record:

```text
volume_availability
volume_provenance
volume_imputation_policy
volume_imputed
amount_availability
amount_provenance
amount_imputed / synthesized
```

If upstream Kronos requires a numerical placeholder, any imputation must be explicit, versioned, replayable, and must degrade evidence status until separately validated.

Synthetic amount must be marked synthetic, never observed.

## 7.4 Timeframe correctness

No unknown timeframe may silently fall back to 5 minutes.

All supported timeframes require exact canonical definitions, including at minimum those exposed by the outer API, such as:

```text
1m
3m
5m
15m
30m
1H
4H
1D / daily
1W / weekly
```

If a timeframe is unsupported, return explicit `UNSUPPORTED_TIMEFRAME`.

## 7.5 NSE calendar correctness

Future timestamp generation and bar closure must use the same canonical Indian-market calendar/session logic as the rest of Decision Spine.

Do not rely only on generic Monday-Friday `BDay` behavior.

Calendar semantics must cover:

```text
NSE holidays
special sessions if applicable
market open / close
partial final interval handling
session boundaries
weekly/monthly transitions
```

## 7.6 Exact model and runtime provenance

Replace vague provenance such as:

```text
MODEL_REVISION = "local-snapshot"
```

with a replay-grade manifest.

Every canonical/research receipt should be able to identify:

```text
upstream Kronos git SHA
model repository + exact revision
model weight SHA256
tokenizer repository + exact revision
tokenizer weight SHA256
adapter version
service version
Python version
PyTorch version
CUDA version / device runtime
critical dependency lock digest
container/image digest if containerized
model name
max context
actual context used
forecast horizon
seed(s)
temperature
top_p
sample count
input snapshot hash
output hash
```

## 7.7 Determinism claims

Setting random seeds alone is not sufficient to assert universal deterministic replay.

The determinism contract should distinguish:

```text
seed_reproducible_same_environment
fully_deterministic_algorithms_enabled
cross_device_reproducible
cross_dependency_version_reproducible
```

If only the first is proven, do not simply publish `deterministic=true` without qualification.

---

# 8. Runtime efficiency for many stocks — target 8.5–9/10

The historical global inference lock was safe but serial.

At small scale:

```text
RELIANCE → inference
TCS      → waits
INFY     → waits
SBIN     → waits
```

At NSE-universe scale, this becomes expensive, especially with many horizons and sampled paths.

## 8.1 Target scheduler architecture

```text
forecast requests
        ↓
Kronos scheduler
        │
        ├── validation / eligibility
        ├── priority
        ├── snapshot-hash cache
        ├── request deduplication
        ├── adaptive sampling budget
        └── queue
                ↓
          inference workers
          ┌─────┴─────┐
          ↓           ↓
   warm mini       challenger
   primary         worker(s)
```

## 8.2 Cache key

At minimum include:

```text
model identity / model hash
adapter version
snapshot hash
symbol
timeframe
context length
forecast horizon
seed or seed set
sampling configuration
calendar/session version
```

A cache hit is valid only if every causal input is identical.

## 8.3 Request deduplication

If multiple Trade Vision modules request the same forecast for the same immutable snapshot, compute once and share the same traced evidence object.

This follows the project law:

```text
RAW FACT CALCULATED ONCE → MANY BRAINS INTERPRET
```

## 8.4 Adaptive sampling budget

Example policy to benchmark rather than hard-code blindly:

```text
offline proof / calibration        32–64+ paths
important ambiguous research case 16–32 paths
normal bounded research case       8–16 paths
invalid / stale / unavailable      0 model inference
```

Sampling budget should be a documented function of purpose, latency budget, model uncertainty, and validation state.

## 8.5 Warm workers

Avoid repeated:

```text
mini → unload → base → unload → mini
```

Prefer:

```text
Worker A = Kronos-mini warm primary
Worker B = small/base challenger when resources justify it
```

A single-process model-switching path may remain for low-resource development, but production research benchmarks should account for reload cost.

## 8.6 Scaling measurements

Track at minimum:

```text
p50 / p95 / p99 latency
throughput forecasts/sec
queue delay
GPU utilization
VRAM allocation
model load time
cache hit rate
deduplication rate
samples/sec
failure rate
timeout rate
fallback rate
```

Performance optimisation must never weaken PIT, availability, or safety checks.

---

# 9. Real-model validation and proof — target 9/10

Code integration is not model proof.

A model must demonstrate where it adds value on Trade Vision's actual Indian-market problem.

## 9.1 Build a Kronos Proof Laboratory

Every historical forecast must behave as if it is truly living at that historical instant.

Example:

```text
Historical decision time: 2025-07-10 10:00 IST

Allowed:
all information causally available by 10:00

Forbidden:
10:05 bar
10:10 bar
10:15 bar
rest of session
tomorrow's information
revised data unavailable at 10:00
```

Workflow:

```text
freeze PIT input snapshot
        ↓
generate Kronos forecast
        ↓
store immutable forecast receipt
        ↓
advance historical clock
        ↓
reveal outcome
        ↓
score forecast
        ↓
repeat across large OOS sample
```

## 9.2 Always compare against simple baselines

Kronos must earn its complexity.

Compare against at least:

```text
last-close persistence
random walk
historical drift
simple momentum
EMA / trend baseline
ATR-based naive movement baseline
historical mean / seasonal naive baseline
M3 canonical trend state alone
other already-proven simple Trade Vision predictors where appropriate
```

If Kronos directional accuracy is 57% and a simple baseline is 59%, Kronos has not proven value for that scope.

If Kronos is only superior in a specific regime, use it only in that proven regime.

## 9.3 Do not create one global Kronos accuracy number

Build a reliability profile / reliability cube indexed by relevant dimensions.

Candidate axes:

```text
symbol or liquidity bucket
instrument class
timeframe
forecast horizon
time of day
market regime
trend / chop state
volatility regime
gap regime
ORB phase
event-day state
expiry context if relevant
data-completeness state
model version
sampling configuration
```

Example:

| Context | Reliability state |
|---|---|
| RELIANCE / 5m / +3 / trending | strong if OOS proof supports it |
| RELIANCE / 5m / +12 / chop | weak if OOS proof shows degradation |
| NIFTY / 15m / +3 / expansion | strong only if proven |
| SBIN / 5m / result day | insufficient evidence until sample exists |
| NSE universe / 1H / calm | medium only if proven |

## 9.4 Minimum promotion evidence

A future `KronosReliabilityProfile` should carry fields such as:

```text
model_revision
calibration_revision
scope
sample_count
OOS window
walk_forward_scheme
baseline identities
metric set
metric values
calibration error
interval coverage
latency profile
known failure regimes
availability conditions
promotion status
expiry / revalidation date
```

A forecast can receive canonical bounded weight only when its exact scope has sufficient current proof.

## 9.5 Edge decay

Markets change.

Therefore calibration/reliability must age.

Support:

```text
fresh
aging
stale
invalidated
insufficient_recent_sample
```

A once-good model must not retain permanent credibility.

---

# 10. M4 evidence contract

M4 must not receive only:

```text
Kronos says BULLISH.
```

A strong evidence object should look conceptually more like:

```text
claim:
  direction: bullish
  epistemic_level: predictive
  model: Kronos-mini
  forecast_horizon: +3 bars
  raw_direction_fraction: 0.78
  calibrated_probability: 0.61        # only if actually calibrated
  uncertainty_state: moderate
  interval_coverage_state: healthy
  reliability_scope_sample_count: 1842
  reliability_state: moderate
  calibration_error: ...
  snapshot_hash: ...
  decision_time: ...
  last_closed_bar_time: ...
  model_provenance: ...
  input_availability: ...
  contradictions: ...
  freshness: ...
  invalidation_conditions: ...
```

M4 may reason about it.

M4 must not treat it as independent confirmation if its evidence ancestry overlaps another predictor.

D6 remains final authority.

---

# 11. High-uncertainty and unavailable behavior

The real-model path must be at least as conservative as test/mock behavior.

Do not allow a real forecast to become more authoritative merely because it came from the real model.

High uncertainty should be able to produce:

```text
forecast_generated = true
canonical_influence_allowed = false
reason = HIGH_UNCERTAINTY
```

Likewise:

```text
missing_volume
unsupported_timeframe
calendar_uncertainty
PIT_proof_failure
snapshot_hash_mismatch
model_provenance_failure
insufficient_history
stale_calibration
out_of_scope_reliability
```

should degrade or block evidential use according to an explicit contract.

Never convert uncertainty into neutral evidence.

---

# 12. Correct ATR / volatility semantics

If a helper computes only average high-low candle range, do not call it canonical ATR.

Canonical ATR must use true-range semantics including prior close/gap effects and an explicitly defined lookback/timeframe.

Possible fields:

```text
mean_high_low_range_proxy
true_range
atr_14
atr_pct
```

Keep proxy and canonical concepts separate.

---

# 13. Fine-tuning policy

Do not fine-tune first and validate later.

Correct sequence:

```text
1. prove zero-shot baseline
2. identify where zero-shot succeeds/fails
3. create frozen train/validation/OOS partitions
4. fine-tune separately versioned challenger
5. compare challenger against zero-shot Kronos and simple baselines
6. evaluate calibration and regime robustness
7. promote only if incremental OOS value is real
```

A fine-tuned model must never overwrite the identity of the base model in historical receipts.

Store separate model/tokenizer provenance and training-data manifest hashes.

---

# 14. CI and test requirements

Main API tests that mock an HTTP response are useful but insufficient.

The Kronos program should have multiple test layers.

## 14.1 Contract/unit tests

Test:

```text
schema validation
safety flags
authority flags
missing/unavailable semantics
timeframe rejection
snapshot hash binding
output hashes
fallback quarantine
```

## 14.2 Causality/PIT adversarial tests

Test at minimum:

```text
future candle injection
forming candle injection
decision time omitted
snapshot hash mismatch
out-of-order timestamps
duplicate timestamps
sequence mismatch
cross-session interval
holiday/session transition
one-bar / insufficient history
```

## 14.3 Data-semantic tests

Test:

```text
volume missing
true zero volume
amount missing
synthetic amount
NaN / inf
zero-range candle
invalid OHLC
corporate-action-adjusted inputs where relevant
```

## 14.4 Sampling/distribution tests

Test:

```text
same seed same-environment replay
seed-set reproducibility
multiple-path preservation
quantile ordering
path count
no probability naming before calibration
high-dispersion abstention
```

## 14.5 Timeframe/calendar tests

Test every supported timeframe, including historically problematic 30m/4H cases.

Test NSE holidays and session boundaries through the canonical calendar.

No silent fallback interval is allowed.

## 14.6 Real-model integration verification

Add a dedicated real-model verification path where feasible.

It should prove:

```text
expected upstream source revision installed
expected model/tokenizer hashes installed
model loads
known frozen input snapshot predicts without crash
output schema validates
replay receipt produced
no execution authority
```

If full model artifacts are too heavy for ordinary CI, create a dedicated host verification workflow/artifact receipt rather than pretending mocks are equivalent to real inference.

## 14.7 Performance tests

Measure:

```text
single-symbol latency
multi-symbol queue latency
cache behavior
deduplication
concurrent request behavior
VRAM growth
model-switch penalty
sampling budget scaling
```

## 14.8 Regression tests

Every fixed Kronos defect should receive a named regression test so it cannot silently return.

---

# 15. Recommended implementation sequence

This order is intentional.

## Stage K1 — Epistemic Hardening

Fix first:

- mandatory PIT decision binding for M4-eligible forecasts
- exact snapshot/hash lineage
- true closed-candle validation
- missing volume/amount semantics
- strict timeframe handling
- canonical NSE calendar integration
- replay-grade model/runtime provenance
- qualified determinism claims
- mock/synthetic/fallback quarantine

**Exit gate:** Kronos cannot produce canonically eligible evidence without proving causal inputs and provenance.

## Stage K2 — Distribution Engine

Build:

- multi-seed / multi-path forecasting
- raw path retention
- quantiles
- direction fractions
- path dispersion
- MFE/MAE distribution
- high-uncertainty abstention
- honest pre-calibration vocabulary

**Exit gate:** uncertainty comes from model-path behavior rather than hand-shaped bands.

## Stage K3 — Calibration Engine

Build:

- walk-forward PIT evaluator
- immutable prediction receipts
- outcome scoring
- calibration maps
- reliability diagrams
- Brier/log-loss where applicable
- interval/quantile calibration
- minimum sample rules
- stale-calibration handling

**Exit gate:** no field is called calibrated probability/confidence unless OOS calibration evidence supports it.

## Stage K4 — Capability Optimizer

Benchmark:

- context lengths
- horizons
- T / top_p
- sampling budgets
- mini vs small/base
- timeframe-specific configurations
- regime-specific configurations

**Exit gate:** production/research configuration is selected from measured OOS evidence, not intuition.

## Stage K5 — Runtime Engine

Build:

- snapshot-hash cache
- deduplication
- scheduler/queue
- warm mini worker
- separate challenger worker strategy
- adaptive sampling budgets
- observability
- graceful degradation

**Exit gate:** broad-universe forecasting is resource-efficient without weakening safety or causality.

## Stage K6 — Reliability Profile and M4 Wiring

Build:

- reliability cube/profile
- predictive evidence contract
- correlation/dependency identity
- bounded M4 weighting
- abstention / invalidation
- evidence freshness

**Exit gate:** M4 sees a calibrated, traceable predictive hypothesis; D6 remains sole final authority.

---

# 16. Promotion rules

A Kronos change is not GREEN merely because tests pass.

For capability promotion, require all relevant gates:

```text
implementation complete
unit tests green
adversarial tests green
PIT/replay tests green
full regressions green
real-model verification green
OOS proof sufficient
baseline comparison acceptable
calibration acceptable
latency/resource budget acceptable
safety/authority audit green
exact-head CI/workflow green
```

If any necessary proof is unavailable, mark the state explicitly:

```text
IMPLEMENTED_BUT_UNPROVEN
RESEARCH_ONLY
INSUFFICIENT_EVIDENCE
AMBER
```

Never use a green label to hide missing empirical proof.

---

# 17. Suggested reliability evidence states

Use explicit states rather than fabricating neutral numbers:

```text
UNAVAILABLE
INSUFFICIENT_HISTORY
INSUFFICIENT_SAMPLE
UNCALIBRATED
CALIBRATED_WEAK
CALIBRATED_MODERATE
CALIBRATED_STRONG
STALE
HIGH_UNCERTAINTY
OUT_OF_SCOPE
CONFLICTED
INVALIDATED
```

The mapping from these states to M4 influence must be versioned and testable.

---

# 18. Suggested forecast receipt structure

A future receipt may include fields conceptually like:

```text
KronosForecastReceipt

identity:
  forecast_id
  adapter_version
  service_version
  model_id
  model_revision
  tokenizer_id
  tokenizer_revision

causality:
  decision_time_ns
  last_closed_bar_time_ns
  snapshot_id
  snapshot_hash
  no_future_leakage_proven
  closed_candle_proven

input:
  symbol
  timeframe
  context_length
  bar_count
  volume_availability
  amount_availability
  imputation_state
  source_provenance

sampling:
  seed_set
  temperature
  top_p
  sample_count
  horizon_bars

raw_distribution:
  path_refs_or_hashes
  p10
  p25
  p50
  p75
  p90
  bullish_fraction
  bearish_fraction
  sideways_fraction
  dispersion
  tail_risk

calibration:
  state
  profile_revision
  scope
  sample_count
  calibrated_probability
  calibration_error
  interval_coverage
  stale

eligibility:
  uncertainty_state
  reliability_state
  M4_evidence_eligible
  blockers

safety:
  research_only = true
  trade_allowed = false
  order_routing_enabled = false
  live_trading_blocked = true
  cannot_override_no_trade = true
  cannot_override_risk = true

provenance:
  upstream_git_sha
  model_weight_sha256
  tokenizer_weight_sha256
  runtime_lock_digest
  device_profile
  output_hash
```

Exact schema names may evolve, but the semantic distinctions must remain.

---

# 19. What must never be done

Do **not**:

1. Rebuild a fake Kronos algorithm instead of using upstream Kronos.
2. Give Kronos execution or order-routing authority.
3. Let Kronos override risk, veto, or NO-TRADE authority.
4. Treat one sampled path as certainty.
5. Call a hand-written score a probability without calibration.
6. Call ATR-shaped bands model uncertainty if they did not come from sampled-model dispersion.
7. Change missing volume to observed zero without explicit imputation semantics.
8. Use an incomplete/forming candle as canonical input.
9. Permit future leakage in backtests or replay.
10. Silently map unknown timeframes to 5m.
11. Use generic business days as a complete NSE trading calendar.
12. Claim exact replay with vague `local-snapshot` provenance.
13. Claim global deterministic behavior from seed-setting alone.
14. Treat synthetic candles/amount/volume as real observations.
15. Promote a bigger model merely because it is bigger.
16. Fine-tune before establishing a clean zero-shot baseline.
17. Use one global accuracy score across all regimes.
18. Let old calibration retain permanent authority after edge decay.
19. Count correlated descendants as independent confirmations in M4.
20. Convert missing/conflicted/unavailable evidence to neutral.

---

# 20. Target end state

The target Kronos architecture is:

```text
OFFICIAL KRONOS
      ↓
exact source/model/tokenizer provenance
      ↓
canonical closed point-in-time candles
      ↓
model-aware context
      ↓
multi-path stochastic sampling
      ↓
empirical forecast distribution
      ↓
quantiles + dispersion + tail risk
      ↓
walk-forward OOS calibration
      ↓
NSE / timeframe / horizon / regime reliability profile
      ↓
uncertainty-aware abstention
      ↓
bounded predictive evidence
      ↓
M4 reasoning
      ↓
D6 final decision
```

The desired score after sufficient implementation **and proof** is approximately:

| Area | Target |
|---|---:|
| Forecast capability utilisation | 9/10 |
| Uncertainty / calibration | 9/10 |
| PIT / epistemic correctness | 9.5/10 |
| Runtime efficiency | 8.5–9/10 |
| Real-model validation | 9/10 |
| Safety / zero execution authority | 10/10 |

A forecasting system should not aim for a fictional permanent 10/10 prediction score. Markets change.

The strongest Kronos specialist is one that knows:

```text
when it has evidence of edge
when it has no evidence of edge
how uncertain the current forecast is
whether the input is causally valid
whether its calibration is still fresh
whether the current regime is inside its proven scope
when it must abstain
when M4 should ignore it
```

Its most important valid output may sometimes be:

```text
I DON'T KNOW / INSUFFICIENT EVIDENCE
```

That behavior is a strength, not a defect.

---

# 21. Upstream references

- Official repository: `https://github.com/shiyu-coder/Kronos`
- Paper: `https://arxiv.org/abs/2508.02739`
- Upstream fine-tuning implementation: `https://github.com/shiyu-coder/Kronos/tree/master/finetune_csv`

Future work must verify current upstream revisions before adopting new upstream behavior.

---

# 22. Final implementation directive for future agents

When asked to "improve Kronos," do not start over.

Continue the existing Trade Vision / Decision Spine implementation and apply this sequence:

```text
VERIFY CURRENT GITHUB TRUTH
        ↓
IDENTIFY WHICH REFERENCE ITEMS ARE STILL OPEN
        ↓
FIX SEMANTICS / PIT / PROVENANCE FIRST
        ↓
ADD REAL DISTRIBUTION + UNCERTAINTY
        ↓
BUILD OOS CALIBRATION + RELIABILITY
        ↓
OPTIMIZE CAPABILITY AND RUNTIME
        ↓
WIRE ONLY PROVEN, BOUNDED EVIDENCE INTO M4
        ↓
KEEP D6 FINAL AUTHORITY
        ↓
RUN ADVERSARIAL + REPLAY + REGRESSION + REAL-MODEL VERIFICATION
        ↓
VERIFY EXACT-HEAD CI
        ↓
UPDATE THIS REFERENCE WITH WHAT IS NOW PROVEN
```

Repository truth, causal correctness, explicit uncertainty, and empirical proof outrank convenience.