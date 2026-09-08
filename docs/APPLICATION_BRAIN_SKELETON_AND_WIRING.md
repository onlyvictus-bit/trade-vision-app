# TRADE VISION — APPLICATION BRAIN, SKELETON & WIRING REFERENCE

> **Purpose:** Durable plain-English map of how Trade Vision thinks, calculates, arbitrates, and produces a final trading-research decision.
>
> Use this file before changing decision logic, adding a new engine, rewiring an existing engine, changing ORB/AFRE behavior, or adding a new final-output surface.
>
> **Created:** 2026-09-08  
> **Last roadmap update:** 2026-09-08 — added the Canonical Decision Spine / Brain Orchestration evolution sequence.  
> **Code scope reviewed:** active API wiring plus major Behavior, ORB, adaptive AFRE, Jarvis, risk, memory, hypothesis, derivatives, replay/proof and external-review paths.  
> **Important branch note:** the AFRE v4 failure/derivatives/18-variant work described here is present on `afre-v4-production-hardening`; it is not assumed to be merged into `main` until the PR is merged.  
> **Source-of-truth rule:** this document explains the architecture. Implementation code remains the executable source of truth.

---

## 1. The application in one sentence

Trade Vision is not one trading algorithm. It is a **team of specialist calculation and reasoning engines** that convert trusted market evidence into a bounded decision such as `WAIT`, `WATCH`, `NO_TRADE`, or `PAPER-CANDIDATE`, with reasons, invalidation, risk, and next required evidence.

The system should behave like a disciplined trading desk:

- data-quality staff decide whether inputs are trustworthy;
- calculation engines describe price, volume, indicators and levels;
- context engines explain where the move is happening;
- memory engines compare current behavior with history;
- strategy engines recognize ORB/ORR and other setups;
- derivatives and event engines add non-price context;
- failure engines actively search for ways the idea can fail;
- risk and execution engines test whether the idea is realistically tradable;
- arbiter engines resolve disagreement;
- Jarvis converts the result into a human-readable decision room;
- proof, safety and human approval remain above any paper candidate;
- live broker routing remains outside Trade Vision and blocked by design.

---

## 2. The easiest mental model

```text
                         MARKET / REFERENCE DATA
                                  |
                                  v
                         DATA QUALITY + PIT
                                  |
                                  v
                    CALCULATION / FEATURE LAYER
                 candle / ATR / VWAP / indicators /
                    levels / gaps / volume / MTF
                                  |
              +-------------------+-------------------+
              |                   |                   |
              v                   v                   v
          PRICE BRAIN         CONTEXT BRAIN       MEMORY BRAIN
       candle/structure      levels/index/HTF    similar history/
        condition state       sector/session       stock behavior
              |                   |                   |
              +-------------------+-------------------+
                                  |
                                  v
                         STRATEGY / HYPOTHESIS
                         ORB / ORR / scenarios
                                  |
                 +----------------+----------------+
                 |                                 |
                 v                                 v
         DERIVATIVES / EVENT                 FAILURE / RISK BRAIN
       VIX / IV / PCR / OI /               trap / chop / event /
       GEX / basis / rollover              data / model failures
                 |                                 |
                 +----------------+----------------+
                                  |
                                  v
                     EXECUTION + PORTFOLIO REALITY
                 liquidity / spread / slippage / R:R /
                       exposure / cooldown / loss
                                  |
                                  v
                         DECISION ARBITRATION
               Behavior Decision / Confluence / Twin /
                        Jarvis Arbiter + Fusion
                                  |
                                  v
                       ONE HUMAN-FACING OUTPUT
                 WAIT / WATCH / NO_TRADE / PAPER-CANDIDATE
                entry / stop / target / invalidation / why /
                      wait-for / avoid-if / blockers
                                  |
                                  v
                    PROOF + SAFETY + HUMAN APPROVAL
                                  |
                                  v
                              PAPER ONLY
```

### Core design principle

A lower-priority engine must not be able to overrule a higher-priority safety fact.

Examples:

- bullish indicators cannot overrule bad data;
- a forecast cannot overrule a liquidity block;
- Gemini/Grok/Kronos cannot upgrade a Trade Vision `NO_TRADE`;
- an observed ORB variant cannot bypass ORB proof;
- unavailable external data must remain unavailable, not be treated as neutral/safe.

---

## 3. What the project is trying to answer

For a stock and a point in time, the full application should answer:

1. What is price doing now?
2. What candle/auction behavior produced that move?
3. Where is price relative to VWAP, OR, CPR, PDH/PDL and other levels?
4. Does the higher timeframe agree?
5. Do Nifty/sector/relative-strength conditions agree?
6. What session phase are we in, and how does this stock normally behave in this phase?
7. Have similar historical situations occurred?
8. Is continuation, reversal, fakeout, chop, or another scenario more plausible?
9. Which strategy/ORB variant is actually observed or armed?
10. What do derivatives and event conditions add or warn about?
11. What can make this setup fail?
12. Is the data complete, causal and point-in-time safe?
13. Is liquidity/execution quality good enough?
14. Is risk/reward and portfolio risk acceptable?
15. Is there enough historical/OOS/walk-forward proof?
16. What is the best action now?
17. If action is not ready, exactly what should the system wait for?
18. What observation would invalidate/cancel the idea?

The intended output is **decision intelligence**, not a blind signal.

---

## 4. Major specialist brains and their jobs

