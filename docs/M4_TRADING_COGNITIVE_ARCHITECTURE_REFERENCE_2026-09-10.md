# Trade Vision / TrendForge — M4 Trading Cognitive Architecture Reference

Date: 2026-09-10
Status: REFERENCE / DESIGN SOURCE — NOT A LOCKED IMPLEMENTATION SPEC
Branch: `m4-d6-orchestration-redesign`

## Purpose

This file preserves the major architecture ideas, corrections, weaknesses, and enhancement directions developed during the M4 thinking-engine discussion. It is intentionally separate from the ordered M4 build specifications.

Use this document as a source when creating dedicated build plans for each thinking engine and supporting evidence system. Do not treat every idea below as already implemented or production-proven. Before coding any item, re-audit the current repository state, identify what is already canonical/locked, identify legacy/mock paths, and avoid weakening D1/D2 safety, M3 locked intelligence, or the sole-final-authority rule.

## Project objective

The target is not a normal trading bot, indicator vote counter, weighted-score machine, or LLM that says BUY/SELL.

The target is a bounded, deterministic, auditable trading decision-intelligence architecture that can:

- understand price, context, memory, patterns, derivatives, market phase, and multiple time horizons;
- generate competing explanations rather than one-direction confirmation;
- distinguish evidence strength from evidence independence;
- preserve UNKNOWN / MISSING / STALE / DEGRADED / OOD states;
- search for failure paths before promoting a setup;
- test counterfactuals and adversarial alternatives;
- reason about whether a setup is robust enough for research-only paper guidance;
- learn only through delayed, PIT-safe, offline-reviewed feedback;
- remain fast by consuming precomputed canonical facts rather than recomputing the market inside M4;
- never execute trades and never bypass human approval.

The intended product outputs remain research/paper-guidance states such as `WAIT`, `WATCH`, and `PAPER-CANDIDATE`.

---

# 1. Core architecture relationship

`M-FLOW` should mean the entire end-to-end decision flow.

`M4` is the central thinking/reasoning layer inside that flow.

`D6 / FINAL_CONFLUENCE_ARBITER` remains the sole final-band authority inside the M4 reasoning path.

Canonical conceptual flow:

```text
                              M-FLOW

MARKET DATA / EVENTS / DERIVATIVES
                |
                v
        D1 SAFETY / INTEGRITY
                |
                v
        D2 CLOSED SNAPSHOT
                |
       +--------+--------+
       |        |        |
       v        v        v
     M3.1     M3.2     M3.3
     PRICE   CONTEXT   MEMORY
       |        |        |
       +--------+--------+
                |
                v
     CANONICAL DECISION CONTEXT
                |
                v
         M4 THINK ENGINE
                |
                v
      D6 FINAL ARBITRATION
                |
                v
       DECISION RECEIPT
                |
                v
         PAPER GUIDANCE
```

Do not introduce another decision authority above D6 merely by naming it M-FLOW.

---

# 2. Original helper model and intended roles

The conversation used the following simple mental model as a starting point:

- Indicators come through M3.1 price proof.
- The new real 9-candle album comes through M3.3 memory proof.
- The old fake/mock 9-candle album stays outside the canonical path and is only for practice/research.
- History and pattern diary come through M3.3 memory proof.
- Kronos stands outside the core as a market-sequence / candlestick forecast specialist.
- Hypothesis engine proposes candidate explanations.
- Twin provides disagreement/conflict observations.
- ORB and AFRE are strategy specialists that may suggest setups only when safety and proof gates permit.
- Gemini/Grok or other external LLM reviewers may provide commentary/challenge, but they do not receive final-band authority.

The stronger design keeps these roles but replaces simplistic voting with structured reasoning.

---

# 3. Corrections to earlier reasoning

## 3.1 Correlated does not mean identical

EMA 9, EMA 20, EMA 50, EMA 200, MACD, Supertrend, Ichimoku, etc. may share price-derived information, but they do not express identical horizons or functions.

A correct system must preserve:

- fast trend;
- medium trend;
- structural/slow trend;
- slope;
- stack/order;
- separation/compression;
- cross age;
- price location relative to each average;
- actual source timeframe;
- confirmation lag;
- regime sensitivity.

Do not collapse EMA 9/20/50 into one signal. Also do not count them as fully independent proofs simply because there are three indicators.

Example:

```text
5m EMA9 rising
5m EMA20 rising
5m EMA50 rising
EMA9 > EMA20 > EMA50

=> fast trend bullish
=> medium trend bullish
=> structural intraday trend bullish
=> ordered stack
=> possible expansion phase
```

Different case:

```text
EMA9 > EMA20
EMA20 < EMA50
EMA50 falling

=> short-horizon recovery
=> medium-horizon transition
=> higher-horizon structure still bearish
=> possible countertrend rally / early reversal / short-covering
```

Multi-timeframe evidence must use actual closed higher-timeframe states rather than pretending a longer EMA on 5m is literally a 1H trend.

## 3.2 Indicator count must never equal confidence

Many bullish indicators can be derivatives of the same underlying information. M4 must preserve each useful observation but reason about dependency and independence.

Correct principle:

`information richness != independent proof count`

## 3.3 Patterns are contextual events, not standalone votes

A hammer, engulfing pattern, harmonic pattern, Elliott count, order block reaction, or VWAP reclaim means different things depending on:

- location;
- prior sequence;
- volume;
- market phase;
- regime;
- index/sector state;
- derivatives state;
- nearby liquidity;
- historical failure behavior.

## 3.4 Stronger upstream evidence makes M4 stronger, but cannot replace M4 reasoning

The system quality depends on both evidence truth and reasoning quality.

Conceptually:

```text
Decision quality
≈ Evidence truth
× Reasoning quality
× Authority correctness
× Uncertainty honesty
× Replay determinism
```

A sophisticated arbiter cannot recover information that upstream sources never produced.

---

# 4. Repository weaknesses / improvement opportunities identified during discussion

These findings must be re-verified before implementation because repository state can change.

## 4.1 Indicator registry already has a strong skeleton but needs ontology v2

The registry currently describes approximately 94 output groups and includes metadata such as:

- family;
- subfamily;
- purpose;
- category;
- best/bad regime;
- best timeframe;
- direction meaning;
- lag behavior;
- false-positive conditions;
- confirmation rules;
- conflict rules;
- trade/risk/no-trade usage;
- warmup/PIT/future-pivot policies.

However, much of the ontology is generated through broad category/name heuristics. The next step should be expert-curated or empirically validated `Indicator Ontology v2`, indicator by indicator.

## 4.2 Indicator runtime relationship model is too coarse

The real indicator adapter already emits `family`, `dependency_family`, and `correlation_group`, and has snapshot/window-aware caching.

Improvement direction:

replace a single correlation bucket with a typed evidence relationship graph.

Possible edge types:

- `DERIVED_FROM`
- `CORRELATED_WITH`
- `CONFIRMS`
- `CONTRADICTS`
- `REQUIRES`
- `INVALIDATES`
- `LEADS`
- `LAGS`
- `CONDITIONAL_ON`
- `LOCATION_CONTEXT`
- `FAILURE_PRECURSOR`
- `REGIME_DEPENDENT`
- `TIMEFRAME_PARENT`
- `TIMEFRAME_CHILD`

## 4.3 Current legacy hypothesis engine is too primitive for canonical M4 use

Observed design characteristics include:

- only continuation, reversal, fakeout hypotheses;
- manually scored rules;
- normalized `raw_probability` values;
- fallback confirmation/invalidation prices when true levels are not available.

Canonical M4 should not manufacture trade boundaries or treat normalized rule scores as calibrated probabilities.

A new Hypothesis Engine v2 should be built as structured competing explanations.

## 4.4 Twin should not become the canonical conflict engine

Twin is useful as a reviewer/compatibility component and can observe Behavior-vs-Kronos disagreement.

M4 itself needs a generalized conflict graph spanning all canonical evidence sources.

## 4.5 Kronos must be separated into real validated evidence vs mock/research evidence

The existing Kronos bridge can operate with real model artifacts when configured, but also contains deterministic mock fallback behavior.

Canonical M4 law:

```text
REAL + VALIDATED KRONOS
    => reviewer / sequence evidence

MOCK / FALLBACK KRONOS
    => research-only / quarantined
    => zero canonical decision influence
```

Kronos should be improved rather than permanently left as a weak weather note, but it must never become final authority.

## 4.6 Canonical 9-candle memory is already much stronger than legacy mock 9C

The canonical M3.3 path already uses:

- D2 closed candles;
- M3.1 indicator telemetry;
- PIT-safe persisted memory;
- snapshot/time identity checks;
- independent session matching;
- explicit OOD / insufficient evidence states;
- no decision/final-band/execution authority.

Do not rewrite this merely because legacy `nine_candle_hybrid.py` still contains mocks. First prove canonical reachability.

## 4.7 Canonical pattern memory already fixes important legacy errors

The canonical pattern-memory design includes:

- close-time wall-clock windows;
- explicit missing previous close instead of `gap_pct=0` fabrication;
- missing masks;
- bounded candidate/match counts;
- versioned vectors.

Enhance only where needed, especially retrieval performance and transition/failure memory.

