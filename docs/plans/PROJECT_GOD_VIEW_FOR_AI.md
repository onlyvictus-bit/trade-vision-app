# PROJECT GOD VIEW — Full Skeleton for External AIs

> **Audience:** Gemini, Claude, Kimi, GLM, Grok, any AI with **zero prior context**.  
> **Purpose:** Understand the **entire monorepo**, every major **indicator family**, every **thinking/decision engine**, **why it exists**, **how it roughly works**, and **how to use features correctly** for plans (esp. one-touch paper guidance).  
> **Date:** 2026-07-22 · **TV tip:** v1.86 · **Stock App:** port **8014**  
> **Companion (short planning pack):** `FINAL_REQUIRED_FLOW.md Appendix A (AI Brief)`  
> **Requirement spine:** `FINAL_REQUIRED_FLOW.md`  
> **ORB research lab plan:** `ORB_RESEARCH_ENGINE_PLAN.md`  
> **Think-engine best flow (question-driven):** `FINAL_REQUIRED_FLOW.md Appendix B (Think Engine)`  
> **Implement lock (OLD + 3 patches):** `TRADE_VISION_ARCHITECTURE_DESIGN.md` **§0**  
> **This file is the long god-view.** Prefer this when an AI must invent architecture without the repo open.

---

## 0. One-paragraph truth

This monorepo is **two products**:

1. **Stock App** (repo root) — charting, ~48 custom indicators, classic TA, ML BUY/SELL/HOLD, HMM regime, Backtrader backtests, research discovery jobs, **manual SQLite paper sim**.  
2. **Trade Vision** (`trade-vision-app/`) — safety-first research cockpit with **71 self-indicator registry IDs + 23 PTA marker groups**, many **behavior “thinking engines”** (chart reasoning, structure, risk, reliability, Jarvis, Kronos twin), outputs **WAIT / WATCH / PAPER-CANDIDATE**, **never live broker orders**.

**Critical product gap:** many analyzers exist, but there is **no single connected “touch → one guidance → paper fill → result” spine**. Engines are largely **parallel evidence APIs/panels**, not one organized action. Planning should **organize reuse**, not invent 50 new indicators.

**Parallel research gap (ORB):** Stock App has Opening Range **Reversal** (+ hybrid) and a generic research discovery engine, but **not** a full **ORB combination research lab** that sweeps strategy × timeframe × ORB candle count/clock window × filters for **profit + most repeated success**. See §4.6b and `ORB_RESEARCH_ENGINE_PLAN.md`.

---

## 1. Monorepo skeleton (god map)

```text
stock-app/                              # MONOREPO ROOT
│
├── server.py                           # Stock App FastAPI monolith (~all chart APIs)
├── scheduler.py                        # Daily regime monitor
├── walk_forward.py                     # WF helper
├── sim_trading.db                      # PAPER SIM LEDGER (real paper book for Stock App)
├── research.db                         # Research discovery DB
├── requirements.txt
├── STOCK_APP_ARCHITECTURE.md          # Stock App deep arch (only root arch file)
├── static/                             # Browser UI pages
│   ├── index.html                      # Main chart + indicators + sim UI
│   ├── research.html / backtest.html / portfolio.html / compare.html / realtime.html
│   └── manifest.json + service-worker.js  # PWA
├── indicators/                         # Pattern brains + detectors
│   ├── trend_brain/detector, adv_trend_*, curve_*, elliott_wave, horizontal_sr, ml_store
│   └── self_indc/                      # ~48 Python custom indicator modules (disk files)
├── shared/indicators/                  # Bridge: self_indc.py, pta_signal_markers.py, patterns.py
├── backtest/                           # Backtrader engine + RF/HMM strategies
├── validation/                         # Purged walk-forward, CPCV, permutation
├── hmm/                                # 3-state MarketHMM
├── research/                           # Strategy discovery product (/api/research)
│   ├── engine/ data/ ml/ signals/ storage/ validation/ advanced/ filters/ jobs/ selection/
│   └── orb/                            # PLANNED: ORB combo research lab (not fully built yet)
├── portfolio/ alerts/ cache/ config/ tests/ reports/
│
└── trade-vision-app/                   # SEPARATE PRODUCT (research decision cockpit)
    ├── ARCHITECTURE.md, SPEC.md, TEST_PLAN.md, TRADE_VISION_README.md
    ├── docs/                           # Handoffs, plans, safety, status
    ├── apps/api/                       # FastAPI + behavior engines
    │   └── app/
    │       ├── main.py                 # ~hundreds of routes
    │       ├── models.py               # Pydantic contracts
    │       ├── storage.py
    │       └── behavior/               # ~143 thinking modules (THE BRAIN)
    ├── apps/web/                       # React workspaces (Jarvis, Behavior, Replay, System…)
    ├── apps/kronos-service/            # Isolated Kronos GPU inference
    ├── apps/openalgo-adapter/          # HMAC simulator adapter (NOT live broker fills product)
    ├── external/kronos/                # Upstream Kronos source
    ├── legacy/stock_app/               # Vendored reference copy of chart stack
    └── data/                           # Local DBs, snapshots, secrets README
```

### Authority boundary

```text
Stock App sim may book paper fills in sim_trading.db (manual).
Trade Vision must NOT place live broker orders.
TV safety invariants do NOT automatically govern every root server.py route.
OpenAlgo is external boundary / simulator / paper-review — not TV execution authority.
```

---

