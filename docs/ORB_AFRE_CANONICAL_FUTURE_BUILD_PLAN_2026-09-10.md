# TRADE VISION — ORB + AFRE CANONICAL FUTURE BUILD PLAN

**Repository:** `onlyvictus-bit/trade-vision-app`  
**Planning branch:** `m4-d6-orchestration-redesign`  
**Document date:** 2026-09-10  
**Status:** FUTURE BUILD SPECIFICATION — this document records intended design and acceptance criteria. Its presence does **not** mean every item below is implemented or production-ready.

---

## 1. Canonical objective

Build ORB as a **research-driven, per-stock setup engine** that uses Trade Vision's existing research/intelligence systems, produces explicit ORB signals and proof-backed trade parameters, learns from completed historical outcomes with machine learning, and then sends its evidence to AFRE/D6 for final deliberation.

ORB must **not** become an independent final decision-maker. ORB produces setup evidence, signals, trade-plan candidates, research statistics, and calibrated ML probabilities. AFRE/D6 remains responsible for weighing supporting and contradicting evidence and issuing only the permitted guidance state such as `WAIT`, `WATCH`, or `PAPER-CANDIDATE`.

The desired system is **not** a fixed ORB-15 strategy and **not** “add more indicators.” It must research which ORB duration, confirmation timeframe, signal type, trade parameters, and context combination historically work best for each stock and regime, prove those findings on unseen data, and abstain when evidence is weak.

---

## 2. Non-negotiable previous-session invariant

1. “Previous-day candle” means **one completed DAILY session candle** built from the prior NSE session, normally 09:15–15:30 IST.
2. The system must never substitute the last 5-minute, 10-minute, 15-minute, or other intraday candle of yesterday for the previous-day DAILY candle.
3. Intraday data may be aggregated into the completed prior DAILY OHLCV candle only after that session is complete.
4. Previous-session context must be point-in-time safe: no data from the current decision's future may enter any feature, label, signal, parameter, backtest, playbook, ML input, or AFRE evidence.
5. Missing previous-session data must remain missing/unknown; never fabricate a neutral value to make a gate pass.

---

## 3. Canonical ORB Context Brain

Create one canonical context object for every ORB research run and live/paper guidance snapshot. It should collect, normalize, version, hash, and expose point-in-time-safe evidence including:

1. Previous completed DAILY OHLCV candle.
2. Previous-day candle anatomy: body size, range, body/range ratio, upper wick, lower wick, close location, gap relationship, directional strength, and abnormal-range flags.
3. Previous-day named candlestick-pattern evidence, including available single-bar and multi-bar patterns such as Doji, Harami, Engulfing, Piercing, Kicker, Hanging Man, Morning/Evening Star, Shooting Star, Hammer, Inverted Hammer, Three Inside, Dark Cloud/Piercing, Outside Reversal, SFP, and other validated registered candle structures.
4. CPR from completed prior-session data: Pivot, BC, TC, CPR width, ATR-normalized width, percentage width, and `NARROW` / `NORMAL` / `WIDE` class.
5. Previous-day levels: PDH, PDL, PDC and relevant pivot/support/resistance references.
6. Current opening gap state and opening location relative to previous-day levels and CPR zones.
7. Bollinger Band context: basis, upper/lower bands, width, squeeze/compression, expansion, slope, price location, band touch/break state, and volatility transition.
8. VWAP context: daily and weekly VWAP plus upper/lower deviation bands 1, 2, and 3 (`+1/+2/+3`, `-1/-2/-3`), distance from VWAP/bands, acceptance/rejection, and confluence with pivots/other levels.
9. ATR and volatility regime.
10. Volume and participation context, including OR volume, breakout/retest volume, relative volume, abnormal volume, and usable auction/volume evidence.
11. Market/index context, including Nifty or applicable benchmark alignment.
12. Sector context and relative-strength/weakness evidence where available.
13. Market-structure/liquidity evidence, including traps, sweeps, FVG/order-block/structure evidence when validated and point-in-time safe.
14. Event, derivatives, OI, expiry, volatility, and liquidity-risk context where available and valid for the symbol/session.
15. Existing AFRE/Decision-Spine evidence that is allowed to inform ORB context without creating circular authority.
16. Data quality, freshness, source identity, snapshot hash, feature version, and all missing/suspect-data flags.

The context brain must describe **what the market looked like before the ORB decision**; it must not decide the trade by itself.

---

## 4. ORB Timing and Confirmation Research Engine

Do not assume one opening range is best for every stock.

For each eligible stock, research multiple opening-range durations and confirmation schemes, including at minimum:

- ORB-5
- ORB-10
- ORB-15
- ORB-20
- ORB-30
- additional durations only when data granularity allows them without synthetic leakage
- relevant confirmation timeframes such as 1m / 3m / 5m / 15m where source data supports exact reconstruction

For every stock × OR duration × confirmation timeframe × signal family × regime/context bucket, measure at least:

- sample count
- win rate
- loss rate
- expectancy in R and currency-normalized form
- median/mean R
- profit factor where appropriate
- maximum drawdown
- MAE/MFE
- false-break rate
- retest success rate
- average time to trigger
- average time in trade
- entry-cutoff sensitivity
- no-chase sensitivity
- stop/target sensitivity
- regime dependence
- stability across years/market conditions
- performance on unseen/holdout data
- uncertainty/confidence interval
- edge decay/drift

The engine must be able to conclude that **different stocks need different ORB timing**. Example output is allowed to be conceptually similar to: “RELIANCE has stronger unseen-data evidence for ORB-15 with 5m close confirmation in trend/gap-supportive regimes, while ORB-5 is unstable.” This example must never be hard-coded as truth.

---

## 5. Explicit ORB Signal Engine

ORB must produce a first-class, versioned signal object. Do not hide the ORB signal inside a generic confluence score.

The signal engine should support and independently research validated families such as:

1. `NO_SETUP`
2. `BREAKOUT_LONG`
3. `BREAKDOWN_SHORT`
4. `RETEST_LONG`
5. `RETEST_SHORT`
6. `REVERSAL_LONG` / failed-break recovery below ORL
7. `REVERSAL_SHORT` / failed-break recovery above ORH
8. `SECOND_CHANCE_REENTRY_LONG`
9. `SECOND_CHANCE_REENTRY_SHORT`
10. `TRAP_LONG` / `TRAP_SHORT` evidence where a failed breakout creates the opposite thesis
11. `INVALIDATED` / stale setup when the configured setup no longer qualifies

Each ORB signal record must contain, when applicable:

- symbol
- session date
- source timeframe
- researched OR duration
- confirmation timeframe
- signal family/type
- direction/side
- OR start/end and lock time
- ORH / ORL / midpoint / width / width-to-ATR
- signal timestamp and closed-candle confirmation time
- trigger price
- breakout/breakdown buffer used
- breakout close or breach evidence
- retest evidence and retest quality
- volume confirmation state
- VWAP confirmation state
- context-support score/evidence summary
- context-conflict score/evidence summary
- trap/failure evidence
- signal freshness/staleness
- invalidation reason
- source snapshot identity/hash
- deterministic signal hash
- point-in-time / no-future-leakage proof
- signal-engine version
- explicit reasons FOR the signal
- explicit reasons AGAINST the signal

A signal is **evidence**, not final trade authority.

---

## 6. Trade Parameter Research and Selection Engine

Every promoted ORB playbook must contain proof-backed **trade parameters**, not only “long/short.” Research and select parameters per stock, signal family, and regime/context when sufficient evidence exists.

Trade-parameter research must cover at least:

1. Entry style: breakout-close entry, confirmed breach, pullback/retest entry, and allowed second-chance re-entry.
2. Entry price or entry zone.
3. Breakout/breakdown buffer.
4. Maximum chase distance from ORH/ORL, ATR, VWAP, or researched reference.
5. Confirmation rule: close confirmation vs permitted breach logic.
6. Required breakout/retest volume threshold.
7. VWAP/3-band acceptance or veto rule when research proves utility.
8. Stop methodology: opposite OR boundary, signal-candle/swing invalidation, ATR-based stop, structure-based stop, or validated hybrid.
9. Stop price and invalidation explanation.
10. Target methodology: fixed R multiple, ATR target, next proven structure/PDH/PDL/pivot/VWAP-band target, or validated hybrid.
11. Target price(s) and expected R.
12. Minimum reward:risk requirement.
13. Entry cutoff / latest allowed new entry time.
14. Setup expiry/staleness time.
15. Maximum holding period and mandatory paper flat time where applicable.
16. Retest wait window.
17. Maximum number of re-entries; default research must strongly constrain re-entry and never permit uncontrolled repeated attempts.
18. Slippage/transaction-cost assumptions used by backtests.
19. Liquidity requirements and spread/market-impact safeguards where data exists.
20. Regime-specific or context-specific parameter overrides only when unseen-data proof supports them.
21. Expected win probability, loss probability, expectancy, uncertainty, and sample count attached to the chosen parameter set.
22. Parameter-set version and proof dataset/version.

Trade parameters must be learned/researched from historical evidence, then frozen/versioned for a promoted playbook. They must **not** change ad hoc during a current session because the engine sees the future path.

The system remains research/paper guidance only. Position sizing must not create live broker authority; any paper `size_hint` remains subordinate to safety/risk policy and human approval.

---

## 7. Combination Research — Learn Context, Not Isolated Indicators

Do not evaluate CPR, BB, VWAP, candle pattern, gap, volume, index alignment, structure, and event context only one at a time. Research **combinations** and contradictions.

The research engine should be able to ask questions such as:

- When the previous completed DAILY candle was bullish engulfing, CPR was narrow, price accepted above daily VWAP, BB was expanding, and index context was bullish, how did ORB-long perform?
- When the ORB signal was bullish but the previous DAILY candle was bearish rejection, price opened into wide CPR, BB was contracting, and the index/sector disagreed, how often did the breakout fail?
- Which context combinations improve retest entries but hurt direct breakout entries?
- Which conditions make ORB-5 noisy but ORB-15 stable for this stock?
- Which signals work only in gap-up/gap-down/trend/range/expiry/event regimes?

Combinations must be subject to minimum-sample, multiple-testing/overfit controls, unseen-data validation, and uncertainty penalties. Sparse combinations must cause abstention or pooling, not false certainty.

---

## 8. Per-Stock ORB Playbook

The proven output of research should be a versioned playbook per stock/timeframe/context scope. A playbook should include at least:

- symbol
- eligible source timeframe(s)
- preferred OR duration(s)
- preferred confirmation timeframe(s)
- supported ORB signal families
- best historical contexts
- bad/no-trade contexts
- preferred direction biases only when evidence supports them
- breakout vs retest preference
- false-break/trap behavior
- allowed re-entry rule
- volume requirements
- VWAP/3-band rules
- CPR rules
- previous-day candle/pattern rules
- BB volatility-state rules
- market/index/sector alignment rules
- event/derivatives/liquidity vetoes
- entry rule
- stop rule
- target rule
- minimum RR
- no-chase rule
- entry cutoff
- setup expiry
- hold/flat rule
- sample count
- train/validation/holdout date ranges
- deterministic backtest statistics
- ML probability/calibration metadata if ML is promoted
- uncertainty/confidence interval
- known failure modes
- drift/edge-decay status
- playbook version
- data/feature/model versions
- promotion status

No playbook becomes active merely because an in-sample backtest looks good.

---

## 9. Machine-Learning Accuracy Engine

Add a dedicated **research-only ML layer** to improve future ORB accuracy and calibration. ML must support deterministic research and AFRE evidence; it must never directly trade, route orders, bypass hard gates, or manufacture certainty.

### 9.1 ML goal

Estimate conditional probabilities and expected outcomes such as:

- probability an ORB signal reaches target before stop
- probability of false breakout/trap
- probability a retest succeeds
- expected R / expected return after costs
- probability a setup remains valid after a defined horizon
- which OR duration and confirmation timeframe are most suitable for the current stock/context
- which proven trade-parameter set has the best expected risk-adjusted outcome under the current context

ML should improve **calibration and ranking**, not replace deterministic ORB definitions or safety rules.

### 9.2 ML feature set

Use only features available at the decision time. Candidate features include:

- symbol and stable stock descriptors when justified
- OR duration and confirmation timeframe
- OR width, width/ATR, OR volume, OR VWAP
- ORB signal family and direction
- breakout strength, close location, retest quality, time-to-breakout
- selected trade-parameter candidate identifiers
- previous completed DAILY candle anatomy and named pattern
- CPR/PDH/PDL/PDC/gap/zone context
- BB state
- daily/weekly VWAP and ±1/±2/±3 band state
- ATR/volatility regime
- relative volume/participation evidence
- index/sector context
- market structure/liquidity/trap context
- event/derivatives/OI/expiry context where valid
- historical analog/reliability features that are themselves point-in-time safe
- prior playbook performance statistics using only outcomes known before the decision

Never use future high/low/close, future target/stop outcome, end-of-day information that was not yet known, or post-entry facts as decision-time features.

### 9.3 Labels

Labels may be created only after the required future horizon has fully completed. Possible labels include win/loss/timeout, target-before-stop, maximum favorable/adverse excursion, realized R after costs, false-break status, retest-success status, and completed-session day type.

Label generation must be isolated from decision-time features so target leakage is impossible.

### 9.4 Training and validation

At minimum:

1. Chronological train/validation/test split.
2. Walk-forward evaluation.
3. Purged/embargoed validation where overlapping trade horizons can leak information.
4. Final untouched holdout/unseen period before promotion.
5. Per-stock models only when sample size is sufficient; otherwise use pooled/hierarchical/global models with stock identity handled safely.
6. Compare ML against deterministic and simple statistical baselines.
7. Hyperparameter search must occur only inside training/validation data, never on final holdout.
8. Retraining must use only matured historical labels.
9. Dataset, feature schema, code, model, and training window must be versioned and reproducible.

### 9.5 Accuracy and quality metrics

Do not judge the model only by raw classification accuracy. Record at least where applicable:

- Brier score
- log loss
- calibration error / reliability curve
- ROC-AUC and/or PR-AUC when meaningful
- precision/recall for rare trap/failure classes
- probability-bin hit rates
- expected R by probability decile
- realized expectancy after costs
- drawdown of ML-ranked vs baseline playbooks
- stability by stock, year, regime, and signal family
- uncertainty/confidence interval

A model with higher raw accuracy but worse calibration, expectancy, or unseen stability must not automatically win.

### 9.6 Future-accuracy learning loop

After each completed session/trade horizon:

1. Store the immutable decision-time feature snapshot.
2. Wait until the outcome label is mature.
3. Attach the completed outcome without mutating the original feature snapshot.
4. Update rolling performance and calibration statistics.
5. Detect drift, edge decay, probability miscalibration, and regime shift.
6. Retrain only when predefined evidence/data thresholds are met.
7. Evaluate the challenger model on walk-forward and untouched unseen data.
8. Promote only if it materially improves the required metrics without weakening safety, calibration, or stability.
9. Keep the previous champion model available for deterministic rollback.
10. If the new model degrades or evidence is insufficient, remain on the prior model or abstain.

This loop is the mechanism for **future accuracy improvement**. It must be controlled learning, not uncontrolled self-modification.

### 9.7 ML authority limits

