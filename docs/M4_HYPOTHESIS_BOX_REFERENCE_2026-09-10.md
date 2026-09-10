# Trade Vision / TrendForge — Hypothesis Box Running Reference

Date: 2026-09-10
Status: RUNNING REFERENCE / DISCUSSION LOG — NOT A LOCKED IMPLEMENTATION SPEC
Branch: `m4-d6-orchestration-redesign`
Parent reference: `docs/M4_TRADING_COGNITIVE_ARCHITECTURE_REFERENCE_2026-09-10.md`

## Purpose

This file is the dedicated place for all future discussion, corrections, ideas, weaknesses, and improvement plans for the Hypothesis Box / Hypothesis Engine v2.

Whenever the Hypothesis Box is discussed again, update this file instead of scattering important design ideas across chats.

The Hypothesis Box is a reasoning helper. It proposes possible market stories. It does not execute trades and does not own the final WAIT / WATCH / PAPER-CANDIDATE decision. D6 remains the sole final-band authority.

---

# 1. Simple meaning

Think of the Hypothesis Box as a market detective.

It looks at clues and says:

> These are the possible explanations for what price may be doing next.

It should not say only:

- bullish;
- bearish;
- buy;
- sell.

It should create several possible stories and explain why each story may be right or wrong.

Example stories:

- long continuation;
- long reversal;
- short continuation;
- short reversal;
- breakout follow-through;
- breakout failure;
- range / mean reversion;
- squeeze expansion;
- gap-and-go;
- gap exhaustion / fade;
- liquidity-sweep reversal;
- trend pullback;
- event-distorted market;
- chop / no-edge.

---

# 2. Can the Hypothesis Box find support and resistance?

## Short answer

It can USE and INTERPRET support and resistance, but it should not be the main raw support/resistance calculator.

The cleaner architecture is:

```text
M3.1 / PRICE STRUCTURE / MARKET FACT KERNEL
        -> finds and proves price levels
        -> support
        -> resistance
        -> pivots
        -> CPR
        -> VWAP
        -> PDH / PDL
        -> swing highs / lows
        -> volume-profile levels when available
        -> order-block / liquidity zones when available

HYPOTHESIS BOX
        -> asks what those levels mean for the current story
```

Why?

If every thinking engine calculates its own support and resistance separately, two helpers may create different levels from the same price data. That makes the system harder to audit.

Better rule:

> Calculate the market fact once. Let many reasoning engines use the same proven fact.

## What the Hypothesis Box CAN do with S&R

It can ask:

- Is price approaching support or resistance?
- Has the level already been tested many times?
- Did price reject the level or accept above/below it?
- Is volume increasing at the level?
- Is VWAP supporting the same area?
- Is CPR or a pivot close to the same level?
- Is an order block or liquidity zone near it?
- Is the higher timeframe level stronger than the small timeframe level?
- Did previous similar setups fail at this level?
- Does derivatives positioning make the level more dangerous?
- What happens if the level breaks?
- What happens if the level rejects price?

So the Hypothesis Box does not merely see `Resistance = 1000`.

It can reason:

```text
Resistance = 1000
Price = 998
VWAP = 990
5m trend = bullish
1h structure = bearish
Volume = rising
Call OI wall = near 1000
Previous breakout failures = common near this state

Possible story A:
real breakout

Possible story B:
failed breakout / rejection
```

---

# 3. How can it "predict" anything?

The Hypothesis Box should not pretend that it knows the future.

It predicts in a safer way:

> It creates possible future paths from current evidence, then checks which paths are supported, contradicted, missing evidence, or already invalid.

Think of weather forecasting.

Dark clouds do not guarantee rain. They make one future story more reasonable.

The market is similar.

Example:

```text
Current facts:
- price above VWAP
- EMA9 > EMA20 > EMA50
- strong volume
- ORH broken
- index bullish

Possible future path:
- price holds above ORH
- small pullback
- higher low
- continuation upward
```

But the box must also create the opposite story:

```text
Possible failure path:
- breakout above ORH
- no follow-through
- volume drops
- price returns below ORH
- VWAP lost
- selloff begins
```