## 2. How the two products “think” (different languages)

| Layer | Stock App | Trade Vision |
|-------|-----------|--------------|
| Primary UI language | BUY / SELL / HOLD (ML/TA) | WAIT / WATCH / PAPER-CANDIDATE / AVOID / NO TRADE |
| Indicators | Chart overlays + self_indc compute | Registry IDs `si_*` + `pta_*` (94 groups) |
| Decision boss | **None unified** | **Intended:** final confluence arbiter v1.75 (reduce-only) |
| Paper | Manual `/api/sim/*` | Label only; OA package review |
| Live | No | Blocked |

**Do not treat ML BUY as equal to TV PAPER-CANDIDATE.** They are different systems.

---

## 3. Data flow (both products)

### 3.1 Stock App chart path

```text
Browser static/index.html
  → GET /api/stock/{symbol}?interval&period
  → yfinance OHLCV
  → inline classic indicators (MA, RSI, MACD, BB…)
  → optional parallel GETs:
       /api/harmonics, /curves, /trendlines, /horizontal-sr, /elliott-wave
       /api/predict/* , /api/stock/.../predict
       /api/verified-trade-signal/{symbol}
  → optional WS /ws/price/{symbol}
  → human optional POST /api/sim/.../trade → sim_trading.db
```

### 3.2 Trade Vision research path

```text
React apps/web
  → apps/api routes /api/v1/behavior/* , /api/v1/jarvis/* , integrations/*
  → behavior modules compute evidence reports
  → Jarvis assembles blockers + room
  → final confluence can produce WAIT/WATCH/PAPER-CANDIDATE
  → OpenAlgo: preview/export/verify/transport (no live fill product)
  → Kronos service: forecast on shared snapshot (research twin)
  → ALWAYS: live_trading_blocked=true, trade_allowed=false on decision surfaces
```

### 3.3 Required future spine (not fully built)

```text
One snapshot → fixed engine order → one arbiter → PaperTradeGuidance
→ human approve → sim fill → PaperTradeResult
See FINAL_REQUIRED_FLOW.md / FINAL_REQUIRED_FLOW.md Appendix A (AI Brief)
```

---

## 4. Stock App — classic indicators & ML (how calculated)

### 4.1 Classic series (inline / server)

| Indicator | Typical calc | Purpose |
|-----------|--------------|---------|
| MA / SMA(n) | mean(close, n) | Trend baseline |
| EMA(n) | exponential smooth | Faster trend |
| RSI(14) | avg gain/loss → 0–100 | Overbought/oversold |
| MACD(12,26,9) | EMA12−EMA26; signal EMA9; hist | Momentum cross |
| Bollinger(20,2) | mid±2σ | Volatility envelope |
| Supertrend | ATR-based trail | Trend following stop |
| Volume ratio | vol / SMA(vol) | Participation |

### 4.2 Rule technical predictor (BUY/SELL/HOLD)

```text
Votes:
  MA5>MA20>MA60 → +1 ; reverse → −1
  price vs MA20 → ±1
  RSI<30 → +1 ; RSI>70 → −1
  MACD>signal & MACD>0 → +1 ; opposite → −1
Average >0.3 BUY ; <−0.3 SELL ; else HOLD
API: GET /api/stock/{symbol}/predict
Role: discretionary opinion — NOT paper auto-execution
```

### 4.3 ML feature set (RF / CatBoost / XGB / LightGBM / ensemble)

```text
Features (approx 10):
  RSI14, MACD hist/signal, MA cross ratios (10/30, 20/60),
  BB %B, volume ratio, momentum 5/10/20d, vol 20d

Label: price up vs down over next N days (e.g. 5)
Threshold: low confidence → HOLD
Ensemble: majority vote of models
Cache: cache/model_cache.py pickles
APIs: /api/predict/catboost|xgboost|lightgbm|ensemble/{symbol}
Role: evidence opinion — must map under one arbiter if used in spine
```

### 4.4 HMM regime

```text
Observations: log_return, vol_20d, volume_ratio
States: Bull / Sideways / Bear (auto-label by mean return)
Use: filter trading in Bear (HMMFilterStrategy in backtest)
Module: hmm/market_hmm.py
Role: regime gate evidence
```

### 4.5 Backtest / validation engines

| Module | Purpose |
|--------|---------|
| `backtest/backtrader_engine.py` | Run strategies with TWSE-style costs |
| `backtest/rf_strategy.py` | RF signals in Backtrader |
| `backtest/hmm_filter_strategy.py` | Regime-filtered entries |
| `validation/purged_walk_forward.py` | Train/test + purge + embargo |
| `validation/cpcv_*.py` | Combinatorial CV + Sharpe distribution |
| Role | Historical evaluation — not live paper guidance |

### 4.6 Research discovery engine (`research/`)

| Subsystem | Purpose |
|-----------|---------|
| `engine/` | Combinator, runner, scorer, backtester (VectorBT), agent |
| `signals/` | momentum, trend, volatility, volume, structure, patterns, PTA |
| `ml/` | Research ML gates |
| `data/` | MTF loaders, validators, lag audit |
| `storage/` | research.db persistence |
| UI | `/research` + `/api/research/*` |
| Role | Strategy search jobs — parallel product surface |

**How it works (generic):**  
fetch OHLCV → precompute signals → generate combos → VectorBT backtest → score/rank → store top results in `research.db`. Supports param grids, OOS split, cost stress, optional regime filters.