| Brain / engine | Simple job | High-signal code |
|---|---|---|
| Data adapter / quality | Convert data into canonical form; reject bad inputs | `behavior/data_adapter.py`, `behavior/data_quality.py` |
| Point-in-time / causal guard | Prevent future or incomplete information from entering a decision | `behavior/point_in_time_guard.py`, `behavior/causal_whitelist.py`, `behavior/timeframe_sync.py` |
| Candle Anatomy | Measure body, wick, range, ATR relation, volume effort, gaps and candle structure | `behavior/candle_anatomy.py` |
| Condition Classifier | Classify breakout, fakeout, chop, absorption, accumulation, distribution, etc. | `behavior/condition_classifier.py` |
| Context Engines | VWAP/ORB/CPR/PDH/PDL, HTF, gap, index/sector/relative-strength context | `behavior/context_engines.py` |
| Market regime / structure | Describe regime, liquidity and structural environment | `behavior/market_regime_feedback.py`, `behavior/market_structure_liquidity.py` |
| Indicator intelligence | Technical indicator observations, voting, reliability and history | `behavior/indicator_*`, replay indicator modules |
| Session / Stock DNA memory | Learn time-of-day and day-of-week behavior with minimum-sample guards | `behavior/session_memory.py`, `behavior/stock_memory_profile.py` |
| Pattern / similar history | Compare current structure with old paths and outcomes | `behavior/pattern_memory.py`, `behavior/analog_research.py`, `behavior/combination_similarity.py`, `behavior/design_similarity.py` |
| Nine-candle hybrid | Short-horizon setup DNA, analogs and calibration | `behavior/nine_candle_*` |
| Hypothesis Engine | Keep continuation, reversal and fakeout explanations competing | `behavior/hypothesis_engine.py` |
| ORB Core | Build OR, detect ORB/ORR signal, produce research entry/SL/target | `orb/core.py` |
| ORB Discovery | Search historical ORB parameter combinations | `orb/discovery.py` |
| ORB Proof / Playbook | Train-only selection, holdout, walk-forward, promotion gate | `orb/proof.py` |
| Adaptive ORB / AFRE | Stateful causal ORB scenario controller | `orb/adaptive/controller.py`, `orb/adaptive/runtime.py` |
| 18-variant ORB assessment | Observe every original ORB variant without bypassing proof | `orb/adaptive/variants.py` |
| Failure detector | Detect A-G registered failure scenarios | `orb/adaptive/scenario_detection.py`, `orb/adaptive/registry.py` |
| Derivatives overlay | VIX/IV/PCR/OI/max pain/GEX/basis/rollover/GIFT/FII calculations | `orb/adaptive/derivatives.py` |
| External factual risk context | Result/MPC/macro/ex-dividend/restriction/data/model facts | `orb/adaptive/risk_context.py` |
| Execution/Event/OI reality | Fill probability, spread, slippage, impact, event/options limits | `behavior/execution_event_oi_risk.py` |
| Behavior Risk | Position/risk sizing and portfolio/daily-loss/cooldown gates | `behavior/risk_engine.py` |
| Execution simulator | Research-only fill/slippage/latency/queue/impact behavior | `behavior/execution_simulator.py` |
| Behavior Decision | Universal-agreement decision + safety gates | `behavior/decision_engine.py` |
| Final Confluence Arbiter | Resolve conflicts using priority-weighted evidence hierarchy | `behavior/final_confluence_arbiter.py` |
| Kronos / Twin | Compare Behavior conclusion with forecast prior; disagreement downgrades | `behavior/kronos_proxy.py`, `behavior/twin_arbiter.py` |
| Gemini / Grok reviewers | External review/explanation only | `behavior/gemini_provider.py`, `behavior/grok_provider.py`, `behavior/grok_gateway_provider.py` |
| Jarvis Decision Room | Assemble chart, indicators, history, reviewers, safety and decision | `behavior/jarvis_decision_room.py` |
| Jarvis Arbiter | Enforce no-upgrade conflict and safety rules | `behavior/jarvis_decision_arbiter.py` |
| Jarvis Fusion | Combine Trade Vision + external reviewer evidence read-only | `behavior/jarvis_decision_fusion.py` |
| Jarvis Master Panel | Human-facing all-evidence panel; old paths preserved | `behavior/jarvis_master_panel.py` |
| Trading Decision Output | Final trader-readable plan/evidence/blocker presentation | `behavior/jarvis_trading_decision_output.py` |
| Proof / release / safety | Replay, validation, drift/OOD, evidence export and approval | `behavior/validation.py`, `behavior/safety_hardening.py`, `behavior/release_*`, ORB proof |
| API spine | Wires the above engines into endpoints and system pipeline | `apps/api/app/main.py` |

---

## 5. Input trust layer — the first authority

Before interpreting a pattern, Trade Vision should prove that the inputs are usable.

Typical questions:

```text
Is the candle closed?
Is its timestamp valid?
Is there a duplicate/revision conflict?
Is OHLC mathematically possible?
Is the feature from the future?
Are higher timeframes closed at the decision timestamp?
Are symbols/timeframes synchronized?
Is a reference/capability still valid and unexpired?
```

### Required behavior

- Invalid data must block or quarantine the affected decision.
- Missing data must not silently become zero/neutral.
- Future/full-day information must never enter an intraday decision.
- A new engine must consume the same causal snapshot instead of inventing a parallel non-PIT data path.

This layer outranks all forecasts, indicators and patterns.

---

## 6. Candle / price behavior brain

`behavior/candle_anatomy.py` converts a raw candle into structural facts such as:

- body size and body %;
- upper/lower wick %;
- close-location value;
- range relative to ATR;
- volume z-score;
- effort-versus-result;
- wick clusters;
- inside/outside bar;
- gap %;
- follow-through count;
- failed follow-through;
- trend, rejection, engulfing, compression, expansion, fake-break, absorption-looking and distribution-looking tags.

The intended reasoning is not `green candle = bullish`; it is a richer description of **how price moved and whether the move was accepted or rejected**.

`behavior/condition_classifier.py` then converts those facts into conditions such as:

- opening-drive continuation;
- opening-drive reversal;
- range/balance;
- breakout day;
- fake breakout;
- VWAP rejection/support trend;
- absorption;
- accumulation/distribution;
- compression-before-expansion;
- choppy/avoid;
- manipulated-looking movement.

It can also mark a condition as trade-blocking.

---

## 7. Context brain — pattern plus location

A pattern is not meaningful without its location and broader market state.

The context layer evaluates:

- VWAP;
- ORH/ORL;
- CPR;
- PDH/PDL;
- volume-profile nodes where supplied;
- higher-timeframe confirmation;
- gap type / fill / trap context;
- Nifty/index direction;
- sector direction;
- stock relative strength;
- global-risk context where supplied.

Example principle:

> A bullish candle at support with VWAP and index alignment is different from the same candle directly under resistance while the sector is weak.

Context can veto a setup even when a local pattern is attractive.

---

## 8. Memory and analog brain

Trade Vision contains several memory families. They must be treated as **evidence**, not oracle predictions.

### Session memory

The NSE day is divided into behavioral windows including:

- 09:15-09:30 opening drive;
- 09:30-10:15 trend confirmation;
- 10:15-11:30 continuation/fade;
- 11:30-13:30 lunch compression;
- 13:30-14:30 post-lunch expansion;
- 14:30-15:15 closing drive;
- 15:15-15:30 square-off/fake-spike risk.

It learns continuation/fakeout quality for the stock by session phase and day of week.

### Historical analog families

The project also contains:

- pattern memory;
- day-shape similarity;
- combination similarity;
- design similarity;
- event-sequence mining;
- exact-time session memory;
- nine-candle analog/calibration;
- indicator sequence/reliability memory;
- candle cause/effect memory.

### Evidence guard

Strong historical claims should remain blocked until minimum sample requirements pass. Low sample is a reason to reduce confidence, not an invitation to invent precision.

---

## 9. Hypothesis brain — do not lock into one story too early

`behavior/hypothesis_engine.py` explicitly keeps competing explanations alive:

```text
CONTINUATION
REVERSAL
FAKEOUT
```

Each hypothesis has:

- supporting factors;
- opposing factors;
- a relative score/probability;
- a confirmation trigger;
- an invalidation level.

Future upgrades should preserve this mindset: **new evidence should update/refute hypotheses rather than merely add more bullish/bearish votes**.

---

## 10. ORB is two different subsystems

### 10.1 ORB research / discovery / proof

The original ORB stack is a research pipeline:

```text
Causal closed bars
      -> ORB Core
      -> historical Discovery
      -> train-only candidate selection
      -> unseen holdout
      -> expanding walk-forward
      -> promotion eligibility
      -> stored playbook
```

`orb/core.py` builds the opening range and identifies configured ORB/ORR signals.

`orb/discovery.py` searches combinations.

`orb/proof.py` ensures a candidate is not selected using future/holdout results. Promotion requires sufficient train trades, OOS performance and repeated walk-forward success.

### 10.2 Adaptive ORB / AFRE

AFRE is the **during-the-session scenario controller**.

It reconstructs state from a bounded immutable causal prefix and does not use an LLM/repeated debate/online fitting for the core decision.

Its main scenario branches are:

1. accepted continuation;
2. orderly retest;
3. failed break;
4. unfilled-gap fade;
5. failure then reclaim;
6. two-sided chop;
7. extension/exhaustion risk;
8. unknown/unsupported.

A new closed bar can strengthen, weaken, refute or confirm these branches.

An observed scenario does not automatically become an executable plan.

---

## 11. The complete 18 ORB variant catalogue

The adaptive branch assesses all 18 original ORB variants from the same causal snapshot:

1. `V01` Classic ORB-15
2. `V02` ORB-5 micro
3. `V03` ORB-30
4. `V04` Volume-confirmed ORB
5. `V05` VWAP-filtered ORB
6. `V06` Index-aligned ORB
7. `V07` Narrow-OR expansion
8. `V08` Wide-OR reduced-risk
9. `V09` Gap-and-go
10. `V10` Gap-fade / ORR
11. `V11` False-breakout reversal
12. `V12` Pullback / retest
13. `V13` Second-chance reclaim/re-entry
14. `V14` Post-result ORB
15. `V15` PDH/PDL breakout
16. `V16` Expiry-day ORB
17. `V17` Afternoon range breakout (research-only unless policy-promoted)
18. `V18` Extension / no-chase

Each assessment uses a state such as:

```text
UNOBSERVABLE
WAITING
ARMED
CONFIRMED
BLOCKED
```

### Critical authority rule

`CONFIRMED` means **the market pattern is observed**. It does not mean `TAKE TRADE`.

The existing TradePlan/proof/paper gate remains authoritative.

### Large-gap rule

The registered large-gap threshold in adaptive ORB is **strictly**:

```text
gap > 1.5 x prior ATR
```

Exactly `1.5 x ATR` is not classified as large. Do not silently reintroduce the old 1.4x multiplier or hidden 1% floor.

---

## 12. Failure brain — ask how the idea can fail before asking how much it can make

The adaptive failure detector covers the registered A-G families.

### A — Regime

- chop;
- VIX coma;
- VIX spike/high-volatility risk;
- gap exhaustion (`>1.5 x ATR`);
- news/shock conditions.

### B — Signal

- false breakout;
- OR too wide;
- OR too narrow;
- first-bar contamination proxy;
- level staleness/cutoff;
- double-stop whipsaw.

### C — Event

- result-day whipsaw;
- RBI MPC window;
- budget/election/macro event;
- ex-dividend misread/adjustment.

### D — Instrument

- circuit lock;
- ASM/GSM/T2T/surveillance restriction;
- illiquidity/slippage;
- F&O ban.

### E — Data / execution

- feed lag / bad tick / invalid prefix;
- order rejection / broker square-off risk;
- PIT violation;
- backtest/live mismatch.

### F — Derivatives

- expiry pinning;
- gamma squeeze / negative-gamma shock risk;
- OI wall rejection;
- rollover distortion.

### G — Statistical

- edge decay;
- overfit risk;
- small sample.

### State semantics

The detector intentionally separates:

```text
OBSERVED_*       = condition is evidenced now
RISK_ARMED_*     = precursor exists; failure is not yet fully observed
NOT_OBSERVED_*   = enough verified input exists and condition is absent
UNOBSERVABLE_*   = required independent input is missing/invalid
```

Never convert `UNOBSERVABLE` to `SAFE`.

---

## 13. Derivatives brain — Task-3 overlay

`orb/adaptive/derivatives.py` calculates a deterministic point-in-time overlay from canonical derivative snapshots.

It can calculate:

- India VIX regime;
- VIX % change;
- ATM IV;
- IV rank;
- IV crush;
- near/next expiry term structure;
- 25-delta skew;
- front-expiry PCR;
- front-expiry max pain and distance;
- futures OI buildup: long buildup, short buildup, short covering, long unwinding, ambiguous;
- raw and fair-value-adjusted futures basis;
- rollover %;
- strong positive-basis rollover;
- unsigned GEX;
- dealer-signed GEX only when dealer sign is actually supplied;
- aggregate vanna/charm;
- expiry-day state from verified calendar input;
- GIFT implied gap and gap/ATR;
- index gap %;
- FII index-futures short %.

High-signal capability thresholds include:

- VIX change `>= 8%` -> spike/block capability;
- IV rank `> 60` -> high IV rank;
- term inversion `> 5` vol points;
- PCR `> 1.3` or `< 0.7` -> extreme;
- max-pain distance `<= 0.5%` -> near max pain;
- rollover `> 85%` plus positive adjusted basis -> strong positive-basis rollover;
- adjusted futures basis `> +15 bps` or `< 0`;
- GIFT gap `> 1.5 x ATR` -> extreme;
- absolute index gap `> 2.5%` -> extreme;
- FII futures short share `> 80%` or `< 30%` -> extreme/light.

### Critical dealer-GEX rule

Open interest does **not** reveal dealer direction. If upstream data does not provide a dealer-position sign, dealer-signed GEX remains unobservable. Never infer dealer side from OI alone.

---

## 14. Risk-context brain — factual non-price warnings

`orb/adaptive/risk_context.py` converts verified outside facts into expiring capabilities, including:

- result day;
- RBI MPC;
- macro event;
- ex-dividend and adjustment verification;
- verified news shock;
- circuit / surveillance / F&O restrictions;
- illiquidity/slippage warning;
- feed lag / bad tick;
- order rejection / square-off risk;
- PIT/replay-live mismatch;
- OI-wall/gamma-squeeze/rollover-distortion facts;
- edge decay / overfit / small sample;
- index alignment;
- sector divergence;
- market-breadth support.