ML may:

- rank proven ORB candidates
- estimate calibrated probabilities
- estimate expected R/outcome distributions
- recommend which already-proven playbook/parameter set best matches the current context
- contribute evidence FOR/AGAINST to AFRE/D6
- reduce confidence or recommend abstention

ML may **not**:

- create broker orders
- grant itself live-trading authority
- bypass data-quality, PIT, event, liquidity, risk, playbook, or human-approval gates
- activate an unproven parameter set because a model score is high
- overwrite the deterministic ORB signal definition
- use future data

---

## 10. ORB + AFRE Integration

The intended authority flow is:

```text
Historical/PIT-safe Market Data
        |
        v
Previous Completed DAILY Session Context
(Candle + CPR + PDH/PDL/PDC + BB + VWAP ±1/2/3 + ATR + volume)
        |
        +----> Market / Index / Sector / Structure / Event / Derivatives Context
        |
        v
Canonical ORB Context Brain
        |
        +----> ORB Timing/TF Research
        +----> Combination Research
        +----> ML Probability / Expected-Outcome Research
        |
        v
Proof-Backed Per-Stock ORB Playbook
        |
        v
Today's Locked Opening Range
        |
        v
Explicit ORB Signal Engine
        |
        v
Proof-Backed Trade Parameter Selection
        |
        v
ORB Evidence Package
(signal + parameters + statistics + ML calibration + reasons for/against)
        |
        v
AFRE Evidence/Reasoning Layers
        |
        v
D6 Final Deliberation / Confluence Arbitration
        |
        +----> WAIT
        +----> WATCH
        +----> PAPER-CANDIDATE
```

ORB must explicitly provide AFRE/D6 with both **supporting and contradicting evidence**. AFRE must be allowed to reject an apparently strong ORB when stronger risk/context evidence disagrees.

---

## 11. Example of intended reasoning

Example only; values are illustrative and must never be hard-coded:

```text
RELIANCE — 09:40 IST

ORB research:
- ORB-15 is the strongest currently promoted duration for this stock/context.
- 5m close confirmation is the promoted confirmation scheme.

Previous completed session:
- DAILY pattern: Bullish Engulfing.
- Close near session high.
- CPR: Narrow.
- Daily VWAP: accepted above value.
- VWAP band state: positive.
- Bollinger state: expanding.

Today:
- Moderate gap up.
- Locked ORH/ORL available.
- BREAKOUT_LONG confirmed on a closed candle.
- Breakout volume passes the promoted threshold.
- Nifty/index alignment supports long.

Trade-parameter engine:
- Entry: researched breakout/retest rule.
- Stop: promoted invalidation rule.
- Target: promoted structure/RR rule.
- No-chase distance: passes.
- Entry cutoff: passes.

ML research evidence:
- Similar PIT-safe contexts have sufficient historical evidence.
- Calibrated probability and expected R are supportive.
- Model is not drift-blocked and holdout performance remains within promotion limits.

Against:
- Weekly resistance is nearby.
- Trap risk is non-zero.

AFRE/D6 reasoning:
- ORB signal, prior-session context, volume, and index alignment support continuation.
- Nearby resistance lowers confidence and may alter target/abstention logic.

Final permitted output:
- WATCH or PAPER-CANDIDATE depending on all hard gates and final arbitration.
```

---

## 12. Build sequence

### Phase 0 — Baseline lock and audit

- Record current branch head and existing ORB/AFRE behavior.
- Identify all existing relevant modules before coding.
- Preserve current passing tests and authority boundaries.
- Do not duplicate an existing canonical calculation when it can be safely reused.

### Phase 1 — Canonical previous-session ORB context

- Build the previous completed DAILY session object.
- Wire candle anatomy/patterns, CPR, PDH/PDL/PDC, gap, BB, VWAP ±1/±2/±3, ATR, volume and quality metadata.
- Add tests proving the prior DAILY candle is not the previous intraday candle.

### Phase 2 — Timing/TF research

- Research OR duration × confirmation timeframe per stock.
- Add unseen-data and walk-forward proof.

### Phase 3 — Explicit ORB signal contract

- Promote ORB signal to a first-class deterministic schema.
- Implement/reconcile breakout, breakdown, retest, reversal, trap, re-entry, stale/no-setup semantics.

### Phase 4 — Trade-parameter research

- Research entry, stop, target, RR, buffers, volume, VWAP conditions, no-chase distance, cutoff, expiry and hold rules.
- Version and freeze promoted parameter sets.

### Phase 5 — Combination research

- Research context combinations, conflicts and regime-specific behavior.
- Add sparse-sample and overfit protection.

### Phase 6 — ML dataset and feature store

- Create immutable PIT-safe decision snapshots.
- Create delayed/matured outcome labels separately.
- Version datasets/features and prove zero target leakage.

### Phase 7 — ML training/calibration/challenger framework

- Train baseline and candidate models.
- Run walk-forward, purged validation and untouched holdout.
- Add calibration, drift and edge-decay monitoring.

### Phase 8 — Per-stock playbook promotion

- Combine deterministic research, trade parameters and approved ML metadata.
- Promote only proof-backed playbooks.

### Phase 9 — AFRE/D6 evidence integration

- Package ORB signal + parameters + deterministic statistics + ML probabilities + FOR/AGAINST evidence.
- Feed that package into AFRE/D6 without granting ORB or ML final authority.

### Phase 10 — Adversarial tests and CI

- Run no-future-leakage, deterministic replay, missing-data, stale-data, wrong-session, duplicate-bar, corporate-action, sparse-sample, overfit, ML-leakage, drift, signal-staleness, parameter-version, playbook-promotion, and authority-boundary tests.
- Require exact-head CI before declaring a stage GREEN.

### Phase 11 — Paper-only operational validation

- Run shadow/paper guidance.
- Require explicit human approval for paper records.
- Keep broker routing and live trading blocked.

---

## 13. Mandatory acceptance gates

The build is incomplete unless all applicable gates below pass:

1. Previous-day context is the completed prior DAILY session, not the final intraday bar.
2. All research and live/paper features are point-in-time safe.
3. Current/future bars cannot alter earlier historical decisions when replayed.
4. CPR calculations use one canonical implementation.
5. BB context is explicitly wired into the ORB context package when enabled/validated.
6. Daily/weekly VWAP and bands ±1/±2/±3 are explicitly wired when enabled/validated.
7. Detailed previous-day candlestick anatomy/pattern evidence is explicitly wired into ORB context.
8. Multiple OR durations are researched per stock.
9. Multiple confirmation timeframes are researched where data allows.
10. ORB signals are first-class, deterministic and versioned.
11. Trade parameters are first-class, researched, versioned and playbook-bound.
12. No-chase, cutoff, staleness and invalidation are explicit.
13. Combination research exists; isolated indicator scores are not the only context mechanism.
14. Train/validation/holdout periods are chronological and reproducible.
15. Final holdout is never used for hyperparameter tuning.
16. ML labels are generated only after the outcome horizon matures.
17. ML features contain no future/end-of-day/post-entry leakage at decision time.
18. ML probability output is calibrated and compared against a baseline.
19. Model drift/edge decay is monitored.
20. Challenger models require unseen-data improvement before promotion.
21. Low sample or high uncertainty can force abstention.
22. Per-stock modeling is used only when sample sufficiency allows it.
23. Promoted playbooks contain OR timing, confirmation TF, signal family and trade parameters.
24. ORB evidence contains both reasons FOR and AGAINST.
25. ML evidence contains uncertainty and cannot bypass hard blockers.
26. ORB cannot make the final system decision by itself.
27. ML cannot make the final system decision by itself.
28. AFRE/D6 can veto an ORB candidate when higher-authority context/risk evidence contradicts it.
29. No component gains live order-routing authority.
30. Human approval remains required for paper-trade recording/action.
31. Missing/suspect inputs remain visible and fail closed where required.
32. No fake READY/GREEN status is allowed; status must be backed by exact tests/CI evidence.