### 4.6b ORB / Opening-Range research (present + planned lab)

#### What exists today (ORR — Opening Range **Reversal**)

| Piece | Location | Defaults / notes |
|-------|----------|------------------|
| `opening_range_reversal(...)` | `shared/indicators/self_indc.py` | `or_start/or_end` (e.g. 09:30–10:00), `entry_start/entry_end`, `l1_mult` |
| `hyb_opening_range_reversal(...)` | same | + volume, ATR, VWAP, RSI, max attempts, cooldown |
| Backtrader strategies | `server.py` | `opening_range_reversal`, `hyb_opening_range_reversal` |
| Registry | `si_opening_range_rev`, `si_hyb_opening_range_rev` | Chart/TV inventory |
| Tests | `tests/test_opening_range_reversal.py`, hybrid test | Unit coverage |

**ORR idea:** define opening range high/low in a morning window; enter related to OR extremes (reversal/red-entry style); exit via TP/SL logic. **Not** a full multi-dimension ORB breakout sweep lab.

#### What is required / planned (ORB Research Engine)

**Full plan:** `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md`

```text
User need:
  Backtest stocks to find which ORB strategy + timeframe + ORB candle count
  (or clock window / which time to run) + filter combination is
  most profitable AND most repeatedly successful.
```

| Dimension to sweep | Examples |
|--------------------|----------|
| Strategy family | `orb_breakout`, `orr_reversal`, `hyb_orr` |
| Bar timeframe | `1m`, `3m`, `5m`, `15m`, … |
| ORB length | bar counts `3/5/15/30` **or** clock `09:15–09:30`, `09:15–09:45` |
| Entry window | after OR locks → e.g. next 60–120 minutes |
| Filters | volume, VWAP, RSI, ATR, cooldown, regime |
| Exits | R:R grid, OR-width targets, time exit |
| Rank by | profit (PF, return, expectancy) **and** consistency (months profitable, OOS) |

**Target package (to build):**

```text
research/orb/
  definitions.py   # session, bar_count vs clock window OR
  strategies.py    # breakout + wrap existing ORR/hybrid
  grid.py          # TF × orb_bars × filters × R:R
  sweep.py         # job runner on VectorBT stack
  metrics.py       # profit + repeated-success / consistency
  report.py        # winner tables + heatmaps
```

**Pipeline:**

```text
Load OHLCV per TF → lock OR only after last OR bar closes (no lookahead)
→ entries (breakout and/or reversal) → filters → SL/TP → VectorBT
→ score profit + consistency + OOS → rank → research.db + report
→ optional later: top combo as evidence for PaperTradeGuidance
→ never auto live trade from winner
```

**ORB vs ORR language (do not confuse):**

| Family | Idea | Status |
|--------|------|--------|
| ORB breakout | Trade break of opening range high/low after range locks | Lab **planned** |
| ORR reversal | Fade/reverse style on OR geometry | **Present** |
| Hybrid | ORR + volume/VWAP/RSI filters | **Present** |

**Role:** offline research playbook discovery. Feeds paper-guidance **later** as evidence only; human still approves paper.

#### Best placement (purpose-split — not one folder only)

ORB is **four jobs**; best architecture is a **pipeline of places**:

| Purpose | Best place | Why |
|---------|------------|-----|
| Find best strategy/TF/orb length/combo | **`research/orb` + VectorBT** | Combo explosion |
| Prove repeated success (not luck) | **`validation/` + OOS/WF** on **top-K only** | Truth filter |
| Store recipe | **`research.db` playbook** | Durable ranked params |
| Decide now (one touch) | **Paper-guidance / Jarvis evidence** | Fast; reads playbook, no re-sweep |
| Paper fill | **`sim_trading.db` after human approve** | Existing paper ledger |
| Draw OR on chart | **`self_indc` / chart UI** | Visual only |

```text
Discover (research) → Prove (validation) → Playbook (DB)
        → Decide (guidance evidence) → Paper (sim, approve)
```

Wrong: put full ORB grid search inside TV click path or only in Backtrader.  
Right: discover offline, prove top-K, decide with frozen playbook, paper only on approve.  
Full reasoning: `ORB_RESEARCH_ENGINE_PLAN.md` §0.

#### ORB vs Kronos / Vision think engines (summary for AIs)

| Brain | Flow | ORB link |
|-------|------|----------|
| ORB discover/prove/playbook | Offline research (Stock App) | **ORB home** |
| Vision engines v1.70–75, MTF, reliability | Online decide (TV) | Optional **playbook evidence vote** later |
| Final arbiter | Online decide boss | Indirect only; reduce-only |
| Jarvis | Desk assembly | Display playbook + blockers |
| Kronos + twin | Same-snapshot research prior | **No default link**; never mutual boss |
| TrendForge / external AI | Research/review | No ORB authority |
| Paper sim | After human approve | No auto from ORB job |

```text
ORB offline:  discover → prove → playbook
Vision online: snapshot → engines + [optional playbook] + optional Kronos → arbiter
Paper:         human approve → sim

ORB teaches playbook. Vision/Kronos judge the moment. Human approves paper.
```

**Full influence matrix, hierarchy, anti-patterns, present vs intended:**  
→ `ORB_RESEARCH_ENGINE_PLAN.md` **§0.8** (authoritative AI reference).

**Coding lock (do not invent alternate pipelines):**  
→ `TRADE_VISION_ARCHITECTURE_DESIGN.md` **§0** = **OLD Flow D** + only:

```text
1) snapshot_hash at D2 (not D1)
2) D6 post-agg low_evidence → max WATCH
3) Week 4 ORB prove+promote only; guidance bridge v1.1
```

### 4.7 Pattern brains (`indicators/` root, not self_indc)

| Module | Purpose |
|--------|---------|
| `trend_detector` / `trend_brain` | Trendline detection + ML-ish brain |
| `adv_trend_*` | Advanced trendlines / projection |
| `curve_detector` / `curve_brain` | Curve patterns |
| `elliott_wave` | Elliott wave structure |
| `horizontal_sr` | Horizontal support/resistance |
| `deduplicator` | Dedupe overlapping patterns |
| `ml_store` | Persist pattern ML metrics |
| APIs | `/api/harmonics`, `/curves`, `/trendlines`, `/horizontal-sr`, `/elliott-wave` |
| Role | Chart overlays / context — not auto trade |

### 4.8 Verified trade signal (strict, narrow)

```text
GET /api/verified-trade-signal/{symbol}
Logic: readiness gates on long history (notably INFY 5m path)
TRADE only if strategy passed train/val/holdout AND active on last bars
Else NO TRADE
Does NOT place paper trades
Reports under reports/indicator_audit/
```

---

## 5. Indicator inventory — Trade Vision registry (94 groups)

**Source of IDs:** `behavior/runtime_readiness.py`  
**Contracts/ontology:** `behavior/indicator_registry.py`  
**Disk implementations (Stock App):** `indicators/self_indc/*.py` + `shared/indicators/*`  
**Count:** **71 `si_*` + 23 `pta_*` = 94** output groups  

### 5.1 How to interpret registry status

| Status idea | Meaning for planning |
|-------------|----------------------|
| validated / non_empty_sample | Safer to use as evidence |
| proxy / empty_no_signal_on_sample | Registered but weak/empty on sample — **explanation-only**, don’t promote confidence alone |
| uses_future_pivots | Must wait confirmation_delay; FORMING until closed |
| lag_behavior leading/coincident/lagging | Lagging cannot alone promote WATCH→PAPER |
| family weight | Correlated family should not fake multi-vote agreement (cap ~1.0 per family) |

**EMPTY_NO_SIGNAL_ON_SAMPLE (treat carefully):**  
`si_chandelier, si_dark_cloud, si_flowscope, si_har_zz, si_harmonic, si_hybrid_ml, si_ichimoku, si_kc_pyti, si_pta_cdl, si_sar_tapy, si_three_inside_filtered, si_vol_exh`

### 5.2 All 71 self-indicator group IDs (`si_*`) with purpose map

Grouped by **function** (not alphabetical only). Names are registry IDs; disk files may use longer names (e.g. `smc_bos.py` ↔ `si_bos`).

#### A. Candlestick / multi-bar / reversal

| ID | Intent / typical calc idea | Use as |
|----|----------------------------|--------|
| `si_cdl` | Classic CDL patterns (pandas_ta style) | Event evidence |
| `si_cdl_mb` | Multi-bar candle patterns | Event |
| `si_pta_cdl` | PTA candle markers | Proxy-prone event |
| `si_dark_cloud` | Dark cloud / piercing | Reversal event |
| `si_three_inside` / `si_three_inside_filtered` | Three inside up/down | Reversal |
| `si_nbar` | N-bar reversal | Reversal |
| `si_outside_rev` | Outside bar reversal | Reversal |
| `si_mk_inside` / `si_inside_out` | Inside/outside mother-child | Structure event |
| `si_inside_candle_strategy` | Inside + EMA + SuperTrend strategy geometry | Setup lines |
| `si_bahai` | Bahai reversal points | Reversal points |
| `si_rev_radar` | Reversal radar multi-logic | Reversal scanner |
| `si_opening_range_rev` / `si_hyb_opening_range_rev` | Opening range reverse (ORR; hybrid filters) | Session structure — see also **ORB research plan** for full ORB breakout/TF/bars sweep lab (not fully built) |

#### B. Trend / momentum oscillators

| ID | Intent | Use as |
|----|--------|--------|
| `si_macd_ta` | MACD cross (TA lib) | Lagging momentum |
| `si_rsi_ss` / `si_rsi_div` / `si_rsi_div_auto` | RSI cross / divergence | Momentum/div |
| `si_dual_ma_osc` | Dual MA oscillator | Trend/momentum |
| `si_st_talipp` | SuperTrend | Trend trail |
| `si_sar_tapy` | Parabolic SAR | Trail stop style |
| `si_ichimoku` / `si_ichi_trend_osc` | Ichimoku / trend oscillator (trailing only) | Trend force |
| `si_trend_sig` | Trend signals with TP/SL style | Setup |
| `si_impulse` | Impulse/BOS waves | Trend impulse |
| `si_adaptive_flow` | Adaptive flow trend | Trend flow |
| `si_twin_range` | Twin range filter | Trend filter |
| `si_chandelier` | Chandelier exit | Trail (proxy sample) |

#### C. Volatility / bands

| ID | Intent | Use as |
|----|--------|--------|
| `si_bb_break` | Bollinger breakout | Vol breakout |
| `si_kc_pyti` | Keltner channel | Vol envelope |
| `si_vwap_conf` / `si_vwap_super` / `si_vwap_bb_ml_conf` | VWAP + BB confluence (+ ML) | Value + vol confluence |
| `si_hybrid_ml` / `si_hybrid_ml_cpr` | Hybrid ML + levels | Mixed (proxy sample risk) |

