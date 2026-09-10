# M4 Hypothesis Box v2 — Market Deliberation Implementation Plan

Date: 2026-09-10
Status: FORMAL IMPLEMENTATION PLAN — CODE BUILD REFERENCE
Branch: `m4-d6-orchestration-redesign`
Parent references:
- `docs/M4_TRADING_COGNITIVE_ARCHITECTURE_REFERENCE_2026-09-10.md`
- `docs/M4_HYPOTHESIS_BOX_REFERENCE_2026-09-10.md`

## 1. Mission

Hypothesis Box v2 must not be another indicator scorer, signal voter, or free-form AI opinion layer.

It should become a bounded **Market Deliberation System** that:

1. receives immutable point-in-time market facts;
2. separates facts from interpretation;
3. builds a structured world model;
4. identifies the market question currently being resolved;
5. generates several competing hypotheses;
6. builds arguments for and against each hypothesis;
7. understands dependency and redundancy between evidence;
8. predicts observable next events for each hypothesis;
9. compares those expectations with subsequent closed-bar evidence;
10. strengthens, weakens, invalidates, expires, or resolves hypotheses over time;
11. uses real M3.3 memory and validated Kronos only as bounded challengers;
12. detects unknown / out-of-distribution states;
13. identifies what missing observation would best distinguish competing stories;
14. produces a deterministic, auditable reasoning receipt;
15. never executes and never owns final WAIT / WATCH / PAPER-CANDIDATE authority.

D6 / `FINAL_CONFLUENCE_ARBITER` remains the sole final-band authority.

---

# 2. Constitutional laws

These laws are mandatory and must be tested as invariants.

```text
LAW-HB-001  Hypothesis Box never routes an order.
LAW-HB-002  Hypothesis Box never owns final WAIT/WATCH/PAPER-CANDIDATE.
LAW-HB-003  Every market fact is traceable to a PIT-safe source.
LAW-HB-004  No synthetic/fallback price level may masquerade as real S/R.
LAW-HB-005  Missing evidence remains missing.
LAW-HB-006  Stale evidence remains explicitly stale.
LAW-HB-007  Incomplete/future candles cannot enter causal reasoning.
LAW-HB-008  Indicator duplication cannot manufacture independent evidence.
LAW-HB-009  Every serious thesis must have a serious anti-thesis.
LAW-HB-010  Every active directional hypothesis must specify falsifiable expected observations.
LAW-HB-011  Every hypothesis needs invalidation or an explicit reason invalidation is unavailable.
LAW-HB-012  Every hypothesis has a horizon and expiry.
LAW-HB-013  Contradictions cannot silently disappear through averaging.
LAW-HB-014  Multiple horizons remain distinguishable.
LAW-HB-015  Historical analogues report raw matches and independent episode counts separately.
LAW-HB-016  Mock/synthetic memory never enters canonical production reasoning.
LAW-HB-017  Mock/unvalidated Kronos never enters canonical production reasoning.
LAW-HB-018  Kronos cannot create final decision authority.
LAW-HB-019  Free-form text cannot create a canonical market fact.
LAW-HB-020  Probabilities cannot be published without empirical calibration provenance.
LAW-HB-021  OOD / novelty can force abstention / NO_EDGE.
LAW-HB-022  Same snapshot + same policy versions = same structured receipt.
LAW-HB-023  Live outcomes cannot silently self-modify production reasoning policy.
LAW-HB-024  Learning changes require versioned offline validation and promotion.
LAW-HB-025  D6 remains sole final-band authority.
```

Preserve project-wide laws:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
future != causal
unfinished != closed
stale != fresh
correlated facts != independent evidence
label observed later != label available now
```

---

# 3. Target architecture

```text
IMMUTABLE D2 SNAPSHOT
        |
        v
MARKET FACT KERNEL
        |
        v
EPISTEMIC GATE
        |
        v
WORLD MODEL
        |
        v
MARKET QUESTION DETECTOR
        |
        v
DYNAMIC EVIDENCE ROUTER
        |
        v
EVIDENCE DEPENDENCY GRAPH
        |
        v
ARGUMENTATION GRAPH
        |
        v