---

## 14. Line-by-line requirement audit

This section is intentionally redundant. It exists so a future build agent can verify that the design request was not shortened or silently reinterpreted.

| Audit ID | Required design line | Captured in |
|---|---|---|
| A01 | Create one Canonical ORB Context Brain. | §§3, 12 Phase 1 |
| A02 | Use previous completed DAILY candle. | §§2, 3 |
| A03 | Never treat yesterday's last 5m/10m/15m candle as previous-day candle. | §2 |
| A04 | Include detailed previous-day candle anatomy and pattern. | §§3.2–3.3 |
| A05 | Include CPR. | §3.4 |
| A06 | Include PDH/PDL/PDC and opening gap/zone. | §§3.5–3.6 |
| A07 | Include Bollinger Band state. | §3.7 |
| A08 | Include daily/weekly VWAP with ±1/±2/±3 bands. | §3.8 |
| A09 | Include ATR/volatility and volume. | §§3.9–3.10 |
| A10 | Include market/index/sector context. | §§3.11–3.12 |
| A11 | Include structure/liquidity/trap context. | §3.13 |
| A12 | Include event/derivatives/OI/expiry/liquidity risk where valid. | §3.14 |
| A13 | Include allowed existing AFRE evidence without circular authority. | §3.15 |
| A14 | Preserve quality/freshness/snapshot/missing-state metadata. | §3.16 |
| A15 | Backtest which OR time is best for each stock. | §4 |
| A16 | Backtest which confirmation timeframe is best for each stock. | §4 |
| A17 | Test ORB-5/10/15/20/30 rather than assume ORB-15. | §4 |
| A18 | Measure win rate, expectancy, drawdown, false-break, sample size, stability and unseen-data performance. | §4 |
| A19 | Research combinations, not isolated indicators only. | §7 |
| A20 | Learn supportive and conflicting context combinations. | §7 |
| A21 | Build a per-stock proof-backed ORB playbook. | §8 |
| A22 | Playbook stores best/bad contexts and regime dependence. | §8 |
| A23 | Playbook stores timing/TF and signal behavior. | §8 |
| A24 | Playbook stores volume/VWAP/CPR/candle/BB rules. | §8 |
| A25 | ORB becomes evidence; AFRE is the reasoning layer. | §§1, 10 |
| A26 | D6 reasons over support and contradiction. | §§10–11 |
| A27 | Final outputs remain WAIT/WATCH/PAPER-CANDIDATE. | §§1, 10–11 |
| A28 | Add explicit ORB signal output. | §5 |
| A29 | Include breakout/breakdown signals. | §5 |
| A30 | Include retest signals. | §5 |
| A31 | Include reversal/failed-break/trap evidence. | §5 |
| A32 | Include constrained second-chance re-entry semantics. | §5 |
| A33 | Signal includes ORH/ORL, timing, price, volume, VWAP, context, freshness, hashes and reasons. | §5 |
| A34 | Add explicit trade parameters. | §6 |
| A35 | Research entry style/price/zone. | §6.1–§6.2 |
| A36 | Research breakout buffer and no-chase distance. | §6.3–§6.4 |
| A37 | Research volume/VWAP confirmation requirements. | §6.6–§6.7 |
| A38 | Research stop methodology and invalidation. | §6.8–§6.9 |
| A39 | Research target methodology and target prices. | §6.10–§6.11 |
| A40 | Research minimum RR, cutoff, staleness, hold and retest windows. | §6.12–§6.16 |
| A41 | Constrain maximum re-entry attempts. | §6.17 |
| A42 | Include slippage/cost/liquidity assumptions. | §§6.18–6.19 |
| A43 | Bind parameters to stock/signal/regime with proof and versioning. | §§6.20–6.22 |
| A44 | Add machine learning for future accuracy improvement. | §9 |
| A45 | ML estimates win/trap/retest/expected-R probabilities. | §9.1 |
| A46 | ML may help select OR duration, confirmation TF and proven parameter set. | §9.1 |
| A47 | ML uses only PIT-safe decision-time features. | §9.2 |
| A48 | ML includes prior DAILY candle, CPR, BB and VWAP-band features. | §9.2 |
| A49 | ML labels are delayed until outcomes mature. | §9.3 |
| A50 | Use chronological train/validation/test and walk-forward evaluation. | §9.4 |
| A51 | Protect against overlapping-horizon leakage with purge/embargo where needed. | §9.4 |
| A52 | Keep an untouched holdout for promotion proof. | §9.4 |
| A53 | Do not force per-stock ML when samples are too small. | §9.4 |
| A54 | Compare ML with deterministic/simple baselines. | §9.4 |
| A55 | Evaluate calibration and trading-relevant quality, not raw accuracy alone. | §9.5 |
| A56 | After new completed outcomes, update calibration/drift and retrain only under controlled rules. | §9.6 |
| A57 | Champion/challenger promotion requires unseen improvement. | §9.6 |
| A58 | Keep rollback and abstention paths. | §9.6 |
| A59 | ML may rank/contribute evidence but cannot execute or bypass gates. | §9.7 |
| A60 | ORB signal + trade parameters + ML evidence must reach AFRE/D6 together. | §10 |
| A61 | Preserve no-future-leakage and deterministic replay. | §§2, 13 |
| A62 | Missing data must not be fabricated. | §§2, 13 |
| A63 | Prevent overfit and small-sample false certainty. | §§7, 9, 13 |
| A64 | Keep train/test separation and proof on unseen data. | §§4, 9, 13 |
| A65 | Keep ORB/AFRE/ML at zero live-trading authority. | §§1, 6, 9.7, 13 |
| A66 | Human approval remains required for paper action. | §§6, 12 Phase 11, 13 |
| A67 | Harden with adversarial tests and exact-head CI before GREEN. | §12 Phase 10, §13 |
| A68 | Do not fake READY/GREEN. | §13.32 |

**Audit result at document creation:** 68/68 requested design requirements are explicitly represented in this specification. Future implementation must re-run this audit against code, tests, docs, CI evidence, and promoted playbook/model artifacts; this document alone is not implementation proof.

---

## 15. Definition of future completion

The ORB + AFRE upgrade is complete only when Trade Vision can, for an eligible stock and decision snapshot:

1. reconstruct the correct previous completed DAILY session and its full context;
2. identify the currently promoted OR duration and confirmation timeframe from proof-backed research;
3. produce an explicit deterministic ORB signal or `NO_SETUP`;
4. attach a versioned proof-backed trade-parameter plan when eligible;
5. attach calibrated ML probability/expected-outcome evidence from a promoted, non-drifted model when eligible;
6. explain both supporting and contradicting evidence;
7. prove all information was available at the decision time;
8. send the complete package to AFRE/D6;
9. allow AFRE/D6 and hard safety/risk gates to veto it;
10. return only the permitted guidance state, with live trading and order routing still blocked.

That is the intended future design: **research what works for this stock, detect today's ORB signal, choose only proven trade parameters, use controlled ML to improve future probability accuracy, and let AFRE/D6 reason over the complete evidence rather than blindly following an ORB breakout.**

---

# 16. Canonical Build Order and Inter-Stage Data Flow

This section is a required implementation map. It defines **how the build proceeds, what exact class of data enters every stage, what that stage is allowed to calculate, and what artifact is permitted to flow to the next stage**.

There are two separate but connected pipelines:

1. **Research/build pipeline** — uses historical point-in-time-safe data to discover, validate, prove, calibrate, and promote per-stock ORB playbooks and ML models.
2. **Daily runtime pipeline** — uses only information available at the current decision timestamp, the already-promoted playbook/model, and closed candles to create today's ORB evidence package for AFRE/D6.

Do not mix these two pipelines. Historical future outcomes may be used to create matured research labels **after** their horizon completes, but may never flow into the feature snapshot used to reproduce an earlier decision.

## 16.1 Full build order

| Stage | Build responsibility | Main data IN | Canonical data/artifact OUT |
|---|---|---|---|
| 0 | Baseline Lock and Audit | branch SHA, current ORB code, AFRE/D6 code, tests, current CI, authority registry | `ORB_BASELINE_MANIFEST` |
| 1 | Canonical ORB Context Brain | historical OHLCV, previous completed DAILY session, CPR, BB, VWAP bands, ATR, volume, index, sector, structure, events, derivatives, quality/provenance | `ORB_CONTEXT_SNAPSHOT` |
| 2 | Timing/Confirmation Research | historical context snapshots + closed historical intraday bars + historical matured outcomes | `ORB_TIMING_RESEARCH_REPORT` |
| 3 | Explicit ORB Signal Engine | promoted/researched OR-duration rules + locked ORH/ORL + closed post-OR bars + context | `ORB_SIGNAL` |
| 4 | Trade Parameter Research and Selection | historical ORB signals + decision-time context + later matured price-path outcomes | `ORB_PARAMETER_SET` candidates and proof |
| 5 | Combination Research | context + signal + parameters + matured outcomes | `ORB_COMBINATION_EVIDENCE` |
| 6 | ML Dataset / Feature Store | immutable decision-time snapshots + separately matured labels | versioned ML feature/label dataset |
| 7 | ML Training / Calibration / Challenger | chronological train/validation data + approved feature schema | model artifact + calibration + uncertainty + promotion evidence |
| 8 | Per-Stock Playbook Promotion | timing proof + signal proof + parameter proof + combination proof + approved ML metadata | versioned `ORB_PLAYBOOK` |
| 9 | AFRE/D6 Integration | today's context + playbook + ORB signal + selected trade parameters + ML evidence + FOR/AGAINST evidence | `ORB_EVIDENCE_PACKAGE` to AFRE/D6 |
| 10 | Safety / Adversarial CI | replay cases, missing/stale data, leakage attacks, authority attacks, model drift cases | exact-head test/CI evidence |
| 11 | Paper Operational Validation | live closed-candle market data + promoted playbook/model, no broker authority | immutable paper decision snapshots + later matured outcomes |

The ordering matters. Do not train ML before there is a stable, versioned feature contract. Do not promote a per-stock playbook before timing, signal, trade-parameter, and unseen-data proof exist. Do not wire ORB as a final authority before AFRE/D6 evidence contracts and veto behavior are tested.

---

# 17. Stage 0 — Baseline Lock and Audit

Before new ORB coding:

```text
CURRENT BRANCH HEAD
       +
CURRENT ORB MODULES
       +
CURRENT AFRE/D6 MODULES
       +
CURRENT TESTS / CI
       +
CURRENT AUTHORITY RULES
       ↓
ORB_BASELINE_MANIFEST
```

The baseline manifest should record at minimum:

- exact branch
- exact commit SHA
- existing ORB engine versions
- existing AFRE/D6 versions
- current data contracts
- current tests and passing/failing status
- current CI run IDs where applicable
- known gaps
- known legacy behavior that must not silently change
- research-only/live-trading-blocked invariants

This prevents a future implementation from starting over or falsely claiming an existing feature is missing.

---

# 18. Stage 1 — Canonical ORB Context Brain Data Flow

Stage 1 is the **market-context construction layer**. It does not make the final trade decision.

## 18.1 Previous completed DAILY session creation

Historical/live intraday bars flow as:

```text
Yesterday's closed intraday candles
09:15
09:20
09:25
...
15:25
15:30
       ↓
validate session completeness / provenance
       ↓
aggregate once
       ↓
ONE PREVIOUS COMPLETED DAILY OHLCV CANDLE
```

The following substitution is forbidden:

```text
Yesterday's last 5m / 10m / 15m candle
                 ≠
Yesterday's completed DAILY candle
```

## 18.2 Previous-day data extracted/calculated

From the completed prior session:

```text
PREVIOUS COMPLETED DAILY SESSION
│
├── OHLCV
├── candle anatomy
│   ├── body size
│   ├── full range
│   ├── body/range ratio
│   ├── upper wick
│   ├── lower wick
│   ├── close location
│   ├── directional strength
│   └── abnormal range flags
│
├── candlestick pattern evidence
│   ├── Engulfing
│   ├── Hammer
│   ├── Inverted Hammer
│   ├── Shooting Star
│   ├── Doji
│   ├── Harami
│   ├── Kicker
│   ├── Morning Star
│   ├── Evening Star
│   ├── Three Inside
│   ├── Dark Cloud / Piercing
│   ├── Outside Reversal
│   ├── SFP
│   └── other validated registered patterns
│
├── CPR
│   ├── Pivot
│   ├── BC
│   ├── TC
│   ├── CPR width
│   ├── width / ATR
│   └── NARROW / NORMAL / WIDE
│
├── PDH
├── PDL
├── PDC
│
├── Bollinger context
│   ├── basis
│   ├── upper
│   ├── lower
│   ├── width
│   ├── compression/squeeze
│   ├── expansion
│   ├── slope
│   └── price/band relationship
│
├── VWAP context
│   ├── Daily VWAP
│   ├── Daily +1 / +2 / +3
│   ├── Daily -1 / -2 / -3
│   ├── Weekly VWAP
│   ├── Weekly +1 / +2 / +3
│   ├── Weekly -1 / -2 / -3
│   ├── distance
│   ├── acceptance/rejection
│   └── confluence
│
├── ATR / volatility regime
├── volume / participation evidence
├── market structure / liquidity / trap evidence
└── data-quality / provenance metadata
```

## 18.3 Current-session context available before the decision

Only information already known at the current timestamp may be added:

```text
TODAY SO FAR
│
├── opening price
├── gap size / gap direction
├── position vs PDH/PDL/PDC
├── position vs CPR zones
├── closed-candle intraday volatility
├── closed-candle volume / RVOL
├── Nifty / benchmark alignment
├── sector alignment
├── structure/liquidity/trap evidence
├── event risk
├── derivatives / OI / expiry context when valid
└── data quality / freshness
```

## 18.4 Stage-1 canonical output

All of the above is normalized into:

```text
ORB_CONTEXT_SNAPSHOT
```

Example structure:

```text
symbol = RELIANCE
snapshot_time = 09:40 IST
previous_daily_pattern = BULLISH_ENGULFING
previous_daily_close_location = 0.91
cpr_class = NARROW
vwap_state = ABOVE_DAILY_PLUS_1
bb_state = EXPANDING
atr_regime = NORMAL_HIGH
nifty_alignment = BULLISH
sector_alignment = BULLISH
event_state = NONE
quality = GOOD
snapshot_hash = ...
feature_version = ...
```

Every value must include enough identity/provenance to reproduce it. Missing values remain explicitly unavailable/unknown instead of being converted to zero or neutral.

---

# 19. Stage 2 — ORB Timing and Confirmation-Timeframe Research Flow

Stage 2 asks **which opening-range duration and confirmation timeframe actually work for this stock and context**.

Inputs:

```text
HISTORICAL ORB_CONTEXT_SNAPSHOTs
             +
HISTORICAL CLOSED INTRADAY BARS
             +
MATURED HISTORICAL OUTCOMES
```

Research matrix includes at minimum:

```text
ORB-5
ORB-10
ORB-15
ORB-20
ORB-30
```

