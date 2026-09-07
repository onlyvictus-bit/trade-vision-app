# ORB Gap-Morning Trading — External AI Review Brief

> **What this file is:** a complete, self-contained briefing for an outside AI
> reviewer. It describes what is built, what is not, how the system works,
> and exactly what guidance is wanted. No repo access needed.
> **Date:** 2026-09-04 · **System state:** v2.02-derivatives (914/914 tests green, 2026-09-07; OFF-by-default derivatives dormant; v2.01 classifier standalone)

---

## 1. The system in 60 seconds

Trade Vision is a **research-only** stock-market analysis system (Indian NSE
stocks, 5-minute candles). It studies Opening Range Breakout (ORB): the first
minutes of the day set a high/low range, and a close beyond it can signal a
trade. The system backtests strategies on history, proves winners on unseen
data, stores proven recipes ("playbooks"), and shows daily advice tickets
(WAIT / WATCH / PAPER-CANDIDATE). **It never trades, routes orders, or touches
a broker. A human approves every paper trade.**

Stack: Python FastAPI backend (`apps/api/app/`), React frontend, SQLite,
pandas/numpy/scipy. Data: local CSV history (~90 NSE stocks × 7 timeframes,
2015→present, 5-minute bars with open/high/low/close/volume).

## 2. What is BUILT and verified (do not redesign these)

| # | Piece | What it does | Proof |
|---|---|---|---|
| 1 | Market-data loader | Reads CSVs, fixes IST timezone, filters to session 09:15–15:30, rejects bad data | 10 test gates |
| 2 | Safety gate (D1) | 9 checks (mode, kill switch, symbol match, bar-count bound, finite values, quality ≥ 0.85, closed candles, no broker) → fail means WAIT | 9/9 pass on real data |
| 3 | ORB signal engine | Locks opening range, detects 5m-close breakouts/reversals, computes entry/stop/target with costs | 12 tests |
| 4 | Discovery engine | Tests every combination (strategy × window × risk-reward × volume) on every past day, ranks by profit + monthly consistency | 12 tests |
| 5 | Proof engine | 75/25 train-holdout split + 4 walk-forward folds; only passed proofs can become playbooks | 12 tests |
| 6 | Timing research | Per-stock study of which opening window wins (09:20/09:30/09:35/09:40) | 10 tests |
| 7 | Opening classifier | Labels every session: gap state (FLAT/UP/DOWN/LARGE) + CPR width class (NARROW/NORMAL/WIDE) + price zone (Z1–Z5) | 8 tests incl. 1611-session real-data proof |
| 8 | Day-type predictor | Opening combination → TREND / RANGE / UNCLASSIFIED guess | 2 tests |
| 9 | Indicator library | 49 of 94 indicators compute live (trend, momentum, volume, volatility, CPR, pivots, patterns) | 9 catalog gates |
| 10 | Paper loop | Human-approved paper trades tracked bar-by-bar → win/loss + reliability memory | full suite green |

**Full backend suite: 914 passed / 0 failed (v2.02-derivatives, 2026-09-07).** Key formulas: gap FLAT < 0.1%,
LARGE ≥ max(1.0%, 1.4×ATR%); CPR narrow < 0.5×ATR; R = |entry − stop|;
lag_weight = 1/(1+delay); costs = commission + slippage, stop-first on ties.

## 3. Measured evidence (treat as ground truth, not opinion)

- **BEL, 09:15–09:20 window:** backtest +60.2R, PF 1.30, 515 trades, 70% months
  positive → walk-forward proof: holdout (138 unseen days) PF 1.271, +12.08R,
  4/4 folds passed → **promoted to the one live playbook.** Real edge.
- **TCS/VEDL/TATAPOWER:** same windows breakeven-to-negative. No playbook.
- **Gap/CPR layer test (11,043 trades, 5 symbols):** breakout-on-NARROW vs WIDE
  p=0.455 (NO difference); gap-aligned vs counter-gap p=0.522 (NO difference).
  WIDE regime nearly absent (115 vs 5661 days).