## 4.8 Memory performance can be improved before using approximate ANN

For currently bounded corpora, prefer deterministic exact vectorized top-k retrieval first:

```text
feature matrix
+ missing mask
+ vectorized distance
+ argpartition shortlist
+ exact deterministic refinement
```

Introduce HNSW/FAISS only when corpus scale justifies it and determinism/recall can be proven.

---

# 5. Target Trading Cognitive Architecture

```text
                         MARKET OBSERVATION
                                |
                                v
                       D1 SAFETY / INTEGRITY
                                |
                                v
                         D2 CLOSED SNAPSHOT
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
  M3.1 PRICE WORLD       M3.2 CONTEXT WORLD      M3.3 MEMORY WORLD
        |                       |                       |
        +-----------------------+-----------------------+
                                |
                                v
                    CANONICAL EVIDENCE BUS
                                |
                    MARKET FACT KERNEL
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
 INDICATOR SEMANTICS      STRUCTURE/AUCTION        DERIVATIVES
        |                       |                       |
        +-----------------------+-----------------------+
                                |
                                v
                  MULTI-HORIZON WORLD MODEL
                                |
                                v
                MARKET-PHASE STATE MACHINE
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
 ORB / AFRE / STRATEGY      KRONOS / SEQUENCE      MEMORY / PATTERN
      PROPOSALS                 REVIEWER              SPECIALISTS
        |                       |                       |
        +-----------------------+-----------------------+
                                |
                                v
                     M4 THINK ENGINE
                                |
                   1. Evidence validation
                   2. Authority classification
                   3. Epistemic classification
                   4. PIT/causal validation
                   5. Dependency/independence graph
                   6. Thesis generation
                   7. Anti-thesis generation
                   8. Conflict graph
                   9. Failure-mode search
                  10. Scenario lattice
                  11. Counterfactual testing
                  12. Adversarial challenge
                  13. OOD/drift reasoning
                  14. Decision fragility
                  15. Uncertainty synthesis
                  16. Thesis survival test
                                |
                                v
                     D6 FINAL ARBITRATION
                                |
                                v
                  WAIT / WATCH / PAPER-CANDIDATE
                                |
                                v
                       DECISION RECEIPT
                                |
                                v
                 DELAYED PIT-SAFE OUTCOME MEMORY
```

---

# 6. Indicator Ontology v2

Every indicator should become a typed market sensor, not merely `bullish/bearish`.

Suggested canonical knowledge contract:

```text
IndicatorKnowledge
  identity
  formula/version
  source timeframe
  effective horizon
  market role
  information dependency
  current state
  direction semantics
  location semantics
  regime applicability
  confirmation age
  lag characteristics
  warmup state
  failure conditions
  false-positive conditions
  valid confirming evidence
  valid contradicting evidence
  invalidators
  what it must never conclude
  per-stock reliability
  per-timeframe reliability
  per-regime reliability
  sample sufficiency
  source hash
  PIT state
```

Major indicator/sensor families to model separately:

| Intelligence family | Examples | Primary question |
| --- | --- | --- |
| Trend | EMA 9/20/50/200, Supertrend, Ichimoku | What direction/phase? |
| Momentum | MACD, RSI, Stochastic, impulse | Accelerating, weakening, exhausted? |
| Value | VWAP, anchored VWAP, VWAP bands | Accepted above/below fair value? |
| Location | CPR, pivots, PDH/PDL, S/R, Fibonacci | Where is price? |
| Auction | POC, VAH, VAL, volume profile | Where has business been accepted? |
| Participation | Volume, RVOL, CMF, MFI, OBV | Is participation supporting the move? |
| Structure | swings, BOS, CHOCH, HH/HL/LH/LL | What is price structurally doing? |
| Liquidity | FVG, order block, sweep, SFP | Where can liquidity/rejection occur? |
| Volatility | ATR, BB, KC, squeeze, VIX | What movement regime exists? |
| Pattern | candlesticks, harmonic, chart structures | What geometry/behavior is forming? |
| Derivatives | OI, PCR, IV, skew, GEX, Greeks | What positioning/volatility forces exist? |
| Relative context | Index, sector, breadth, RS | Is the stock aligned with its environment? |
| Memory | analogs, 9C, pattern diary | What happened in comparable states? |
| Sequence model | Kronos | What future K-line paths are plausible? |

---

# 7. Indicator relationship reasoning

M4 should reason about relationships rather than count confirmations.

Example graph:

```text
EMA9  --same_source--> EMA20
EMA20 --same_source--> EMA50

EMA stack --confirmed_by--> ADX
EMA stack --location_context--> VWAP

VWAP reclaim --confirmed_by--> volume expansion
CPR breakout --confirmed_by--> acceptance close
Resistance --conflicts_with--> bullish continuation
Bearish RSI divergence --becomes_relevant_at--> resistance
Call OI wall --threatens--> long breakout
Gamma state --modifies--> expected path behavior
```

The system should preserve multiple observations while avoiding fake evidence multiplication.

---

# 8. Location × pattern × sequence reasoning

A pattern should be interpreted as a narrative event.

Example:

```text
PATTERN:
bullish hammer

LOCATION:
PDL + support confluence

PRECEDING SEQUENCE:
three expanding bearish candles

VOLUME:
climactic sell volume then contraction

STRUCTURE:
no downside follow-through

CONTEXT:
index stabilising

MEMORY:
similar rejection trajectories available

THESIS:
seller exhaustion / reversal candidate

FALSIFIER:
closed break below support with renewed volume
```

This is much stronger than `hammer = bullish`.

---

# 9. Pattern Sequence Intelligence

Expand beyond static pattern recognition.

Compare and model:

- previous 1 candle;
- previous 3 candles;
- previous 5 candles;
- previous 9 candles;
- opening sequence;
- level-interaction sequence;
- volume sequence;
- structure-transition sequence;
- failure-transition sequence.

Example trajectory:

```text
strong red
-> smaller red
-> doji at PDL
-> bullish engulf
-> VWAP reclaim
```

Create transition memory such as:

```text
approach resistance
-> failed breakout
-> re-enter range
-> VWAP loss
-> accelerated selloff
```

Goal: recognize trajectories and failure paths, not just pictures.

---

# 10. Elliott / Harmonic reasoning

Elliott and harmonic modules should propose structured hypotheses, never final signals.

Example Elliott hypothesis:

```text
possible wave-3 impulse

EXPECTED:
- shallow pullbacks
- expanding momentum
- structural higher highs
- no invalid wave overlap
- participation expansion

INVALIDATION:
wave structure violation

ALTERNATIVE:
ABC corrective rally
```

Example harmonic hypothesis:

```text
possible bullish Gartley PRZ

requires:
- geometry validity
- completion zone
- actual price rejection
- volume response
- structural shift
```

Price/market behavior validates pattern hypotheses.

---

# 11. Derivatives reasoning

Do not convert derivatives into one score.

Reason separately about:

- VIX regime and change;
- IV rank;
- term structure;
- skew;
- PCR;
- max pain proximity;
- futures OI buildup;
- basis;
- rollover;
- unsigned GEX;
- dealer-signed GEX only where dealer sign is actually observed;
- vanna;
- charm;
- expiry state;
- GIFT/index gap context;
- FII futures positioning.

Each derivatives fact can support, condition, threaten, or invalidate different hypotheses.

---

# 12. Kronos upgrade program

Kronos should evolve from a weak outside weather note into a validated financial sequence specialist while remaining non-authoritative.

Required program:

1. Prove real-service path and model artifacts.
2. Quarantine deterministic mock fallback from the canonical decision path.
3. Benchmark available open model variants on NSE held-out data.
4. Evaluate by task, not one aggregate score:
   - 5m direction;
   - 15m direction;
   - 1H direction;
   - volatility;
   - path shape;
   - breakout failure;
   - reversal;
   - continuation;
   - opening behavior.
5. Compare latency, calibration, path accuracy, robustness and regime stability.
6. Use real validated outputs only as sequence/reviewer evidence.
7. Never permit Kronos to override D1, D6, or hard safety states.
8. Any later fine-tuning must use PIT-clean Indian-market data and go through offline/OOS/shadow/paper validation before promotion.

Principle:

`largest model != automatically best model for NSE intraday`

---

# 13. Hypothesis Engine v2

Replace simple continuation/reversal/fakeout scoring with structured competing explanations.

Candidate hypothesis library may include:

- long continuation;
- long reversal;
- short continuation;
- short reversal;
- breakout follow-through;
- breakout failure;
- range mean reversion;
- squeeze expansion;
- gap-and-go;
- gap exhaustion/fade;
- liquidity-sweep reversal;
- trend pullback;
- event-distorted market;
- chop/no-edge.

Every hypothesis must carry:

```text
hypothesis_id
thesis
direction
timeframe
market_phase
required_facts
supporting_evidence
opposing_evidence
unknown_evidence
invalidators
expiry
expected_sequence
expected_failure_sequence
regime_assumptions
failure_modes
robustness_state
```

Do not emit fake calibrated probabilities without a valid label/calibration program.

---

# 14. Thesis vs anti-thesis

For every trade-like thesis, M4 must generate the best opposing explanation.

Example:

```text
THESIS:
ORB breakout is genuine.

ANTI-THESIS:
Opening move is exhausted into daily resistance and call OI wall.

FOR THESIS:
volume
VWAP
EMA horizon stack
index support

FOR ANTI-THESIS:
1.7 ATR extension
higher-timeframe resistance
OI wall
sector weakness

MISSING:
fresh participant OI

FAILURE PATH:
breakout -> stalled acceptance -> VWAP loss -> ORH failure
```

A thesis cannot be promoted merely because it has more supportive indicators.

---

# 15. Market Phase State Machine

Indicator meaning changes by market phase.

Suggested states:

```text
PREOPEN
OPENING_AUCTION
OR_FORMATION
BREAKOUT_ATTEMPT
ACCEPTANCE
REJECTION
RETEST
FOLLOW_THROUGH
FAILURE
MIDDAY_COMPRESSION
AFTERNOON_EXPANSION
CLOSE
```

Example: RSI=75 can mean momentum strength during an opening drive, exhaustion near extended resistance, or low-value noise inside a range.

Same numeric value, different semantic meaning.

---

# 16. Dynamic relevance / attention routing

Do not deeply evaluate all 94 indicator outputs for every decision.

First classify the active market question.

Example event:

`price attempting breakout above CPR + ORH`

Relevant specialists may include:

```text
LOCATION:
CPR, ORH, pivots, S/R, POC, order block

BREAKOUT:
volume, RVOL, VWAP, BOS, candle acceptance

TREND:
EMA horizon structure, ADX, MACD

CONTEXT:
index, sector, breadth

DERIVATIVES:
OI wall, PCR, IV, gamma

MEMORY:
similar successful/failed breakouts

KRONOS:
forward path distribution
```

This reduces noise and improves speed without discarding available intelligence.

---

# 17. Conflict graph

Twin may continue providing a compatibility/reviewer disagreement note, but canonical M4 conflict detection must work independently.

M4 asks:

- What disagrees?
- Is the disagreement logical, directional, temporal, regime-based, or data-quality-based?
- Which source has greater authority?
- Are both sources fresh?
- Are both sources PIT-safe?
- Are they actually independent?
- Can both observations simultaneously be true?
- Does the conflict veto a direction?
- Does it cap the final band?
- Does it only widen uncertainty?
- Is there enough information to resolve it?

Do not average contradictions away.

---

# 18. Failure intelligence

History must answer more than “what similar cases won?”

Three memory questions:

1. ANALOG — have we seen something similar?
2. RELIABILITY — how reliably did this policy work in comparable conditions?
3. FAILURE — when it failed, how did it fail?

Example:

```text
historical analogs broadly support breakout
BUT dominant failed cases contained:
- >1.8 ATR extension
- nearby OI wall
- sector divergence after 10:00

current market contains 2/3 failure precursors
=> WATCH, not promotion
```

Failure trajectory memory is a major target enhancement.

---

# 19. Scenario / counterfactual / adversarial reasoning

M4 must explicitly test alternative worlds.

Examples:

- What if the strongest bullish indicator disappears?
- What if sector freshness changes from FRESH to STALE?
- What if the OI wall rejects price?
- What if price closes back below VWAP?
- What if memory support is removed because sample size is insufficient?
- What if Kronos is unavailable?
- What if the apparent breakout is actually a liquidity sweep?
- What if the higher-timeframe bearish structure dominates the fast bullish move?

The decision should be judged on how well the thesis survives plausible perturbations, not on one static snapshot score.

---

# 20. Uncertainty and robustness

Confidence is not win probability.

Possible dimensions:

- source quality;
- evidence coverage;
- independence;
- authority;
- freshness;
- contradiction;
- missingness;
- OOD;
- drift;
- memory sample sufficiency;
- regime match;
- counterfactual robustness;
- scenario stability;
- failure-risk density;
- single-factor dependence;
- decision fragility.

Example final internal state:

```text
THESIS_STATE = VALID
ANTI_THESIS = MATERIAL
SAFETY = PASS
EVIDENCE_COVERAGE = GOOD
INDEPENDENT_SUPPORT = MODERATE
CONFLICT = RESOLVABLE
FAILURE_RISK = MATERIAL
OOD = LOW
ROBUSTNESS = MODERATE
```

D6 can then map semantic states to WAIT/WATCH/PAPER-CANDIDATE without weighted voting.

---

# 21. ORB / AFRE role

ORB and AFRE are strategy specialists / thesis generators, not judges.

Each proposal should eventually include:

```text
strategy_id
variant_id
direction
entry_thesis
invalidation
required_conditions
proof_hash
snapshot_hash
decision_time
regime_assumptions
failure_risks
expected_holding_window
evidence_dependencies
```

M4 may conclude:

`valid setup != valid paper candidate`

A technically valid ORB/AFRE setup can still be rejected due to failure risk, event context, derivatives hostility, OOD, uncertainty, or authority/safety constraints.

---

# 22. Speed architecture

More reasoning must not mean repeated market computation.

## 22.1 Market Fact Kernel

Compute reusable facts once per closed snapshot:

- OHLCV;
- returns;
- ATR;
- VWAP;
- EMA states;
- rolling volume;
- session partitions;
- levels;
- swing structure;
- index relationship;
- sector relationship;
- profile/auction facts where available.

## 22.2 Multi-timeframe kernel

Derive closed timeframe states from one canonical source stream where valid:

```text
base stream
  -> 3m closed
  -> 5m closed
  -> 15m closed
  -> 30m closed
  -> 1H closed
```

Never use unfinished higher-timeframe candles as finished evidence.

## 22.3 Incremental computation

Maintain stateful rolling calculations rather than rebuilding long windows unnecessarily:

- EMA state;
- ATR state;
- rolling volume;
- VWAP accumulators;
- swing state;
- profile buckets.

## 22.4 M4 bounded reasoning budgets

Target design constraints may include bounded counts such as:

- evidence nodes;
- conflicts;
- active hypotheses;
- scenarios;
- counterfactuals;
- failure modes;
- receipt bytes.

No network calls inside deterministic D6 final arbitration.

No historical corpus scan inside D6.

No required LLM call inside D6.

---

# 23. Controlled learning architecture

The system should improve from outcomes without becoming an unsafe self-modifying bot.

```text
DECISION
  -> immutable decision receipt
  -> wait for outcome horizon
  -> delayed PIT-safe label
  -> outcome attribution
  -> failure attribution
  -> candidate knowledge update
```

Learn conditionally by:

- stock;
- timeframe;
- market phase;
- regime;
- hypothesis;
- indicator state;
- evidence combination;
- failure pattern.

Promotion pipeline:

```text
candidate learned rule
  -> offline evaluation
  -> walk-forward
  -> out-of-sample
  -> shadow
  -> paper
  -> human-reviewed promotion
```

No direct live self-modification.

---

# 24. Revised M4 build-program concept

Before starting the previously frozen M4-A production implementation, create dedicated planning/audit work for the enhanced thinking engines.

Proposed conceptual sequence:

```text
M4-P0  Canonical Path Audit
M4-P1  Indicator Ontology v2
M4-P2  Multi-Timeframe Fact Kernel
M4-P3  Evidence Relationship Graph
M4-P4  Pattern + Sequence Intelligence
M4-P5  Real Kronos Intelligence
M4-P6  Memory Performance Hardening

M4-A   Canonical Evidence Contract v2
M4-B   Market State + Epistemic + Authority Graph
M4-C   Hypothesis / Anti-Hypothesis Engine
M4-D   Conflict + Independence Reasoning
M4-E   Failure-Prediction Engine
M4-F   Scenario + Counterfactual Engine
M4-G   Uncertainty + Robustness Engine
M4-H   D6 Deterministic Arbitration
M4-I   Reason Tree + Decision Receipt
M4-J   Paper Guidance / M-FLOW Wiring
M4-K   Controlled Learning Loop
M4-L   Adversarial / Replay / OOS / Performance
M4-M   Authority Audit + Exact-Head CI + Lock
```

This sequence is a reference proposal. Each engine should receive its own detailed implementation document before code changes.

---

# 25. Dedicated thinking-engine plans to create from this reference

Future planning should separate at least the following systems so each can be deeply audited and optimized without turning M4 into one giant rewrite:

1. Indicator Ontology & Indicator Intelligence Plan
2. Multi-Timeframe Trend/Horizon Intelligence Plan
3. Market Fact Kernel & Incremental Compute Plan
4. Price Structure / S&R / CPR / Pivot / VWAP / Auction Intelligence Plan
5. Candlestick & Pattern Sequence Intelligence Plan
6. Harmonic Pattern Intelligence Plan
7. Elliott / Wave Hypothesis Intelligence Plan
8. Derivatives / OI / PCR / IV / GEX / Greeks Intelligence Plan
9. Real 9-Candle Memory Enhancement Plan
10. Historical Pattern / Failure Trajectory Memory Plan
11. Kronos Real Sequence-Model Plan
12. Hypothesis / Anti-Hypothesis Engine v2 Plan
13. Twin Compatibility + Canonical Conflict Graph Plan
14. ORB Specialist Contract Plan
15. AFRE Specialist Contract Plan
16. Market Phase State Machine Plan
17. Dynamic Relevance / Attention Router Plan
18. Evidence Dependency / Independence Graph Plan
19. Failure Prediction Plan
20. Scenario Lattice Plan
21. Counterfactual Reasoning Plan
22. Adversarial Self-Challenge Plan
23. OOD / Drift / Epistemic State Plan
24. Uncertainty / Robustness / Fragility Plan
25. D6 Deterministic Arbitration Plan
26. Reason Tree / Decision Receipt Plan
27. Controlled Learning / Delayed Outcome Plan
28. Performance / Caching / Vector Retrieval Plan
29. M-FLOW / Paper Guidance Integration Plan
30. Full Adversarial / Replay / OOS / Authority / CI Lock Plan