COMPOSITIONAL HYPOTHESIS GENERATOR
        |
        +------------------+
        |                  |
        v                  v
   THESIS BUILDER     ANTI-THESIS BUILDER
        |                  |
        +--------+---------+
                 |
                 v
         TEMPORAL PATH COMPILER
                 |
        +--------+---------+
        |                  |
        v                  v
   M3.3 MEMORY        VALIDATED KRONOS
        |                  |
        +--------+---------+
                 |
                 v
       ADVERSARIAL FALSIFIER
                 |
                 v
       SURPRISE / BELIEF UPDATE
                 |
                 v
       OOD + UNCERTAINTY + VOI
                 |
                 v
        HYPOTHESIS RECEIPT
                 |
                 v
       D6 FINAL ARBITRATION
```

The engine must expose structured reasoning objects, not hidden prose reasoning.

---

# 4. Facts and interpretations are different objects

A raw fact is not automatically bullish or bearish.

Example:

```text
EvidenceFact:
RSI14 = 76
```

The contextual meaning may differ:

```text
breakout + RVOL expansion + accepted resistance break
=> may support continuation

weekly resistance + sweep + fading participation
=> may support exhaustion/rejection
```

Therefore use two layers:

```text
EvidenceFact
EvidenceInterpretation
```

Suggested `EvidenceFact` contract:

```text
EvidenceFact {
    fact_id
    fact_type
    symbol
    exchange
    timeframe
    effective_horizon
    value
    unit
    source_engine
    source_snapshot_hash
    source_input_hashes
    observed_at
    candle_open_at
    candle_close_at
    available_at
    decision_time
    confirmed_at
    calculation_version
    formula_version
    parameter_version
    quality_state
    freshness_state
    pit_state
    dependency_family
    dependency_ids
    source_family
    uncertainty_metadata
    trade_authority = NONE
}
```

Do not put `bullish_score`, `bearish_score`, or fake probability inside the fact object.

---

# 5. First-class epistemic states

Every important input must have one explicit state:

```text
KNOWN_VALID
UNKNOWN
UNAVAILABLE
MISSING
STALE
INCOMPLETE
CONTRADICTORY
PIT_INVALID
OOD
QUARANTINED
INSUFFICIENT
ERROR
```

These states must survive all the way to the final receipt.

Example:

```text
participant_OI = UNAVAILABLE
```

must never become:

```text
participant_OI = NEUTRAL
```

---

# 6. World model

Before generating hypotheses, construct a structured current-market world.

Example dimensions:

```text
LOCATION
- near weekly resistance
- inside / outside value
- distance to ORH/ORL/PDH/PDL/VWAP/AVWAP/profile edges

LOCAL_STRUCTURE
- bullish HH/HL
- bearish LH/LL
- balance
- transition

HIGHER_TIMEFRAME_STRUCTURE
- 15m / 1h / daily state from completed HTF bars only

VALUE_STATE
- VWAP relationship
- AVWAP relationship
- VWAP U1/U2/U3 or L1/L2/L3 position
- POC/VAH/VAL relationship

VOLATILITY_STATE
- ATR regime
- BB/KC compression
- expansion
- band-walk / extension

TREND_HORIZONS
- EMA9/20/50/200 state
- slopes
- separation
- stack
- Supertrend / Ichimoku context

MOMENTUM_STATE
- RSI
- MACD
- stochastic
- ADX/DMI
- divergence

PARTICIPATION_STATE
- volume
- time-of-day RVOL
- OBV/CMF/MFI
- available real order-flow evidence

LIQUIDITY_STATE
- S/R
- confirmed swing levels
- chart order blocks
- FVG
- sweep/SFP state
- inferred stop zones

DERIVATIVES_STATE
- price + OI change
- strike OI
- PCR
- IV / IV rank / skew
- gamma concentration
- vanna/charm
- basis / rollover
- expiry

MARKET_CONTEXT
- Nifty
- sector
- relative strength
- breadth
- VIX
- event state

MEMORY_STATE
- 9C matches
- pattern diary
- failure trajectories
- independent episode count
- OOD/regime mismatch

MODEL_STATE
- validated Kronos output availability/quality
```

The world model must describe the market without making a trade conclusion.

---

# 7. Market question detector

Do not begin with "is stock bullish?"

Identify the actual uncertainty being resolved.

Question classes:

```text
BREAKOUT_ATTEMPT
BREAKOUT_ACCEPTANCE
RETEST
LIQUIDITY_SWEEP
TREND_PULLBACK
STRUCTURAL_REVERSAL
RANGE_EDGE
COMPRESSION
VOLATILITY_EXPANSION
GAP
EXPIRY
EVENT_SHOCK
MTF_CONFLICT
VALUE_RECLAIM
VALUE_REJECTION
FAILURE_TRANSITION
UNKNOWN_MARKET_QUESTION
```

Multiple questions may coexist, each with its own horizon.

Example:

```text
Will price obtain genuine acceptance above the Rs 1,000 resistance/liquidity cluster,
or is the move becoming a sweep/rejection?
```

This is a better decision question than "bullish or bearish?"

---

# 8. Compositional hypothesis ontology

Do not hard-code hundreds of flat enum names.

Build hypotheses from dimensions:

```text
DIRECTION
UP / DOWN / NEUTRAL / TWO_SIDED