crossed with supported confirmation timeframes such as:

```text
1m
3m
5m
15m
```

A research cell is conceptually:

```text
SYMBOL
  ×
OR DURATION
  ×
CONFIRMATION TF
  ×
SIGNAL FAMILY
  ×
REGIME / CONTEXT
```

Example research comparisons:

```text
RELIANCE + ORB-5  + 5m confirmation + narrow CPR + bullish prior day
RELIANCE + ORB-15 + 5m confirmation + narrow CPR + bullish prior day
RELIANCE + ORB-30 + 15m confirmation + same context
```

For each cell, calculate at least:

- sample count
- win/loss rate
- expectancy
- mean/median R
- profit factor
- drawdown
- MAE/MFE
- false-break rate
- retest success
- average trigger time
- average holding time
- no-chase sensitivity
- entry-cutoff sensitivity
- stop/target sensitivity
- regime dependence
- year-to-year stability
- unseen/holdout performance
- uncertainty/confidence interval
- edge decay/drift

Output:

```text
ORB_TIMING_RESEARCH_REPORT
```

Possible data-driven result:

```text
symbol = RELIANCE
ORB-5 = unstable
ORB-10 = acceptable
ORB-15 = strongest promoted evidence
ORB-20 = good but lower opportunity count
ORB-30 = lower expectancy / too late
preferred_confirmation_tf = 5m
```

This example is illustrative only. The engine must discover the result from historical proof.

---

# 20. Stage 3 — Explicit ORB Signal Engine Data Flow

Stage 2/playbook tells runtime **how the OR should be formed**. Stage 3 determines **what signal actually occurred today**.

Example promoted configuration:

```text
symbol = RELIANCE
OR duration = 15m
confirmation = 5m closed candle
```

Today's opening range:

```text
09:15–09:30 closed bars
        ↓
ORH = highest eligible high
ORL = lowest eligible low
ORM = midpoint
OR width
OR width / ATR
OR volume
OR VWAP
        ↓
LOCKED OPENING RANGE
```

After the OR is locked, only fully closed eligible bars can create authority.

Example:

```text
ORH = 1510
ORL = 1490
09:35 closed candle close = 1514
volume confirmation = PASS
        ↓
ORB_SIGNAL.type = BREAKOUT_LONG
```

Allowed explicit signal families include:

```text
NO_SETUP
BREAKOUT_LONG
BREAKDOWN_SHORT
RETEST_LONG
RETEST_SHORT
REVERSAL_LONG
REVERSAL_SHORT
TRAP_LONG
TRAP_SHORT
SECOND_CHANCE_REENTRY_LONG
SECOND_CHANCE_REENTRY_SHORT
INVALIDATED
```

Stage-3 output:

```text
ORB_SIGNAL
│
├── symbol/session
├── signal family
├── direction
├── OR duration
├── confirmation TF
├── ORH / ORL / midpoint
├── width / ATR
├── lock time
├── trigger time
├── closed-candle confirmation time
├── trigger price
├── breakout buffer
├── volume confirmation
├── VWAP confirmation
├── retest evidence
├── trap evidence
├── freshness / staleness
├── invalidation
├── context support summary
├── context conflict summary
├── reasons FOR
├── reasons AGAINST
├── source snapshot hash
├── deterministic signal hash
└── engine version
```

`ORB_SIGNAL` is evidence. It is never a broker instruction or final decision.

---

# 21. Stage 4 — Trade Parameter Research and Selection Data Flow

An ORB signal such as `BREAKOUT_LONG` is incomplete without a proven plan.

Stage 4 receives:

```text
HISTORICAL ORB_SIGNALs
       +
DECISION-TIME ORB_CONTEXT_SNAPSHOTs
       +
LATER MATURED PRICE-PATH OUTCOMES
```

Research parameter families:

```text
ENTRY
├── breakout close
├── confirmed breach
├── ORH/ORL + buffer
├── first retest
└── confirmed pullback

STOP
├── opposite OR boundary
├── signal candle invalidation
├── swing/structure invalidation
├── ATR based
└── validated hybrid

TARGET
├── fixed R
├── ATR based
├── PDH/PDL
├── CPR/pivot
├── VWAP band
├── next structure/level
└── validated hybrid
```

Also research:

```text
breakout buffer
no-chase distance
minimum RR
volume threshold
VWAP acceptance/veto
entry cutoff
setup expiry
maximum holding time
mandatory flat rule
retest wait window
maximum re-entry count
slippage/cost assumptions
liquidity/spread safeguards
```

Example sensitivity grid:

```text
No-chase: 0.20 ATR / 0.30 ATR / 0.50 ATR
Entry cutoff: 10:00 / 10:30 / 11:00 / 11:30
Retest wait: 1 / 2 / 3 candles
Target: 1.5R / 2R / structure / hybrid
```

Output:

```text
ORB_PARAMETER_SET
│
├── entry rule / entry zone
├── breakout buffer
├── confirmation rule
├── volume requirement
├── VWAP requirement
├── stop rule
├── stop/invalidation semantics
├── target rule
├── target semantics
├── minimum RR
├── no-chase rule
├── entry cutoff
├── setup expiry
├── hold/flat rule
├── retest rule
├── re-entry limit
├── slippage/cost model
├── liquidity constraints
├── expected win/loss probability
├── expected R
├── sample size
├── uncertainty
├── proof dataset/version
└── parameter-set version
```

Promoted parameters are frozen/versioned before runtime. They must not be changed ad hoc using future price movement from the same session.

---

# 22. Stage 5 — Combination Research Data Flow

Stage 5 does not ask only whether a single indicator works. It asks which **combinations and contradictions** materially change ORB outcomes.

Inputs:

```text
ORB_CONTEXT_SNAPSHOT
       +
ORB_SIGNAL
       +
ORB_PARAMETER_SET
       +
MATURED OUTCOME
```

Examples of combination questions:

```text
ORB-15
+
Bullish Engulfing yesterday
+
Narrow CPR
+
Above/accepted daily VWAP
+
BB expanding
+
Moderate bullish gap
+
Nifty bullish
+
Sector bullish
+
Strong volume
        ↓
How did BREAKOUT_LONG perform?
```

Contradiction example:

```text
BREAKOUT_LONG
BUT
previous DAILY bearish rejection
+
wide CPR
+
BB contracting
+
Nifty bearish
+
sector weak
+
weekly resistance nearby
        ↓
How often did the breakout fail?
```

The combination layer should learn:

```text
what materially SUPPORTS ORB
what materially CONTRADICTS ORB
what appears irrelevant/noisy
what works only in a particular regime
what helps retest but hurts direct breakout
what makes ORB-5 noisy but ORB-15 stable
```

Output:

```text
ORB_COMBINATION_EVIDENCE
│
├── combination identity
├── support/contradiction direction
├── signal family
├── context bucket
├── sample count
├── success/failure statistics
├── expectancy
├── uncertainty
├── stability
├── unseen-data proof
└── overfit/sparsity status
```

Low-sample combinations must not become false rules.

---

# 23. Stage 6 — Machine-Learning Dataset and Feature-Store Flow

ML begins only after deterministic snapshot and signal contracts are stable.

Every historical ORB decision becomes an **immutable decision-time feature row**.

Example at 09:40:

```text
DECISION SNAPSHOT — 2025-04-15 09:40

symbol = RELIANCE
ORB_duration = 15
confirmation_tf = 5m
signal = BREAKOUT_LONG
OR_width_ATR = 0.42
previous_daily_pattern = BULLISH_ENGULFING
CPR = NARROW
BB = EXPANDING
VWAP_band_state = ABOVE_PLUS_1
Nifty = BULLISH
Sector = BULLISH
Volume_ratio = 1.65
Gap = +0.55%
selected_parameter_set = ...
entry = 1514
stop = 1505
target = 1532
snapshot_hash = ...
feature_schema_version = ...
```