Each dedicated plan should contain:

- current code paths;
- what is already canonical and locked;
- legacy/mock paths;
- known bugs/weaknesses;
- functionality currently underused;
- exact trading purpose;
- desired semantics;
- dependencies;
- authority boundaries;
- PIT/freshness requirements;
- failure behavior;
- data contracts;
- algorithms;
- performance budget;
- tests;
- adversarial cases;
- migration/compatibility strategy;
- rollback strategy;
- acceptance criteria;
- exact files expected to change;
- proof required before marking GREEN/LOCKED.

---

# 26. Canonical improvement duty for future work

For every future thinking-engine review:

1. Inspect the actual current code before planning.
2. If code is broken, weak, mock-fed, inefficient, unsafe, or functionally incomplete, identify it explicitly.
3. Determine whether the problem is in the canonical path or only a legacy/research path.
4. Improve or replace canonical functionality when justified instead of merely documenting the weakness.
5. Do not break already-locked safety or intelligence stages casually.
6. Preserve fail-closed behavior.
7. Never convert missing/unknown/unavailable data to a neutral signal.
8. Never create fake confidence or probability.
9. Never grant reviewers or specialists final-band/execution authority.
10. Measure speed and correctness with reproducible tests rather than assuming improvement.

---

# 27. Target reasoning behavior

The mature system should be able to answer, internally and deterministically:

```text
What is happening?
Where is price?
What market phase are we in?
What is the short horizon doing?
What is the medium horizon doing?
What is the higher horizon doing?
What is structure doing?
What is value doing?
What is participation doing?
Where is liquidity?
Where are important levels?
What are derivatives implying?
What are index and sector doing?
What sequence led here?
What similar historical trajectories existed?
What happened when similar setups failed?
What future K-line paths does validated Kronos consider plausible?
What strategy hypotheses apply?
What supports the best thesis?
What contradicts it?
Which evidence is truly independent?
What information is missing or stale?
What invalidates the thesis?
What is the likely failure path?
What is the dangerous failure path?
What happens if the strongest support disappears?
What happens if the strongest opposition proves correct?
Is the decision robust or fragile?
Should the system remain WAIT, move to WATCH, or become PAPER-CANDIDATE?
Why?
```

The output must be explainable through structured receipts, not hidden chain-of-thought.

---

# 28. Non-negotiable safety and authority laws

Preserve these principles throughout all future engine plans:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
future != causal
unfinished != closed
stale != fresh
correlated facts != independent episodes
label observed later != label available now
```

Additional laws:

- D1 safety/integrity outranks predictors/reviewers.
- `FINAL_CONFLUENCE_ARBITER` / D6 remains sole final-band authority.
- Specialists do not execute.
- External reviewers do not execute.
- `trade_allowed=false` inside Trade Vision research intelligence.
- `order_routing_enabled=false`.
- `live_trading_blocked=true`.
- human approval remains required for paper workflow.
- M4 must not silently change locked M3 calculations simply to simplify orchestration.

---

# 29. Working definition of “AGI-level” for this project

Do not claim consciousness or general AGI.

For this project, the phrase should mean a high-quality bounded trading reasoning system exhibiting:

- broad evidence integration;
- context-sensitive interpretation;
- multi-timeframe understanding;
- explicit competing hypotheses;
- causal/PIT discipline;
- dependency awareness;
- adversarial self-challenge;
- failure prediction;
- scenario reasoning;
- counterfactual robustness;
- uncertainty honesty;
- structured memory use;
- deterministic replay;
- explainable authority decisions;
- fast bounded execution;
- controlled offline learning.

This is the engineering quality target, not a claim of human-like consciousness or guaranteed market accuracy.

---

# 30. Use of this file

This reference exists so the project does not lose the design thinking developed before implementation.

When the next planning phase starts:

1. Re-read this file.
2. Re-read canonical M0–M4 status/docs.
3. Re-audit the live repository branch/HEAD.
4. Select one thinking engine from the dedicated-plan list.
5. Inspect every relevant implementation/test/wiring path.
6. Produce an engine-specific build plan.
7. Only after the plan is accepted/locked should production changes begin for that engine.

Do not attempt to implement all enhancement ideas as one unreviewed mega-commit.

End of reference.


---

## Agreed think-engine planning order — 2026-09-10

This is the current order for creating separate improvement/update plans for the existing thinking engines. It is a planning priority list, not an implementation-completion claim and not a change to final authority.

1. **Hypothesis Box** — first priority. Build stronger thesis / anti-thesis generation, explicit required evidence, invalidators, expiry, expected sequence, and failure paths.
2. **Twin** — second. Improve disagreement, contradiction, and competing-explanation detection. Twin remains a reviewer/compatibility component; canonical M4 conflict reasoning remains broader than Twin.
3. **ORB + AFRE** — third. Strengthen strategy-specialist reasoning after hypothesis/conflict logic is defined; preserve safety/proof gates and proposal-only authority.
4. **Kronos** — fourth. Upgrade toward real validated sequence/candlestick intelligence; mock/fallback output remains research-only and must not influence canonical decisions.
5. **Indicators / M3.1 Price Proof** — fifth. Improve indicator ontology, multi-horizon interpretation, relationship/dependency reasoning, and efficiency while preserving locked M3.1 contracts and evidence provenance.
6. **9-Candle Real Album / M3.3 Memory Proof** — sixth. Improve interpretation, retrieval quality, contextual matching, and speed without weakening the canonical real/PIT-safe route.
7. **History + Pattern Diary / M3.3 Memory Proof** — seventh. Deepen analog, sequence-transition, failure-pattern, regime-conditioned, and historical reasoning after core memory handling is stable.
8. **Old Fake / Mock Album** — never integrate into production reasoning. Keep strictly outside the canonical path for practice, fixtures, and research-only testing.

Short planning sequence:

```text
Hypothesis Box
    -> Twin
    -> ORB / AFRE
    -> Kronos
    -> Indicators / M3.1
    -> 9-Candle Real Memory / M3.3
    -> History + Pattern Diary / M3.3
    -> Old Fake Album remains outside production
```

For each engine, the dedicated plan should begin by auditing current repository truth, identifying weak/broken/legacy functionality, separating canonical from mock paths, and defining measurable correctness, speed, safety, and acceptance tests before implementation.


---

# 31. Unified Market Evidence and Reasoning Architecture — research upgrade

Date merged: 2026-09-10
Status: RESEARCH-BACKED ARCHITECTURE REFERENCE — NOT AN IMPLEMENTATION-COMPLETE CLAIM

This section merges the deeper market-evidence research into the existing M4 cognitive architecture reference. It strengthens the earlier plan; it does not erase the earlier sections, the agreed think-engine planning order, locked M0–M3 behavior, D1/D2 safety, or D6 sole-final-authority rule.

The engineering target is broad, context-sensitive, adversarially challenged market reasoning. It must remain bounded, deterministic where required, replayable, point-in-time safe, explicit about missing information, and research/paper-guidance only.

## 31.1 Core rule — evidence is typed information, not a vote

The unified system must not reason like this:

```text
EMA bullish + RSI bullish + VWAP bullish + OBV bullish + MACD bullish = BUY
```

That loses semantics and can count the same underlying information multiple times.

The stronger canonical flow is:

```text
D1 SAFETY / DATA INTEGRITY
-> D2 CLOSED PIT SNAPSHOT
-> MARKET FACT KERNEL
-> VERSIONED TYPED EVIDENCE
-> MARKET PHASE / ACTIVE QUESTION
-> RELEVANCE ROUTER
-> DEPENDENCY + RELATIONSHIP GRAPH
-> COMPETING HYPOTHESES
-> THESIS / ANTI-THESIS
-> FAILURE-PATH SEARCH
-> SCENARIOS
-> COUNTERFACTUALS
-> ADVERSARIAL CHALLENGE
-> OOD / UNCERTAINTY / ROBUSTNESS
-> D6 SOLE FINAL ARBITRATION
-> WAIT / WATCH / PAPER-CANDIDATE
```

A market sensor may answer direction, trend persistence, momentum, structural location, value/auction location, volatility state, participation, liquidity/rejection risk, derivatives positioning or convexity, market context, historical similarity, or plausible future sequence. No sensor receives final authority merely because it is popular or visually persuasive.

## 31.2 Canonical market-fact contract

Every decision-affecting observation should eventually carry an explicit contract similar to:

```text
EvidenceFact
  evidence_id
  feature_id
  family
  subfamily
  formula_id
  formula_version
  parameter_hash
  source_id
  source_snapshot_hash
  source_timeframe
  effective_horizon
  confirmation_time
  decision_time
  value
  normalized_state
  direction_semantics
  location_semantics
  market_role
  market_phase
  freshness_state
  PIT_state
  availability_state
  quality_state
  dependency_keys[]
  correlation_group
  independent_episode_key
  supports[]
  contradicts[]
  requires[]
  invalidates[]
  conditional_on[]
  uncertainty
  allowed_conclusions[]
  forbidden_conclusions[]
  warnings[]
  evidence_hash