External facts should arrive through this kind of structured snapshot/capability contract rather than free-form text inside the decision engine.

---

## 15. Adaptive runtime — one reducer, not parallel brains with different clocks

`orb/adaptive/runtime.py` is the synchronized event reducer for research/human-paper sessions.

Important behavior:

- validates bars/references against the event watermark;
- converts raw derivative and risk snapshots into `Capability[]`;
- preserves independently refreshed capability families;
- quarantines identity/revision/out-of-order faults;
- evaluates each symbol through the same controller;
- requires synchronized universe watermarks for global selection;
- preserves controller hard blocks when projecting public tickets;
- cancels pending plans if authority, safety or proof is revoked;
- invalidates pending plans when the original thesis is no longer true;
- protects against execution-feed deadlines and data quarantine;
- permits `PAPER-CANDIDATE` only when paper authority and proof are present.

Future data providers should feed this reducer rather than building an alternate derivative-specific decision path.

---

## 16. Execution and risk reality

A chart setup is not enough. Trade Vision also asks whether the theoretical idea could realistically be executed.

`behavior/execution_event_oi_risk.py` examines:

- fill probability;
- estimated spread/slippage;
- market-impact proxy;
- depth availability;
- volume percentile;
- single-tick/wick risk;
- gap-through-entry risk;
- liquidity grade;
- event risk;
- earnings proximity;
- expiry pinning;
- expected-move limits;
- gamma-wall/max-pain context.

`behavior/risk_engine.py` then examines:

- entry-to-stop risk;
- reward/risk;
- simulated position size;
- maximum risk-per-trade;
- daily loss limit;
- consecutive-loss cooldown;
- chop cooldown;
- sector/index exposure;
- portfolio heat;
- correlation risk;
- liquidity/slippage requirements.

These layers may veto a structurally attractive setup.

---

## 17. Decision layers — why there are several “brains” named decision/arbiter

The repository evolved additively. Older decision surfaces were often preserved while newer arbitration layers were added.

This is why multiple modules may look like final authorities.

### 17.1 Behavior Decision Engine

`behavior/decision_engine.py`

Uses a universal-agreement model across signal, candle structure, context, session rhythm, similar history, market regime and risk quality, plus hard gates for data/liquidity/context/cooldown/OOD/drift/etc.

### 17.2 Final Confluence Arbiter

`behavior/final_confluence_arbiter.py`

Acts like a senior trader and uses an evidence hierarchy roughly in this order:

1. risk/safety;
2. data quality;
3. liquidity;
4. market regime;
5. structure/levels;
6. volume/auction;
7. relative strength;
8. indicators;
9. external AI.

Post-entry thesis state is also high authority.

The important principle is **weighted priority, not vote counting**.

### 17.3 Twin Arbiter

`behavior/twin_arbiter.py`

Compares the Behavior conclusion with Kronos. Hard directional conflict or unavailable/uncertain forecast reduces the result to `WAIT`/`NO_TRADE`; Kronos cannot override Behavior risk.

### 17.4 Jarvis Decision Arbiter

`behavior/jarvis_decision_arbiter.py`

Combines Trade Vision decision, validated Gemini display, Kronos/OpenAlgo status, MTF and paper-reality gates. A Trade Vision `NO_TRADE` cannot be upgraded by an external reviewer.

### 17.5 Jarvis Fusion / Master Panel

`behavior/jarvis_decision_fusion.py` and `behavior/jarvis_master_panel.py`

These are primarily **aggregation / presentation / extra safety** layers. Their code explicitly preserves older panels/code paths.

### Architectural warning

The project contains several overlapping “decision-like” layers because development preserved old surfaces. Future evolution should move toward:

```text
many specialist evidence producers
          -> one canonical conflict/decision authority
          -> one final decision object
          -> multiple read-only presentation panels
```

Do not create another independent final decision engine unless the authority model is explicitly redesigned.

---

## 18. Jarvis — the meeting room and human explanation layer

Jarvis should be treated as the place that **assembles and explains** evidence, not a place where external AI can bypass core risk.

The Jarvis stack currently brings together combinations of:

- chart context;
- latest candle structure;
- indicators;
- sequential signals;
- levels/zones;
- MTF alignment;
- similar-history evidence;
- Trade Vision decision;
- safety summary;
- Kronos status/prior;
- Gemini/Grok review;
- OpenAlgo report evidence;
- paper execution reality.

The final output layer can present:

- current scenario/pattern;
- final action;
- entry zone and condition;
- stop;
- target;
- invalidation;
- R:R;
- wait-for conditions;
- avoid/cancel conditions;
- indicator/candle evidence;
- similar historical cases;
- blockers and quality flags;
- trader-readable explanation;
- next best action.

Jarvis/external reviewers remain read-only and cannot execute or override `NO_TRADE`/risk.

---

## 19. Desired canonical final output

The user should not have to manually inspect dozens of engine responses. The target human-facing output is approximately:

```text
SYMBOL — TIME — TIMEFRAME

FINAL DECISION
WAIT / WATCH / AVOID / PAPER-CANDIDATE
Bias: LONG / SHORT / NEUTRAL

CURRENT MARKET STORY
What price did, where it is, and what changed.

BEST MATCHING SETUP
Strategy/ORB variant + state.

COMPETING SCENARIOS
Continuation / retest / failed break / fade / chop / exhaustion / unknown.

DERIVATIVES
VIX / IV / PCR / OI / max pain / GEX / basis / rollover / FII.

FAILURE CHECK
Which failures are observed, armed, absent, or unobservable.

MARKET CONTEXT
VWAP / levels / index / sector / HTF / session.

HISTORY / MEMORY
Comparable samples, continuation/fakeout mix, evidence quality.

EXECUTION + RISK
Liquidity, fill/slippage risk, R:R, portfolio/cooldown constraints.

ENTRY PLAN
Entry condition / zone
Stop
Target(s)
Invalidation
R:R

WAIT FOR
Exact evidence required before promotion.

AVOID / CANCEL IF
Exact observations that kill the thesis.

MAIN BLOCKER
The single most important reason not to promote now.

PROOF / DATA / AUTHORITY
PIT state
Data quality
Strategy proof
Paper authority
Human approval requirement
```

### Output rule

The final output should answer:

> **Given everything currently known, what is the best action now, why, what can prove us wrong, and what exact new evidence is required next?**

It should not reduce the system to a blind `BUY 72%` signal.

---

## 20. Current production/deployment boundary

The codebase contains rich calculation and reasoning contracts, but calculation completeness is not the same as data-source completeness.

For AFRE v4 specifically:

```text
Derivatives math/contracts      -> built on branch
Failure detector                -> built on branch
18 ORB assessments              -> built on branch
Reducer/capability wiring       -> built on branch

Verified real upstream adapters
      -> must still populate DerivativesSnapshot / RiskContextSnapshot
         from trustworthy sources for full real-market use.
```

If upstream facts are missing, the correct output is `UNOBSERVABLE` / unavailable, not fabricated neutrality.

---

## 21. Safety invariants that future patches must not break

Current architectural intent keeps Trade Vision research/paper-focused:

```text
research_only = True
trade_allowed = False
order_routing_enabled = False
live_trading_blocked = True
```

A `PAPER-CANDIDATE` in the adaptive path still requires the relevant proof/authority/safety state and human approval.

Future work must preserve at least these principles unless an explicitly reviewed project-level safety redesign says otherwise:

1. no future leakage;
2. no incomplete-bar decision authority;
3. no missing-data-as-neutral shortcut;
4. no external-AI safety override;
5. no forecast override of hard risk/data gates;
6. no ORB variant bypass of proof;
7. no stale/tampered proposal acceptance;
8. no live broker route hidden inside a research engine;
9. no dealer-GEX side inference from OI alone;
10. no silent change to registered trading thresholds such as strict `>1.5 x ATR` large gap;
11. material decision-code changes must force fresh proof/review where fingerprint governance requires it;
12. unknown scenarios remain representable as unknown/unsupported.

---

## 22. Recommended authority model for future evolution

The biggest architectural risk is not lack of intelligence; it is **too many overlapping final-decision surfaces**.

When upgrading the project, prefer this hierarchy:

```text
LEVEL 0  Raw source data
LEVEL 1  Data quality / PIT / freshness / identity
LEVEL 2  Deterministic calculations and features
LEVEL 3  Specialist evidence engines
LEVEL 4  Strategy + scenario + failure + derivatives interpretation
LEVEL 5  Execution / portfolio / safety gates
LEVEL 6  ONE canonical conflict/decision authority
LEVEL 7  Proof / paper-authority / human approval
LEVEL 8  Read-only Jarvis UI / explanation / external-review comparison
```

External AI belongs at the evidence/reviewer side of the hierarchy, not above safety.

---

## 23. Rules for adding a new “brain”

Before creating another engine, answer these questions:

1. What unique evidence does it produce that no existing engine owns?
2. Is it a calculator, evidence producer, strategy recognizer, risk gate, arbiter, or presentation layer?
3. What canonical snapshot does it consume?
4. What is its point-in-time availability rule?
5. How does missing input appear?
6. What can it block?
7. What can it never override?
8. Which existing arbiter consumes its output?
9. Is its evidence correlated/duplicative with another engine?
10. What deterministic tests prove the contract?
11. Does it require OOS/walk-forward proof before influencing a paper candidate?
12. Does adding it change a policy/code fingerprint and invalidate old proof?

If those questions are not answered, do not add another decision-like module.

---

## 24. Rules for patching existing wiring

When a future patch changes decision flow:

```text
1. Locate the owning engine in this document / FILE_DOCUMENT_INDEX.
2. Trace its input contract to the canonical source/reducer.
3. Trace its output to the next arbiter/gate.
4. Verify it does not create a parallel authority path.
5. Preserve PIT/freshness/identity semantics.
6. Preserve hard-veto semantics across outer runtime projections.
7. Add regression tests for both pass and block paths.
8. Re-run targeted subsystem tests.
9. Re-run broader regression/no-new-regression suite.
10. Update this document if ownership, authority, or wiring changed.
11. Update `docs/FILE_DOCUMENT_INDEX.md` if new files were added/moved.
12. Require fresh proof/review when material strategy/decision logic changed.
```

---

## 25. Fast code-trace recipes

### “Why did the system say WAIT?”

Start with:

1. final Jarvis/trading-decision output;
2. Jarvis arbiter/fusion gates;
3. final confluence/Behavior decision gates;
4. execution/risk blocks;
5. context/condition classifier;
6. AFRE decision reason codes/scenario status if ORB;
7. data/PIT/quarantine state.

### “Why did ORB not become PAPER-CANDIDATE?”

Trace:

```text
orb/adaptive/features.py
  -> variants.py / scenario_detection.py
  -> controller.py
  -> runtime.py
  -> active proposal selection
  -> proof hash / paper authority / safety / synchronized universe
```

### “Why is derivatives context missing?”

Trace:

```text
upstream verified source/provider
  -> DerivativesSnapshot
  -> EventBatch.derivatives
  -> derivatives.calculate()
  -> derivatives.capabilities()
  -> MarketSnapshot.capabilities
  -> scenario detector / controller
```

### “Why does external AI disagree?”

Treat AI output as review evidence. Check Trade Vision data/decision first. The AI reviewer cannot upgrade a hard block.

---

## 26. High-signal source map

### Application/API spine

- `apps/api/app/main.py`
- `apps/api/app/models.py`
- `apps/api/app/state.py`
- `apps/api/app/storage.py`
- `apps/api/app/order_guard.py`

### Behavior / intelligence

- `apps/api/app/behavior/candle_anatomy.py`
- `apps/api/app/behavior/condition_classifier.py`
- `apps/api/app/behavior/context_engines.py`
- `apps/api/app/behavior/session_memory.py`
- `apps/api/app/behavior/hypothesis_engine.py`
- `apps/api/app/behavior/decision_engine.py`
- `apps/api/app/behavior/risk_engine.py`
- `apps/api/app/behavior/execution_event_oi_risk.py`
- `apps/api/app/behavior/final_confluence_arbiter.py`
- `apps/api/app/behavior/twin_arbiter.py`

### Jarvis / final presentation

- `apps/api/app/behavior/jarvis_decision_room.py`
- `apps/api/app/behavior/jarvis_decision_arbiter.py`
- `apps/api/app/behavior/jarvis_decision_fusion.py`
- `apps/api/app/behavior/jarvis_master_panel.py`
- `apps/api/app/behavior/jarvis_decision_quality_gate.py`
- `apps/api/app/behavior/jarvis_trading_decision_output.py`

### ORB research/proof

- `apps/api/app/orb/core.py`
- `apps/api/app/orb/discovery.py`
- `apps/api/app/orb/proof.py`
- `apps/api/app/orb/timing_research.py`

### Adaptive ORB / AFRE

- `apps/api/app/orb/adaptive/contracts.py`
- `apps/api/app/orb/adaptive/features.py`
- `apps/api/app/orb/adaptive/controller.py`
- `apps/api/app/orb/adaptive/runtime.py`
- `apps/api/app/orb/adaptive/registry.py`
- `apps/api/app/orb/adaptive/scenario_detection.py`
- `apps/api/app/orb/adaptive/variants.py`
- `apps/api/app/orb/adaptive/derivatives.py`
- `apps/api/app/orb/adaptive/risk_context.py`
- `apps/api/app/orb/adaptive/execution.py`
- `apps/api/app/orb/adaptive/governance.py`
- `apps/api/app/orb/adaptive/service.py`