- **Day-type predictor test (2,685 sessions):** TREND precision 0.30 (=
  chance), RANGE precision 0.248 (< chance 0.271). Opening combination alone,
  at current thresholds, adds no edge.
- **Structural fact:** median CPR-width/ATR = 0.147 — CPR width is almost
  always NARROW, so "NARROW→trend" fires 84% of days and means little.

## 4. What is NOT built (do not assume these exist)

Gap/CPR/zone awareness **inside** the live signal engine · PDH/PDL breakout
family · exit simulator (book half at 1R, trails) · capital-risk sizing ·
daily loss cap · regime filter · re-entry rules · any external feed (no VIX,
no GIFT Nifty, no futures, no options chain, no news — anything needing these
cannot work today) · live trading (forbidden by design, forever).

## 5. THE FOCUS — read carefully, reviewer

**The trader trades ONLY gap-up or gap-down stocks, ONLY in the first
30–60 minutes after market open (09:15 IST), intraday only. CPR is used as a
second confirming vote, not the system.**

Constrain ALL guidance to this game:
- Universe: gap days only (|gap| ≥ 0.1%; LARGE ≥ max(1.0%, 1.4×ATR%) special).
- Window: entries 09:15–10:15 only. Nothing after. No afternoon trades.
- Families: gap-direction breakouts + gap-fill fades only.
- CPR role: confirmation vote (NARROW supports breakout, WIDE supports fade
  or skip) — never a standalone entry trigger.
- Exits: fixed 1R/2R targets + 15:10 hard flat (intraday, no overnight).
- Costs always applied; stop-first on same-bar ties; max 1 position/day.

## 6. What we want from you (and what we don't)

**Wanted — concrete, numbered suggestions for THIS game only:**
1. Entry timing inside the first hour (first-break vs retest vs second-close?)
2. Filters that kill bad gap mornings (volume? first-bar anomalies? gap size bands?)
3. How to use the CPR vote sharply (which CPR states actually confirm a gap trade?)
4. Gap-fill vs gap-and-go: how to tell them apart BEFORE 09:45?
5. Position sizing for gap days (fixed risk %? smaller on LARGE gaps?)
6. What to measure to prove each suggestion (metric + minimum sample).

**Not wanted:** live-trading code, broker integration, new indicators,
redesign of the proven pipeline, options/derivatives strategies, thresholds
stated as facts (give ranges to calibrate), anything needing VIX/GIFT/futures
feeds (they don't exist — say so if your idea needs them).

**Rules for your answer:** research-only framing (no live-trade instructions);
every suggestion must name which existing module it touches (loader, signal
engine, discovery grid, proof thresholds, or guidance display); flag any
suggestion needing data we don't have; keep the 1-trade-per-day discipline.

---

## 7. COPY-PASTE PROMPT (give this + the whole file above to the AI)

```text
You are reviewing a research-only stock-trading analysis system. Read the
brief above completely before answering. The trader trades ONLY gap-up or
gap-down NSE stocks in the FIRST 30-60 MINUTES after 09:15 IST open,
intraday only, max 1 position/day, with CPR as a confirming vote.

Measured facts you must respect: gap/CPR layers showed NO edge across all
trades (p=0.45-0.52); CPR is NARROW 97% of days; one proven edge exists
(BEL 09:15-09:20, holdout PF 1.27, walk-forward 4/4). Do not contradict
these measurements - build on them.

Give me numbered, concrete improvements ONLY for this gap-morning game:
(1) entry timing inside the first hour, (2) filters that kill bad gap
mornings, (3) sharp CPR-vote rules, (4) telling gap-fill from gap-and-go
before 09:45, (5) gap-day position sizing, (6) what to measure to prove
each suggestion (metric + minimum sample).

Constraints: research-only framing, no live-trading instructions; every
suggestion names which module it touches; flag anything needing data beyond
daily+5-minute OHLCV (no VIX/GIFT/futures/options feeds exist); thresholds
as calibratable ranges, never facts; keep 1-trade-per-day.
```