```

Important invariants:

```text
same label + different formula/config != same fact
same price source != independent confirmation
same event seen through multiple indicators != multiple independent episodes
missing input != numeric zero
calculation error != no signal
unconfirmed pivot != confirmed structure
unfinished HTF bar != closed HTF evidence
```

## 31.3 Price Structure intelligence

Price Structure answers: **Where is price structurally, and what has price actually proven?**

- **Support / Resistance** — dynamic reaction zones, not magical exact lines. Use confirmed swing/auction/level sources. Zone width, touch count, recency and volatility normalization must be versioned. Stale or repeatedly tested zones should lose reliability unless evidence proves otherwise.
- **HH / HL / LH / LL** — maintain a confirmed swing sequence. Forming pivots must remain separate from confirmed pivots.
- **BOS** — continuation-style break of a defined structural swing. Store swing source, close/wick policy, breakout buffer, confirmation bar and time.
- **CHOCH** — potential transition against the previous structural sequence. It is a reversal/transition hypothesis, not proof that a new trend already exists.
- **PDH / PDL** — previous completed trading session high/low using an exchange-aware calendar.
- **CPR** — prior-period central pivot range. Canonical formula should be explicit: `P=(H+L+C)/3`, `BC=(H+L)/2`, `TC=2P-BC`.
- **Classic pivots** — formula/version explicit. Common form: `R1=2P-L`, `S1=2P-H`, `R2=P+(H-L)`, `S2=P-(H-L)`.
- **Fibonacci** — low-authority candidate location/confluence only. Swing anchors, ratios and confirmation must be explicit. It must never be a promotion gate by itself; its conditional incremental value should be measured empirically by stock/timeframe/phase/regime.

Prefer semantic structure states over one score. Example:

```text
STRUCTURE_5M:
  trend_sequence = HH_HL
  latest_confirmed_event = BOS_UP
  forming_event = NONE
  distance_to_daily_resistance_atr = 0.28
  structural_state = BULLISH_BUT_OBSTRUCTED
```

## 31.4 Liquidity / smart-money-structure intelligence

Liquidity Structure answers: **Where may price be probing, rejecting, filling imbalance, or triggering clustered orders?**

Canonical concepts include chart order blocks, FVG, liquidity sweep, SFP and inferred stop zones.

Epistemic rules:

```text
chart-derived order block != observed institutional order
chart-derived stop zone != observed stop inventory
FVG != guaranteed future fill
```

These are OHLCV-derived structural proxies unless direct order-book/order-flow evidence exists. Their schema should state `inference_type=CHART_DERIVED_PROXY`.

A common three-candle FVG geometry may be represented as:

```text
bullish_gap when low[t] > high[t-2]
bearish_gap when high[t] < low[t-2]
```

but the production contract must also define body/wick policy, minimum gap size, ATR normalization, mitigation/fill state and expiry.

A liquidity sweep should require a sequence:

```text
known liquidity/reference level
-> price trades beyond level
-> failure to accept beyond level
-> close/re-entry into expected region
-> optional displacement/participation confirmation
```

SFP reasoning should distinguish attempted breakout, excursion size, close location, reclaim speed, volume/RVOL, higher-timeframe location, repeated tests and next-bar confirmation. Liquidity intelligence is especially important to the anti-thesis of a breakout.

## 31.5 Value / Auction intelligence

Value/Auction answers: **Where has the market accepted business, and is current price near, above or below that value?**

### VWAP

Canonical session VWAP:

```text
typical_price = (high + low + close) / 3
VWAP = cumulative_sum(typical_price * volume) / cumulative_sum(volume)
```

The exact price basis must be configurable/versioned because implementations may use different price bases.

Use VWAP for session value location, reclaim/loss sequence, breakout acceptance context, pullback-to-value context and strategy side veto when required. `price > VWAP` is not a universal long signal.

### Anchored VWAP

Anchored VWAP uses the same weighted-average principle but resets at an explicit causal anchor such as session open, confirmed swing, event time, breakout event, result event or prior major gap. Every AVWAP must store `anchor_type`, `anchor_time`, `anchor_reason` and `anchor_available_at_decision_time`. Hindsight-selected anchors are not PIT-safe.

### VWAP bands

All VWAP envelopes must store their actual multiplier rather than only a display name:

```text
vwap_band:
  center = VWAP
  dispersion_method = VOLUME_WEIGHTED_RUNNING_STD
  sigma_multiplier = 1.0
  reset = SESSION