#### D. Levels / pivots / value area

| ID | Intent | Use as |
|----|--------|--------|
| `si_cpr` / `si_cpr_v4` / daily CPR variants | Central Pivot Range | Intraday levels |
| `si_strg_pivt` / `si_cm_strg_pivt` / `si_hourly_pvt` / `si_wekly_pivot` | Pivot families | S/R |
| `si_fib` | Fibonacci levels | Geometry levels |
| `si_mp_va` | Market profile value area | Auction value |
| `si_delta_vp` | Delta / volume profile style | Volume structure |
| `si_trendln` | Trendline breakout | Structure break |

#### E. SMC / liquidity / structure

| ID | Intent | Use as |
|----|--------|--------|
| `si_bos` | Break of Structure | Structure |
| `si_choch` | Change of Character | Reversal structure |
| `si_fvg` | Fair Value Gap | Imbalance |
| `si_ob` | Order Block | Supply/demand zone |
| `si_sfp` | Swing Failure Pattern | Liquidity grab |
| `si_liquidity_entry` / `si_liq_intelg` / `si_lrb` | Liquidity entry/intel/bands | Liquidity |
| `si_sweep_inside_rr` | Sweep + inside RR strategy | Setup (closed trigger only) |
| `si_swing_str` / `si_swing_break` | Swing structure / break | Structure |
| `si_fractal` | Fractals | Pivot fractals |
| `si_zz_swing` | ZigZag swings | Swing skeleton |
| `si_sbs` | Swing areas / trades | Swing zones |
| `si_ctz_gann` | Gann/CTZ style swings | Geometry |

#### F. Harmonics / curves / patterns

| ID | Intent | Use as |
|----|--------|--------|
| `si_harmonic` / `si_har_zz` / `si_flowscope` | Harmonic patterns | Geometry (often lag/proxy) |
| `si_curve` | Curve/circle patterns | Geometry |
| `si_hs` | Head & shoulders | Chart pattern |
| `si_dbl` | Double top/bottom | Chart pattern |
| `si_fmfm300` | Rich overlay: VWAP, pivots, FVG, TL, heatmap, HTF | **Overlay context; future pivots lag** |

#### G. Volume / exhaustion / special grids

| ID | Intent | Use as |
|----|--------|--------|
| `si_vol_exh` | Volume exhaustion | Climax evidence |
| `si_problty_grid` | Probability grid | Grid probabilities |
| `si_sfb_hybrid` | SFB hybrid | Hybrid structure |

### 5.3 Disk modules in `indicators/self_indc/` (~48 files)

These implement many of the above (not 1:1 always with all 71 IDs; some IDs are variants/bridges):

```text
bahai_reversal_points, bollinger_band_breakout, candlestick_multibar,
candlestick_patterns_identified, central_pivot_range, chart_pattern_hs,
cm_hourly_pivots, curve_circle_patterns, dark_cloud_piercing_line_tradingfinder,
double_top_bottom_ultimate, fibonacci_levels, finta_chandelier,
flowscope_hapharmonic, harmonic_patterns, harmonic_strategy, hybrid_ml_vwap_bb,
impulse_trend_boswaves, mp_value_area, n_bar_reversal_luxalgo(+strategy),
outside_reversal, pandas_ta_cdl, previous_candle_inside_outside_mk, pyti_keltner,
reversal_radar_v2, rsi_divergence, sbs_swing_areas_trades, sfp_candelacharts,
si_fractal, smc_bos, smc_choch, smc_fvg, smc_ob, stockstats_rsi_cross,
swing_structure, ta_macd_cross, talipp_supertrend, tapy_psar,
three_inside_tradingfinder, trend_signals_tp_sl_ualgo, trendln_breakout,
tti_ichimoku_tk, twin_range_filter, vedhaviyash4_daily_cpr, volume_exhaustion,
vwap_bb_confluence, vwap_bb_super_confluence_2, zigzag_swing
```

**How they generally compute:**  
OHLCV window → pure functions / class markers → lists of events or series (entry/stop/target lines, directions, states).  
**PIT rule:** prefer closed bar; if pivots need future bars → mark FORMING until confirmed.

### 5.4 PTA marker groups (23) — statistical / TA-lib style markers

```text
pta_amat, pta_aroon_sig, pta_chop, pta_cmf, pta_drawdown, pta_dsp, pta_ebsw,
pta_entropy, pta_fisher_sig, pta_hlc3, pta_kdj, pta_kurtosis, pta_log_ret,
pta_long_run, pta_mfi_sig, pta_rsx, pta_short_run, pta_skew, pta_squeeze,
pta_tsi, pta_ttm, pta_vortex, pta_zscore
```

| Examples | Calc idea | Role |
|----------|-----------|------|
| chop | Choppiness index | Regime chop |
| cmf | Chaikin money flow | Volume-pressure |
| mfi_sig | Money flow index signals | Vol+price |
| squeeze | BB/Keltner squeeze | Compression |
| vortex | Vortex indicator | Trend direction |
| zscore / kurtosis / skew / entropy | Statistical shape | Distribution |
| aroon / kdj / tsi / fisher / ttm | Classic oscillators | Momentum |
| drawdown / long_run / short_run | Path stats | Risk shape |

