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
