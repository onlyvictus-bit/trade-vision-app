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