That is prediction by competing explanations, not fortune telling.

---

# 4. What information goes inside?

The Hypothesis Box should consume already-proven canonical evidence where available.

Possible inputs include:

### Price / structure
- current price;
- closed candles;
- swing highs/lows;
- BOS / CHOCH;
- support/resistance;
- CPR;
- pivots;
- PDH / PDL;
- VWAP and bands;
- order blocks;
- FVG / liquidity zones;
- POC / VAH / VAL when available.

### Trend / momentum
- EMA 9 / 20 / 50 / 200;
- slopes and stack order;
- MACD;
- RSI;
- ADX;
- Supertrend;
- Ichimoku;
- other M3.1 indicator evidence.

### Participation
- volume;
- RVOL;
- OBV / CMF / MFI where useful;
- breakout participation.

### Context
- index direction;
- sector direction;
- relative strength;
- market regime;
- market phase;
- event context.

### Derivatives
- VIX;
- IV;
- PCR;
- OI buildup;
- max pain;
- GEX / gamma where valid;
- vanna / charm where valid;
- basis / rollover;
- expiry context.

### Memory
- real 9-candle M3.3 memory;
- historical analogs;
- pattern diary;
- previous failure trajectories.

### Outside reviewers
- real validated Kronos sequence evidence;
- ORB / AFRE specialist proposals;
- Twin disagreement notes.

Mock/fake evidence must remain outside canonical decision influence.

---

# 5. Inside the Hypothesis Box — simple step-by-step flow

## Step 1 — Understand the current situation

Ask:

- Where is price?
- What is the trend?
- What market phase are we in?
- Is price near an important level?
- Is the market trending, ranging, squeezing, breaking out, or failing?

Example:

```text
Price is just below resistance.
Fast trend is bullish.
Higher timeframe is still bearish.
Volume is increasing.
```

## Step 2 — Select relevant evidence

Do not treat all 94 indicator outputs as equally important every time.

If price is testing resistance, useful evidence may be:

- resistance quality;
- VWAP;
- volume;
- EMA horizon state;
- RSI divergence;
- BOS / CHOCH;
- index/sector;
- OI wall;
- memory of similar resistance tests.

An unrelated indicator should not become important just because it exists.

## Step 3 — Create possible stories

For a resistance test, possible stories can be:

```text
A. breakout continuation
B. failed breakout
C. rejection and reversal
D. sideways compression below resistance
```

## Step 4 — Find evidence FOR every story

Example for breakout continuation:

- strong volume;
- price above VWAP;
- EMA stack bullish;
- index aligned;
- resistance already tested several times.

## Step 5 — Find evidence AGAINST every story

Example against breakout continuation:

- strong higher-timeframe resistance;
- bearish RSI divergence;
- call OI wall;
- price already extended 1.8 ATR;
- sector is weakening.

This step is important. The box must try to prove itself wrong.

## Step 6 — Write the expected next sequence

A good hypothesis should say what should happen next if it is correct.

Example:

```text
BREAKOUT_CONTINUATION expected sequence:
1. close above resistance
2. volume remains healthy
3. pullback stays above old resistance
4. old resistance becomes support
5. higher low forms
6. continuation
```

## Step 7 — Write the failure sequence

Example:

```text
BREAKOUT_FAILURE expected failure sequence:
1. price moves above resistance
2. no acceptance
3. volume weakens
4. candle closes back below resistance
5. VWAP lost
6. downside acceleration
```

## Step 8 — Mark invalidation

Every story needs a clear reason to stop believing it.

Example:

```text
Long breakout hypothesis invalid if:
- closed candle returns below breakout level
- VWAP is lost
- downside structure breaks
```

The exact invalidation must come from real market levels/evidence. Do not manufacture fake levels because data is missing.

---

# 6. Main thesis and anti-thesis

Every important idea should have a strong opposite idea.

Example:

```text
THESIS:
The breakout above 1000 is real.

ANTI-THESIS:
The move above 1000 is a liquidity grab and will fail.
```