MECHANISM
CONTINUATION
REVERSAL
BREAKOUT_CONTINUATION
BREAKOUT_FAILURE
REJECTION
LIQUIDITY_SWEEP_REVERSAL
MEAN_REVERSION
COMPRESSION_EXPANSION
GAP_CONTINUATION
GAP_FADE
TREND_PULLBACK
EVENT_DISLOCATION
NO_EDGE
UNKNOWN_MECHANISM

LOCATION
ORH / ORL / PDH / PDL / VWAP / AVWAP / CPR / PIVOT / S_R_ZONE /
ORDER_BLOCK / FVG / PROFILE_EDGE / LIQUIDITY_POOL / OTHER

HORIZON
NEXT_CLOSED_BAR
NEXT_3_BARS
NEXT_9_BARS
SESSION_REMAINDER
CUSTOM_BOUNDED_HORIZON

REGIME
TREND / RANGE / COMPRESSION / EXPANSION / EVENT / EXPIRY / TRANSITION / UNKNOWN

STATE
CANDIDATE / ACTIVE / STRENGTHENED / WEAKENED /
INVALIDATED / EXPIRED / RESOLVED_SUCCESS / RESOLVED_FAILURE
```

Human-readable names such as `BREAKOUT_FOLLOW_THROUGH` may remain aliases generated from these dimensions.

---

# 9. Separate dependency graph from reasoning graph

Two different graphs are required.

## 9.1 Provenance/dependency graph

Answers:

> Are these measurements independent?

Examples:

```text
EMA9  --derived_from--> close
EMA20 --derived_from--> close
EMA50 --derived_from--> close
MACD  --derived_from--> EMA transforms of close
RSI   --derived_from--> price changes
OBV   --derived_from--> price direction + volume
CMF   --derived_from--> OHLC + volume
```

Relationship vocabulary:

```text
DERIVED_FROM
SHARES_INPUT_WITH
SAME_SOURCE_FAMILY
DUPLICATES
CORRELATED_WITH
TIMEFRAME_PARENT
TIMEFRAME_CHILD
```

## 9.2 Reasoning / argumentation graph

Answers:

> What argues for or against a market explanation?

Relationship vocabulary:

```text
SUPPORTS
ATTACKS
INVALIDATES
REQUIRES
CONDITIONAL_ON
FAILURE_PRECURSOR
TEMPORALLY_PRECEDES
TEMPORALLY_FOLLOWS
EXPECTED_BEFORE
EXPECTED_AFTER
```

Do not merge these graphs.

Ten correlated indicators must never become ten independent confirmations.

---

# 10. Dynamic evidence router

Use broad knowledge but selective cognition.

Example: market question = breakout at major resistance.

High relevance:

```text
actual structural level
closed-bar acceptance/rejection
volume/RVOL
range re-entry
ATR / volatility expansion
VWAP / AVWAP / profile relationship
liquidity sweep / SFP
higher-timeframe structure
sector/index/breadth
nearby derivatives positioning
historical breakout/failure trajectories
```

Conditional relevance:

```text
EMA horizons
ADX
Bollinger bands
FVG
order block
CMF/MFI
MACD
RSI
```

Low discriminating value:

```text
facts that merely repeat already-known local momentum without helping distinguish competing hypotheses
```

The routing criterion is:

> Does this fact help distinguish the leading hypotheses?

Not:

> Is this indicator available?

---

# 11. Argumentation engine

For each hypothesis, create explicit arguments and counterarguments.

Example:

```text
H1 = UP / BREAKOUT_CONTINUATION / Rs 1,000 / NEXT_3_BARS
```

Supporting arguments:

```text
A1 accepted close above resistance
A2 breakout followed compression
A3 RVOL expanded
A4 VWAP rising below price
A5 sector/index aligned
A6 independent historical analogues show similar successful sequence
```

Attacking arguments:

```text
B1 daily resistance overlaps location
B2 options concentration nearby
B3 price already at extreme value/volatility extension
B4 failed-break memory is similar
B5 sector relative strength weakening
```

Counterargument example:

```text
B2: call OI concentration threatens breakout
C1: static OI concentration alone cannot prove rejection after actual price/participation acceptance
```

This replaces flat score voting.

---

# 12. Temporal path compiler

Every serious hypothesis must make pre-registered observable predictions before seeing the future bar.

Example H1 breakout continuation:

```text
EXPECT_1  price remains accepted above resistance within next 1-2 closed 5m bars
EXPECT_2  retest, if it occurs, does not deeply re-enter old range
EXPECT_3  participation does not collapse immediately
EXPECT_4  higher low forms before continuation
EXPECT_5  sector/index do not materially reverse against thesis
```

Competing sweep/failure hypothesis:

```text
EXPECT_1  breakout fails to maintain acceptance
EXPECT_2  price returns below prior resistance
EXPECT_3  rejection evidence increases
EXPECT_4  local value/structure weakens
EXPECT_5  historical failure trajectory becomes more similar
```

Each expectation has:

```text
predicate
observation_window
source facts
importance
failure consequence
```

---

# 13. Surprise and belief revision

The system should update based on whether hypotheses predicted subsequent evidence.

Example:

```text
H1 expected: acceptance above Rs 1,000
Observed: close Rs 994 after trading Rs 1,006
Result: MAJOR_SURPRISE
H1: ACTIVE -> WEAKENED or INVALIDATED