At 09:40 the feature row must **not** contain:

```text
today's eventual close       ❌
today's future high/low       ❌
future target-hit state       ❌
future stop-hit state         ❌
future MFE/MAE                ❌
post-entry facts not yet known❌
```

Data flow:

```text
DECISION-TIME FEATURE SNAPSHOT
           ↓
          FREEZE
           ↓
wait until configured outcome horizon matures
           ↓
CREATE OUTCOME LABEL SEPARATELY
           ↓
JOIN FOR TRAINING BY IMMUTABLE ID
```

A matured label may contain:

```text
target_before_stop = YES
win/loss/timeout = WIN
realized_R_after_costs = +2.0
MFE = +2.4R
MAE = -0.25R
false_break = NO
retest_success = YES/NA
```

The original 09:40 snapshot must never be mutated after the outcome becomes known.

---

# 24. Stage 7 — Machine-Learning Training, Calibration and Challenger Flow

Inputs:

```text
VERSIONED PIT-SAFE FEATURES
         +
MATURED OUTCOME LABELS
         ↓
CHRONOLOGICAL DATASET
```

ML tasks may estimate:

```text
P(target before stop)
P(false breakout / trap)
P(retest success)
Expected R after costs
P(setup remains valid for horizon)
Most suitable already-researched OR duration / confirmation TF
Best expected risk-adjusted already-proven parameter set
```

ML must also output/retain:

```text
model version
feature schema version
training window
sample size
probability calibration
Brier score
log loss
ROC-AUC / PR-AUC when meaningful
uncertainty
stability by stock/year/regime/signal
drift state
edge-decay state
```

Training flow:

```text
chronological training data
        ↓
train baseline + candidate/challenger
        ↓
validation / hyperparameter selection
        ↓
purged/embargoed validation where horizons overlap
        ↓
walk-forward tests
        ↓
FINAL UNTOUCHED HOLDOUT
        ↓
compare challenger vs champion and deterministic baseline
        ↓
PROMOTE / REJECT / ABSTAIN
```

Never tune hyperparameters on final holdout.

Do not judge ML only by raw classification accuracy. Better raw accuracy with worse probability calibration, expectancy, drawdown, or unseen stability does not automatically qualify for promotion.

---

# 25. Stage 8 — Per-Stock Playbook Promotion Flow

Inputs:

```text
ORB_TIMING_RESEARCH_REPORT
          +
ORB signal-family proof
          +
ORB_PARAMETER_SET proof
          +
ORB_COMBINATION_EVIDENCE
          +
approved ML model/calibration metadata
          ↓
PLAYBOOK PROMOTION GATE
```

Output:

```text
ORB_PLAYBOOK
```

A promoted per-stock playbook should contain conceptually:

```text
symbol = RELIANCE
preferred_OR = 15m
confirmation = 5m close
supported_signals = BREAKOUT_LONG, RETEST_LONG, ...
strong_contexts = ...
weak/no-trade_contexts = ...
false-break/trap behavior = ...
volume requirements = ...
VWAP 3-band rules = ...
CPR rules = ...
previous DAILY candle/pattern rules = ...
BB rules = ...
index/sector alignment = ...
event/derivatives/liquidity vetoes = ...
entry rule = ...
stop rule = ...
target rule = ...
minimum RR = ...
no_chase = ...
entry_cutoff = ...
setup_expiry = ...
reentry_max = ...
hold/flat rule = ...
training range = ...
validation range = ...
holdout range = ...
backtest statistics = ...
ML model/version/calibration = ...
uncertainty = ...
known failure modes = ...
drift status = ...
playbook_version = ...
promotion_status = ACTIVE/REJECTED/SHADOW/etc.
```

The runtime engine reads a frozen promoted playbook. It does not reinvent OR timing or parameters during the current session using future observations.

---

# 26. Stage 9 — Daily Runtime Data Flow

The runtime flow is distinct from research.

```text
D2 / CLOSED-CANDLE MARKET DATA
             │
             ▼
PREVIOUS COMPLETED DAILY SESSION
             │
             ▼
CANONICAL ORB CONTEXT BRAIN
             │
      ┌──────┼─────────────────────────────────┐
      │      │              │                  │
      ▼      ▼              ▼                  ▼
Daily/CPR/  Market &      Structure /        Risk/Event/
BB/VWAP     Index/Sector  Liquidity/Trap      Derivatives
      │      │              │                  │
      └──────┴──────────────┴──────────────────┘
                         │
                         ▼
                 ORB_CONTEXT_SNAPSHOT
                         │
                         +----> ACTIVE ORB_PLAYBOOK
                         │
                         ▼
                 BUILD TODAY'S OR
                         │
                   ORH / ORL LOCK
                         │
                         ▼
                    ORB_SIGNAL
                         │
                         ▼
             SELECT PROMOTED PARAMETERS
                         │
                         ▼
                 ORB_PARAMETER_SET
                         │
                         ▼
               PROMOTED ML INFERENCE
                         │
                         ▼
                ML EVIDENCE / SCORE
                         │
                         ▼
              ORB_EVIDENCE_PACKAGE
                         │
                         ▼
                    AFRE / D6
                         │
                         ▼
             WAIT / WATCH / PAPER-CANDIDATE
```

The daily pipeline must never call research code in a manner that leaks same-day future outcomes back into current decisions.

---

# 27. ORB Evidence Package Contract

Before AFRE/D6, all ORB-related evidence should be assembled into one traceable package:

```text
ORB_EVIDENCE_PACKAGE
│
├── identity
│   ├── symbol
│   ├── session
│   ├── decision timestamp
│   ├── source snapshot hash
│   └── package version/hash
│
├── canonical context
│   ├── previous DAILY candle/pattern
│   ├── CPR / PDH / PDL / PDC
│   ├── BB state
│   ├── daily/weekly VWAP ±1/±2/±3
│   ├── ATR / volatility
│   ├── volume
│   ├── index / sector
│   ├── structure / liquidity / traps
│   ├── events / derivatives
│   └── quality / availability
│
├── ORB_SIGNAL
│   ├── signal family / direction
│   ├── ORH / ORL
│   ├── OR duration / confirmation TF
│   ├── trigger / confirmation
│   ├── volume / VWAP confirmation
│   ├── retest/trap evidence
│   └── signal freshness/invalidation
│
├── ORB_PARAMETER_SET
│   ├── entry
│   ├── stop
│   ├── target
│   ├── RR
│   ├── no-chase
│   ├── cutoff / expiry
│   ├── re-entry
│   └── costs/liquidity assumptions
│
├── deterministic research evidence
│   ├── sample count
│   ├── win/loss statistics
│   ├── expected R
│   ├── drawdown
│   ├── false-break / retest statistics
│   ├── unseen-data performance
│   └── stability / uncertainty
│
├── combination evidence
│   ├── historical supporting contexts
│   ├── historical contradicting contexts
│   └── sparsity/overfit flags
│
├── ML evidence
│   ├── calibrated P(success)
│   ├── P(false break)
│   ├── P(retest success)
│   ├── expected R
│   ├── uncertainty
│   ├── calibration state
│   ├── model version
│   └── drift/edge-decay state
│
├── reasons FOR
├── reasons AGAINST
├── hard blockers / unavailable inputs
└── PIT / causality proof
```

This package is evidence, not an order.

---

# 28. AFRE/D6 Consumption and Authority Flow

AFRE/D6 must receive the ORB package alongside its other canonical evidence.

Example:

```text
ORB_SIGNAL:
BREAKOUT_LONG

Trade plan candidate:
Entry 1514
Stop 1504
Target 1534

Deterministic ORB research:
ORB-15 / 5m confirmation historically strong in comparable promoted contexts

ML evidence:
P(success) = 0.68
Expected R = +0.46R
calibration = valid
uncertainty = ...

Previous day:
Bullish Engulfing
Narrow CPR
BB expansion
VWAP positive

Current context:
Index bullish
Volume strong
```

But AFRE/D6 can simultaneously receive contradiction:

```text
Weekly resistance = VERY CLOSE
Event risk = MEDIUM
Trap evidence = elevated
Sector = slightly weak
```

Therefore the reasoning structure is:

```text
FOR
├── ORB breakout
├── volume
├── previous DAILY evidence
├── CPR
├── VWAP
├── BB
├── index alignment
├── deterministic historical proof
└── calibrated ML evidence

AGAINST
├── nearby resistance
├── sector conflict
├── trap risk
├── event risk
└── any other stronger canonical contradiction
```

Then D6 retains final authority to return only the permitted guidance band:

```text
WAIT
WATCH
PAPER-CANDIDATE
```

A 68% ML probability does **not** mean `BUY`. An ORB breakout does **not** mean `BUY`. An attractive trade parameter set does **not** mean `BUY`. They are evidence inputs to final deliberation.

---

# 29. After-the-Outcome Learning Flow

After the configured session/trade horizon is complete, the system may learn from the result.

Example original decision:

```text
09:40
ORB_SIGNAL = BREAKOUT_LONG
ML P(success) = 0.68
ORB evidence package hash = X
```

Later, after the label is mature:

```text
target_before_stop = YES
realized_R = +2.0R
```

The system stores:

```text
ORIGINAL IMMUTABLE DECISION SNAPSHOT
              +
SEPARATE MATURED OUTCOME LABEL
```

It must not rewrite the original feature snapshot with information learned later.

Controlled future-learning loop:

```text
NEW MATURED OUTCOMES
        ↓
rolling calibration / expectancy statistics
        ↓
drift / edge-decay / regime-shift detection
        ↓
enough new evidence to retrain?
       / \
     NO   YES
     │     │
keep      train challenger
champion       │
               ▼
        walk-forward + holdout proof
               │
          ┌────┴────┐
          │         │
        WORSE     BETTER
          │         │
        REJECT    eligible for promotion
          │         │
          └────┬────┘
               ▼
     champion / rollback registry
```

Promotion requires material unseen-data improvement without degraded safety, calibration, expectancy, or stability. If evidence is insufficient, the system keeps the previous champion or abstains.

---

# 30. Which Data Is Allowed to Flow Where

## 30.1 Allowed forward flow

```text
Raw closed market facts
        ↓
canonical calculations
        ↓
context snapshot
        ↓
ORB research / signal
        ↓
parameter research/selection
        ↓
combination evidence
        ↓
ML feature representation / inference
        ↓
ORB evidence package
        ↓
AFRE/D6
```

## 30.2 Matured outcome flow

Matured future outcomes may flow only into **research/evaluation/training after the outcome horizon completes**:

```text
matured outcome
   ├──> backtest statistics
   ├──> timing research
   ├──> parameter research
   ├──> combination research
   ├──> ML labels
   ├──> calibration monitoring
   └──> challenger evaluation
```

Matured outcomes may never flow backward into an earlier decision-time feature snapshot.

## 30.3 Forbidden flow

```text
future candle → current signal                  ❌
end-of-day high/low → 09:40 feature             ❌
future target hit → current ML input             ❌
future stop hit → current trade parameters       ❌
holdout results → hyperparameter tuning          ❌
ML score → bypass hard safety gates              ❌
ORB signal → broker order                        ❌
parameter engine → execution authority           ❌
AFRE sub-engine → overwrite D1/D2 causality      ❌
missing value → neutral/zero fabrication         ❌
```

---

# 31. Canonical Short-Form Architecture

The complete intended runtime architecture can be summarized as:

```text
RAW MARKET DATA
      ↓
PREVIOUS-DAY + CURRENT MARKET CONTEXT
      ↓
PER-STOCK ORB RESEARCH / ACTIVE PLAYBOOK
      ↓
BEST PROVEN OR TIME + CONFIRMATION TF
      ↓
LOCK TODAY'S ORH / ORL
      ↓
EXPLICIT ORB SIGNAL
      ↓
PROVEN ENTRY / STOP / TARGET PARAMETERS
      ↓
ML PROBABILITY + EXPECTED R + UNCERTAINTY
      ↓
FULL ORB EVIDENCE PACKAGE
      ↓
AFRE REASONING
      ↓
D6 FINAL ARBITRATION
      ↓
WAIT / WATCH / PAPER-CANDIDATE
      ↓
LATER MATURED OUTCOME
      ↓
CALIBRATION / DRIFT / CHALLENGER LEARNING
      ↓
FUTURE MODEL / PLAYBOOK IMPROVEMENT
```

The governing architecture law for this ORB build is:

> **RAW FACT CALCULATED ONCE → MANY BRAINS INTERPRET → EVERY INTERPRETATION TRACEABLE.**

For ORB specifically:

> **Raw facts are canonical → context describes the market → research discovers what has proof → ORB produces an explicit signal → the parameter engine produces a proof-backed trade-plan candidate → ML estimates calibrated outcome probabilities → AFRE weighs support and contradiction → D6 retains final authority.**

---

# 32. Inter-Stage Contract Audit

Future implementation must verify these data handoffs one by one:

| Flow ID | Producer | Consumer | Required payload | Forbidden contamination |
|---|---|---|---|---|
| F01 | Raw market-data adapter | Canonical context | closed PIT-safe OHLCV + provenance | incomplete/future candles |
| F02 | Previous-session aggregator | Context Brain | completed DAILY OHLCV | last intraday candle masquerading as daily |
| F03 | Canonical indicators/structure | Context Brain | CPR, BB, VWAP bands, ATR, structure, quality | duplicate inconsistent recalculation |
| F04 | Context Brain | Timing Research | immutable historical context snapshots | future outcomes inside features |
| F05 | Closed bars + playbook | Signal Engine | locked OR + confirmation bars | incomplete-bar authority |
| F06 | Signal Engine | Parameter Selection | deterministic `ORB_SIGNAL` | final-trade authority |
| F07 | Historical signals/context | Parameter Research | signal/context + later matured outcomes | same-session future leakage into decision inputs |
| F08 | Context + signal + parameters | Combination Research | versioned identities + matured outcomes | sparse-combination false certainty |
| F09 | Decision snapshot | ML Feature Store | only decision-time features | future/post-entry facts |
| F10 | Matured outcome builder | ML Label Store | labels after horizon completion | immature labels |
| F11 | Feature/label store | ML Trainer | chronological versioned dataset | holdout leakage |
| F12 | ML Trainer | Model Registry | model + calibration + uncertainty + proof | unproven model promotion |
| F13 | Research stages | Playbook Promotion | timing + signal + parameters + combinations + approved ML metadata | in-sample-only promotion |
| F14 | Playbook + current context | Runtime Signal/Parameters | frozen promoted rules | ad-hoc future-aware rule mutation |
| F15 | ML Runtime | ORB Evidence Package | calibrated probabilities/expected R/uncertainty | deterministic-signal override |
| F16 | ORB subsystem | AFRE/D6 | complete evidence package with FOR/AGAINST | order-routing authority |
| F17 | AFRE/D6 | Guidance | final evidence arbitration | ORB/ML bypass of D6 |
| F18 | Completed horizon | Learning loop | immutable snapshot + matured outcome | rewriting original snapshot |

A future implementation is incomplete if any one of these handoffs is implicit, unversioned, unhashable, non-replayable, or able to smuggle future information into an earlier decision.