The box then builds both cases.

### Thesis evidence

- volume expansion;
- VWAP support;
- EMA horizon stack bullish;
- index bullish;
- repeated resistance testing.

### Anti-thesis evidence

- daily resistance;
- call OI wall;
- price overextended;
- bearish divergence;
- weak sector;
- similar historical failures.

The system should not simply count which side has more indicators.

It should ask:

- Which facts are more important for this situation?
- Which facts are independent?
- Which facts are duplicated information?
- Which facts are fresh?
- Which facts are missing?
- Which facts can invalidate the whole idea?

---

# 7. Easy example — ₹1,000 resistance

Imagine a stock has a big resistance wall at ₹1,000.

Current price sequence:

```text
₹985
₹990
₹995
₹1,002
```

The Hypothesis Box can create:

## Story A — Real breakout

Why it may be true:

- ₹1,000 was broken;
- volume is strong;
- price is above VWAP;
- EMA9 > EMA20 > EMA50;
- Nifty and sector are rising.

Expected next:

```text
₹1,002
-> holds above ₹1,000
-> small pullback
-> ₹1,000 behaves like support
-> higher low
-> continuation
```

## Story B — Fake breakout

Why it may be true:

- ₹1,000 is major daily resistance;
- call OI is heavy near ₹1,000;
- stock is already highly extended;
- previous similar breakouts often failed;
- sector momentum is slowing.

Expected failure:

```text
₹1,002
-> buyers cannot continue
-> price closes ₹997
-> ₹1,000 becomes resistance again
-> VWAP lost
-> decline
```

The Hypothesis Box sends BOTH stories forward.

It does not say:

> I saw ₹1,002, therefore buy.

---

# 8. How S&R helps prediction

Support and resistance give the Hypothesis Box a location.

Indicators often answer:

> What is price doing?

S&R answers:

> Where is price doing it?

That difference is important.

Example:

`RSI = 75`

By itself, this is weak information.

Case A:

```text
RSI 75
price just broke ORH
volume expanding
above VWAP
no major resistance nearby
```

Possible meaning:

> strong momentum.

Case B:

```text
RSI 75
price at weekly resistance
1.8 ATR extended
bearish divergence
large call OI wall
```

Possible meaning:

> exhaustion / breakout-failure risk.

Same RSI number. Different location. Different hypothesis.

---

# 9. How memory helps prediction

The Hypothesis Box can ask M3.3:

> Have we seen a similar setup before?

But memory should not just answer:

> 7 of 10 went up.

Better memory questions are:

1. What similar setups existed?
2. In what market regimes?
3. What happened next?
4. When they failed, how did they fail?
5. Does the current setup contain the same failure warning signs?

Example:

```text
Current breakout looks bullish.

Memory says failed versions often had:
- >1.5 ATR extension
- nearby call OI wall
- sector divergence

Current setup has all three.
```

The Hypothesis Box should then make the anti-thesis much more important.

---

# 10. How Kronos helps

Real validated Kronos can give a sequence-model opinion such as:

> Similar K-line sequences often produce pullback first, then continuation.

The Hypothesis Box may use that as one reviewer clue.

It must NOT say:

> Kronos predicts up, therefore long.

Kronos is supporting/contradicting sequence evidence only.

Mock Kronos must have zero canonical decision influence.

---

# 11. How ORB and AFRE help

ORB and AFRE can send suggestion letters such as:

```text
ORB proposal:
Long breakout candidate above ORH.
Required conditions satisfied.
Invalidation = ORH failure.
```

The Hypothesis Box can turn this into a broader market story and challenge it.

Example:

```text
ORB says breakout setup exists.
Hypothesis Box says:

YES, setup exists,
BUT:
- higher timeframe resistance nearby
- OI wall hostile
- gap already exhausted
- memory shows failure pattern

Alternative story:
ORB trap / failed breakout.
```

This is why:

`valid strategy setup != automatically valid paper candidate`

---

# 12. What the Hypothesis Box should output

A future structured output could look like:

```text
HYPOTHESIS_ID:
LONG_BREAKOUT_CONTINUATION

THESIS:
Price may continue upward after accepting above ORH.

MARKET_PHASE:
BREAKOUT_ATTEMPT

TIMEFRAME:
5m

SUPPORT:
- ORH close accepted
- volume expanding
- VWAP support
- EMA horizon stack bullish
- index aligned

OPPOSITION:
- daily resistance nearby
- call OI wall

UNKNOWN:
- fresh participant OI unavailable

EXPECTED_SEQUENCE:
- hold above ORH
- retest
- higher low
- continuation

FAILURE_SEQUENCE:
- no follow-through
- close below ORH
- VWAP loss
- acceleration lower

INVALIDATORS:
- confirmed ORH failure
- bearish structure break

ALTERNATIVE_HYPOTHESIS:
BREAKOUT_FAILURE

STATE:
PLAUSIBLE / FRAGILE / INVALID / etc.
```

Do not use fake probability such as `73% chance` unless a real statistically valid calibration system exists.

---

# 13. What it must never do

The Hypothesis Box must never:

- execute a trade;
- route an order;
- own final decision authority;
- invent missing support/resistance;
- convert missing data to neutral;
- use unfinished candles as finished evidence;
- use future labels as if known now;
- call a hand-made score a real probability;
- count correlated indicators as independent proofs;
- allow mock Kronos or fake memory to influence canonical decisions;
- ignore a strong anti-thesis because the preferred thesis has more indicators.

---

# 14. Current known weakness of the legacy Hypothesis Box

The existing hypothesis engine is too simple for the intended M4 reasoning role.

Known design weaknesses to re-audit before implementation:

- mainly continuation / reversal / fakeout hypotheses;
- hand-written scoring;
- normalized values named like probabilities even though they are not properly calibrated probabilities;
- fallback confirmation/invalidation prices can be manufactured when real levels are unavailable;
- some market facts are recomputed inside the engine instead of consuming one immutable canonical evidence bundle.

Hypothesis Engine v2 should replace these weaknesses rather than hide them.

---

# 15. Desired Hypothesis Box v2 idea

Simple architecture:

```text
CANONICAL MARKET EVIDENCE
        |
        v
UNDERSTAND MARKET STATE
        |
        v
FIND RELEVANT EVIDENCE
        |
        v
CREATE MULTIPLE HYPOTHESES
        |
        +--> THESIS
        +--> ANTI-THESIS
        +--> NO-EDGE POSSIBILITY
        |
        v
FOR EACH HYPOTHESIS
- support
- opposition
- missing facts
- expected path
- failure path
- invalidation
- expiry
- regime assumptions
- dependency / independence
        |
        v
SEND STRUCTURED HYPOTHESES TO M4
        |
        v
D6 FINAL ARBITRATION
```

---

# 16. Important design decision about S&R

Recommended architecture decision:

> Hypothesis Box should be an S&R reasoning consumer, not the primary S&R discovery engine.

S&R discovery belongs upstream in canonical price/structure intelligence so every specialist sees the same audited levels.

The Hypothesis Box can still:

- rank which proven level matters for a specific hypothesis;
- describe the role of that level;
- create breakout/rejection/acceptance hypotheses around it;
- compare multiple nearby levels;
- reason about level confluence;
- define expected behavior around the level;
- detect when price action invalidates the story.

This separation improves determinism and prevents duplicated level calculations.

---

# 17. Running update log

## 2026-09-10 — Initial dedicated reference created

Captured:

- simple 10-year-old mental model;
- possible hypothesis families;
- thesis vs anti-thesis;
- S&R responsibility boundary;
- how hypothesis-style prediction works;
- expected-sequence and failure-sequence reasoning;
- relationship with M3.1, M3.3, Kronos, ORB and AFRE;
- current legacy weaknesses;
- safety/authority limits;
- target Hypothesis Box v2 flow.

Future discussions about the Hypothesis Box should append new dated entries here and, when appropriate, revise earlier design sections rather than creating conflicting undocumented rules.

---

