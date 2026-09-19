# ORB Research Engine Plan

> **Status:** Approved ORB-first paper-guidance campaign; implementation starts after v1.88 snapshot spine  
> **Date:** 2026-07-24  
> **Owner need:** Backtest stocks to find **which ORB strategy**, **timeframe**, **ORB candle count / clock window**, and **ORB combination** is best by **profit** and **most repeated success**  
> **Placement principle:** **split by use case** — not “everything in one folder.”  
> **Discovery home:** Stock App `research/` (+ ORR indicators)  
> **Truth home:** Stock App `validation/` (OOS / WF / CPCV stress on top-K)  
> **Playbook home:** frozen ranked results store (`research.db` / playbook table)  
> **Decision home:** Paper-guidance spine / Jarvis (ORB is the **primary setup candidate**; arbiter remains final authority)  
> **Execution home:** sim paper after human approve — never ORB job auto-trade  
> **Relation:** Does **not** replace FINAL_REQUIRED_FLOW Phase 0–2.

---

## Approved Trade Vision Version Mapping

| Trade Vision version | ORB phase | Purpose |
|---|---|---|
| **v1.88** | Spine prerequisite | Snapshot-bound guidance and sole-arbiter enforcement |
| **v1.89** | **ORB-0/1** | Contracts, NSE session lock, ORB/ORR/hybrid strategy builders |
| **v1.90** | **ORB-2** | Offline combination discovery with costs and async jobs |
| **v1.91** | **ORB-3** | OOS/WF/consistency proof and playbook promotion |
| **v1.92** | **ORB-4/5** | Jarvis ORB main action, chart/ticket UI, read-only playbook bridge |
| **v1.93** | Paper record | Human-approved simulated fill linked to guidance/playbook |
| **v1.94** | Feedback/hardening | Outcome memory, lifecycle review, monitoring and release proof |

The earlier references to an unnumbered or `v1.1` ORB-5 bridge are superseded by
**Trade Vision v1.92**. Historical review notes may retain the old label, but
implementation and status tables must use the mapping above.

Authority rule:

```text
ORB = primary setup generator
D6 arbiter = only final-band authority
human approval = only paper-record trigger
live broker/OpenAlgo routing = out of scope
```

---

## 0. High-reasoning placement (purpose → best place)

A single “put ORB only in research/orb” sketch is **too thin**.  
ORB is not one feature; it is **four jobs** with different quality needs. Putting all four in one place makes a bad product.

### 0.1 Purposes (what ORB must deliver)

| Purpose ID | Purpose | Nature |
|------------|---------|--------|
| **P-DISCOVER** | Search huge combo space (strategy × TF × orb length × filters × R:R) | Offline, heavy, many trials |
| **P-PROVE** | Prove winner is not a lucky curve (OOS, WF, costs, consistency) | Offline, rigorous, fewer candidates |
| **P-PLAYBOOK** | Store “for symbol X, run ORB with these params” as a stable recipe | Persistent config/results |
| **P-DECIDE** | At decision time: is today’s setup aligned with a proven playbook? | Online, fast, one snapshot |
| **P-PAPER** | If guidance says enter: book paper and measure real sim outcome | Explicit human approve |
| **P-LIVE** | Real broker | **Out of scope** until separate safety program |

### 0.2 Candidate homes (honest fit)

| Place | Strengths | Weaknesses for ORB |
|-------|-----------|---------------------|
| **`research/` VectorBT discovery** | Built for combo explosion, scoring, jobs, `research.db` | Not the deepest anti-overfit layer by itself |
| **`server.py` Backtrader ORR** | Already has ORR/hybrid, cost model path | Slow for 10k+ combos; fixed-strategy mindset |
| **`validation/` purged WF / CPCV** | Best for “repeated success is real?” | Too heavy to run on full raw grid first |
| **TV `behavior/*` engines** | Best for closed-bar decision evidence, arbiter, safety | Wrong place for multi-hour grid search |
| **Paper-guidance spine** | Best for one-touch WAIT/ENTER_PAPER | Must stay fast; must not run full ORB sweep on click |
| **Chart `self_indc` only** | Good signal geometry | No ranking/research product |
| **OpenAlgo** | Execution boundary later | Not for discovery |

### 0.3 Best place per use case (decision table)

| Use case (what user wants) | Best place | Why it fits | What must NOT go there |
|----------------------------|------------|-------------|-------------------------|
| **U1.** “Which TF + orb candles + strategy is best historically?” | **`research/orb` sweep** on VectorBT stack | This is combinatorial discovery; research runner already does combos → backtest → rank | TV arbiter, paper click path |
| **U2.** “Is that winner repeatedly successful or overfit?” | **`validation/` + research OOS** on **top-K only** | WF/CPCV/consistency are truth filters, not search engines | Running CPCV on every raw combo |
| **U3.** “Save the recipe for RELIANCE 5m OR=6 bars” | **`research.db` playbook table** (or job artifact store) | Durable, queryable, versioned params + metrics | Hard-coding winners in UI only |
| **U4.** “Before open / at 10:00, should I take this ORB today?” | **Paper-guidance spine / Jarvis evidence** reading **frozen playbook** + today’s OR levels | Decision needs one snapshot + playbook match, not a re-sweep | Re-running full grid every touch |
| **U5.** “Show OR box on chart” | **Stock App chart + `self_indc` ORR/ORB markers** | Visual only | Ranking logic |
| **U6.** “Paper trade the setup” | **Sim API → `sim_trading.db`** after **human approve** from guidance | Real paper ledger already exists | ORB job auto-submit trades |
| **U7.** “Deep single-config audit with exchange-style costs” | **Backtrader path** (`server.py` strategies) as optional second pass | Good for 1–20 finalists, not 50k grid | First-stage mass search |
| **U8.** Live broker | **Neither product today** | Safety | Entire ORB research |

### 0.4 Recommended architecture (multi-layer — best overall idea)

```text
LAYER A — DISCOVER (Stock App research)
  research/orb + engine/backtester + scorer
  Purpose: answer U1 (best combo search)
  Cadence: nightly / on-demand job (minutes–hours)

LAYER B — PROVE (Stock App validation)
  oos_split / walk_forward / cost_stress / consistency
  Purpose: answer U2 (repeated success is real)
  Cadence: after A produces top-K (e.g. top 20)

LAYER C — PLAYBOOK (store)
  research.db orb_playbooks
  Purpose: answer U3 (stable recipe per symbol/regime)
  Cadence: promote only PROVE-passed combos

LAYER D — DECIDE (Trade Vision paper-guidance spine)
  final arbiter + optional “ORB playbook match” evidence vote
  Purpose: answer U4 (do I take it now?)
  Cadence: per operator click / session

LAYER E — PAPER (Stock App sim)
  /api/sim/* → sim_trading.db
  Purpose: answer U6 (practice fill + result)
  Cadence: only after human approve on D

LAYER F — CHART (optional visual)
  self_indc OR geometry on index.html
  Purpose: answer U5 (see the range)
```

```text
   [Job: Discover]                [Job: Prove]              [Store]
   research/orb sweep  ──top-K──► validation/OOS/WF ──pass──► playbook row
                                                              │
                         operator click                       │
                              │                               ▼
                              └────────► guidance spine ◄── read playbook
                                              │
                                         human approve
                                              │
                                              ▼
                                         sim paper fill
```

### 0.5 Why “only research/orb” was incomplete