**Registry note:** PTA entries are often **proxy until full PIT audit** — use as supporting markers, not sole boss.

### 5.5 Indicator families (weighting concept)

```text
price_structure, trend, momentum, volatility, volume_participation,
vwap_value_area, support_resistance, breakout_retest, candlestick,
smart_money_structure, harmonic_geometry, session_opening_range,
reversal, liquidity_order_flow_proxy, statistical_distribution, risk_execution
```

**Rule for efficient use:**  
10 RSI-like signals ≠ 10 independent votes. Cap family contribution (~1.0).  
Lagging MACD/EMA cannot alone promote to PAPER/ENTER.

---

## 6. Trade Vision thinking engines (`behavior/` ~143 modules)

Organize by **role**, not alphabet.

### 6.1 Data, PIT, snapshot (foundation)

| Module | Purpose | Why present |
|--------|---------|-------------|
| `data_adapter` | Normalize OHLCV into behavior types | One input shape |
| `data_quality` | Detect bad timestamps/gaps | Gate garbage |
| `point_in_time_guard` | Block future / incomplete HTF | No leakage |
| `shared_snapshot` | Immutable snapshot hash for TV+Kronos | Twin integrity |
| `timeframe_sync` / `timeframe_feature_builder` | Multi-TF closed bars | MTF truth |
| `causal_whitelist` | Only causal features | Safety |
| `feature_store` | Persist feature snapshots | Memory/research |
| `feature_manifest_integrity` | Version/hash integrity | Audit |
| `feature_redundancy` | Correlation clusters | Anti double-count |
| `corporate_action_abnormal_market` | CA / abnormal sessions | Context integrity |

### 6.2 Chart / candle / structure intelligence (v1.70–v1.72 core)

| Module | Version spirit | What it computes | Output role |
|--------|----------------|------------------|-------------|
| `candle_anatomy` | early | Wick/body/ranges | Anatomy features |
| `condition_classifier` | early | Candle condition classes | Context |
| `chart_reasoning_volatility` | **v1.70** | Rejection, Hurst, fractal, ATR%, BB width%, VCP, EMA tangle, hidden div, chop/trend health | Chart evidence packet |
| `market_regime_feedback` | **v1.71** | Breadth/RS/Bayes-ish posterior, cooldowns (needs context inputs) | Regime evidence |
| `market_structure_liquidity` | **v1.72** | VP POC/VAH/VAL, TPO-ish, VSA, sweeps, OB/FVG-style, traps | Structure evidence |
| `execution_event_oi_risk` | **v1.73** | Fill prob, slippage, liquidity grade A/B/C, event/OI if present else unavailable | Risk cap evidence |
| `post_entry_lifecycle` | **v1.74** | BE/trail/invalidate **simulation guidance** | Post-entry only |
| `final_confluence_arbiter` | **v1.75** | Weighted hierarchy + conflicts → decision_band | **Boss** (reduce-only) |
| `real_mtf_pullback` | **v1.63** | MTF pullback vs opposition | MTF evidence |
| `multi_timeframe_conflict` | — | TF conflict matrix | Conflict evidence |
| `level_confluence` / `level_proximity` / `level_memory_extended` / `band_level_distance` | — | Level geometry | Structure support |
| `context_engines` | — | VWAP/ORB style context | Session context |

**v1.75 evidence hierarchy (hard-coded priority):**

```text
risk/safety > data quality > liquidity > market regime > structure/levels
> volume/auction > relative strength > indicators > external AI
(+ post_entry can override thesis when weakened)
```

Indicators are **low weight** vs risk/liquidity/structure by design.

### 6.3 Indicator runtime / intelligence / memory

| Module | Purpose |
|--------|---------|
| `indicator_registry` | 94 groups + ontology (purpose, lag, conflicts, usage) |
| `runtime_readiness` | Inventory 71+23 + readiness gates |
| `indicator_runtime_bridge` / `real_indicator_adapter` / `indicator_expansion` | Run/adapt indicator compute |
| `indicator_result_cache` | Cache results |
| `indicator_lag_voting` | **v1.80** lag-aware vote weights |
| `indicator_reliability_memory` | **v1.81** outcome labels → reliability |
| `indicator_signal_history_ingestion` | **v1.84** save pending signals |
| `indicator_signal_history_completion` | **v1.85** complete with future bars |
| `indicator_observations` / `indicator_promotion_gates` / `indicator_runtime_coverage` | Observation + gates |
| `outcome_labeler` / `outcome_learning` | Barrier labels TARGET/SL/ambiguous |
| `combination_similarity` / `analog_research` / `design_similarity` | Historical analogs |
| `event_sequence_mining` | Sequential causality of signals |
| `false_agreement_confluence` | Detect fake multi-indicator agreement |
| `pattern_memory` / `pattern_taxonomy` / `pattern_by_timeframe` | Pattern memory |
| `nine_candle_*` (history/hybrid/calibration/reasoning_arbiter) | 9-candle DNA reasoning |
| `session_memory` / `exact_time_session_memory` / `stock_memory_profile` | Session/stock DNA |
| `jarvis_indicator_combination_memory` / `jarvis_candle_cause_effect_memory` | Jarvis memory cards |

### 6.4 Decision / risk / execution **simulation** (not live)