# 18. Preferred multi-sensor Hypothesis Box design — 2026-09-10

This is the preferred direction from the later design discussion. It replaces any earlier impression that Hypothesis Box should mainly reason from EMA, VWAP and OI. Those were examples only.

## Core rule

Hypothesis Box must not be a normal indicator-voting engine:

```text
EMA bullish + VWAP bullish + OI bullish = LONG
```

Instead it should be a bounded, deterministic, auditable market-reasoning engine that:
- understands many evidence types;
- knows what each one actually measures;
- knows when each one is unreliable;
- selects evidence dynamically for the current market question;
- understands dependencies so correlated indicators do not inflate confidence;
- creates several competing hypotheses;
- creates an anti-thesis for the preferred hypothesis;
- describes expected path, failure path and invalidation;
- compares current state with PIT-safe real history/memory;
- preserves missing, unknown and conflicting evidence;
- never owns final authority. D6 remains sole final-band authority.

## Evidence world to support

### Price structure / location
S&R, HH/HL/LH/LL, swing highs/lows, BOS/CHOCH, PDH/PDL/PDC, CPR, pivots, Fibonacci when valid, ORH/ORL, gaps, and true higher-timeframe levels.

### Liquidity / smart-money-style structure
Chart-derived order blocks/supply-demand zones, FVGs, liquidity sweeps, SFP/stop-run evidence, repeated level tests, mitigation/retest, rejection and acceptance.

Chart order blocks are inferred price zones. They must not be presented as proof of actual institutional orders. Real order-book/order-flow evidence is a separate evidence type.

### Value / auction
Session, anchored, daily and weekly VWAP; U1/L1, U2/L2, U3/L3 VWAP bands; VWAP slope/distance/reclaim/rejection/band ride; POC/VAH/VAL and volume profile when available.

The 3 upper + 3 lower VWAP bands should be treated as one richer distribution map, not seven independent votes.

### Volatility / distribution
ATR, Bollinger center, future validated +/-1 sigma, +/-2 sigma and +/-3 sigma bands, band width/slope, squeeze/compression, expansion, band walk, rejection/acceptance, Keltner Channel, realized volatility and VIX context.

An upper Bollinger-band touch must not automatically mean sell; it can represent momentum expansion or exhaustion depending on context.

### Trend / horizon
EMA9, EMA20/21, EMA50, EMA200, each slope, stack order, separation/compression, price location relative to each horizon, true higher-timeframe trend, Supertrend, Ichimoku and ADX.

EMA9/20/50 remain distinct horizon facts but are not three independent proofs because they share price dependency.

### Momentum
RSI level/slope/divergence, MACD state/transition, stochastic, acceleration/deceleration and other validated M3.1 oscillators.

### Participation / real flow
Volume, RVOL, volume expansion/contraction, OBV, CMF, MFI, breakout participation, and real order-book/order-flow/trade-flow evidence when provenance is known.

### Derivatives
Futures price + OI change, options OI by strike/side, change in OI, PCR, volume, IV, IV rank, term structure, skew, max pain, GEX/gamma only when assumptions are valid, vanna/charm, basis, rollover, expiry and PIT-safe participant/FII positioning.

Raw OI alone must never be converted directly to bullish/bearish.

### Market context
Nifty/benchmark, sector, relative strength, breadth, volatility regime, market phase, opening behavior, event calendar and expiry/session context.

### Pattern / sequence
Candlestick patterns, multi-candle transitions, breakout/retest/rejection sequences, harmonic geometry plus validation, Elliott/wave hypotheses only as uncertain structure, opening sequence, 1/3/5/9-bar context, level-interaction and volume sequences.

### Memory / reviewers
Real 9-candle memory, historical analogs, pattern diary, failure trajectories, regime-conditioned reliability, OOD/drift, ORB, AFRE, Twin disagreement, and real validated Kronos sequence evidence. Mock/synthetic evidence stays outside canonical influence.

## Dynamic evidence routing

The box should not process all 94 outputs as equal votes. It first identifies the market question.