| If you only put ORB in… | What breaks |
|-------------------------|-------------|
| Only `research/` | Users may trust max profit without **prove** layer |
| Only Backtrader | Cannot efficiently find best TF/bars among thousands of combos |
| Only TV behavior | Slow, wrong lifecycle, safety confusion, mixes research with decision |
| Only paper spine | Touch becomes multi-hour job; ruins one-touch UX |
| Only chart indicator | No answer to “which combo is best / repeated success” |

**Best idea:** **pipeline of places**, each owns one purpose.  
Discovery ≠ proof ≠ decision ≠ paper.

### 0.6 What “fullfills required purpose” maps to

| Required purpose (your words) | Fulfilled by layer |
|------------------------------|--------------------|
| Which ORB strategy | A Discover |
| Which timeframe | A Discover |
| ORB candle count / which time to run | A Discover (`orb_bars` or clock window + entry window) |
| Which combination is best | A Discover + **B Prove** (final “best” only after prove) |
| Profit | A metrics + B cost-stressed metrics |
| Most repeated success | **B Prove** (consistency / multi-period / OOS) — not A alone |
| Use for trading decision | **D Decide** (playbook match), not re-sweep |
| Paper practice | **E Paper** after approve |

### 0.7 Simple operator journeys (best path)

**Journey R — Researcher (“find the best ORB”)**  
`research UI/job → Layer A → Layer B → Layer C report`  
Stop. No paper required.

**Journey T — Trader morning (“should I take ORB today?”)**  
`chart (F) → guidance (D) reads playbook (C) → WAIT/ENTER_PAPER → approve → sim (E)`  
Does **not** re-run Layer A on click.

**Journey A — Analyst audit (“is this winner real?”)**  
`pick top combo → Layer B deep WF/CPCV → optional Backtrader (U7)`  

### 0.8 ORB vs Kronos, Vision, and other think engines (AI reference)

This section is the **authority answer** for:  
*In which flow is ORB present, and how does it affect or influence Kronos / Vision / other think engines?*

#### 0.8.1 One-sentence truth

```text
ORB lives in the offline research → prove → playbook flow (Stock App).
Kronos and Trade Vision think engines live in the online decide-now flow.
ORB should influence Vision only as an optional, weak evidence vote (proven playbook match).
ORB does not run inside Kronos; Kronos is not an ORB param searcher.
ORB never auto-paper or auto-live; paper only after human approve on guidance.
```

#### 0.8.2 What is present in which flow

| Brain | Product | Flow it lives in | Role |
|-------|---------|------------------|------|
| **ORB lab** (planned) | Stock App `research/orb` | **Discover → Prove → Playbook** (offline jobs) | Find best strategy/TF/orb length/combo |
| **ORR / hybrid OR** (present) | Stock App indicators + backtest | Chart + single strategy backtest | Geometry / one fixed strategy |
| **Trade Vision think engines** (v1.70–75, MTF, reliability…) | TV `behavior/*` | **Decide now** (per click / snapshot) | Evidence for WAIT/WATCH/PAPER-CANDIDATE |
| **Jarvis** | TV | Operator desk assembly | Merge evidence + blockers + AI review |
| **Final confluence arbiter** | TV | Decision boss | Reduce-only final band |
| **Kronos + twin arbiter** | TV + `kronos-service` | Research twin on **same OHLCV snapshot** | Forecast prior; cannot override NO_TRADE |
| **TrendForge** | TV intake | Research evidence packet | Scanner evidence only |
| **External AI (Gemini/Grok)** | TV | Display review | Cannot override risk |
| **Paper sim** | Stock App | After human approve | Fills in `sim_trading.db` |

#### 0.8.3 Flow map (ORB offline vs Vision/Kronos online)

```text
                    OFFLINE / SLOW                         ONLINE / FAST
        ─────────────────────────────────        ─────────────────────────────

        ORB DISCOVER (research/orb) ★
        ORB PROVE (validation/OOS)
        ORB PLAYBOOK (research.db)
                 │
                 │  optional promote as evidence
                 ▼
        ┌────────────────────────────────────────────────────────┐
        │  TRADE VISION DECIDE FLOW (one snapshot)               │
        │                                                        │
        │  chart/structure/regime/risk engines (v1.70–74)        │
        │  indicator lag/reliability                             │
        │  [ORB playbook match]  ← only if wired later           │
        │  Kronos twin (optional research)                       │
        │  TrendForge / AI review (optional)                     │
        │           │                                            │
        │           ▼                                            │
        │  Final confluence arbiter (boss)                       │
        │           │                                            │
        │           ▼                                            │
        │  WAIT / WATCH / PAPER-CANDIDATE                        │
        │           │                                            │
        │           ▼ human approve                              │
        │  Stock App sim paper                                   │
        └────────────────────────────────────────────────────────┘

        ★ ORB full grid search does NOT run inside the online box
```

**Today (honest):**

- ORB **lab** is mostly **not built** (ORR signals exist).  
- Kronos / Vision engines **do not call** ORB sweep.  
- ORB **does not currently drive** Kronos or the arbiter.  
- Intended coupling is **playbook → optional evidence only**.

#### 0.8.4 Three flows (do not mix)

**Flow A — ORB research (where ORB *is*)**

```text
Job → research/orb discover → prove top-K → playbook in DB → report
Affects other engines: NONE until playbook is exported/wired
```

**Flow B — Vision decide (where Kronos / think engines *are*)**

```text
Snapshot → v1.70–74 + indicators + (optional ORB playbook) + optional Kronos
        → arbiter → WAIT/WATCH/PAPER-CANDIDATE
ORB influence: only if playbook vote is wired; weight limited
```

**Flow C — Paper**

```text
Guidance ENTER + human approve → sim fill
ORB influence: none direct; only via guidance that used playbook evidence
```

#### 0.8.5 How ORB should influence other engines (designed)

| Direction | Influence? | How |
|-----------|------------|-----|
| **ORB → Vision engines** | **Optional, later** | Playbook match score = **one evidence vote** (setup quality), family-capped |
| **ORB → Final arbiter** | **Indirect only** | Via that evidence vote; arbiter remains reduce-only boss |
| **ORB → Jarvis** | **Display + package** | Show “ORB playbook #1: 5m / 6 bars / breakout” on desk |
| **ORB → Kronos** | **No** (default) | Kronos = path forecast on OHLCV, not ORB grid search |
| **ORB → Twin arbiter** | **No direct** | Twin = Behavior vs Kronos; ORB is not a third twin by default |
| **ORB → TrendForge** | **No** | Separate scanner intake |
| **ORB → Gemini/Grok** | **No authority** | May explain ORB in narrative; cannot change band |
| **ORB → Paper sim** | **No auto** | Only if guidance says ENTER and **human approves** |
| **Vision engines → ORB** | **Light optional** | e.g. discover ORB only in certain regimes (filter during Discover) |
| **Kronos → ORB** | **Optional research filter** | e.g. prove-stage discard combos that fight strong path risk — advanced, not v1 required |

#### 0.8.6 Influence matrix

| Source | Affects Vision engines? | Affects Kronos? | Affects arbiter? | Affects paper? |
|--------|-------------------------|-----------------|------------------|----------------|
| **ORB discover job** | No (offline) | No | No | No |
| **ORB playbook (stored)** | Yes **if wired** as evidence | No (default) | Yes **indirectly** (one vote) | Only via guidance + approve |
| **ORR on chart now** | Visual / optional indicator vote | No | Only if in indicator score | No auto |
| **Kronos** | Can reduce confidence | — | Yes (reduce) | No auto |
| **Vision structure/risk** | — | No | Yes (strong) | Via guidance |