H2 expected: brief trade above then re-entry below
Observed: exact sequence
Result: EXPECTATION_CONFIRMED
H2: ACTIVE -> STRENGTHENED
```

Do not represent this merely as `score -= 0.2`.

Use explicit lifecycle transitions and surprise reason codes.

---

# 14. Hypothesis lifecycle

The engine must maintain hypotheses through time rather than rebuilding unrelated stories each candle.

```text
CANDIDATE
  -> ACTIVE
  -> STRENGTHENED
  -> WEAKENED
  -> INVALIDATED

or

ACTIVE
  -> RESOLVED_SUCCESS

or

ACTIVE
  -> EXPIRED
```

Every transition must be deterministic and receipt-backed.

Store:

```text
hypothesis_id
created_at
activated_at
last_updated_at
expires_at
previous_state
new_state
transition_reason_codes
triggering_fact_ids
```

---

# 15. Value-of-information engine

When competing hypotheses remain unresolved, the system should identify the next observation most useful for separating them.

Example:

```text
H1 = real breakout
H2 = liquidity sweep

MOST_DISCRIMINATING_INFORMATION:
ORH_RETEST_ACCEPTANCE

EXPECTED_WINDOW:
next 2 closed 5m bars

UNTIL_THEN:
uncertainty remains material
```

This provides a principled reason for `WATCH` rather than guessing.

The first implementation should use deterministic information-discrimination rules, not an opaque optimizer.

---

# 16. OOD / novelty / abstention

V2 must support:

```text
KNOWN_HYPOTHESES_EXPLAIN_MARKET_POORLY
```

leading to:

```text
UNKNOWN_MECHANISM
OOD_HIGH
NO_EDGE
INSUFFICIENT_KNOWLEDGE
```

Possible OOD factors:

```text
memory distance
regime mismatch
unusual volatility/gap
new or thinly observed symbol
novel event state
abnormal session
feed degradation
unseen derivative configuration
hypothesis coverage failure
```

No-edge / abstention is a first-class intelligent result.

---

# 17. Multiple horizons remain independent

Do not collapse:

```text
5m bullish
1h bearish
daily resistance
```

into:

```text
mixed = 50%
```

Represent:

```text
H1: 5m breakout continuation, horizon 15-30 minutes
H2: 1h resistance rejection, horizon 1-3 hours
```

Both may be correct at different horizons.

True higher-timeframe facts must come from completed higher-timeframe bars or validated closed-bar resampling.

---

# 18. Memory integration

M3.3 memory must provide more than winner/loser counts.

For each analogue expose:

```text
raw_matches
independent_episodes
stock_match
regime_match
time_of_day_match
volatility_match
market_question_match
expiry_event_match
horizon_match
distance_from_current_state
```

Failure memory should preserve transition shapes such as:

```text
approach resistance
-> breakout
-> weak acceptance
-> sweep
-> range re-entry
-> VWAP loss
-> lower high
-> downside expansion
```

The Hypothesis Box should ask:

> Are we entering a known failure trajectory?

Similarity is not probability and not causality.

---

# 19. Kronos integration

Kronos is a sequence challenger, not a commander.

Canonical flow:

```text
real validated Kronos output
      |
      v