```

Repository-specific correction: a current legacy Trade Vision VWAP helper uses multipliers `0.5, 1.0, 1.5` while labeling outputs upper/lower `1,2,3`. Other implementations may mean `1,2,3` standard deviations. These must never share one canonical feature identity unless formula/config identity matches.

### POC / VAH / VAL / Volume Profile

Volume Profile must be a versioned volume-at-price approximation or exchange-derived profile. Contract must define window/session, price binning, number/width of bins, volume allocation, value-area percentage, POC tie-breaking and whether source data is actual trade-at-price or candle-distributed approximation.

POC is the price/bin with greatest modeled volume concentration. VAH/VAL are value-area boundaries for the configured volume mass, commonly around 70%, but that percentage is a parameter rather than a universal law. Volume Profile is primarily location/acceptance context, not a standalone next-direction forecast.

## 31.6 Volatility intelligence

Volatility answers: **How much is price moving, how unusual is the movement regime, and is volatility compressing or expanding?**

### ATR

```text
TR[t] = max(high-low, abs(high-close[t-1]), abs(low-close[t-1]))
ATR = versioned smoothing of TR, commonly Wilder/RMA over 14 bars
```

ATR is non-directional. Use it for normalized level distance, breakout extension, stop/target scale research, gap magnitude, volatility regime, buffer sizing and cross-instrument/timeframe comparison.

### Bollinger Bands

Classic default representation should be explicit:

```text
middle = SMA(close, 20)
upper = middle + 2 * rolling_std
lower = middle - 2 * rolling_std
```

If Trade Vision calculates +/-1 sigma and +/-3 sigma envelopes, they are useful extensions but must be named/versioned separately. Useful derived facts include normalized band width and percent-B. Band touches are not automatic buy/sell instructions; strong trends can walk a band.

### Keltner Channel

Version center, ATR method and multiplier. A common form:

```text
center = EMA(close, 20)
upper = center + k * ATR
lower = center - k * ATR
```

BB-inside-KC can be compression evidence; release can create an expansion hypothesis, but direction must come from structure/acceptance/context.

### Compression / Expansion

Compression can combine BB-width percentile, ATR percentile, BB/KC relationship, realized range contraction, volume behavior and structural-range duration. Expansion requires realized follow-through/acceptance, not only a volatility indicator turning up.

## 31.7 Trend intelligence

Trend answers: **What direction and persistence exist at each effective horizon?**

EMA recurrence:

```text
alpha = 2 / (period + 1)
EMA[t] = alpha * price[t] + (1-alpha) * EMA[t-1]
```

Preserve EMA 9/20-or-21/50/200 as distinct horizon observations:

```text
EMA9   -> fast impulse / immediate trend
EMA20  -> short-medium intraday trend
EMA50  -> structural intraday trend
EMA200 -> slow/background structure on that source timeframe
```

They share price dependency, so four bullish EMAs are not four independent proofs.

Useful facts: normalized slope, separation in bps/ATR, ordered stack, average compression, cross age, distance from stack and stack persistence.

Example:

```text
EMA9 > EMA20 > EMA50
all slopes rising
separation expanding
price not excessively extended
=> coherent same-timeframe trend structure
```

Different case:

```text
EMA9 > EMA20
EMA20 < EMA50
EMA50 falling
=> fast recovery inside still-bearish structural state
=> countertrend rally / short covering / early reversal possible
```

A longer moving average on 5m data is not equivalent to a true 1H trend. HTF evidence must come from closed native bars or validated closed-bar resampling.

Supertrend should be treated as ATR-based trailing trend state; version ATR method, multiplier, band-update rules and flip semantics.

Ichimoku should preserve Tenkan, Kijun, cloud state, price/cloud location, Tenkan/Kijun relation, cloud thickness and trailing-only decision-safe representation. Visual forward shifts must never introduce future information into decision time.

## 31.8 Momentum intelligence

Momentum answers: **Is the move accelerating, decelerating, stretched, diverging, or transitioning?**

- **RSI** — keep numeric value, slope, regime-adjusted zone, range shift, divergence and confirmation age. `RSI=75` can describe strength in a high-participation trend or support exhaustion anti-thesis at major resistance after a sweep.
- **MACD** — common form `EMA12-EMA26`, signal `EMA9(MACD)`, histogram `MACD-signal`. Keep sign, slope, histogram change, cross age and zero-line context.
- **Stochastic** — common `%K = 100*(close-lowest_N)/(highest_N-lowest_N)` with smoothed `%D`. Most useful for turning behavior in ranges/pullbacks; extreme values can persist in trends.
- **ADX/DMI** — ADX is primarily trend-strength information, not bullish/bearish direction. Direction belongs to +DI/-DI and surrounding trend/structure facts.
- **Divergences** — require confirmed pivots and therefore delay. Store pivot timestamps, confirmation timestamp, price relation, oscillator relation, hidden/regular type, direction, age and location context. Never backdate divergence evidence.

## 31.9 Participation intelligence

Participation answers: **Is trading activity supporting, rejecting or failing to confirm the price story?**

Absolute volume requires session context. For intraday NSE, prefer seasonality-aware RVOL such as current bar/cumulative volume divided by historical expected volume for the same elapsed session time.

OBV should be interpreted by trend/divergence rather than raw absolute level. CMF requires explicit handling of zero-range bars. MFI is a price-volume momentum sensor.

Dependency rule:

```text
Volume + RVOL + OBV + CMF + MFI
can enrich the participation story
but must not count as five independent confirmations.
```

## 31.10 Derivatives intelligence

Derivatives answers: **What positioning, volatility expectations, strike structure and convexity forces may change the path?**

### Price + OI change

Classic classification is contextual evidence:

```text
price up   + OI up   -> LONG_BUILDUP candidate
price down + OI up   -> SHORT_BUILDUP candidate
price up   + OI down -> SHORT_COVERING candidate
price down + OI down -> LONG_UNWINDING candidate
```

Open interest counts outstanding contracts; it does not reveal all participant direction by itself.

### Futures OI / Call-Put OI / PCR

Track current OI, delta, percent delta, price change, expiry, contract migration, rollover, basis and participant data where available. Large call OI is not automatically resistance and large put OI is not automatically support; interpretation depends on position side, OI change, price/IV move, expiry and participant composition.

PCR type must be explicit:

```text
PCR_OI = total_put_OI / total_call_OI
PCR_VOLUME = put_volume / call_volume
```

### IV / IV Rank / Skew

IV expresses option-implied expected volatility rather than bullish/bearish direction. Store whether IV is vendor/exchange supplied or locally solved and preserve model/assumptions.

A common IV rank form is:

```text
IV_rank = 100 * (current_IV - min_IV_window) / (max_IV_window - min_IV_window)
```

Window length and observation frequency are part of the feature identity.

25-delta skew must define its convention. Put-IV minus call-IV can indicate richer downside protection pricing but is not a direct next-candle signal.

### Max Pain

If used, calculate from one identified option-chain snapshot and store chain completeness, expiry and multiplier. Treat max pain as low/moderate contextual evidence whose value must be empirically tested, especially near expiry.

### Gamma / GEX / Vanna / Charm

Keep unsigned exposure, signed position exposure, assumed dealer exposure and observed/known dealer-position exposure distinct. Open interest alone does not identify dealer side. Preserve the existing Trade Vision law: dealer-signed GEX is unavailable unless dealer-position sign is explicitly supplied.

Vanna/charm are expiry/volatility-path modifiers and depend on time-to-expiry, underlying move, IV move and position assumptions. They are not standalone directional votes.

### Rollover / Basis

Rollover must preserve expiring and next-contract identity. Basis can be stored as raw observed basis:

```text
basis_bps = (futures_price - spot_price) / spot_price * 10_000
```

Raw basis must remain distinct from fair-value-adjusted basis using carry/dividend/time assumptions.

## 31.11 Market Context intelligence

Market Context answers: **Is the stock's local thesis aligned with or fighting its environment?**

Required context: Nifty/relevant benchmark, sector, relative strength, breadth, India VIX and events.

Represent stock/index/sector state at compatible horizons. A stock can be bullish while sector is weak; that may indicate genuine stock-specific leadership rather than automatic invalidation. M4 should ask whether the move can survive the headwind and whether historical evidence supports it.

Relative-strength benchmark and horizon must be explicit. A simple form is `stock_return_horizon - benchmark_return_horizon`; more advanced beta/volatility-adjusted forms must remain separately identified.

Breadth must define universe and calculation, such as advance/decline, percent above VWAP, percent above EMA20/50, up/down volume or sector participation. Universe changes must not silently alter comparability.

India VIX is expected-volatility context, not bullish/bearish direction. Use level, regime, change and shock as volatility/risk context.

Events require PIT availability and event-time identity. Important classes include company results, RBI policy, Budget/election sessions, corporate actions, exchange restrictions, F&O ban/MWPL and major scheduled macro releases. Unknown/stale event state cannot become `NO_EVENT`.

## 31.12 Memory intelligence

Memory answers: **Have we seen comparable states, what happened next, and how did similar cases fail?**

Canonical real 9-candle memory should remain based on the last nine closed bars, current M3.1 evidence, PIT-safe episodes, delayed labels and snapshot/time/hash verification. Improve retrieval/interpretation without reintroducing mock album data.

Pattern diary should store transition narratives:

```text
state_before
-> approach sequence
-> level interaction
-> breakout/rejection
-> value/VWAP behavior
-> participation behavior
-> context
-> derivatives context
-> outcome path
-> failure path
```

Similarity should use exact schema/version, missing masks, appropriate stock/timeframe/regime/phase filters, deterministic distances, bounded top-k, sample sufficiency and episode independence. Ten near-identical correlated episodes from one event are not ten independent proofs.

Failure trajectories deserve first-class storage. Example:

```text
approach resistance
-> breakout attempt
-> low acceptance
-> return below level
-> VWAP loss
-> participation deterioration
-> accelerated reversal
```

## 31.13 Real validated Kronos

Kronos is a sequence-model specialist, not an oracle.

Canonical influence rule:

```text
REAL MODEL
+ VERIFIED WEIGHTS
+ PIT-CLEAN INPUT
+ BENCHMARKED ON HELD-OUT NSE DATA
+ CALIBRATION / RELIABILITY RECEIPT
=> eligible as bounded sequence evidence