#### 0.8.7 Hierarchy if ORB is connected (who wins)

```text
HARD BOSSES (always win over ORB)
  kill switch, PIT/data quality, live_trading_blocked
  liquidity C / hard risk blocks
       │
       ▼
SOFT BOSSES
  final confluence arbiter (reduce-only)
       │
       ├── structure / regime / risk engines
       ├── indicator reliability (lag-aware)
       ├── ORB playbook match   ← ORB’s only normal seat
       ├── Kronos twin (research prior; can reduce confidence)
       └── external AI (display only; weight ~0 for promotion)
       │
       ▼
  WAIT / WATCH / PAPER-CANDIDATE
```

**Even a historically best ORB combo cannot:**

- force ENTER_PAPER through risk/liquidity block  
- override NO_TRADE / kill switch  
- outvote structure+risk by stacking many ORB clones  
- force Kronos “agreement”  
- auto-submit paper or live orders  

#### 0.8.8 What each brain is for (ORB must not steal their job)

| Engine | Job | ORB’s relationship |
|--------|-----|--------------------|
| **ORB discover** | Historical combo search | Source of **playbook**, not live decision |
| **ORB prove** | Repeated success truth | Filters fake ORB winners |
| **Chart reasoning v1.70** | Candle/vol shape now | Independent; may agree/disagree with “ORB day type” |
| **Structure v1.72** | Levels/liquidity geometry | Stronger than raw ORB breakout hype |
| **Regime v1.71** | Market context | Can **cap** ORB promotion (e.g. chop) |
| **Exec/OI risk v1.73** | Fill/event risk | Can **block** ORB entry even if playbook green |
| **Indicator lag vote** | Many si_*/pta_* | ORR markers may sit here; full ORB lab does not run here |
| **Reliability memory** | Did this signal work before? | Can score ORB playbook outcomes if logged |
| **Kronos** | Future path scenarios on same bars | Parallel research prior; not ORB param search |
| **Twin** | Behavior vs Kronos conflict | Conflict → WAIT; ORB playbook still subordinate |
| **Jarvis** | Human-readable merge | Surfaces ORB playbook + blockers together |
| **Arbiter** | Final band | Only place that “decides” |

#### 0.8.9 Mental model for AIs

```text
ORB     = “which opening-range recipe worked repeatedly?”   (research brain)
Vision  = “what is safe/true on this bar right now?”      (decision brain)
Kronos  = “what paths look plausible next?”               (scenario brain)
Arbiter = “given all votes, WAIT / WATCH / PAPER-CANDIDATE?” (boss)

ORB should  teach  the playbook.
Vision/Kronos should  judge  the moment.
Paper should  execute  only after human yes.
```

#### 0.8.10 Present vs intended links (no false hope)

| Link | Today | Intended best design |
|------|--------|----------------------|
| ORB full sweep in research | **Mostly missing** (ORR exists) | Layer A Discover |
| ORB → Vision engines live | **Not connected** | Playbook evidence vote only |
| ORB ↔ Kronos | **No link** | Optional prove-stage filter later; never mutual boss |
| ORB → paper auto | **No** | Never; approve only |
| Kronos / Vision without ORB | **Fully independent** | Stay independent if no playbook |

#### 0.8.11 Anti-patterns (reject in any AI plan)

```text
- Run full ORB grid inside every guidance click
- Make Kronos and ORB twin bosses of each other
- Let ORB winner auto paper or auto live
- Treat ORR single defaults as the full ORB research lab
- Rank only max in-sample profit without prove/consistency
- Put ORB discovery logic only inside TV behavior modules
```

---

## 1. Requirement (what you asked for)

### 1.1 Goal in one sentence

```text
For one or many stocks, systematically backtest Opening Range Breakout (ORB) variants
and report which strategy + timeframe + ORB length/time window + filter combination
is most profitable and most repeatedly successful.
```

### 1.2 Questions the engine must answer

| # | Question | Output field idea |
|---|----------|-------------------|
| Q1 | Which **ORB strategy type** wins? | `strategy_id` ranking |
| Q2 | Which **bar timeframe** to run? | `1m / 3m / 5m / 15m / …` ranking |
| Q3 | Which **ORB candle count** (or clock window)? | e.g. first **3 / 5 / 15 / 30** bars or `09:15–09:30` |
| Q4 | Which **time to run** entries? | `entry_start`–`entry_end` window ranking |
| Q5 | Which **ORB combination** (filters + TP/SL + direction rules)? | full param combo id |
| Q6 | Which is **most profitable**? | net return, expectancy, PF, avg R |
| Q7 | Which has **most repeated success**? | win rate stability, OOS wins, month/year hit rate, consistency score |

### 1.3 “ORB combination” definition (search space)

A single candidate combo is the Cartesian product of:

```text
combo = {
  symbol(s),
  session_calendar,          # e.g. NSE 09:15, US 09:30
  bar_timeframe,             # 1m, 3m, 5m, 15m, …
  orb_definition: {
    mode: "bar_count" | "clock_window",
    orb_bars: 3|5|15|30|…,   # if bar_count
    or_start, or_end,        # if clock_window (e.g. 09:15–09:30)
  },
  strategy_family: "breakout" | "failed_breakout_reversal" | "hybrid",
  direction: "long_only" | "short_only" | "both",
  entry_rules: {
    entry_start, entry_end,  # when trades allowed after OR locked
    break_buffer_ticks?,
    retest_required?,
  },
  filters: {
    volume_mult?, vwap?, rsi?, atr_min?, max_attempts_per_day?, cooldown_bars?,
    regime_filter?,          # optional HMM / ADX
  },
  exits: {
    stop: "or_opposite" | "atr_mult" | "fixed_pct",
    target: "R_multiple" | "or_width_mult" | "fixed_pct",
    time_exit?,
  },
  costs: commission + slippage model,
}
```

### 1.4 Success metrics (must report all)

| Metric | Why |
|--------|-----|
| `n_trades` | Sample size |
| `win_rate` | Hit rate |
| `profit_factor` | Gross profit / gross loss |
| `net_return_pct` | Total performance |
| `expectancy` | Avg $ or R per trade |
| `max_drawdown_pct` | Risk |
| `avg_R` / `median_R` | Quality of wins |
| `consistency_score` | **Repeated success**: e.g. fraction of months profitable, or rolling win-rate std |
| `oos_metrics` | Train/val/holdout or walk-forward |
| `rank_composite` | Weighted score for “best overall” |

**“Most repeated success”** is not only max total profit. Prefer combos that:

```text
- win in many independent periods (months/years)
- pass holdout / WF folds
- do not rely on one lucky year
```

---

## 2. What is already present (reuse)

### 2.1 Research discovery engine (`research/`) — general, not ORB-specific

| Piece | Path | Can use for ORB? |
|-------|------|------------------|
| Orchestrator | `research/engine/runner.py` | Yes — pattern for sweep → backtest → score → store |
| Combinator | `research/engine/combinator.py` | Yes — combo generation pattern |
| VectorBT backtester | `research/engine/backtester.py` | Yes — fast signal backtests |
| Scorer / rank | `research/engine/scorer.py` | Yes — composite ranking |
| Risk pairs R:R | `research/engine/risk_matrix.py` | Yes — TP/SL grids |
| MTF data | `research/data/mtf_loader.py`, `mtf_cache.py` | Yes — multi timeframe |
| OOS split | `research/validation/oos_split.py` | Yes — repeated success / holdout |
| Gates / FDR / cost stress | `research/validation/*` | Yes — anti-overfit |
| Monte Carlo / sensitivity | `research/advanced/*` | Optional robustness |
| Regime filter | `research/filters/regime.py` | Optional combo dimension |
| Job state + DB | `research/jobs/`, `research/storage/`, `research.db` | Persist ORB jobs/results |
| API + UI | `research/api.py`, `static/research.html` | Extend or add ORB job type |