Kronos adapter
      |
      v
comparable sequence predicates
- hold-above-level likelihood/state
- range re-entry likelihood/state
- forecast volatility path
- forecast price-path envelope
- disagreement with hypothesis expectations
      |
      v
Hypothesis Challenger
```

Never:

```text
Kronos says UP -> promote decision
```

Requirements before canonical influence:

1. real model only;
2. explicit model/version hash;
3. input snapshot hash;
4. PIT-clean data;
5. NSE walk-forward benchmark;
6. latency bound;
7. OOD detection;
8. deterministic adapter output;
9. mock fallback = QUARANTINED / research only;
10. zero final-band and zero execution authority.

Research basis:
- Kronos paper: https://arxiv.org/abs/2508.02739
- Official project: https://github.com/shiyu-coder/Kronos

---

# 20. Uncertainty and calibration

Phase 1 must use qualitative states, not fake percentages.

Example:

```text
THESIS_STATE          ACTIVE
ANTI_THESIS_STATE     ACTIVE
SUPPORT_COVERAGE      GOOD
INDEPENDENT_SUPPORT   MODERATE
OPPOSITION            MATERIAL
CONFLICT_STATE        UNRESOLVED
OOD_STATE             LOW
ROBUSTNESS            FRAGILE
INFORMATION_GAP       IMPORTANT
```

Do not publish `83% confidence` unless it has a real empirical definition.

Later probability calibration may be attached only when genuine OOS observations exist, conditioned by:

```text
market question
hypothesis mechanism
horizon
market regime
evidence coverage
instrument population
```

Prefer calibrating path events, not only direction:

```text
Will breakout remain accepted for N bars?
Will retest hold?
Will range re-entry happen?
Will VWAP be lost after failed breakout?
Will volatility expand after squeeze?
Will higher low form before invalidation?
```

Research basis:
- Calibration of modern neural networks: https://proceedings.mlr.press/v70/guo17a
- Adaptive conformal inference: https://arxiv.org/abs/2106.00170

---

# 21. Learning policy

Live reasoning must never silently rewrite production policy.

```text
LIVE SESSION
-> append immutable outcomes

OFFLINE
-> fit / recalibrate / evaluate
-> compare against frozen incumbent

PROMOTION GATE
-> human/release approval
-> new version