---

## 27. Documents to use together with this reference

This file is the **plain-English application brain/wiring map**. It complements rather than replaces:

- `docs/FILE_DOCUMENT_INDEX.md` — master file/document router;
- `docs/TV_COMPLETE_FLOW_MAP.html` — visual flow and code-truth map;
- `docs/PROJECT_BRAIN.html` — quick block-by-block onboarding;
- `ARCHITECTURE.md` — formal architecture/operator map;
- `docs/BUILD_AUDIT.md` — plan-vs-code audit;
- `docs/ENGINE_BLOCK_ACTION_INVENTORY.md` — engine/block/action inventory;
- `docs/IMPLEMENTATION_STATUS.md` — latest shipped/build status;
- `docs/NEXT_BUILD_TARGET.md` — next planned work;
- `docs/SAFETY_INVARIANTS.md` — rules future code must not violate;
- `docs/ORB_SIMPLE_FLOW.md` — ORB-specific plain-English flow.

Use this document when the question is specifically:

> “What brains exist, what does each one do, how are they supposed to be wired, which one has authority, and how should we evolve the system without creating conflicting decision paths?”

---

## 28. Maintenance rule

Update this file whenever any of the following changes:

- a major calculation/reasoning/decision engine is added or removed;
- authority moves from one arbiter to another;
- final output semantics change;
- ORB/AFRE scenario or variant ownership changes;
- derivatives/risk context wiring changes;
- a new data provider becomes canonical;
- paper/proof authority changes;
- a safety invariant changes;
- a formerly presentation-only module gains decision authority;
- duplicated decision paths are consolidated.

For ordinary bug fixes that do not change ownership, authority, contracts or wiring, this file does not need version-by-version noise.

---

## 29. Final design statement

The project should evolve toward **one disciplined trading brain assembled from many specialists**, not toward many independent brains shouting separate BUY/SELL answers.

The intended pattern is:

```text
observe facts
  -> test data quality
  -> calculate structure/context
  -> compare memory/hypotheses
  -> recognize strategy scenarios
  -> search for failure
  -> test derivatives/events
  -> test execution/risk
  -> resolve conflicts by authority
  -> require proof and safety
  -> explain one bounded action to the human
```

The canonical final question remains:

> **Given everything currently known, what is the best action now — WAIT, WATCH, AVOID/NO_TRADE, or PAPER-CANDIDATE — why, what can prove the idea wrong, and what exact evidence must happen next?**

---

# PART II — EVOLUTION ROADMAP: TURN THE EXISTING ENGINES INTO ONE CORRECTLY WIRED TRADING BRAIN

> **Roadmap purpose:** The next phase is not to add more independent intelligence. It is to turn the engines already built into **one correctly wired trading brain**.
>
> The repository product requirement already defines the destination: **one organized analysis pipeline, one boss arbiter, one decision language, and one `PaperTradeGuidance`/final-decision result**.
>
> **Time-sensitive checkpoint rule:** Section 30 records facts verified on **2026-09-08**. Re-check GitHub PR/CI state before executing those steps in a later session. Sections 31–38 are the durable architectural sequence unless a reviewed design decision changes them.

---

## 30. Immediate checkpoint — stabilize AFRE v4 PR #1 first

### Verified checkpoint: 2026-09-08

At this checkpoint:

- AFRE targeted tests are green;
- PR #1 is still Draft;
- PR #1 is mergeable;
- the latest CI run is red because `api-no-new-regressions` is still running the five known baseline failures that its command is intended to deselect;
- that failure set includes:
  - pre-existing 9C real-runtime normalization/telemetry failures;
  - pre-existing PTA marker/runtime behavior failures;
  - missing HSTRY CSV fixture in Linux CI;
  - PowerShell parser test running on Ubuntu without `powershell`;
- therefore the first repair target is the **CI baseline/exclusion mechanism**, not trading behavior.

### Do not “fix” trading code to make baseline infrastructure failures disappear

The immediate task is:

```text
AFRE v4 PR
    |
    v
repair no-new-regression CI
    |
    v
prove branch adds zero new failures
    |
    v
review AFRE safety / proof-fingerprint behavior
    |
    v
keep paper promotion fail-closed
    |
    v
merge AFRE v4
```

### PR-scope rule

Do **not** put the next major orchestration refactor into PR #1.

PR #1 already contains a large cohesive change set:

- 18 ORB variants;
- derivatives calculations;
- failure-scenario detection;
- risk-context wiring;
- adaptive runtime changes;
- regression tests;
- documentation.

Finish, verify, review and merge that unit first. Start brain orchestration on a separate branch/PR.

### Acceptance before moving on

Do not start the major orchestration migration until all of the following are true:

```text
[ ] AFRE targeted suite passes
[ ] no-new-regression job correctly distinguishes branch failures from baseline failures
[ ] branch introduces zero unexplained regressions
[ ] strict gap / dealer-GEX / UNOBSERVABLE semantics remain intact
[ ] code/proof fingerprint behavior is reviewed after material source changes
[ ] PAPER-CANDIDATE remains proof + authority + safety + human gated
[ ] no live broker route was introduced
[ ] PR #1 is merged or explicitly abandoned/replaced
[ ] NEXT_BUILD_TARGET / IMPLEMENTATION_STATUS are refreshed after the merge decision
```

---

## 31. Next major milestone — Canonical Decision Spine / Brain Orchestration

### Why this is the next major build

The project already has strong specialist intelligence. The architectural problem is that several components can appear to produce a decision:

```text
Behavior Decision
Final Confluence Arbiter
Twin Arbiter
Jarvis Arbiter
Jarvis Fusion
Jarvis Master Panel
ORB / AFRE decision
Kronos opinion
Gemini / Grok review
```

That makes authority harder to reason about, test and evolve.

The next milestone should therefore be named:

> **Canonical Decision Spine / Brain Orchestration**

### Target architecture

```text
                    ALL VERIFIED DATA
                           |
                           v
                 CANONICAL MARKET SNAPSHOT
                           |
                           v
                 CALCULATORS / FEATURES
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
 Price / Structure       Context            Memory
        |                  |                  |
        +------------------+------------------+
                           |
                           v
                       HYPOTHESES
                           |
                           v
                  STRATEGY / ORB / AFRE
                           |
                           v
                  DERIVATIVES / EVENTS
                           |
                           v
                     FAILURE ENGINE
                           |
                           v
                EXECUTION + RISK REALITY
                           |
                           v
                    FINAL CONFLUENCE
                   ONE FINAL AUTHORITY
                           |
                           v
                    PROOF / SAFETY GATE
                           |
                           v
                     FINAL DECISION
                           |
                           v
                         JARVIS
                           |
                           v
                  HUMAN-READABLE VIEW
```