| Module | Purpose |
|--------|---------|
| `decision_engine` | No-trade intelligence / reason tree style decisions |
| `risk_engine` | Sizing / risk constraints |
| `position_portfolio_cooldown` | Portfolio + cooldown |
| `execution_simulator` | Slippage/partial/no-fill realism **sim** |
| `trade_lifecycle_simulation` | Lifecycle scenarios |
| `hypothesis_engine` | Hypothesis framing |
| `regime_gate` | Regime gating |
| `walk_forward_validation` / `validation` | OOS/WF style checks |
| `safety_hardening` / `operational_safety` / `red_team_final_gate` | Safety + red team |
| `matrix_decision_readiness` | Matrix → decision readiness |

### 6.5 Jarvis room (operator desk assembly)

Jarvis modules assemble evidence into operator-facing packages:

| Cluster | Examples | Role |
|---------|----------|------|
| Room core | `jarvis_decision_room`, `jarvis_master_panel`, `jarvis_decision_fusion`, `jarvis_decision_arbiter` | Combine evidence |
| Quality/blockers | `jarvis_decision_quality_gate`, `jarvis_production_blockers`, `jarvis_blocker_resolution` | Block bad promotions |
| Evidence | `jarvis_evidence_assembly`, `jarvis_verified_evidence`, `jarvis_preflight_evidence` | Pack proofs |
| AI review | `jarvis_gemini_*`, `grok_provider`, `gemini_provider`, `external_ai_reliability`, disagreement/diff/ledger modules | **Display-only review** |
| OpenAlgo | `jarvis_openalgo_*`, `jarvis_paper_ready_safety_audit`, `jarvis_paper_execution_loop` | Paper-**review** readiness, not auto fill product |
| Freshness/latency | `jarvis_realtime_freshness`, `jarvis_latency_budget`, `jarvis_replay_determinism` | Ops quality |

**Jarvis is the desk; arbiter is the rule judge; indicators are witnesses.**

### 6.6 Kronos / twin / TrendForge

| Module | Purpose |
|--------|---------|
| `kronos_proxy` | Call Kronos service |
| `twin_arbiter` / `full_twin_analysis` | Compare Behavior vs Kronos on same snapshot |
| `trendforge_bridge` | **v1.86** signed research intake (HMAC, loopback default) |

**Rules:** Kronos disagreement → reduce/WAIT; agreement never overrides risk/NO_TRADE. TrendForge packets cannot enable orders.

### 6.7 OpenAlgo transport cluster

| Module | Purpose |
|--------|---------|
| `openalgo_transport` / `transport_resilience` / `transport_security` | Outbox, retries, security posture |
| `openalgo_adapter_harness` / `openalgo_report_importer` | Harness + import reports |
| `paper_executor_permission` / `paper_reality_check` / `execution_intent_paper_safety` | Paper permission/reality |
| `apps/openalgo-adapter/` | **Simulator service** — always broker_order_created=false |

### 6.8 Release / frontend maps

| Module | Purpose |
|--------|---------|
| `release_control` / `release_readiness_evidence` / `final_release_audit` | Release governance |
| `frontend_panels` | Backend panel map for UI |
| `replay_indicator_matrix` / `replay_indicator_validation` / `chart_replay` | Replay evidence |
| `ai_credentials_vault` | Gemini/Grok slots only |

---

## 7. UI surfaces (what operator sees)

### Stock App pages (`static/`)

| Page | Function |
|------|----------|
| `/` index | Chart, indicators, ML, sim |
| `/research` | Discovery jobs (generic; **ORB lab UI planned** under ORB research plan) |
| `/backtest` | Strategy backtests (includes single ORR/hybrid strategies today) |
| `/portfolio` | Holdings analysis |
| `/compare` | Model/strategy compare |
| `/realtime` | WS quote dashboard |

### Trade Vision workspaces (`apps/web`)

| Workspace | Function |
|-----------|----------|
| Jarvis Decision Room | Combined guidance + blockers + AI review + OA preview |
| Behavior | Engine cards (MTF, 9C, reliability, v1.70–75) |
| Research | Chart/indicator lab |
| Replay | Golden/archive proof |
| System | MOCK watermark, kill switch, credentials |
| Knowledge | Graph/status |

---

## 8. How to use features **correctly and efficiently** (rules for planning AIs)

### 8.1 Efficient spine (do this)

```text
1) One shared closed-bar snapshot
2) Run ONLY a fixed subset of engines in order (not all 143)
3) Indicators → family-capped evidence votes (not N independent BUYs)
4) Gates can only reduce/block
5) One arbiter produces final_band
6) Optional approve → Stock App sim fill
7) Everything else is drill-down
```

### 8.2 Recommended engine subset for v1 paper guidance

```text
REQUIRED:
  point_in_time_guard + data_quality
  chart_reasoning_volatility (v1.70)
  market_structure_liquidity (v1.72)
  execution_event_oi_risk (v1.73)
  final_confluence_arbiter (v1.75)

HIGH VALUE IF AVAILABLE:
  market_regime_feedback (v1.71) — else mark unavailable → cap confidence
  real_mtf_pullback (v1.63)
  indicator_lag_voting + reliability summary (subset of si_*)
  optional Stock App ensemble predict as ONE vote

DEFER:
  Full 71+23 every bar (expensive / noisy)
  Full analog FAISS mega memory
  OpenAlgo real fill loop
  Post-entry until after entry exists
  Live pilot
```

### 8.3 Indicator selection heuristics