### 2.2 Existing Opening-Range **Reversal** (ORR) — related, not full ORB lab

| Piece | Path | Notes |
|-------|------|-------|
| `opening_range_reversal(...)` | `shared/indicators/self_indc.py` | Params: `or_start`, `or_end`, entry window, `l1_mult` |
| `hyb_opening_range_reversal(...)` | same | + volume, ATR, VWAP, RSI, max attempts, cooldown |
| Backtrader strategies | `server.py` `OpeningRangeReversalBacktestStrategy`, hybrid | Default OR 09:30–10:00, entry 10:00–11:30 |
| Registry IDs | `si_opening_range_rev`, `si_hyb_opening_range_rev` | Chart/TV inventory |
| Tests | `tests/test_opening_range_reversal.py`, `test_hyb_opening_range_reversal.py` | Unit coverage |

```text
Present = Opening Range REVERSAL (+ hybrid filters) + generic research discovery.
Missing = dedicated ORB BREAKOUT research lab that sweeps:
  strategy family × TF × orb bar count/window × entry clock × filter combos
  and ranks by profit + repeated success.
```

### 2.3 Classic ORB vs current ORR (clarify language)

| Family | Idea | In repo today |
|--------|------|----------------|
| **ORB breakout** | After opening range high/low locks, enter break of ORH/ORL | **Not as full sweep lab** |
| **OR failed break / reversal (ORR)** | Fade or reverse after OR interaction | **Present** (ORR + hybrid) |
| **Hybrid** | ORR + volume/VWAP/RSI filters | **Present** |

The new engine should support **both breakout and reversal families** so “which strategy is best” is honest.

---

## 3. Target product — ORB Research Engine

### 3.1 Name / placement

```text
research/orb/                     # NEW package (recommended)
  definitions.py                  # OR session, bar-count, clock window
  strategies.py                   # breakout, reversal, hybrid signal builders
  grid.py                         # param grids for TF, orb_bars, filters, R:R
  sweep.py                        # run Cartesian / sampled sweep
  metrics.py                      # profit + repeated-success scores
  report.py                       # rank tables, best combo export
  api hooks via research/api.py   # job type: orb_discovery
static: research.html ORB panel   # optional UI
```

Reuse `research/engine/backtester.py` + `runner` patterns; **do not** rewrite VectorBT stack.

### 3.2 Inputs (job config)

```text
OrbResearchJob {
  symbols: ["RELIANCE.NS", "INFY.NS", ...]
  start, end
  session: { exchange, open_time, close_time }   # NSE 09:15, US 09:30, etc.
  timeframes: ["1m","3m","5m","15m"]
  orb_bar_counts: [3,5,15,30]                    # or minutes mapped to bars
  orb_clock_windows: [["09:15","09:30"], ["09:15","09:45"], ...]  # optional
  strategy_families: ["orb_breakout","orr_reversal","hyb_orr"]
  filter_grid: { volume_mult:[], use_vwap:[true,false], ... }
  rr_grid: ["1:1","1:2","1:3", ...]
  costs: { commission_pct, slippage_model }
  validation: { train/val/holdout or walk_forward folds }
  max_combos: N                                  # hard cap
  ranking: { profit_weight, consistency_weight, dd_penalty }
}
```

### 3.3 Pipeline

```text
1) Load OHLCV per symbol+TF (mtf_loader / local cache)
2) Validate session alignment (exchange open)
3) For each combo:
     a) Build OR high/low from first N bars OR [or_start, or_end]
     b) Generate entries (breakout and/or reversal rules)
     c) Apply filters
     d) Apply SL/TP/time exit
     e) VectorBT backtest with costs
4) Score metrics + consistency (monthly / fold)
5) OOS / holdout gates (drop lucky-only combos)
6) Rank tables:
     - Best by net profit
     - Best by consistency (repeated success)
     - Best composite (recommended default)
7) Persist to research.db + export CSV/JSON report
8) Optional: top-K combos → paper-guidance evidence packet (later)
```

### 3.4 Primary reports (user-facing)

| Report | Columns (examples) |
|--------|--------------------|
| **Best overall** | strategy, tf, orb_bars/window, filters, score, PF, WR, DD, consistency |
| **Best by TF** | per timeframe winner |
| **Best orb length** | heatmap orb_bars × tf |
| **Best clock window** | or_start/or_end ranking |
| **Repeated success** | % profitable months, fold pass rate |
| **Stability** | param-neighbor sensitivity (reuse advanced/sensitivity) |

### 3.5 Example answer shape (what “done” looks like)

```text
For RELIANCE.NS 2020–2025:
  Winner (composite):
    family=orb_breakout
    timeframe=5m
    orb_bars=6          # first 6×5m = 30 minutes after open
    entry_window=10:00–11:30 session-local
    filters=volume_mult>=1.2, vwap_side=with_trend
    rr=1:2
    trades=480, WR=46%, PF=1.35, maxDD=-12%, consistency=0.72 (13/18 months +)
    OOS holdout PF=1.18 (passed)

  Most repeated success (not max profit):
    family=hyb_orr, tf=5m, orb=09:15–09:45, ...
```

---

## 4. Gaps / errors to avoid

| Gap / error | Mitigation |
|-------------|------------|
| Sweep only in-sample max profit | Mandatory OOS / WF + consistency score |
| Wrong session open (US vs NSE) | Explicit session config per symbol/exchange |
| Mixing TFs without rebuild | OR built only from that TF’s bars (or documented MTF rule) |
| Lookahead on OR lock | OR high/low fixed only after last OR bar **closes** |
| Same-bar break+stop ambiguity | Conservative fill rules (same as research outcome rules) |
| Calling ORR “full ORB lab” | Support breakout + reversal families explicitly |
| Exploding combo count | `max_combos`, random/Sobol sample, staged grid |
| Costs ignored | Always apply commission + slippage scenarios |
| One stock overfit | Multi-symbol leaderboard + per-symbol report |
| Auto live trade from winner | **Forbidden** — research only; paper via sim after human approve |

---

## 5. How this plugs into the paper-guidance spine

```text
ORB Research Engine (offline / job)
        │
        ▼
  Top combos + stats (evidence packet)
        │
        ▼  (later, optional)
  PaperTradeGuidance can show:
    "ORB playbook ranked #1 for this symbol/TF"
        │
        ▼
  Human approve → sim_trading.db
        │
        X── no auto live
```

**Kronos / Vision / other engines:** see **§0.8** (full influence map).  
Short form: ORB does **not** sit inside Kronos or v1.70–75 compute; it feeds a **playbook evidence vote** under the arbiter only when wired.

**Build order relative to spine:**

| Priority | Work |
|----------|------|
| Paper spine P0–P2 | Still preferred for “one-touch guidance” product |
| **ORB research engine** | Can be built **in parallel** on Stock App `research/` — does not block spine |
| Feed winners into guidance | Only after both exist |

---