Example: price is testing major resistance. It can focus on:
- location: resistance, HTF level, order block, VWAP/BB bands, POC/VAH;
- breakout quality: acceptance, volume/RVOL, retest, BOS, candle sequence;
- trend: EMA horizons and HTF trend;
- context: Nifty, sector, breadth;
- derivatives: strike OI/OI change, IV/skew, expiry;
- memory: prior real/false breakouts and failure paths;
- sequence reviewer: validated Kronos when available.

## Multiple possible worlds

For the same state it may build:
1. real breakout/continuation;
2. resistance rejection;
3. liquidity sweep/false breakout;
4. compression then delayed expansion;
5. range/mean reversion;
6. trend pullback rather than reversal;
7. event-distorted/untrustworthy state;
8. chop/no edge.

For every hypothesis store:
thesis, anti-thesis, required evidence, support, opposition, unknowns, dependencies, market phase, timeframe/horizon, expected sequence, failure sequence, invalidators, expiry, regime assumptions, robustness/fragility and closest alternatives.

Do not decide by counting bullish versus bearish indicators.

## Relationship reasoning example

```text
weekly resistance
+ chart order block
+ VWAP U3
+ BB U2/U3
+ weakening RVOL
+ bearish divergence
```
can support an exhaustion/rejection hypothesis.

But:

```text
same resistance
+ accepted close above it
+ strong RVOL
+ rising VWAP
+ expanding BB with controlled band walk
+ retest holds old resistance as support
+ index/sector aligned
```
can support breakout continuation.

Neither is a guaranteed prediction.

## Prediction means path reasoning

Real-breakout expectation:

```text
break level -> accept above -> healthy participation -> retest -> old resistance holds -> higher low -> continuation
```

False-breakout expectation:

```text
trade above -> no acceptance -> participation weakens -> re-enter range -> lose value area -> structure weakens -> downside expansion
```

New closed-bar evidence should update each hypothesis to plausible, fragile or invalid.

## Evidence must earn importance

No indicator is mandatory simply because it is popular.

Promotion path:

```text
candidate evidence
-> understand what it measures
-> verify formula/implementation
-> verify PIT/freshness/provenance
-> test on real NSE data
-> test by stock/timeframe/market phase/regime
-> measure failures/false positives
-> measure dependency with other evidence
-> walk-forward/OOS testing
-> shadow/paper evaluation
-> assign canonical role only after proof
```

A sensor can be REQUIRED, SUPPORTING, OPPOSING, IRRELEVANT or UNKNOWN depending on the hypothesis and market state.

## Strong design formula

```text
KNOW MANY MARKET FACTS
+ UNDERSTAND THEIR REAL MEANING
+ UNDERSTAND LOCATION / PHASE / TIMEFRAME
+ UNDERSTAND RELATIONSHIPS / DEPENDENCIES
+ CREATE MULTIPLE FUTURE PATHS
+ BUILD ANTI-THESIS
+ TRY TO DISPROVE THE PREFERRED THESIS
+ COMPARE WITH PIT-SAFE REAL MEMORY
+ USE CONDITIONAL EMPIRICAL RELIABILITY
+ PRESERVE MISSING / UNKNOWN / CONFLICT
= STRONG BOUNDED HYPOTHESIS REASONING
```

## Repository-informed scope

The current project already contains or references dynamic VWAP, pivots, zones, FVGs, trendlines, HTF context, an order-block zone builder, daily/weekly VWAP with three upper and three lower deviation bands, Bollinger logic, CPR/pivots and many trend/momentum/volume/structure families. Hypothesis Engine v2 should reason over this broader canonical evidence graph instead of throwing it away.

## Authority remains unchanged

Hypothesis Box has no execution authority, cannot route orders, cannot set the final band, cannot use future data as causal evidence, cannot silently neutralize missing evidence, cannot use fake calibrated probability, and cannot allow mock/synthetic reviewers to affect canonical decisions.

## 2026-09-10 update log

The broader multi-sensor design is now preferred over the earlier narrow EMA/VWAP/OI examples. Future Hypothesis Box discussions should extend or explicitly revise this section.