| Goal | Prefer | Avoid as sole boss |
|------|--------|--------------------|
| Structure entry | bos/choch/fvg/ob/sfp/swing | lagging MACD alone |
| Session levels | cpr/pivots/vwap | harmonics without confirmation |
| Momentum confirm | rsi/macd/supertrend as confirm | 5 momentum clones as 5 votes |
| Compression | bb/squeeze/vcp from chart reasoning | treating compression as breakout certainty |
| Overlay context | fmfm300 after confirmation delays | future pivots as decision-safe |

### 8.4 Calculation philosophy (all engines)

```text
- Prefer closed candles only
- Missing data = unavailable (not zero, not invented)
- Same-bar target+stop = ambiguous / stop-first conservative
- Proxy/empty sample indicators explain but don't promote
- External AI never overrides risk
```

---

## 9. What is present vs missing (for full understanding)

| Present | Missing for one-touch paper / ORB lab |
|---------|----------------------------------------|
| Huge indicator library | Single Run paper guidance action |
| ML/HMM/backtest/research | Single PaperTradeGuidance contract as product UX |
| v1.70–75 evidence APIs | Forced ordered orchestration of engines |
| Jarvis assembly | Wire guidance → sim fill automatically after approve |
| Safety locks | Unified language across Stock App + TV |
| OA simulator/review | OA real paper fill loop (plan future) |
| Kronos twin research | Kronos as execution authority (forbidden) |
| ORR + hybrid + generic research sweep | **ORB lab:** strategy × TF × orb_bars/window × combo ranked by profit + **repeated success** |

---

## 10. Safety god-rules (non-negotiable)

```text
live_trading_blocked=true
order_routing_enabled=false
no broker credentials by TV
no future-bar features
AI/Kronos cannot override NO_TRADE / kill switch / low evidence
Paper v1 = sim_trading.db after human approve
Allowed outputs: WAIT WATCH PAPER-CANDIDATE/ENTER_PAPER AVOID NO TRADE
Forbidden: LIVE BUY/SELL, AUTO EXECUTE, ROUTE ORDER
```

---

## 11. File map for deeper dives (after this god view)

| Need | File |
|------|------|
| Short multi-AI plan pack | `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)` |
| Product requirement spine | `docs/plans/FINAL_REQUIRED_FLOW.md` |
| **ORB research lab (TF/bars/combo)** | `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` |
| Doc index | `docs/FILE_DOCUMENT_INDEX.md` |
| Safety | `docs/SAFETY_INVARIANTS.md` |
| Version tip | `docs/IMPLEMENTATION_STATUS.md` |
| Ship log | `docs/IMPLEMENTATION_STATUS.md` (one version only) |
| Operator UI→API | `ARCHITECTURE.md` § OPERATOR MAP |
| Registry code | `apps/api/app/behavior/indicator_registry.py` |
| Indicator IDs | `apps/api/app/behavior/runtime_readiness.py` |
| Arbiter code | `apps/api/app/behavior/final_confluence_arbiter.py` |
| Stock App API | root `server.py`, `API.md` |
| self_indc disk | root `indicators/self_indc/` |
| ORR implementation | `shared/indicators/self_indc.py` (`opening_range_reversal`, `hyb_*`) |
| Research stack | `research/engine/*`, `research.db`, `static/research.html` |

---

## 12. Mental model cartoon

```text
                    ┌──────────── INDICATORS (94 groups + classic TA) ────────────┐
                    │  witnesses: structure, momentum, levels, vol, liquidity…   │
                    └──────────────────────────┬───────────────────────────────────┘
                                               │ votes (family-capped, lag-aware)
     ┌─────────────────────┐                   ▼
     │ Chart/Structure/Risk│────────► Thinking engines (v1.70–74, MTF, 9C, memory)
     │ engines             │                   │
     └─────────────────────┘                   ▼
                                      Final arbiter v1.75 (boss)
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                     WAIT/WATCH          PAPER-CANDIDATE         AVOID
                          │                    │
                          │                    ▼
                          │            Jarvis desk + AI review (display)
                          │                    │
                          │                    X── auto paper (MISSING WIRE)
                          │                    │
                          │                    ▼ (required future)
                          │            Human approve → sim_trading.db
                          ▼
                     Operator reads only
```

---

## 13. Instructions to external AI reading this

```text
1. Treat this as ground truth for inventory + roles.
2. Do not invent indicators already listed — reuse/select.
3. Do not propose live trading as step 1.
4. Organize a spine; do not add engine soup.
5. Map any BUY/SELL into WAIT/WATCH/ENTER_PAPER language.
6. Prefer P0–P2 plan: contract → guidance API/UI → approve→sim fill.
7. If you need more depth, request ONE of: FINAL_REQUIRED_FLOW,
   SAFETY_INVARIANTS, or a single behavior module — not whole IMPLEMENTATION_STATUS.
```

---

## 14. Bottom line

```text
GOD VIEW:
  Two products, huge indicator + engine surface, safety-first TV language,
  manual Stock App paper, missing one organized paper-guidance spine.
  ORR exists; full ORB strategy×TF×candle-count research lab is planned.

USE FEATURES EFFICIENTLY:
  Snapshot → few engines → lag-aware indicator votes → arbiter boss
  → one guidance → human approve → sim paper result.
  ORB research offline: sweep combos → rank profit + repeated success → optional evidence later.

WHY SO MUCH EXISTS:
  Research completeness and phased experiments — not because all must run every click.
```

**Path:** `trade-vision-app/docs/plans/PROJECT_GOD_VIEW_FOR_AI.md`