NEXT SESSION
-> use frozen approved version
```

One losing trade must never automatically modify production weights/rules.

Store failed experiments as well as successful experiments.

Required experiment metadata:

```text
experiment_id
policy_version
parameter_manifest
hypotheses_tested
datasets_used
development_period
validation_period
final_untouched_period
metrics
failure_notes
promotion_decision
```

---

# 22. Intelligence/computation budget

Broad knowledge does not mean unlimited computation.

Example bounded runtime target:

```text
100+ canonical facts available
-> router selects relevant subgraph
-> dependency collapse identifies independent families
-> top-K hypotheses retained
-> strongest anti-thesis retained for each
-> deep counterfactual only for top hypotheses
-> memory retrieval bounded to top independent analogues
-> Kronos invoked only when contract + latency + validation allow
-> one compact receipt
```

Design budgets must be explicit and CI-tested.

No uncontrolled recursion.
No unbounded analogue scans.
No repeated recomputation of canonical facts.

---

# 23. Formal build stages

## HB-P0 — Ground Truth Audit

Map:

- current `hypothesis_engine.py`;
- all callers;
- tests;
- DecisionContext;
- M3.1 price evidence;
- M3.2 context;
- M3.3 memory;
- derivatives;
- ORB;
- AFRE;
- Twin;
- Kronos;
- D6;
- Paper Guidance;
- all presentation paths.

**Exit:** no undocumented input/output/authority path remains.

## HB-P1 — Constitutional Laws

Encode HB safety, PIT, missingness, authority and determinism laws before intelligence work.

**Exit:** invariant tests fail any illegal authority or fabricated evidence behavior.

## HB-P2 — Canonical Evidence Contract

Implement immutable `EvidenceFact` and evidence-bundle schemas.

**Exit:** every fact has identity, source, timestamp, timeframe, version, availability, quality, PIT state, snapshot hash and dependencies.

## HB-P3 — Epistemic State Engine

Implement explicit known/unknown/unavailable/stale/incomplete/contradictory/PIT-invalid/OOD/quarantined/error states.

**Exit:** missingness cannot become numerical zero or neutral.

## HB-P4 — Market World Model

Construct current world state without trade conclusion.

**Exit:** location, structure, value, volatility, trend horizons, momentum, participation, derivatives, context, memory and model state coexist without flattening.

## HB-P5 — Market Question Detector

Identify breakout/retest/sweep/range/compression/gap/pullback/expiry/event/conflict/unknown questions.

**Exit:** multiple concurrent questions and horizons supported deterministically.

## HB-P6 — Compositional Hypothesis Ontology

Build direction + mechanism + location + horizon + regime + lifecycle state.

**Exit:** existing named hypotheses can be generated compositionally without hard-coded engine branching.

## HB-P7 — Evidence Dependency Graph

Build provenance/shared-input/redundancy structure.

**Exit:** duplicating correlated evidence cannot strengthen independent support.

## HB-P8 — Argumentation Graph

Build support/attack/invalidation/requirement/conditionality/temporal edges.

**Exit:** every active thesis has traceable arguments and counterarguments.

## HB-P9 — Bounded Deliberation Search

Generate deterministic top-K plausible hypotheses and strongest opponents.

**Exit:** finite search space, deterministic ordering, latency budget proven.

## HB-P10 — Temporal Path Compiler

Compile falsifiable expected observations, failure observations, invalidators and expiry windows.

**Exit:** every serious hypothesis predicts observable future events before those events occur.

## HB-P11 — Lifecycle / Belief Revision

Maintain hypotheses across closed candles.

**Exit:** candidate -> active -> strengthened/weakened -> invalidated/expired/resolved transitions replay deterministically.

## HB-P12 — Real Memory Challenger

Integrate M3.3 9C memory, analogues, pattern diary and failure trajectories.

**Exit:** PIT-safe matching, regime distance, raw-match count and independent-episode count visible.

## HB-P13 — Kronos Sequence Challenger

Translate validated Kronos output into comparable path predicates.

**Exit:** Kronos cannot create authority, mock fallback cannot influence canonical path.

## HB-P14 — Counterfactual Falsifier

Attack preferred explanations through evidence removal, context reversal, missing-source tests and dependency collapse.

**Exit:** fragile hypotheses explicitly marked fragile.

## HB-P15 — Information-Value Engine

Identify unresolved observation most useful for separating top hypotheses.

**Exit:** system can request/wait for discriminating evidence rather than guessing.

## HB-P16 — OOD / Novelty / Abstention

Detect poorly represented or unexplained worlds.

**Exit:** `UNKNOWN_MECHANISM` / `NO_EDGE` / `INSUFFICIENT_KNOWLEDGE` are valid outcomes.

## HB-P17 — Uncertainty & Calibration Layer

Use categorical uncertainty first; calibrated probabilities only after genuine OOS evidence.

**Exit:** no manually normalized score is labeled probability.

## HB-P18 — Structured Reasoning Receipt

Produce machine-auditable D6 input.

Receipt should contain:

```text
world_state
market_questions
hypotheses
anti_theses
arguments
counterarguments
dependency_graph
expected_paths
failure_paths
invalidators
unknowns
surprises
lifecycle_transitions
memory_analogues
kronos_challenge
counterfactual_results
ood_state
information_needed
robustness
provenance
receipt_hash
trade_authority = NONE
```

**Exit:** same snapshot + same versions => same receipt hash.

## HB-P19 — Shadow Migration

Run legacy and v2 side-by-side with v2 unable to change final decision.

**Exit:** behavioral differences measurable; no regression in safety/authority interfaces.

## HB-P20 — Empirical Validation

Run genuine PIT replay, walk-forward, perturbation, calibration, OOD, hypothesis-specific temporal and market-case validation.

**Exit:** predefined research thresholds met across stocks, sessions, regimes and horizons.

## HB-P21 — GREEN Lock

Freeze schemas, policies, tests, version manifests and authority contracts.

**Exit:** no regression, future leakage, fabricated evidence, authority leak or replay nondeterminism.

---

# 24. Required testing programme

## Unit / contract

```text
EvidenceFact validation
PIT validation
timestamp ordering
snapshot identity
parameter/version identity
missingness preservation
dependency links
ontology composition
hypothesis transitions
expected-event predicates
invalidation predicates
expiry
receipt hashing
authority boundaries
```

## Property tests

```text
same snapshot + same policy -> exact same output hash
no input level -> no invented S/R
missing OI -> never neutral OI
incomplete 1h candle -> never 1h causal evidence
duplicate EMA20 ten times -> independent support unchanged
add irrelevant indicator -> unrelated hypothesis unchanged
hard invalidator -> hypothesis cannot remain strengthened
expired hypothesis -> cannot remain active
```

## Metamorphic tests

```text
bullish/bearish mirrored series -> mirrored reasoning where definitions permit
price scale x10 -> normalized qualitative structure equivalent
symbol rename + identical data -> same reasoning unless symbol-specific memory/context differs
duplicate evidence under new IDs -> no increase in independent support
```

## Adversarial tests

```text
remove strongest bullish fact
remove strongest bearish fact
mark RVOL stale
sector contradicts index
5m bullish / 1h bearish
derivatives unavailable
OI contradictory
event shock
50 near-duplicate memory examples
Kronos contradiction
Kronos unavailable
Kronos OOD
future candle injection
incomplete HTF candle injection
missing real resistance
correlated indicators all bullish
specialist attempts final authority
reviewer attempts upgrade
execution flag attack
```

## Hypothesis temporal tests

Cover:

```text
BREAKOUT: success / false break / deep retest / shallow retest
SWEEP: high / low / failed sweep / continued breakout
TREND_PULLBACK: healthy / structural failure / late exhaustion
RANGE: mean reversion / range escape / expansion
SQUEEZE: up / down / false expansion
GAP: go / fill / partial fill / exhaustion
EVENT: normal / shock / stale calendar / unknown event
EXPIRY: gamma-sensitive / rollover / OI shift / derivatives unavailable
```

## Lifecycle tests

Replay entire sequences and require identical transitions.

## Surprise tests

Construct cases where H1 and H2 are initially plausible and subsequent observations selectively strengthen one.

## OOD tests

```text
extreme volatility
unusual gap
event shock
new stock
unusual derivative behavior
abnormal session
feed degradation
novel indicator configuration
```

Desired behavior can be high OOD + insufficient knowledge, not forced direction.

## Calibration tests

When real outcomes exist, test by:

```text
horizon
mechanism
regime
stock class
time of day
volatility
market context
```

## Distribution-shift tests

Allow state degradation:

```text
VALIDATED -> DEGRADING -> UNCALIBRATED -> OOD
```

## Backtest-overfitting protection

Every threshold/policy/router/ontology/calibration experiment must be logged, including failed experiments.

Research basis:
- Probability of Backtest Overfitting / selection-bias literature: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Selection bias in backtests: https://academic.oup.com/jfec/article-abstract/9/3/550/841819

---

# 25. Migration policy

Do not delete the legacy interface immediately.

```text
LEGACY HB
continues serving existing interface