MOCK / FALLBACK / UNVERIFIED / OOD KRONOS
=> research-only
=> zero canonical decision influence
```

Useful outputs may include plausible forward K-line paths, direction/path distribution, realized-volatility distribution and breakout/reversal path likelihood only when actually calibrated. Never convert an uncalibrated model score into trade confidence. A larger model is not automatically better for NSE intraday; benchmark latency, horizon quality, calibration, robustness and OOS performance.

## 31.14 Semantic corrections that must become tests

1. `ATR_HIGH` means high movement/range, not bullish.
2. `VIX_UP` means expected volatility increased, not automatically bearish.
3. `ADX_HIGH` means trend strength, not automatically long.
4. `IV_HIGH` means options imply high volatility, not automatically long/short.
5. `OI_HIGH` means many outstanding contracts, not participant direction.
6. `CALL_OI_HIGH` does not automatically mean resistance.
7. `PUT_OI_HIGH` does not automatically mean support.
8. `BOLLINGER_UPPER_TOUCH` is not an automatic sell.
9. `BOLLINGER_LOWER_TOUCH` is not an automatic buy.
10. `FIBONACCI_LEVEL_TOUCH` is not sufficient to promote a thesis.
11. chart `ORDER_BLOCK` is an inferred zone, not proof of institutional orders.
12. `FVG` is imbalance geometry, not a guaranteed fill promise.
13. `VOLUME_PROFILE` is mainly location/acceptance context, not guaranteed forecast direction.
14. `SIGNED_DEALER_GEX` requires position-side evidence or an explicitly quarantined assumption.
15. multiple EMA/MACD/Supertrend facts do not become independent because names differ.
16. multiple memory matches from one correlated episode do not become independent observations.
17. higher-timeframe state must be closed/confirmed at decision time.
18. unavailable indicator/derivatives sources stay unavailable, not zero/neutral.

## 31.15 Market phase and active-question router

The router should first identify the active market problem:

```text
TREND_CONTINUATION
TREND_PULLBACK
BREAKOUT_ATTEMPT
BREAKOUT_ACCEPTANCE
BREAKOUT_FAILURE
LIQUIDITY_SWEEP
RANGE_MEAN_REVERSION
SQUEEZE_COMPRESSION
SQUEEZE_RELEASE
GAP_AND_GO
GAP_EXHAUSTION
EVENT_DISTORTION
EXPIRY_PINNING_OR_GAMMA
MULTI_TIMEFRAME_CONFLICT
NO_EDGE_CHOP
POST_ENTRY_THESIS_CHECK
```

The router does not delete nonselected evidence. It changes reasoning depth/priority while retaining contradictions and hard safety facts.

For a breakout attempt, primary evidence should emphasize structure/location, VWAP/value, volume/RVOL, acceptance closes, index/sector/RS, nearby liquidity and strike/OI structure; trend/momentum/memory/Kronos become secondary or conditional according to context.

## 31.16 Unified case reasoning playbooks

### Case A — Trend continuation / pullback

Ask whether this is a healthy pullback inside an intact trend or beginning trend failure. Support can require intact higher-horizon structure, coherent EMA horizon state, pullback into value/support rather than uncontrolled extension, VWAP/AVWAP/EMA/support interaction, contraction then participation expansion, non-hostile context, no dominant event/derivatives obstruction and comparable successful memory.

Anti-thesis searches for CHOCH, value failure, lower-high response, expanding opposite participation, sector/index deterioration, HTF obstruction and known memory failure paths.

### Case B — Breakout acceptance

Require a confirmed level, defined close/buffer beyond it, participation/RVOL support, hold or successful retest, VWAP/value alignment, structural continuation, acceptable ATR extension, non-hostile context and no dominant OI/liquidity/event obstruction. Anti-thesis is fake breakout/sweep/exhaustion. `close > resistance` alone is insufficient.

### Case C — False breakout / liquidity sweep reversal

Strong narrative:

```text
known level
-> excursion beyond level
-> failed acceptance
-> re-entry
-> SFP/sweep structure
-> opposite displacement
-> VWAP/value reversal
-> participation confirms rejection
```

Memory should compare prior false-break trajectories. Kronos may challenge with alternative continuation paths but cannot override real rejection evidence.

### Case D — Range / mean reversion

Look for weak/flat structural progression, low trend-strength state, repeated VWAP/POC crossing, stable VAH/VAL/range boundaries, oscillating momentum, failed edge breaks and moderate/declining volatility. Do not apply trend-continuation logic in range center. Range-edge reversal hypotheses weaken when participation/volatility expands and acceptance develops outside value.

### Case E — Compression -> expansion

Compression combines low BB width percentile, BB/KC squeeze, ATR contraction, narrowing structure and reduced movement. Expansion confirmation requires a break, increasing realized volatility, participation expansion, value acceptance and structural continuation. Direction comes from structure/acceptance/context, not compression itself.

### Case F — Gap-and-go vs gap exhaustion

Normalize gap by ATR and corporate actions. Compare gap magnitude, opening-drive acceptance, OR structure, VWAP, RVOL, index/sector, event catalyst, prior-day levels, derivatives and same-stock gap memory. Extreme gap + weak acceptance + major resistance + fading participation strengthens exhaustion anti-thesis.

### Case G — Multi-timeframe conflict

Example:

```text
5m bullish BOS + EMA stack
15m transition
1H bearish structure near resistance
```

Do not average to neutral. Preserve `FAST=bullish opportunity`, `MEDIUM=transition`, `HIGHER=bearish headwind`, then ask whether strategy horizon can complete before HTF opposition dominates. This may cap to WATCH.

### Case H — Event shock / distorted market

Events can veto pending entries, widen uncertainty, invalidate analog comparability, alter volatility regime, increase derivatives relevance and reduce value of lagging indicators. Unknown event status is not no event.

### Case I — Expiry / pinning / convexity

Near expiry increase relevance of strike concentration, spot-to-strike distance, gamma state, IV structure, skew, charm/vanna, rollover/basis and low-authority max-pain context. Assumed dealer positioning must never become observed fact.

### Case J — No edge / chop

The engine must be able to conclude no coherent thesis deserves promotion. Repeated conflicting breaks, unstable structure, value recrossing, poor participation, material evidence conflict, insufficient memory, missing required context or a fragile decision that flips under small perturbations should produce `WAIT`, not a forced directional forecast.

## 31.17 Hypothesis Engine v2 consumption contract

Hypothesis Engine v2 should consume immutable canonical evidence and not independently recompute the market.

Every hypothesis should contain:

```text
hypothesis_id
hypothesis_type
direction
source_timeframe
effective_horizon
market_phase
thesis
required_facts[]
supporting_evidence_ids[]
opposing_evidence_ids[]
unknown_required_evidence[]
anti_thesis_id
invalidators[]
expected_sequence[]
expected_failure_sequence[]
expiry_condition
regime_assumptions[]
fragility_factors[]
OOD_state
robustness_state
```

Candidate types include LONG/SHORT CONTINUATION and REVERSAL, BREAKOUT FOLLOW-THROUGH/FAILURE, RANGE MEAN REVERSION, SQUEEZE EXPANSION, GAP-AND-GO, GAP EXHAUSTION FADE, LIQUIDITY SWEEP REVERSAL, TREND PULLBACK, EVENT-DISTORTED MARKET and CHOP/NO-EDGE.

No hypothesis may invent fallback S/R, entry, invalidation or confirmation boundaries when required levels are unavailable. No hand-built rule score may be renamed probability without a PIT-clean calibration contract.

## 31.18 Relationship and independence graph

Replace broad correlation buckets with explicit graph edges:

```text
DERIVED_FROM
SHARES_INPUT_WITH
CORRELATED_WITH
CONFIRMS
CONTRADICTS
REQUIRES
INVALIDATES
LEADS
LAGS
CONDITIONAL_ON
LOCATION_CONTEXT
FAILURE_PRECURSOR
REGIME_DEPENDENT
TIMEFRAME_PARENT
TIMEFRAME_CHILD
SAME_EPISODE_AS
```

Example:

```text
EMA9 SHARES_INPUT_WITH EMA20
EMA20 SHARES_INPUT_WITH EMA50
MACD DERIVED_FROM close
Supertrend DERIVED_FROM price + ATR
BOS_UP CONFIRMED_BY acceptance_close
BOS_UP CONFIRMED_BY RVOL_EXPANSION
BOS_UP CONTRADICTED_BY SFP_DOWN
BOS_UP CONDITIONAL_ON breakout_level_confirmed
LONG_BREAKOUT THREATENED_BY daily_resistance
LONG_BREAKOUT INVALIDATED_BY accepted_reentry_below_level
```

Independent support counts only when graph/episode identity supports independence.

## 31.19 Failure engine

Required failure classes include at least:

```text
FALSE_BREAKOUT
NO_ACCEPTANCE
OR_TOO_WIDE
OR_TOO_NARROW
GAP_EXHAUSTION
EVENT_SHOCK
VIX_SHOCK
DOUBLE_STOP_WHIPSAW
HTF_OPPOSITION
VALUE_REJECTION
OI_WALL_REJECTION
EXPIRY_PINNING
ROLLOVER_DISTORTION
LIQUIDITY_DRY_UP
FEED_STALE
BAD_TICK
PIT_FAILURE
OOD
MEMORY_SAMPLE_TOO_SMALL
EDGE_DECAY
```

For each active thesis, produce likely failure path, dangerous failure path, earliest precursor, confirming precursor, invalidation and whether failure risk caps promotion.

## 31.20 Counterfactual and adversarial challenge

Before promotion, run bounded deterministic challenges such as removing strongest support, removing correlated duplicates, reversing index/sector context, marking one key feed stale, removing memory support, replacing memory with OOD, removing Kronos, adding nearby higher-authority resistance, introducing a liquidity-sweep alternative, increasing event risk and adding contradictory derivatives evidence.

Ask whether the thesis remains logically valid, required evidence remains satisfied, a stronger anti-thesis emerges, final band changes or the conclusion depends on one factor. Do not ask only whether a numeric score remains above threshold.

## 31.21 D6 target semantics — categorical arbitration, not weighted master score

The current D6 v1.75 weighted-score implementation is a migration baseline, not the target M4 reasoning model.

Target D6 inputs should include semantic states such as:

```text
SAFETY
DATA_INTEGRITY
THESIS_STATE
ANTI_THESIS_MATERIALITY
REQUIRED_EVIDENCE_COVERAGE
INDEPENDENT_SUPPORT
CONFLICT_STATE
FAILURE_RISK
OOD_STATE
ROBUSTNESS
FRAGILITY
ENTRY_PLAN_AUTHORITY
```

Possible deterministic lattice:

```text
hard safety/integrity blocker -> WAIT/AVOID according to product contract
invalid thesis -> WAIT
required evidence incomplete -> WAIT or WATCH
material anti-thesis + unresolved conflict -> WATCH
material failure risk or fragile robustness -> WATCH
valid thesis + complete required evidence + sufficient independent support
+ resolved anti-thesis + no hard blocker + survives failure challenge
+ acceptable OOD/robustness -> PAPER-CANDIDATE
```

D6 remains the only final-band authority and remains non-executing.

## 31.22 Calculation normalization and compatibility layer

Create a calculation-definition registry containing:

```text
feature_id
formula_id
formula_version
parameters
units
input_schema
input_timeframe
minimum_history
warmup_policy
session_reset_policy
anchor_policy
pivot_confirmation_policy
missing_policy
error_policy
PIT_policy
output_schema
```

Migration checks:

1. resolve VWAP band naming/multiplier mismatches;
2. resolve BB naming/multiplier mismatches;
3. version alternative pivot formulas;
4. version volume-profile bin/allocation methods;
5. distinguish native HTF from resampled HTF;
6. distinguish confirmed from forming pivots;
7. distinguish chart-inferred SMC proxies from observed order-flow facts;
8. distinguish supplied IV from locally solved IV;
9. distinguish unsigned GEX from signed/assumed dealer GEX;
10. distinguish OI-PCR from volume-PCR;
11. distinguish raw basis from fair-value-adjusted basis;
12. reject same feature id when formula/config identities disagree.

## 31.23 Runtime design for speed and resilience

The system should feel intelligent because it reuses one coherent world model, not because it repeatedly runs 94 independent calculators.

Market Fact Kernel computes reusable primitives once: OHLCV arrays, returns, true range/ATR, rolling min/max, EMA family, SMA/std family, session boundaries, VWAP accumulators, volume baselines, confirmed pivots, swing state, level distances and closed resampled timeframes.

Use a dependency DAG so derived sensors reuse these primitives. Maintain safe incremental state where batch-equivalence can be proven. Cache identity must include snapshot hash, source timeframe, formula version, parameter hash and relevant window hash. Never cache by symbol alone.

Set tested bounds for evidence nodes, hypotheses, conflicts, memory matches, scenarios, counterfactuals, receipt bytes and CPU/memory per decision. No network call, historical corpus scan or required LLM call inside deterministic D6.

## 31.24 Error semantics — make canonical paths non-silent

Legacy wrappers may return empty lists/dicts on exceptions for compatibility. Canonical M4 must not interpret an exception-empty result as genuine no-signal.

Required statuses:

```text
AVAILABLE
NO_SIGNAL
WARMUP
MISSING_INPUT
DEPENDENCY_UNAVAILABLE
STALE
UNCONFIRMED
ERROR
UNSUPPORTED
QUARANTINED
OOD
```

Material epistemic states must survive into the decision receipt.

## 31.25 Robust engineering meaning of “non-breakable”

No market system is literally unbreakable. Target fail-closed behavior, deterministic replay where required, immutable decision inputs, explicit schema/version migrations, backward-compatible adapters, no silent coercion, bounded compute, idempotent calculations, property/adversarial tests, corrupted/missing/stale data fixtures, exact-head CI gates, rollback per stage and unchanged live-trading safety boundaries.

## 31.26 Required acceptance tests for this research upgrade

### Formula identity
- VWAP multiplier is part of feature identity.
- same display label with different multiplier cannot merge silently.
- BB +/-1/+/-2/+/-3 extensions remain distinguishable from classic defaults.
- alternate pivot/profile formulas receive distinct version ids.

### Direction semantics
- ATR, India VIX, ADX, IV or raw OI alone cannot set long/short direction.

### Dependency / independence
- EMA9/20/50/200 agreement is not four independent families.
- MACD+EMA cannot multiply independent support without graph justification.
- OBV/CMF/MFI/RVOL dependencies are represented.
- unlimited duplicate evidence cannot overpower D1.

### Structure / PIT
- future-confirmed pivots cannot appear early.
- unfinished HTF bars are never closed evidence.
- PDH/PDL use prior completed exchange session.
- event availability time is respected.

### SMC epistemics
- chart order block is proxy/inference.
- FVG does not imply guaranteed fill.
- sweep uses defined excursion + acceptance/re-entry logic.

### Derivatives
- OI build-up needs price and OI deltas.
- PCR type is explicit.
- signed dealer GEX unavailable without sign evidence.
- IV rank unavailable with insufficient history.
- expiry/rollover contract identities cannot mix.

### Memory
- delayed labels unavailable before label time.
- correlated episodes cannot inflate independent count.
- missing masks remain in similarity identity.
- mock 9C remains unreachable from canonical M4.

### Kronos
- mock/fallback Kronos has zero canonical influence.
- OOD/unverified output cannot promote.
- model version/input hash appear in receipt.

### Hypothesis
- no fabricated S/R or boundaries.
- every trade-like thesis has anti-thesis.
- unknown required evidence stays explicit.
- fake probability labels rejected without calibration.

### D6
- final authority remains singular.
- reviewers/specialists cannot directly upgrade final band.
- safety blockers dominate unlimited support.
- unresolved material conflict caps promotion.
- fragile/single-factor thesis cannot become PAPER-CANDIDATE.
- no execution/order-routing authority introduced.

## 31.27 Reconciliation with existing agreed planning order

The saved priority remains:

```text
Hypothesis Box
-> Twin
-> ORB / AFRE
-> Kronos
-> Indicators / M3.1
-> 9-Candle Real Memory / M3.3
-> History + Pattern Diary / M3.3
-> Old Fake Album remains outside production
```

New dependency law:

```text
Planning order != unsafe implementation shortcut.
```

Hypothesis v2 may be designed first, but production code must not invent evidence while later Fact-Kernel/Indicator work is unfinished. Missing required evidence stays missing and may cap the hypothesis. Twin can be improved second but canonical conflict/independence semantics must not depend on Twin alone. ORB/AFRE remain proposal specialists; Kronos remains bounded sequence evidence; M3.1/M3.3 improvements strengthen the same contracts without changing authority.

## 31.28 Updated engine-specific planning checklist

Every future dedicated engine plan should answer:

```text
1. What exact market question does this engine answer?
2. Which facts does it consume?
3. Which facts does it calculate, if any?
4. What formula/config versions exist today?
5. Are any names hiding different calculations?
6. What is its effective horizon and source timeframe?
7. What can be known at decision time?
8. What needs delayed confirmation?
9. Which inputs are shared/correlated?
10. Which evidence can actually be independent?
11. Which market phases make the engine relevant?
12. Which regimes weaken it?
13. What supports its thesis?
14. What contradicts it?
15. What invalidates it?
16. What information can be missing?
17. How does missingness propagate?
18. What is its likely failure path?
19. What is its dangerous failure path?
20. What counterfactual should challenge it?
21. What OOD/drift state can occur?
22. What historical evidence is PIT-safe?
23. What mock/synthetic paths stay quarantined?
24. What authority may it exercise?
25. What authority is explicitly forbidden?
26. What bounded latency/memory design applies?
27. What deterministic replay proof is required?
28. What adversarial tests are required?
29. What migration/rollback path exists?
30. What exact evidence marks GREEN/LOCKED?
```

## 31.29 Example unified reason receipt

```text
ACTIVE_CASE:
BREAKOUT_ATTEMPT