## 6. Build phases (ORB lab)

### Phase ORB-0 — Spec lock

```text
- Freeze combo schema + metrics + session rules
- Document ORB vs ORR families
- Define default NSE/US session tables
Deliverable: this plan + typed job schema
```

### Phase ORB-1 — Core signal builders

```text
- research/orb/definitions.py  (bar_count + clock window OR)
- research/orb/strategies.py
    orb_breakout_long/short
    wrap existing opening_range_reversal / hybrid as families
- Unit tests: OR lock no lookahead; session open alignment
```

### Phase ORB-2 — Sweep runner

```text
- research/orb/grid.py + sweep.py
- Use vectorbt backtester + scorer
- Caps, progress, research.db job state
- CLI or API: POST /api/research/orb/discover
```

### Phase ORB-3 — Ranking & repeated success (**Week 4 DoD**)

```text
- consistency_score (monthly / weekly profitability rate)
- OOS + walk-forward
- Report export: best profit vs best consistency vs composite
- Human promote → orb_playbooks in research.db
- NO guidance bridge in this phase (Patch 3)
```

### Phase ORB-4 — UI

```text
- research.html ORB tab: symbol, TF multi-select, orb_bars multi, strategy multi, Run
- Results table + heatmap orb_bars × timeframe
```

### Phase ORB-5 — Guidance bridge (**v1.1 only** — Patch 3)

```text
- Export top combo as evidence vote for PaperTradeGuidance D3a
- Still human approve for paper
- Not part of Week-4 / spine v1 mandatory DoD
```

### Product implement lock (cross-doc)

```text
TRADE_VISION_ARCHITECTURE_DESIGN.md §0:
  OLD plan base + only 3 patches
  Patch 1: snapshot_hash at D2
  Patch 2: D6 low_evidence re-check
  Patch 3: Week 4 prove+promote; this ORB-5 = v1.1
```

---

## 7. Default search grid (starter)

| Dimension | Starter values (tune per market) |
|-----------|----------------------------------|
| Timeframes | `5m`, `15m` first; then `1m`, `3m` if data allows |
| ORB bar counts | `3, 6, 12` on 5m (=15m/30m/60m range length) |
| Clock windows (NSE example) | `09:15–09:30`, `09:15–09:45`, `09:15–10:15` |
| Strategies | `orb_breakout`, `orr_reversal`, `hyb_orr` |
| Entry window | start = OR end; end = OR end + 60–120m |
| R:R | `1, 1.5, 2, 3` |
| Filters | none / volume / vwap / hybrid defaults |

---

## 8. Acceptance checklist

```text
[ ] Job can sweep TF × orb length × strategy family for ≥1 symbol
[ ] OR locked only after OR last bar closes (no lookahead)
[ ] Session open correct per exchange
[ ] Reports: best profit, best consistency, best composite
[ ] OOS or multi-period consistency computed
[ ] Costs applied
[ ] Results stored and exportable
[ ] Does not enable live trading
[ ] Documented how ORR existing code is reused
```

---

## 9. Implementation anchors (code to touch)

```text
NEW:
  research/orb/* 

REUSE:
  research/engine/backtester.py
  research/engine/scorer.py
  research/engine/runner.py          # patterns
  research/data/mtf_loader.py
  research/validation/oos_split.py
  research/storage/*
  shared/indicators/self_indc.py     # opening_range_reversal, hyb_*
  server.py STRATEGY_MAP             # optional wire for single backtest
  static/research.html               # UI later
  research.db
```

---

## 10. Relation to other plans

| Plan | Relation |
|------|----------|
| `FINAL_REQUIRED_FLOW` | Spine for live decision UX; ORB engine is **research feed**, not the spine itself |
| `PROJECT_GOD_VIEW_FOR_AI` | Inventory: ORR exists; this plan adds ORB lab requirement |
| `FINAL_REQUIRED_FLOW` App. A (AI Brief) | Later: top ORB combo as evidence vote |
| `OPENALGO_PAPER_TO_LIVE` | Unrelated until paper path exists |
| Chart/memory plans | Optional filters (regime, structure) as combo dimensions |

---

## 11. Bottom line

```text
YES — we can add this as a Research Engine track.

PRESENT: generic research discovery + Opening Range Reversal (+ hybrid) backtests.
NEED: dedicated ORB combination sweeper:
  strategy × timeframe × orb candle count/window × entry time × filters
  ranked by profit AND repeated success (consistency/OOS).

PLACE (pipeline, not one box):
  Discover research/orb → Prove validation → Playbook DB
  → Decide guidance evidence → Paper sim after approve.

KRONOS / VISION:
  Live in decide-now flow; independent of ORB grid search.
  ORB influences them only as optional weak playbook evidence under arbiter.
  See §0.8 for full AI reference.

OUTPUT: clear winner tables for “what to run, when, how many OR candles.”
NOT: auto live trading from the winner.
```

**Path:** `trade-vision-app/docs/plans/ORB_RESEARCH_ENGINE_PLAN.md`  
**AI reference section for flows/influence:** **§0.8**  

---

# CURRENT ARCHITECTURE RESEARCH ADDENDUM — opening-sequence intelligence (2026-09-18)

The original research-engine plan remains historical methodology/provenance. The current master owns stage boundaries and canonical calculation ownership. This addendum defines how opening-sequence intelligence is researched **without creating a second production calculator stack**.

## Research question

The primary falsifiable question is:

> Does opening-sequence information such as B1→B2→B3 transitions and level interaction add incremental unseen-data value beyond facts the existing ORB already knows?

A prettier representation, better narrative or in-sample separation is not sufficient.

## Registered research variables

Variables are versioned and sourced from canonical receipts where possible:

- formation timeframe;
- sequence length `N`;
- OR duration / lock policy;
- each bar's `PRE_OR_LOCK/CROSSES_OR_LOCK/POST_OR_LOCK` relation;
- deterministic sequence-transition events;
- PDH/PDL/PDC/settlement and canonical level interactions;
- candle anatomy with explicit normalization basis/version;
- valid participation/RVOL/volume facts with explicit missingness;
- benchmark / sector / relative-strength context where applicable;
- BUILD-6 formation state only after BUILD-6 exists;
- M3.3 analogue/pattern evidence after the deterministic sequence manifest is frozen.

### Source-detail opening-sequence research manifest

`OrbOpeningSequenceViewV1` is a read-only composed evidence view. Research consumes its registered/canonical receipts and may derive study features from them; it must not create a competing raw-bar, candle-anatomy, ATR, VWAP, PDH/PDL/PDC, session, contract, or market-data calculator.

`B1/B2/B3` mean ordinal sequence positions under the registered formation policy. They are not permanently the first three 3-minute candles. BUILD-5 owns formation timeframe, sequence length `N`, OR clock/window and confirmation-timing research. A study may compare alternative registered policies without changing the ordinal meaning of B1/B2/B3.

Each opening bar retains `PRE_OR_LOCK`, `CROSSES_OR_LOCK`, or `POST_OR_LOCK`. A `CROSSES_OR_LOCK` bar is not a clean post-lock confirmation example. A usable research prefix must be closed, available by the study `decision_as_of`, contiguous under the registered cadence/anchor policy, and explicit about missing, duplicate, revised, out-of-order, unfinished, future, or source-inconsistent bars. If alignment cannot be established, the sample is `UNKNOWN`/`UNAVAILABLE` under the canonical contract rather than guessed or repaired.