### Architectural invariant

There may be many evidence producers and many specialist vetoes, but there must be **one canonical owner of the final band/action**.

---

## 32. Milestone task 1 — create an authoritative Engine Authority Registry

Before rewiring code, classify every meaningful engine by role and authority.

Minimum registry columns:

```text
engine_id
module
classification
input_contract
output_contract
may_propose
may_veto
may_downgrade
may_set_final_band
may_execute
authority_rank
canonical_consumer
legacy_or_current
notes
```

### Initial authority model

| Engine | Classification | May propose? | May veto? | May set final band? |
|---|---|---:|---:|---:|
| Candle Anatomy | Calculator | No | No | No |
| Condition Classifier | Evidence | No | Limited | No |
| Context Engines | Evidence / context | No | Limited | No |
| Session Memory | Memory evidence | No | No | No |
| Pattern / Analog Memory | Memory evidence | No | No | No |
| Hypothesis Engine | Scenario evidence | No | No | No |
| ORB / AFRE | Strategy / scenario | Yes | Yes | No |
| Derivatives | Evidence / risk | No | Yes | No |
| RiskContext | Factual risk evidence | No | Yes | No |
| Failure Detector | Risk / veto | No | Yes | No |
| Execution/Event/OI Risk | Execution-risk gate | No | Yes | No |
| Risk Engine | Risk gate | No | Yes | No |
| Behavior Decision | Specialist decision evidence during migration | Yes | Yes | No after consolidation |
| Kronos | Reviewer / prior | No | No | No |
| Gemini / Grok | Reviewer | No | No | No |
| Twin Arbiter | Conflict evidence | No | Downgrade only | No |
| Jarvis Arbiter | Migration compatibility / safety wrapper | No | No upgrade; downgrade only | No after consolidation |
| Jarvis Fusion | Aggregation / presentation evidence | No | No upgrade | No |
| Jarvis Master Panel | Presentation | No | No | No |
| **Final Confluence Arbiter** | **Canonical final authority** | **Yes** | **Yes** | **YES** |
| Jarvis Trading Decision Output | Presenter | No | No | No |

### Why do this first

This registry exposes:

- duplicated authority;
- ambiguous ownership;
- hidden final-band writers;
- legacy paths that should become read-only;
- engines that recalculate data instead of consuming canonical evidence;
- safety gates that must remain above strategy confidence.

Do not delete old paths yet. First classify and wrap them, then migrate with regression proof.

---

## 33. Milestone task 2 — create one canonical evidence contract: `DecisionContext`

All specialist engines should contribute to, or consume from, one point-in-time evidence object rather than independently constructing separate worldviews.

Conceptual contract:

```text
DecisionContext

identity
  symbol
  timeframe
  decision_time
  snapshot_hash
  universe_watermark

input_integrity
  data_quality
  PIT_status
  freshness
  quarantine_status

price_structure
candle_anatomy
levels
market_regime
session_context
index_context
sector_context
relative_strength

indicators
memory
historical_analogs

hypotheses

strategy_candidates
orb_variants
afre_scenarios

derivatives
events
failure_scenarios

execution_quality
portfolio_risk

blockers
warnings

proof_status
paper_authority

provenance
  engines_run[]
  evidence_versions[]
  capability_sources[]
```

### Contract rules

1. Same symbol/timeframe/decision timestamp/snapshot hash across the decision.
2. Closed-bar/PIT-safe evidence only.
3. Missing evidence has an explicit state; it is never converted to zero/neutral automatically.
4. Each evidence field has provenance and freshness.
5. Engines do not secretly fetch/recalculate an independent conflicting snapshot during arbitration.
6. Expensive/reusable calculations happen upstream and are shared.
7. Final arbiter consumes the context; it should not be a hidden data-provider layer.
8. A material contract/code change participates in proof/fingerprint governance where applicable.

---

## 34. Milestone task 3 — create one canonical final decision contract

The existing `PaperTradeGuidance` requirement is close to the desired product output. Consolidate it into one canonical final decision contract instead of exposing multiple competing final answers.

Conceptual contract:

```text
FinalDecision

identity
  symbol
  time
  timeframe
  decision_context_hash

action
  WAIT
  WATCH
  AVOID
  PAPER-CANDIDATE

bias
  LONG
  SHORT
  NEUTRAL

market_story

primary_setup
primary_setup_state

alternative_scenarios[]

derivatives_summary

failure_check[]
  OBSERVED
  ARMED
  NOT_OBSERVED
  UNOBSERVABLE

historical_evidence

entry_plan
  side
  entry_zone
  trigger
  stop
  targets
  invalidation
  RR
  size_hint

wait_for[]
avoid_if[]

main_blocker

evidence_confidence

data_quality
PIT_status
proof_status
paper_authority

reason_for[]
reason_against[]
warnings[]
hard_blockers[]

engines_run[]

next_action
  DO_NOTHING
  OFFER_PAPER_TICKET

live_trading_blocked = true
order_routing_enabled = false
```

### Final-decision rule

The user receives **one action** and one plan. Every specialist result remains inspectable as evidence underneath it, but is not shown as an equal competing final answer.

---

## 35. Milestone task 4 — make Final Confluence the sole final-band authority

The migration target is:

```text
specialist evidence
      |
      v
strategy / scenario proposals
      |
      v
risk / execution / failure vetoes
      |
      v
FINAL CONFLUENCE ARBITER
      |
      v
one FinalDecision
```

### Intended roles after consolidation

- **Behavior Decision:** specialist behavior opinion/evidence; not a second product final.
- **ORB/AFRE:** strategy/scenario proposal + veto evidence; never final paper authority.
- **Twin Arbiter:** conflict/downgrade evidence only.
- **Kronos:** research prior/reviewer only.
- **Gemini/Grok:** review/explanation only.
- **Jarvis Arbiter/Fusion:** migration compatibility and read-only aggregation; cannot upgrade final authority.
- **Jarvis Master Panel:** display only.
- **Final Confluence Arbiter:** sole final-band/action owner.
- **Proof/Safety/Human:** still gate promotion after strategy evidence; nothing can bypass them.

### Migration safety rule

Do not delete legacy outputs in the first refactor. Run old and new projections side-by-side in replay, compare them, prove deterministic compatibility/safe downgrades, then retire duplicate authority gradually.

---

## 36. Milestone task 5 — connect real derivatives and risk data to the same spine

AFRE Task-3 math is built, but the real-market system still needs verified upstream sources to populate:

```text
DerivativesSnapshot
RiskContextSnapshot
```

### Correct provider architecture

```text
OpenAlgo / verified NSE sources
            |
            v
OpenAlgoDataProvider / official adapters
            |
            +-----------------------------+
            |                             |
            v                             v
Canonical option-chain snapshot    Canonical futures snapshot
            |                             |
            +-------------+---------------+
                          |
              +-----------+-----------+
              |           |           |
              v           v           v
         VIX snapshot  FII/participant  Event/restriction
                          snapshot          snapshot
              |           |           |
              +-----------+-----------+
                          |
                          v
                 DerivativesSnapshot
                 RiskContextSnapshot
                          |
                          v
                 existing calculators
                          |
                          v
                      Capability[]
                          |
                          v
                 same DecisionContext
```

### Explicit anti-pattern

Do **not** build:

```text
OpenAlgo
   |
   v
separate derivatives decision engine
   |
   v
another BUY / SELL answer
```

Derivatives and external risk are **evidence and veto context inside the same brain**.

### Provider requirements

Every real provider should expose:

- source identity;
- exchange/instrument identity;
- observation timestamp;
- received timestamp;
- expiry/session identity;
- freshness/TTL;
- completeness flags;
- normalization version;
- raw-source reference/hash where practical;
- fail-closed behavior on missing/invalid data.

---

## 37. After wiring — run the trader-specific gap-morning proof

The important unfinished experiment remains the user's real trading problem:

> Gap days + first 30–60 minutes + CPR/context vote.

Do this **after the evidence wiring and authority model are stable**, so the experiment tests the intended final brain rather than a temporary parallel path.

### Factor grid

Test interaction among:

```text
Gap size
x
CPR width / location
x
OR width
x
ORB variant
x
VWAP
x
Nifty alignment
x
sector alignment
x
volume
x
VIX
x
PCR / OI
x
expiry state
x
failure scenarios
```

Use causal values available at each decision timestamp.

### Measure more than profit

Minimum metrics:

```text
Win rate
Expectancy
Profit factor
Max drawdown
False-break rate
Stop-out rate
MFE
MAE
Time-to-target
Failure type
Regime dependency
Sample count
OOS consistency
Walk-forward consistency
```

Also report:

- transaction-cost sensitivity;
- slippage sensitivity;
- result/event-day split;
- expiry/non-expiry split;
- gap bucket split;
- OR-width bucket split;
- time-window split;
- stock-specific vs pooled performance;
- low-sample/unobservable cells.

### Promotion rule

Do not promote the best in-sample combination just because it has the highest R/PF. Selection must remain train-only, followed by unseen holdout and repeated walk-forward proof.

---

## 38. Then real paper observation and outcome feedback

Only after historical proof:

```text
historical replay
      |
      v
unseen holdout
      |
      v
walk-forward
      |
      v
approved playbook
      |
      v
real-market observation
      |
      v
WAIT / WATCH / PAPER-CANDIDATE
      |
      v
human approve
      |
      v
paper result
      |
      v
outcome memory
      |
      v
edge-decay monitoring
```

No automatic live trading is added by this roadmap.

### Paper-observation goals

The live-market paper phase should verify:

- real feed freshness and PIT behavior;
- expected vs actual entry/slippage;
- real false-break frequency;
- whether historical filters still fire with the same causal timing;
- whether external facts arrive before the decision deadline;
- discrepancy between replay and observed paper behavior;
- drift/edge decay;
- whether any engine creates unexplained decision instability.

---

## 39. Exact next sequence — project execution order

```text
NOW
|
+-- 1. Repair PR #1 CI gate
+-- 2. Verify AFRE v4 adds zero new regressions
+-- 3. Review + merge AFRE v4
+-- 4. Update stale NEXT_BUILD_TARGET / IMPLEMENTATION_STATUS after merge decision
|
v
NEW BRANCH / PR
Canonical Decision Spine / Brain Orchestration
|
+-- 5. Inventory every engine and authority
+-- 6. Define canonical DecisionContext
+-- 7. Define single FinalDecision / PaperTradeGuidance
+-- 8. Make Final Confluence the sole final-band authority
+-- 9. Convert Jarvis / Twin / AI layers into evidence/review/presentation roles
+--10. Wire AFRE + derivatives + failure evidence into that spine
+--11. Build verified real DerivativesSnapshot / RiskContext providers
+--12. Add conflict / veto / PIT / determinism integration tests
|
v
PROOF
+--13. Gap-morning focused historical experiment
+--14. OOS + walk-forward
+--15. Real paper observation
+--16. Outcome feedback / edge-decay monitoring
```

### Branching rule

The orchestration work belongs on a **new branch after AFRE v4 is stabilized/merged**. This keeps failure attribution clear and prevents PR #1 from becoming an unreviewable mixture of derivatives/failure work plus system-wide authority migration.

---

## 40. Acceptance criteria for the Canonical Decision Spine milestone

The milestone is not complete merely because a new class named `DecisionContext` exists.

It is complete only when:

```text
[ ] every major engine has a documented authority classification
[ ] one canonical PIT snapshot/context feeds the decision
[ ] one canonical object owns the final action/band
[ ] only Final Confluence can set that product final band
[ ] ORB/AFRE can propose/veto but cannot bypass proof/safety
[ ] Kronos/Gemini/Grok cannot upgrade a hard block
[ ] Jarvis presents the final decision instead of generating a competing one
[ ] hard vetoes survive every projection/API/UI layer
[ ] missing derivatives/event facts remain UNOBSERVABLE, not safe
[ ] real provider evidence carries timestamp/freshness/provenance
[ ] replay is deterministic for identical DecisionContext hashes
[ ] legacy parallel outputs are either wrapped read-only or explicitly deprecated
[ ] integration tests cover contradictory evidence and authority conflicts
[ ] live_trading_blocked=true remains true
[ ] order_routing_enabled=false remains true
[ ] historical proof is rerun when material strategy/decision fingerprints change
```

---

## 41. Roadmap maintenance rule

When resuming this work in a future session:

1. Re-check PR #1 / current main / latest CI; do not assume the 2026-09-08 checkpoint is still current.
2. Read `docs/IMPLEMENTATION_STATUS.md` latest tip and `docs/NEXT_BUILD_TARGET.md`.
3. Read this Part II before adding another decision-like engine.
4. If AFRE v4 is already merged, mark Section 30 historical and continue from the first incomplete numbered milestone.
5. If authority or contracts changed, refresh the Engine Authority Registry and `DecisionContext`/`FinalDecision` definitions here.
6. Keep `docs/FILE_DOCUMENT_INDEX.md` aligned with this roadmap.

The durable priority remains:

> **Consolidate and correctly wire existing intelligence before adding another independent final-decision brain.**