HB-V2
runs in shadow
```

Initially:

```text
may_execute = false
may_set_final_band = false
D6 influence = none
```

Compare:

```text
legacy primary hypothesis
v2 competing hypotheses
expected paths
anti-thesis
unknowns
later observed outcome
```

Only after validation may D6 consume the v2 receipt.

D6 remains final authority.

---

# 26. Files expected to change during implementation

Exact paths must be confirmed during HB-P0, but expected additions may include:

```text
apps/api/app/behavior/decision_spine/hypothesis_v2/
    contracts.py
    epistemic_state.py
    world_model.py
    market_question.py
    ontology.py
    dependency_graph.py
    argument_graph.py
    deliberation.py
    temporal_path.py
    lifecycle.py
    memory_challenger.py
    kronos_challenger.py
    counterfactual.py
    value_of_information.py
    novelty.py
    uncertainty.py
    receipt.py
    adapter.py
```

Tests may mirror the module structure under the repository's canonical test tree.

Do not casually modify locked M3.1/M3.2/M3.3 calculations. Prefer adapters and backwards-compatible receipt extensions.

---

# 27. Performance / determinism requirements

The production path must be:

```text
deterministic
bounded
cache-safe
replayable
concurrency-safe
PIT-safe
fail-closed
```

Rules:

- no unbounded recursive reasoning;
- no network calls inside final deterministic arbitration;
- no repeated raw-market recomputation inside Hypothesis Box;
- no unbounded historical scan;
- stable sort/tie rules;
- versioned cache identity;
- bounded top-K hypotheses;
- bounded top-K memory analogues;
- exact receipt hashing;
- performance CI gates.

---

# 28. Research principles supporting the architecture

The architecture borrows useful concepts from several research families without assuming they prove trading profitability.

## Formal argumentation

Competing arguments and attack relations provide a better model for contradictory evidence than arithmetic vote addition.

References:
- https://www.sciencedirect.com/science/article/pii/000437029400041X
- https://www.sciencedirect.com/science/article/pii/0169023X9500013I

## Deliberative / multi-path search

Exploring alternatives before committing is relevant to bounded hypothesis search.

References:
- https://arxiv.org/abs/2305.10601
- https://proceedings.neurips.cc/paper_files/paper/2024/hash/01025a4e79355bb37a10ba39605944b5-Abstract-Conference.html

## OOD / uncertainty

Prediction systems can be overconfident outside their learned domain; abstention and novelty detection are therefore required.

References:
- https://proceedings.mlr.press/v119/van-amersfoort20a.html
- https://proceedings.mlr.press/v119/sastry20a.html
- https://proceedings.mlr.press/v162/shah22a.html

## Change-point / changing distributions

Market state may shift over time; old evidence/calibration should not remain authoritative indefinitely.

References:
- https://arxiv.org/abs/0710.3742
- https://arxiv.org/abs/2407.16376

## Calibration

A normalized score is not automatically an empirical probability.

Reference:
- https://proceedings.mlr.press/v70/guo17a

## Adaptive computation

Difficult cases can receive more bounded compute than simple cases without using unlimited reasoning.

Reference:
- https://proceedings.mlr.press/v70/bolukbasi17a.html

---

# 29. Build-order dependency graph

```text
HB-P0  Ground Truth Audit
   |