Each B-position links to the canonical anatomy/event receipt and hash/lineage rather than copying the calculation. Before a prefix is eligible, the research episode binds exact instrument, contract where applicable, exchange and session identity from canonical receipts. Where supplied by the canonical owner, the research identity preserves `source_timeframe`, `formation_timeframe`, `expected_prefix_bars`, `observed_prefix_bars`, `session_anchor`, bar open time, bar close time, `available_at`, aggregation/resample policy and version, revision/sequence identity, and `source_snapshot_hash`. Independently supplied bars with unknown alignment are not silently substituted.

Sequence-relation studies may use registered/versioned relations such as high/low extension, close progression, overlap, retracement, net displacement, path efficiency, consecutive higher/lower highs, higher/lower lows, and higher/lower closes. These are research features over canonical facts, not a second raw-fact owner. Owner-emitted availability/completeness states remain intact; the research layer does not mint a private missingness enum.

Research reuses the currently registered taxonomy vocabulary in `apps/api/app/behavior/pattern_taxonomy.py` rather than duplicating these calculations:

```text
body_size
body_pct_of_range
upper_wick_size
lower_wick_size
close_location_value
same_direction_body_sequence
opposite_direction_body_sequence
body_expansion_sequence
body_compression_sequence
wick_expansion_sequence
wick_compression_sequence
nearby_candle_confirmation
nearby_candle_rejection
nearby_candle_absorption
nearby_candle_exhaustion
previous_1_candle
previous_2_candles
previous_3_candles
previous_5_candles
```

Only the registered vocabulary/canonical facts are reusable as truth. Generated/demo activity or outcome rows from research/scaffolding modules are not historical evidence. In particular, `pattern_by_timeframe.py`, predefined outcome distributions in `event_sequence_mining.py`, and generated taxonomy activity rows must never be promoted to real historical outcomes. Existing `condition_classifier` or adaptive-ORB interpretations may be registered comparator/baseline evidence only; their historical fixed thresholds or `trap_probability`-style fields are not calibrated ORB probabilities and do not become a second source of truth.

Opening-expansion research may study this explicit B1 feature family when each field has canonical lineage:

```text
B1_range
B1_body
upper_wick
lower_wick
body_to_range

normalized_range_value
normalization_basis
normalization_version

volume
opening_RVOL

open_minus_previous_close
open_minus_PDH
high_minus_PDH
close_minus_PDH

close_location_value
```

Normalization identity is mandatory. The historical M3.1 `range_atr` field is based on rolling mean candle range (`average_range`), not Wilder ATR. Research must keep `range_vs_mean_intraday_range` and `range_vs_canonical_wilder_atr` (or repository-equivalent separately versioned identities) distinct. No study may silently relabel one as the other.

Giveback is a versioned research metric, not a hidden threshold. A giveback observation records at least:

```text
giveback_value
giveback_ratio
giveback_numerator_basis
giveback_denominator_basis
measurement_start
measurement_end
available_at
metric_version
```

The source example `B1 range = 6`, `measured giveback = 2.2`, `giveback_ratio = 36.7%`, and examples such as `B1 > 3 ATR`, `B2 giveback > 35%`, `10% giveback`, and 25/50/75 checkpoints are `RESEARCH_CANDIDATE` examples only. They are not production thresholds; the source does not freeze the giveback numerator convention.

Close Location Value is descriptive candle geometry:

```text
CLV = (Close - Low) / (High - Low)
```

Research should consume canonical `close_location_value` rather than privately recalculate it. Zero-range and missing inputs follow the canonical M3.1 contract. CLV is not a probability, direction, BUY/SELL signal, or independent evidence family by itself.

PDH/previous-close opening geometry may study:

```text
previous_close
PDH
B1_open
B1_high
B1_close
extension_from_PDH
gap_above_PDH
```

Questions may include whether the opening was already extended, how far B1 extended, whether B2 returned into that extension, time to registered 25%/50%/75% giveback checkpoints, PDH touch, accepted closed-candle loss of PDH, PDH reclaim, or a new session high. Touch, wick-through, close-through, acceptance, hold, reclaim and failure remain distinct canonical/registered events.

Research preserves the competing opening hypotheses rather than forcing an early winner:

```text
H1 BREAKOUT_ACCEPTANCE_CONTINUATION
H2 BREAKOUT_REJECTION_FAILURE
H3 PULLBACK_RECLAIM_CONTINUATION
H4 OPENING_BALANCE_NO_EDGE
```

For each hypothesis the study representation preserves `support`, `opposition`, `unknown`, `expected_sequence`, `failure_sequence`, `next_discriminating_observation`, `confirmation_condition`, `weakening_condition`, `invalidation_condition`, and `expiry_condition` where the owning contract supplies them.

Source-preserved PDH labels are research aliases/state candidates, not production enums:

```text
PDH_OPENING_SPIKE_REJECTION
PDH_OPENING_DRIVE
PDH_OPENING_DRIVE_REJECTION
PDH_OPENING_REJECTION_CANDIDATE
PDH_OPENING_2BAR_REJECTION
PDH_FAILED_BREAKOUT_FADE
PDH_BREAKOUT_PULLBACK_CONTINUATION

Family: OPENING_LOCATION_STRUCTURE
Context: ABOVE_PDH
Event: EXPANSION
Reaction: REJECTION
Confirmation: 2_BAR_FOLLOW_THROUGH

OPEN_ABOVE_PDH__EXPANSION__2BAR_REJECTION
OPEN_ABOVE_PDH__EXPANSION__2BAR_REJECTION__PDH_HOLD
OPEN_ABOVE_PDH__EXPANSION__2BAR_REJECTION__PDH_FAIL
```

`B3` rejection is not a confirmed failed breakout. A source-preserved fade path and a pullback/reclaim continuation path must both remain available until later causal evidence matures the registered failure/continuation condition. No hindsight relabeling is allowed.

BUILD-5 owns timeframe/N/OR-window search. BUILD-7 owns thresholds. The research engine does not smuggle those choices into BUILD-4 implementation constants.

## Outcome labels

Outcome construction must be causal, deterministic and matured before use. Candidate outcomes include:

- touch PDH/PDL within registered N bars/time;
- close beyond a referenced level;
- re-entry/reclaim after a close beyond;
- new session high/low before the opposite boundary;
- `+1R` versus `-1R` ordering under a separately registered execution-free outcome geometry;
- MFE and MAE;
- time-to-level;
- time-to-new-session-high/low;
- failure time;
- reclaim time.

Every label records event time, availability/maturity time, source snapshots, reference-price identity, session/contract identity and label version. Outcomes unavailable at the study cutoff remain unknown; they are not dropped into the winning class.

### Outcome-freeze and independent-episode rules

Outcome columns may include `+5m`, `+15m`, `+30m` returns, MFE, MAE, PDH hold/fail, ORH/ORL break, VWAP reclaim, new high/low, failure, reversal and continuation, but they are revealed only after the causal prefix, anchor, feature vector, candidate state/hypothesis and historical episode IDs are frozen.

Outcome fields are inaccessible to candidate construction, feature calculation, anchor selection, formation labeling at `decision_as_of`, analogue selection, ranking tie-breaks and hyperparameter selection. Revealing or changing matured outcomes must not change the previously selected historical episode IDs.

Overlapping prefixes from one session are not automatically independent samples. Where applicable, research stores:

```text
episode_id
session_id
symbol_or_instrument_id
anchor_identity
prefix_end
overlap_group
independence_group
```