MARKET_PHASE:
OPENING_BREAKOUT_ATTEMPT

THESIS:
BREAKOUT_FOLLOW_THROUGH

SUPPORT:
- confirmed ORH break
- accepted close above ORH
- price above session VWAP
- EMA9>20>50 with positive slopes
- RVOL elevated for same session time
- Nifty and sector supportive

DEPENDENCY_NOTE:
- EMA stack and MACD share price-trend dependency
- RVOL and OBV share volume dependency
- descriptive richness != duplicate independent proof

OPPOSITION:
- daily resistance 0.31 ATR above
- concentrated call OI near next strike

UNKNOWN:
- participant OI unavailable

ANTI_THESIS:
BREAKOUT_FAILURE / LIQUIDITY_SWEEP

EXPECTED_NEXT_IF_THESIS_TRUE:
- hold above ORH
- shallow retest
- VWAP remains below price
- participation remains healthy

EARLY_FAILURE_PRECURSOR:
- immediate re-entry below ORH

INVALIDATION:
- accepted close below ORH plus VWAP loss

MEMORY:
- analogous PIT-safe episodes available
- material historical failure subset rejected at daily resistance

KRONOS:
- REAL_VALIDATED or UNAVAILABLE
- never mock-influenced

ROBUSTNESS:
MODERATE

D6 RESULT:
WATCH

WHY:
Thesis is valid but opposition/failure risk remains material and unresolved.
```

This is desired explainability: structured facts, relationships, alternatives, invalidators and authority outcomes, not hidden chain-of-thought or a weighted indicator-vote dump.

## 31.30 Research references retained for future plan authors

- NSE India VIX overview: https://www.nseindia.com/static/products-services/indices-indiavix-index
- CME open-interest reference: https://www.cmegroup.com/market-data/volume-open-interest/about.html
- TradingView VWAP reference: https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/
- TradingView Relative Volume at Time: https://www.tradingview.com/support/solutions/43000635874-how-do-we-calculate-relative-volume-and-relative-volume-at-time/
- Bollinger Bands official material: https://www.bollingerbands.com/
- Fidelity technical-indicator reference library: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/overview
- Support/resistance empirical study: https://arxiv.org/abs/2101.07410
- Fibonacci retracement empirical study: https://www.sciencedirect.com/science/article/abs/pii/S0957417421012495
- Kronos paper: https://arxiv.org/abs/2508.02739
- Kronos official repository: https://github.com/shiyu-coder/Kronos

## 31.31 Final merged design principle

The unified Trade Vision reasoning engine should know **what each observation means, what it does not mean, how it was calculated, when it became knowable, which observations share its information, which market problem makes it relevant, what alternative explanation competes with it, and how the thesis can fail**.

The system becomes stronger by combining relationships, not by forcing every sensor into one number.

Canonical summary:

```text
TRUTHFUL DATA
-> VERSIONED MARKET FACTS
-> SEMANTIC EVIDENCE
-> CONTEXT / PHASE
-> RELATIONSHIP + INDEPENDENCE GRAPH
-> THESIS + ANTI-THESIS
-> FAILURE / SCENARIO / COUNTERFACTUAL CHALLENGE
-> ROBUSTNESS / OOD / UNCERTAINTY
-> D6 SOLE FINAL AUTHORITY
-> WAIT / WATCH / PAPER-CANDIDATE
```

This section is a research/design source. It does not claim these enhancements are implemented or GREEN/LOCKED until code, tests, adversarial replay and exact-head CI prove them.