HB-P1  Constitutional Laws
   |
HB-P2  Canonical Evidence Contract
   |
HB-P3  Epistemic State Engine
   |
HB-P4  World Model
   |
HB-P5  Market Question Detector
   |
HB-P6  Compositional Hypothesis Ontology
   |
   +-----------------------------+
   |                             |
HB-P7 Dependency Graph      HB-P10 Temporal Path Compiler
   |                             |
HB-P8 Argument Graph             |
   |                             |
HB-P9 Bounded Deliberation ------+
   |
HB-P11 Lifecycle / Belief Revision
   |
   +-----------------------------+
   |                             |
HB-P12 Real Memory          HB-P13 Kronos Challenger
   |                             |
   +--------------+--------------+
                  |
HB-P14 Counterfactual Falsifier
                  |
HB-P15 Information-Value Engine
                  |
HB-P16 OOD / Novelty / Abstention
                  |
HB-P17 Uncertainty / Calibration
                  |
HB-P18 Structured Reasoning Receipt
                  |
HB-P19 Shadow Migration
                  |
HB-P20 Empirical Validation
                  |
HB-P21 GREEN Lock
```

---

# 30. First implementation priority

Do **not** begin by coding dozens of hypothesis templates.

The first build sequence must be:

```text
HB-P0  Truth Audit
HB-P1  Laws
HB-P2  Evidence Contract
HB-P3  Epistemic State
HB-P4  World Model
HB-P5  Market Questions
HB-P6  Hypothesis Ontology
```

Without those foundations, the project would only create a larger version of the current rule engine.

---

# 31. Relationship to later think-engine work

The broader previously agreed enhancement sequence remains:

```text
1. Hypothesis Box v2
2. Twin
3. ORB + AFRE
4. Kronos
5. Indicators / M3.1
6. Real 9-Candle / M3.3
7. History + Pattern Diary / M3.3
```

Hypothesis Box v2 is first because it defines the structured market-deliberation framework that later specialist improvements can feed without gaining authority.

---

# 32. Final implementation target

```text
HYPOTHESIS BOX V2
=
IMMUTABLE MARKET FACTS
+ EPISTEMIC AWARENESS
+ WORLD MODEL
+ QUESTION FORMULATION
+ COMPOSITIONAL HYPOTHESES
+ ARGUMENTATION GRAPH
+ DEPENDENCY INTELLIGENCE
+ TEMPORAL EXPECTATION
+ FAILURE EXPECTATION
+ REAL MEMORY
+ FAILURE MEMORY
+ VALIDATED KRONOS
+ ADVERSARIAL FALSIFICATION
+ BELIEF REVISION
+ NOVELTY/OOD DETECTION
+ VALUE OF INFORMATION
+ CALIBRATED UNCERTAINTY WHEN EARNED
+ ABSTENTION
+ DETERMINISTIC RECEIPT
=
BOUNDED HIGH-INTELLIGENCE MARKET DELIBERATION
```

This file is the formal engineering plan for the future code build. Implementation must proceed stage-by-stage, with repository truth, tests, replay, authority and exact-head verification deciding whether each stage can lock.