Reports distinguish `raw_sample_count`, `independent_episode_count`, and `independent_session_count`. A later PDH failure may be an outcome label; it may not retroactively turn an earlier B3 rejection prefix into a failed-breakout input feature.

## Mandatory adjacent ablation ladder

Register exactly:

```text
A0 existing ORB
A1 + canonical candle anatomy
A2 + level-interaction sequence
A3 + B1/B2/B3 transition facts
A4 + valid RVOL/participation
A5 + benchmark/sector/context
A6 + B6 formation state
A7 + canonical M3.3 analogues
A8 + STUMPY
A9 + DTW reranking
```

Each `A[n]` must justify itself against `A[n-1]` under equivalent samples, chronology, costs and decision times. A8 is not run merely because STUMPY exists; A9 is not run merely because DTW is expressive. Unsupported rungs stop progression.

Feature progression is reversible. If `A[n]` does not add repeatable unseen-data value over `A[n-1]`, the added feature/challenger is recorded as `REJECTED`, removed from the promoted configuration, demoted, or retained `RESEARCH_CANDIDATE` only. Negative/no-go results remain in experiment history; unsupported complexity is not silently carried forward.

## Proof protocol

At minimum, every serious opening-sequence study records:

- chronological development/train period;
- expanding/rolling walk-forward folds;
- untouched final holdout sealed before selection;
- all searched feature sets, thresholds and parameter variants;
- multiple-testing / repeated-consultation controls;
- independent session/episode counts distinct from raw row counts;
- regime slices;
- symbol/instrument slices;
- stock-versus-futures applicability slices;
- realistic cost/slippage assumptions where the outcome requires them;
- latency/availability assumptions;
- sample counts and missing/unknown counts;
- uncertainty / confidence intervals appropriate to the statistic;
- failure rate, OOD rate and abstention rate;
- comparison to the immediately preceding ablation rung;
- code/data/feature-manifest/source hashes.

Train/test rows from one market session are not treated as independent merely because there are multiple candles or labels. Future constituents, future liquidity, future corporate actions, future contract masters or reconstructed winners are forbidden.

### Causality, pattern-fishing, reproducibility and cost realism

A fixed-prefix proof is mandatory. Example:

```text
decision_as_of = 09:24
build receipt/hash H and freeze features + candidate state

append 09:27, 09:30, 10:00 and later session data
reconstruct decision_as_of = 09:24

required:
same receipt
same hash H
same feature vector
same candidate state/hypotheses

otherwise:
FUTURE_DEPENDENCY_DETECTED
```

Before holdout outcomes are inspected, freeze the research generation: grammar version, candidate behavior/pattern families, anchor policy, feature manifest, parameter search space, normalization policy, training window, walk-forward scheme, holdout set, evaluation metrics and failure criteria. Any post-hoc hypothesis or search-space expansion starts a new experiment/version and cannot reuse the consulted holdout as untouched confirmation.

Historical universe construction is point-in-time. Reject current constituents copied backward, modern sector membership used historically, present-day contract masters for old futures, future corporate-action knowledge, future liquidity/volatility, future universe eligibility, future selector outcomes, or examples chosen because they later became winners.

When hypothetical strategy outcomes are evaluated, the research identity states the applicable fees, slippage, spread, latency assumption, fill convention, entry timing, exit timing and stop/target convention. A result that ignores material execution costs may be descriptive research, but it is not presented as tradeable edge.

Deterministic replay binds at least:

```text
dataset_version
source_snapshot_hash
feature_manifest_version
formation_grammar_version
parameter_version
anchor_policy_version
normalization_version
universe_version
research_code_version
split_definition
cost_model_version
random_seed_if_any
```

Identical research identity must reproduce identical selection and results. Prefer deterministic algorithms when randomness is unnecessary.

Negative results are first-class records: `NO_GO`, no incremental value, unstable, insufficient sample/history, OOD, too sparse, cost-sensitive, overfit, regime-specific, unavailable, unknown and rejected experiments are retained rather than deleted.

Current research-result language uses evidence states such as:

```text
UNTESTED
RESEARCH_CANDIDATE
TESTED_NO_GO
TESTED_IN_SAMPLE
WALK_FORWARD_SUPPORTED
HOLDOUT_SUPPORTED
UNSTABLE
INSUFFICIENT_HISTORY
UNAVAILABLE
REJECTED
```

Historical sections above may retain words such as "best" or "winner" as plan/report labels and illustrative examples; current claims must not use them as evidence of edge unless a named B8/OOS experiment supports the statement.

## M3.3 first, external similarity challengers later

Historical retrieval order is:

```text
canonical M3.3 baseline
        ↓
freeze opening-sequence feature manifest
        ↓
measure a concrete retrieval/representation limitation
        ↓
optional STUMPY challenger
        ↓
only if incremental value remains: bounded DTW reranker
```

STUMPY/DTW are not production dependencies in this campaign. Any later adoption requires licence compatibility, PIT/causality compatibility, dependency/maintenance review, runtime suitability and incremental BUILD-8 proof. Reference-only libraries with uncertain licences remain reference-only.

### Similarity normalization and third-party adoption gate

Historical similarity uses a registered/versioned feature manifest and normalized geometry appropriate to the feature. Raw absolute-price matching across instruments is not accepted as a default similarity basis. PIT corpus cutoff, same-time/prefix matching, bounded top-K retrieval, independent analogue counts, episode independence and OOD remain explicit. A challenger manifest may test normalized PDH distance, VWAP distance, volatility/range, volume/RVOL, benchmark/sector context and structure features only when their canonical receipts are available; these dimensions are research candidates, not mandatory truth fields.

Any external package/algorithm, including STUMPY or DTW, remains a challenger until all applicable gates are recorded:

```text
licence_compatibility
PIT_and_causality_compatibility
maintenance_health
dependency_risk
runtime_suitability
determinism_and_replayability
data_requirements
incremental_research_value
OOS_proof
```

Availability on GitHub is not adoption proof. No dependency installation is implied by this plan.

## Research/runtime boundary

The older `research/orb/*` ideas are retained as historical design context, not a mandate to duplicate D2/B1/B2/B3/M3 calculations. Current experiments should call/replay canonical owners or frozen research extracts carrying equivalent identity and provenance. Research may produce a challenger configuration; it cannot mutate the live/shadow policy, final band or execution authority automatically.

A BUILD-8 success claim means only that a registered incremental study passed its declared evidence gate. It does not make B4 code green, does not prove future profitability and does not authorize trading.

# CURRENT ARCHITECTURE RESEARCH ADDENDUM — continuous intraday formation intelligence (2026-09-19)

`OrbOpeningSequenceViewV1` remains the opening-specific composer; `OrbIntradayFormationViewV1` is the continuous causal view under research. Neither is reimplemented here.

Status: `PROPOSED_RESEARCH_CONTRACT`; no claim of measured edge.

## Research target

Test whether causal formation-state, transition, discriminator and dependency-lineage features add incremental explanatory/predictive value over the already registered ORB baselines without using future information or post-hoc pattern fishing.

Research features must be derived from registered `OrbIntradayFormationViewV1`, B6 lifecycle/state, canonical M3.1/M3.2 facts, and M3.3 prefix-safe memory receipts. The research engine must not create a parallel raw-bar calculator or second formation truth owner.

## Frozen research identities

Before holdout consultation, register at minimum:

```text
formation_feature_manifest_version
grammar_version
anchor_policy_version
candidate_formation_families
parameter_search_space
source_timeframe_set
formation_timeframe_set
scope/horizon set
train period
walk-forward periods
untouched holdout
outcome specification
```

### FORM-001 ... FORM-010 - research consequences

The Research Engine does not re-own the formation contracts; it records and tests their research consequences:

- **FORM-001 - arbitrary `as_of`:** every research episode binds `decision_as_of`, `knowledge_cutoff`, `source_snapshot_hash`, `formation_snapshot_hash` and composition/feature identity. Hard law: `information_used_at <= knowledge_cutoff <= decision_as_of`.
- **FORM-002 - deterministic anchors:** research consumes only canonical causal anchors known by the historical cutoff. Preserve `anchor_type`, `event_id`, canonical owner, market time, known-at time, source snapshot and anchor policy/version when supplied. Completed-day hindsight anchors are forbidden.
- **FORM-003 - multi-scale identity:** preserve `source_timeframe`, `formation_timeframe`, `scope`, `horizon` and anchor. Registered scopes such as `MICRO`, `LOCAL_SWING`, `OPENING_SEQUENCE`, `INTRADAY` and `SESSION` may coexist without automatic contradiction.
- **FORM-004 - lifecycle research:** study `SEED`, `DEVELOPING`, `TESTING_BOUNDARY`, `CONFIRMED`, `FAILED`, `EXPIRED` and `AMBIGUOUS`; do not train only on completed textbook formations.
- **FORM-005 - discriminator contract:** preserve `support[]`, `opposition[]`, `unknown[]`, `expected_sequence[]`, `failure_sequence[]`, `next_discriminating_observation`, confirmation, weakening, invalidation and expiry conditions.
- **FORM-006 - prefix-safe analogues:** retrieve from historical prefixes only; freeze episode IDs/rank/retrieval version/feature manifest before matured outcomes are exposed. Outcome changes must not alter retrieval at the same cutoff.
- **FORM-007 - versioned behavioral grammar:** research the hierarchy `CANDLE FACTS -> RELATIONSHIPS -> SEQUENCE BEHAVIOR -> STRUCTURAL FORMATION -> OPTIONAL HUMAN ALIAS`. Behavior candidates include `IMPULSE`, `PULLBACK`, `COMPRESSION`, `EXPANSION`, `RETEST`, `RECLAIM`, `REJECTION`, `FAILURE` and `BALANCE`.
- **FORM-008 - transition diary:** preserve `formation_id`, `previous_state`, `current_state`, `changed_at`, `evidence_added[]`, `evidence_removed[]`, `reason`, source/formation snapshot hashes and transition version so trajectory research is reproducible.
- **FORM-009 - dependency lineage:** preserve `source_event_ids[]`, `dependency_family`, and `derived_from[]`; report raw feature count separately from independent evidence-family count so aliases do not manufacture importance/confluence.
- **FORM-010 - geometry/tolerance versioning:** research artifacts explicitly record `boundary_tolerance_basis`, `pivot_prominence_basis`, `minimum_touch_count`, `slope_policy`, `compression_policy`, `overlap_policy`, `retracement_policy`, `normalization_basis`, `normalization_version` and `parameter_version`. B7 owns candidate policy, B8 proves it, B10 freezes only proven configuration.

## Prefix-safe analogue rule

Historical candidate retrieval uses only historical prefixes available at the equivalent cutoff. Freeze episode IDs/rank/retrieval version before revealing matured outcomes. Outcome fields may not participate in retrieval, feature construction, anchor choice, tie-breaks or hyperparameter selection.

## Formation research variables

Candidate variables may include versioned, source-backed representations of:

- lifecycle state and duration;
- transition counts/sequence;
- anchor-relative displacement;
- compression/expansion behaviour;
- boundary tests and rejections;
- next-discriminator state;
- dependency-family counts;
- multi-scale agreement/conflict descriptors;
- explicit missingness/availability.

These are research candidates until the owner/stage contract and feature lineage are frozen. Human aliases alone are insufficient features unless their deterministic underlying grammar is retained.

### Abstention and incomplete-higher-timeframe research

`NO_STABLE_FORMATION` / explicit unresolved state is a valid research label. Do not force every prefix into a flag, triangle, breakout, reversal or continuation. Research reports coverage, abstention frequency, performance conditional on stable formation, performance conditional on ambiguity, and false-forced-pattern rate; unresolved samples are not silently dropped.

Closed lower-timeframe sub-bars may support a `PROVISIONAL` higher-timeframe research feature only when it is causally constructible at that moment. The same feature may not be labeled `CONFIRMED` before the registered higher-timeframe close. Datasets preserve `closed` versus `provisional` identity.

## Pattern-fishing controls

The study log records every searched anchor, window, timeframe, grammar family, tolerance policy, threshold and normalization. New variants discovered after holdout inspection require a new sealed holdout or later prospective sample; they may not be reported as untouched confirmation.

## Adjacent proof ladder remains

Keep A0→A9 adjacency. `A6 + formation state` must earn its step over A5. `A7 + M3.3 prefix analogues` must earn its step over A6. STUMPY (A8) and bounded DTW reranking (A9) remain optional challengers only after the preceding system demonstrates a concrete limitation and after dependency/licence/runtime/PIT review.

## Required adversarial research checks

At minimum:

1. future-append invariance;
2. hindsight-anchor attack;
3. historical-analogue outcome attack;
4. multi-timeframe coexistence;
5. alias-independence/dependency-family attack;
6. incomplete-candle cannot confirm;
7. pattern-search leakage;
8. `NO_STABLE_FORMATION` abstention case;
9. missingness preservation;
10. feature-OFF legacy parity.

11. giveback-policy identity - changing numerator/denominator/start/end policy changes metric version/hash;
12. CLV lineage - research consumes canonical `close_location_value`; a private redefinition or zero-range fallback fails;
13. premature-failure attack - B3 rejection alone cannot be labeled using a later PDH failure;
14. symmetry/metamorphic attack - where semantics permit, `PDH <-> PDL`, bull <-> bear, and price x10 normalized geometry preserve mirrored behavior;
15. outcome/episode-independence attack - changing matured outcome values after episode IDs are frozen cannot alter prefix selection or independent-episode grouping;
16. opening-prefix data-integrity attack - missing/duplicate/revised/out-of-order/unfinished/future bars, wrong anchor/vendor aggregation, missing level/RVOL, and futures roll/settlement mismatches remain explicit and fail closed where required.

### Research architecture, epistemic and authority lock

```text
RAW FACT CALCULATED ONCE
        -> MANY BRAINS INTERPRET
        -> EVERY INTERPRETATION TRACEABLE
```

The Research Engine consumes immutable/versioned canonical receipts. It is not another candle engine, ATR engine, PDH/PDL engine, session engine, market-identity owner, M3.3 memory owner, B6 lifecycle owner, B7 runtime-parameter owner, D6 final arbiter, order router or execution engine.

Epistemic law:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no_signal != unavailable
no_output != neutral
```

Missing research evidence is never silently imputed to numeric zero unless the registered feature contract states that zero is an observed value.

Zero-authority contract:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true

authority = NONE
may_execute=false
may_set_final_band=false
```

D6 `FINAL_CONFLUENCE_ARBITER` remains the sole final guidance-band authority. Research ranking, similarity, pattern score, historical frequency and any later calibrated model probability are evidence only; research evidence is never execution authority.

A statistically interesting study result does not authorize B10 freeze, B12 probability, final guidance, or trading.