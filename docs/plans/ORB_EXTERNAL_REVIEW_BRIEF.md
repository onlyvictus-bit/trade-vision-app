# ORB System — External Review Brief (for an independent AI reviewer)

> Purpose: you are asked to REVIEW this trading-research system and its upgrade
> plan, not to trade. Everything below is verifiable from the repo
> (`trade-vision-app/`). Flag anything you cannot verify instead of guessing.

## 1. What this is (30 seconds)

An NSE (India) Opening Range Breakout research system. It reads years of
5-minute candles, finds which opening-range settings made money, proves
winners on unseen data, stores the proven recipe ("playbook"), and shows a
daily guidance ticket (WAIT / WATCH / PAPER-CANDIDATE). **Research-only:
no live trading exists anywhere; human approval is required for paper trades.**

## 2. What is built and proven (numbers, not adjectives)

- Engine: signal spotter → history tester (72 combos/stock) → walk-forward
  exam (75/25 split + 4 folds) → playbook store → daily guidance → paper
  ledger → reliability memory. Full test suite: **914 passed, 0 failed**
  (v2.02-derivatives, 2026-09-07; includes derivatives 22/22 OFF-by-default,
  v2.01 scenarios 8).
- One live result: **BEL, 09:15–09:20 window, +60.2R, profit factor 1.30,
  515 trades, 70% of months positive**; holdout (unseen) PF 1.27, +12.08R;
  walk-forward 4/4 folds passed (PF 1.13–1.44). Promoted to playbook `a1c78a28`.
- Honest negatives we publish: a day-type predictor built from gap/CPR rules
  scored precision 0.30 = exactly chance (killed, not shipped); a gap/CPR
  pre-test over 11,043 trades returned NO_GO on all hypotheses.
- 49 of 94 indicators compute live; 6 future-leaking indicators are
  permanently explanation-only; all API routes report research-only status.

## 3. How a decision is made (the flow)

```text
price files → 9 safety checks (bad data → WAIT) → snapshot + fingerprint
→ spot today's setup → 49 indicator votes (lag-weighted, family-capped)
→ memory (what worked before) → advisory reviews (display-only)
→ arbiter (reduce-only final band) → ticket: WAIT/WATCH/PAPER-CANDIDATE
→ HUMAN approves → paper record → outcome feeds memory
```

Key safety properties: kill switch; closed-candle-only; no future data
(PIT); costs + slippage in every backtest; stop-first on same-bar ties;
deterministic hashes on every artifact.

## 4. What is proposed next (v2 upgrade, NOT built)

Wire market context into the engine: gap direction/size, CPR width class,
position vs previous-day high/low, plus traps, event calendar, universe
hygiene, VIX regime, expiry protocol, afternoon session, exit simulator
(book half at 1R, trails), capital-risk sizing, daily loss cap.
Rules (~100) live in `docs/plans/ORB_STRATEGY_MEMORANDUM.md` v2.4;
milestones M0–M6 in `docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md` (§11–§15).
Staged adoption: pre-test first → HSTRY-computable rules → full core only
for proven layers → external feeds last. Thresholds are priors for the
discovery grid to calibrate, never hardcoded constants.

## 5. Questions for you (answer each with a verdict)

1. **Correctness:** recompute any 3 worked numbers you choose from §8 of the
   memorandum. Do they hold? Show your arithmetic.
2. **Missed edge cases:** name up to 5 market situations (gaps, halts,
   circuits, expiries, corporate actions) where these rules break or go silent.
3. **Threshold sanity:** which 3 thresholds look most miscalibrated for NSE
   large-caps, and what would you set as the prior instead (with reasoning)?
4. **Danger ranking:** rank the top 5 ways this system could lose money or
   mislead, assuming all code is correct.
5. **The stopping rule:** what single measured result would make you say
   "do not build M2/M3"?

## 6. Rules for your review

- Verify, don't trust: every claim above traces to repo code/tests; if you
  can't verify something, label it UNVERIFIED rather than assuming.
- Never invent thresholds, statistics, or market facts; cite a source or
  mark as your prior.
- Where two of our documents disagree, quote both and pick the safer reading.
- End with: (a) verdict per question, (b) anything we got wrong with proof,
  (c) anything important we missed, (d) what we already have right.
