# Stock App — Full Architecture Reference
> **Purpose:** Complete wiring map for AI/engineer context. Read this instead of loading the full codebase.  
> **Project path:** `D:\Projects\trading-platforms\stock-app`  
> **Server:** FastAPI on `localhost:8014` — started with `C:\Python314\python.exe server.py 8014`

---

## 1. File Tree (key files only)

```
stock-app/
├── server.py                    ← single-file FastAPI backend (~8000 lines)
├── static/
│   └── index.html               ← single-file SPA frontend (~3600 lines)
├── indicators/                  ← Python computation modules (all imported lazily inside functions)
│   ├── adv_trend_detector.py    ← score_trendline(), extract_trendline_events(), prepare_trendlines()
│   ├── adv_trend_brain.py       ← confidence_score(), extract_line_features(), train_meta_model()
│   ├── deduplicator.py          ← cluster_trendlines() via DBSCAN
│   ├── trend_detector.py        ← base trendline detection (wraps trendln lib)
│   ├── trend_brain.py           ← base ML brain for trendlines
│   ├── ml_store.py              ← persistent model store (joblib/pickle)
│   ├── elliott_wave.py          ← detect_elliott_waves(), find_pivots(), Fib scoring, trade setup
│   ├── horizontal_sr.py         ← get_horizontal_sr_levels() (DBSCAN on price arrays)
│   ├── curve_detector.py        ← detect_curves_multiscale() (parabolic pattern detection)
│   ├── curve_brain.py           ← volume_confirmation(), train_curve_model(), score_curve_signals()
│   ├── curve_circle_patterns.py ← geometric helpers imported by curve_detector
│   └── brain.py                 ← shared ML utilities for curve_brain
├── backtest/                    ← strategy backtesting engines (backtrader + custom)
├── cache/                       ← model_cache.py (ModelCache class)
├── alerts/                      ← signal_alert.py (scheduler-triggered alerts)
├── scheduler.py                 ← APScheduler background job (alert checks)
└── tests/
    └── test_adv_trendlines.py   ← 10 pass, 1 skip (TC09 JS-only guard)
```

---

## 2. Startup & Initialization Flow

```
python server.py 8014
    │
    ├─ FastAPI app created
    ├─ CORS middleware (allow all origins)
    ├─ Static files mounted at /static
    ├─ ThreadPoolExecutor created (background tasks)
    ├─ _hp_cache = TTLCache(maxsize=32, ttl=60)   ← only HP uses module-level cache
    ├─ Backtest/HMM/RF strategies registered (optional, try/except)
    ├─ APScheduler started (monitor alerts every N minutes)
    └─ uvicorn listens on 0.0.0.0:8014

Browser → GET /
    └─ FileResponse("static/index.html")

index.html window.load event:
    ├─ initCharts()        ← creates LightweightCharts + all canvas overlays
    ├─ initDates()         ← date range pickers
    ├─ initWatchlist()     ← loads DEFAULT_WATCHLIST = ['AAPL','NVDA','TSLA','MSFT','GOOG','2330.TW']
    ├─ initIndPanel()      ← builds indicator toggle UI from INDICATORS dict
    ├─ loadSimAccounts()   ← paper trading accounts
    └─ setTimeout(200ms) → loadStock('AAPL')
```

---

## 3. INDICATORS Registry (frontend)

All indicators live in a single `const INDICATORS` dict. A `showIndicators` Proxy exposes `showIndicators.key` as `INDICATORS[key].active`.

| Key | Label | Category | Default | Canvas z-index | Data Global |
|-----|-------|----------|---------|---------------|-------------|
| `ma` | Moving Average | trend | ✅ ON | inline series | — |
| `ema` | EMA 9/21/50/200 | trend | off | inline series | — |
| `supertrend` | Supertrend | trend | off | inline series | `_supertrendData` |
| `psar` | Parabolic SAR | trend | off | canvas overlay | `_psarCanvas` |
| `trf` | Twin Range Filter | trend | off | inline series | — |
| `bb` | Bollinger Bands | volatility | off | inline bands | — |
| `keltner` | Keltner Channels | volatility | off | inline bands | — |
| `atr` | ATR (14) | volatility | off | oscillator panel | `_atrData` |
| `zigzag` | ZigZag | pattern | off | inline series | — |
| `smc` | Smart Money (FVG+OB) | pattern | off | z-index: **5** | `_smcData`, `_smcCanvas` |
| `hp` | Harmonic Patterns | pattern | off | z-index: **6** | `_hpData`, `_hpCanvas` |
| `curves` | Curve Patterns | pattern | off | z-index: **7** | `_curvesData`, `_curvesCanvas` |
| `trendlines` | Adv Trendlines | trend | off | z-index: **8** | `_trendlinesData`, `_trendlinesCanvas` |
| `horizontalsr` | Horizontal S/R | pattern | off | z-index: **9** | `_hsrData`, `_hsrCanvas` |
| `elliottwave` | Elliott Wave | pattern | off | z-index: **10** | `_ewData`, `_ewCanvas` |
| `fib` | Fibonacci Retracement | pattern | off | canvas overlay | `_fibData`, `_fibCanvas` |
| `pivot` | Pivot Points | pattern | off | canvas overlay | `_pivotData`, `_pivotCanvas` |
| `vp` | Volume Profile | volume | off | inline series | — |
| `vwap` | VWAP | volume | off | inline series | — |
| `obv` | OBV | volume | off | oscillator panel | `_obvData`, `_obvCanvas` |
| `rsi` | RSI | momentum | off | oscillator panel | — |
| `macd` | MACD | momentum | off | oscillator panel | — |
| `stoch` | Stochastic | momentum | off | oscillator panel | `_stochData` |
| `cci` | CCI | momentum | off | oscillator panel | `_cciData` |
| `wr` | Williams %R | momentum | off | oscillator panel | `_wrData` |
| `adx` | ADX | momentum | off | oscillator panel | `_adxData` |

**Category filter buttons:** `all / trend / momentum / volatility / volume / pattern`  
Toggling an indicator calls `toggleIndicator(key)` → updates `INDICATORS[key].active` → re-renders chart.

---

## 4. Main Data Load Flow

```
loadStock(symbol)
    │
    ├─ GET /api/stock/{symbol}?interval={iv}&start={s}&end={e}
    │       └─ server: yf.download() → computes ALL inline indicators in one call
    │               Returns: { data:[OHLCV+indicators], info:{}, intraday:bool }
    │
    ├─ updateMainChart(data)           ← sets candles, MA, EMA, BB, Keltner, etc.
    │       ├─ candleSeries.setData()
    │       ├─ volSeries.setData()
    │       ├─ Clears stale canvas data: _smcData=null, _hpData=null,
    │       │   _curvesData=null, _trendlinesData=null, _hsrData=null, _ewData=null
    │       ├─ drawSMCCanvas() / drawHPCanvas() / drawCurvesCanvas() / ...  (clears canvas)
    │       └─ renderOscillatorPanels()  ← RSI, MACD, Stoch, CCI, WR, ADX, ATR, OBV
    │
    └─ Background fetches (parallel, each guarded by showIndicators.X check):
            ├─ _loadHarmonics(symbol, iv)      → GET /api/harmonics/{symbol}?interval={iv}
            ├─ _loadCurves(symbol, iv)         → GET /api/curves/{symbol}?interval={iv}
            ├─ _loadTrendlines(symbol, iv)     → GET /api/trendlines/{symbol}?interval={iv}
            ├─ _loadHorizontalSR(symbol, iv)   → GET /api/horizontal-sr/{symbol}?interval={iv}
            └─ _loadElliottWave(symbol, iv)    → GET /api/elliott-wave/{symbol}?interval={iv}
```

**Interval handling:**
- `currentInterval = null` means daily (`1d`)
- `_isIntraday = true` when interval is `1h / 4h / 5m / 15m / 30m / latest`
- Timestamps: intraday → Unix int (`int(dt.timestamp())`), daily → `"YYYY-MM-DD"` string
- All background indicators use same timestamp encoding as main chart

---

## 5. Canvas Layer Stack

```
#mainChart div (position: relative)
    │
    ├─ LightweightCharts canvas (z-index: 1-4)   ← candles, volume, line series
    ├─ _smcCanvas        z-index: 5   ← Smart Money FVG + OB boxes
    ├─ _hpCanvas         z-index: 6   ← Harmonic Pattern XAB/XABCDs
    ├─ _curvesCanvas     z-index: 7   ← Curve Patterns (parabolic arcs)
    ├─ _trendlinesCanvas z-index: 8   ← Adv Trendlines (support/resistance lines)
    ├─ _hsrCanvas        z-index: 9   ← Horizontal S/R zones (DBSCAN bands)
    └─ _ewCanvas         z-index: 10  ← Elliott Wave zigzag + trade levels
```

**Canvas redraw triggers:**  
Every canvas `draw*Canvas()` function is called on:
1. `timeScale().subscribeVisibleTimeRangeChange()` — user pans/zooms
2. `timeScale().subscribeVisibleLogicalRangeChange()` — logical range change
3. After each background fetch completes
4. After `toggleIndicator()` — indicator enabled/disabled
5. After `selectPattern(i)` — row click in signal table

**Canvas coordinate helpers (in every draw function):**
```javascript
const t2x = t => mainChart.timeScale().timeToCoordinate(t);  // time → px X
const p2y = p => candleSeries.priceToCoordinate(p);           // price → px Y
// Both return null when off-screen → always filter: pts.filter(pt => pt.x !== null)
```

---

## 6. Viewport Subscription (single line wires ALL canvases)

```javascript
// line 1053 in index.html
mainChart.timeScale().subscribeVisibleTimeRangeChange(() => {
    drawSMCCanvas(); drawHPCanvas(); drawCurvesCanvas();
    drawTrendlinesCanvas(); drawHorizontalSRCanvas(); drawElliottWaveCanvas();
    drawPSARCanvas(); drawFibCanvas(); drawPivotCanvas();
});
// line 1054 — same for LogicalRangeChange
```

---

## 7. Backend API Endpoints

### 7a. Inline Indicators — `/api/stock/{symbol}`
```
GET /api/stock/{symbol}?interval=1d&start=YYYY-MM-DD&end=YYYY-MM-DD
    └─ yf.Ticker(symbol).history(period, interval)
    └─ Computes all inline indicators:
        _compute_ema, _compute_supertrend, _compute_psar,
        _compute_stochastic, _compute_cci, _compute_williams_r,
        _compute_atr, _compute_keltner, _compute_vwap,
        _compute_obv, _compute_adx, _compute_fibonacci,
        _compute_pivot_points, _compute_volume_profile, _compute_smc
    └─ Returns: { data:[{t,o,h,l,c,v, ma,ema9,...,rsi,macd,...}], info:{name,symbol,...}, intraday:bool }
```

### 7b. Background Pattern Endpoints (each has 60s TTLCache)

| Endpoint | Cache var | Compute function | Key indicator files |
|----------|-----------|-----------------|---------------------|
| `GET /api/harmonics/{symbol}` | `_hp_cache` | `_run_harmonic_search()` | pyharmonics lib |
| `GET /api/curves/{symbol}` | `_curves_cache` | `_compute_curve_patterns()` | `indicators/curve_detector.py`, `curve_brain.py` |
| `GET /api/trendlines/{symbol}` | `_adv_tl_cache` | `_compute_adv_trendlines()` | `indicators/adv_trend_detector.py`, `adv_trend_brain.py`, `deduplicator.py` |
| `GET /api/horizontal-sr/{symbol}` | `_hsr_cache` | `_compute_horizontal_sr()` | `indicators/horizontal_sr.py` |
| `GET /api/elliott-wave/{symbol}` | `_ew_cache` | `_compute_elliott_wave()` | `indicators/elliott_wave.py` |

**Cache pattern (all identical):**
```python
cache = _get_X_cache()         # lazy-init TTLCache(maxsize=32, ttl=60)
key   = f"{symbol}_{interval}"
if key in cache: return cached_result
result = await loop.run_in_executor(None, _compute_X, symbol, interval)
cache[key] = result
return result
```

---

## 8. Per-Indicator Deep Dive

### 8a. Harmonic Patterns (`hp`)
```
Server: _run_harmonic_search(symbol, interval)
    ├─ yfinance download (1h + 4h + 1d + latest TF)
    ├─ pyharmonics: OHLCTechnicals → HarmonicSearch
    ├─ Patterns: XABCD (Gartley, Bat, Butterfly, Crab, Shark, Cypher)
    └─ Returns: { tf_1h:{patterns:[]}, tf_4h:{...}, tf_1d:{...}, tf_latest:{...} }

Frontend: _loadHarmonics → _hpAllData
    ├─ _hpActiveTf = intraday ? 'tf_latest' : 'tf_1d'
    ├─ drawHPCanvas()  ← draws XABCD zigzag lines + PRZ zones
    └─ renderHPTable() ← signal table, click → _hpSelected → redraw
```

### 8b. Curve Patterns (`curves`)
```
Server: _compute_curve_patterns(symbol, interval)
    ├─ yfinance OHLCV (lowercase cols, DatetimeIndex preserved)
    ├─ detect_curves_multiscale(df, return_traces=True)  ← curve_detector.py
    │       └─ Returns (_, traces) where trace = {label, end_bar, window, r2, curvature, x[], y[]}
    ├─ volume_confirmation(tr, df) per trace
    ├─ train_curve_model(traces, df) + score_curve_signals() [ML optional, fallback 0.5]
    └─ Returns: { patterns:[{label, direction, color, curve_points:[[ts,price],...], prob, vol_confirmed, r2, entry, stop, target}] }

Pattern types:
    U-Bottom  → LONG,  #22d3ee (cyan)
    J-Hook    → LONG,  #f59e0b (amber)
    Arch/Dome → SHORT, #ef4444 (red)
    Roll-over → SHORT, #a855f7 (violet)

Frontend: drawCurvesCanvas()
    ├─ Maps curve_points → canvas pixels via t2x/p2y
    └─ renderCurvesPanel() ← table with ML%, vol✓, entry/stop/target
```

### 8c. Advanced Trendlines (`trendlines`)
```
Server: _compute_adv_trendlines(symbol, interval)
    ├─ yfinance OHLCV
    ├─ trendln.calc_support_resistance(closes) → raw support + resistance lines
    ├─ deduplicator.cluster_trendlines(lines) ← DBSCAN dedup (eps=0.008)
    ├─ adv_trend_detector.score_trendline(t, n_local) → float [0,1]
    ├─ adv_trend_brain.extract_line_features(t, df) → 6 floats
    ├─ adv_trend_brain.confidence_score(score, strength, recency) → float [0,1]
    └─ adv_trend_detector.extract_trendline_events(typed, closes, idx_to_ts, errpct=0.008)
           └─ TOUCH: close within 0.8% of line price
           └─ BREAK: close crosses from one side to other

Returns: { lines:[{slope,intercept,line_type,score,confidence,color,points}],
           events:[{type,ts,price,line_type,color}],
           ml_metrics:{avg_confidence, n_support, n_resistance} }

Frontend: drawTrendlinesCanvas()
    ├─ Lines: extends from start → extrapolated right edge
    ├─ TOUCH events: circle marker (green #22c55e)
    ├─ BREAK events: diamond marker (orange #f97316)
    └─ renderTrendlinesPanel() + selectTrendline(i)
```

### 8d. Horizontal S/R (`horizontalsr`)
```
Server: _compute_horizontal_sr(symbol, interval)
    ├─ yfinance OHLCV
    ├─ Collects all High + Low prices as 1D array
    ├─ horizontal_sr.get_horizontal_sr_levels(prices, eps=0.015, min_samples=3)
    │       └─ DBSCAN(eps=0.015, min_samples=3).fit(StandardScaler().fit_transform(prices))
    │       └─ Each cluster center = one S/R level (mean of cluster)
    ├─ Classifies each level as 'support' or 'resistance' vs current price
    ├─ Counts touches (strength)
    └─ Returns: { levels:[{price, line_type, strength, zone_high, zone_low, color}] }
       Zone bands: ±0.8% around each level

Frontend: drawHorizontalSRCanvas()
    ├─ Filled semi-transparent band between zone_high and zone_low
    ├─ Dashed center line at price level
    ├─ Label: "S 185.20 (4)" or "R 192.50 (3)"
    └─ renderHorizontalSRPanel() ← sortable table
```

### 8e. Elliott Wave (`elliottwave`)
```
Server: _compute_elliott_wave(symbol, interval)
    ├─ yfinance OHLCV
    ├─ Runs detect_elliott_waves() at 3 sensitivities:
    │       left/right = (2,2) → fine-grained pivots
    │       left/right = (3,3) → standard pivots
    │       left/right = (5,5) → coarse pivots
    ├─ Deduplicates by end_bar, caps at 6 patterns
    └─ Returns: { patterns:[{type, direction, color, fib_score, points, entry, stop, target1, target2}] }

elliott_wave.py hybrid algorithm (3 open-source inspirations):
    1. btcorgtfo/ElliottWaveAnalyzer  → structural rule validation:
           W2 < 100% of W1, W3 > W1 top, W4 no W1 overlap, W3 never shortest
    2. DrEdwardPCB/python-taew        → Fibonacci scoring 0-4:
           W2 near 50/61.8/78.6%, W3 near 161.8/261.8%, W4 near 23.6/38.2/50%, W5 near 61.8/100%
    3. ESJavadex/elliot-waves-auto    → trade setup:
           entry = W4_high * 1.005,  stop = W2_low * 0.990
           T1 = entry + risk * 1.618, T2 = entry + risk * 2.618

Pattern types:
    impulse   bullish → #22c55e (green)   — 5-wave W1-W2-W3-W4-W5
    impulse   bearish → #ef4444 (red)
    corrective bullish → #22c55e           — 3-wave A-B-C
    corrective bearish → #ef4444

Frontend: drawElliottWaveCanvas()
    ├─ All patterns: colored zigzag lines connecting pivots
    │       best pattern alpha=0.92, fib_score≥2 alpha=0.55, weak alpha=0.35
    ├─ Pivot badges: small numbered/labeled circles (0,1,2,3,4,5 or 0,A,B,C)
    ├─ ONLY best pattern (highest fib_score, then most recent) draws trade levels:
    │       T2 → T1 → Entry → SL  (drawn top-to-bottom)
    ├─ claimY(y, gap=14) collision guard prevents overlapping labels
    └─ renderElliottWavePanel() + selectElliottWave(i)
```

---

## 9. Interval → yfinance Mapping

| UI interval | `currentInterval` | `_isIntraday` | yfinance `interval` | `period` | Timestamp format |
|-------------|-------------------|---------------|--------------------|---------:|-----------------|
| Daily (default) | `null` | false | `1d` | `2y` | `"YYYY-MM-DD"` |
| 1H | `"1h"` | true | `1h` | `730d` | Unix int |
| 4H | `"4h"` | true | `1h` then resample 4h | `730d` | Unix int |
| Latest (live) | `"latest"` | true | `1h` | `730d` | Unix int |
| 5M | `"5m"` | true | `5m` | `730d` | Unix int |
| 15M | `"15m"` | true | `15m` | `730d` | Unix int |
| 30M | `"30m"` | true | `30m` | `730d` | Unix int |

**4H resampling:**
```python
raw = raw.resample("4h").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
```

---

## 10. Replay Mode

```
startReplay(data)
    ├─ Stores _replayFullData
    ├─ Subscribes to timeScale().subscribeVisibleLogicalRangeChange(_replayPanListener)
    └─ _applyReplayFrame(frameIdx)
            ├─ Slices candles[0..frameIdx]
            ├─ candleSeries.setData(slice)
            └─ Redraws ALL canvases: drawSMCCanvas, drawHPCanvas, drawCurvesCanvas,
                   drawTrendlinesCanvas, drawHorizontalSRCanvas, drawElliottWaveCanvas,
                   drawPSARCanvas, drawFibCanvas, drawPivotCanvas

stopReplay() / exitReplay()
    ├─ Restores full data
    └─ Redraws all canvases

window.shouldDrawInReplay(barIndex) → bool
    └─ Guards canvas draws: only draw elements where end_bar <= current replay frame
```

---

## 11. Oscillator Panels

Below-chart panels rendered in a fixed bottom bar (`#oscPanelsBar`, z-index:20):

```
renderOscillatorPanels(chartData, ind, tByIdx)
    └─ Creates a LightweightCharts chart per active oscillator
    └─ Syncs timeScale with main chart:
           mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => oscChart.timeScale().setVisibleLogicalRange(r))
```

| Oscillator | Series type | Color |
|-----------|-------------|-------|
| RSI | line | #22d3ee |
| MACD | histogram + signal + MACD | #6366f1 / #f59e0b |
| Stochastic | %K + %D lines | #a78bfa |
| CCI | line + ±100 bands | #f472b6 |
| Williams %R | line + -20/-80 bands | #fb7185 |
| ADX | ADX + DI+/DI- | #c084fc |
| ATR | line | #fbbf24 |
| OBV | area | #34d399 |

---

## 12. ML Prediction Endpoints

Four separate ML models, each with own cache and training logic:

| Endpoint | Model | Features |
|----------|-------|----------|
| `GET /api/predict/catboost/{symbol}` | CatBoostClassifier | RSI, MACD, Supertrend, ATR, volume features |
| `GET /api/predict/xgboost/{symbol}` | XGBClassifier | Same feature set |
| `GET /api/predict/lightgbm/{symbol}` | LGBMClassifier | Same feature set |
| `GET /api/predict/ensemble/{symbol}` | Voting ensemble | All three models |
| `GET /api/stock/{symbol}/predict` | RandomForestClassifier | Simplified feature set |

Returns: `{ signal: "BUY"|"SELL"|"HOLD", confidence: float, features: {} }`

---

## 13. Simulation (Paper Trading) Endpoints

```
POST /api/sim/accounts            ← create account {name, initial_balance}
GET  /api/sim/accounts            ← list all accounts
GET  /api/sim/accounts/{id}       ← account detail + positions + PnL
POST /api/sim/accounts/{id}/trade ← execute trade {symbol, action, quantity, price}
GET  /api/sim/accounts/{id}/history ← trade history
DELETE /api/sim/accounts/{id}     ← delete account (prohibited in Claude UI)
```

Stored in-memory (no DB). Lost on server restart.

---

## 14. Backtesting Endpoints

```
POST /api/backtest               ← run backtest {strategy, symbol, params}
POST /api/backtest/walk-forward  ← walk-forward validation
POST /api/validate/walk-forward  ← alternate WF endpoint
POST /api/validate/cpcv          ← Combinatorial Purged CV
POST /api/validate/hmm           ← HMM regime filter
GET  /api/backtest/strategies    ← list available strategies
GET  /api/backtest/compare       ← compare multiple results
```

Available strategies: RF (RandomForest), HMM Filter, custom backtrader strategies.

---

## 15. Portfolio & Monitor Endpoints

```
POST /api/portfolio/analyze      ← analyze holdings
GET  /api/portfolio/summary      ← portfolio summary
GET  /api/portfolio/info         ← metadata
GET  /api/monitor/check          ← run signal checks
GET  /api/monitor/alert-log      ← read alerts
GET  /api/monitor/scheduler-status ← APScheduler status
GET  /api/monitor/signal-check   ← manual signal check
```

---

## 16. WebSocket

```
GET /api/ws/status               ← REST status check
WS  /ws/{symbol}                 ← live price feed (yfinance polling, 1s delay with backoff)
    └─ Emits: { price, change, pct_change, volume, timestamp }
    └─ Frontend: _ws = new WebSocket(...)
               _ws.onmessage → updates price ticker bar
```

---

## 17. Adding a New Indicator — Checklist

### Backend (server.py)
1. Add `_X_cache = None` + `_get_X_cache()` lazy-init function
2. Add `_compute_X(symbol, interval) -> dict` function:
   - sys.path insert for indicators/ (inside function, not module top)
   - yfinance download with lowercase df + DatetimeIndex
   - Call indicator module function
   - Build idx_to_ts map (intraday=Unix int, daily=date string)
   - Return `{"key": result}`
3. Add `@app.get("/api/X/{symbol}")` endpoint with 60s TTL cache

### Frontend (index.html)
4. Add to `INDICATORS` dict (line ~811): `x: { label:'...', category:'...', color:'#hex', active:false }`
5. Add globals: `let _xData = null; let _xCanvas = null;`
6. In `initCharts()` after existing canvas blocks: create canvas with next z-index
7. Add both subscribeVisible*Change lines to include `drawXCanvas()`
8. In `updateMainChart()` stale-data block: `_xData = null; drawXCanvas();`
9. Add `async function _loadX(symbol, interval)` — mirrors _loadElliottWave pattern
10. In `loadStock()` add: `_loadX(symbol, currentInterval || null)`
11. Add `function drawXCanvas()` — standard pattern: `t2x` / `p2y` / filter nulls
12. Add `function renderXPanel()` — signal table below chart
13. In `_applyReplayFrame()` and `stopReplay()` add: `drawXCanvas()`

---

## 18. Key Implementation Patterns

### Lazy sys.path inside compute functions
```python
def _compute_X(symbol, interval):
    import sys as _sys, os as _os
    _ind = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'indicators')
    if _ind not in _sys.path:
        _sys.path.insert(0, _ind)
    from my_indicator import detect_X
    ...
```

### ATR safety (handles pd.NA from yfinance)
```python
try:
    atr_raw = float((raw['High'] - raw['Low']).rolling(14).mean().iloc[end_bar])
    if not math.isfinite(atr_raw): raise ValueError("non-finite")
    atr_val = atr_raw
except (TypeError, ValueError):
    atr_val = abs(float(raw['Close'].iloc[end_bar]) * 0.01)
```

### Canvas draw guard
```javascript
function drawXCanvas() {
    if (!_xCanvas || !mainChart || !candleSeries) return;
    const el = document.getElementById('mainChart');
    const W = el.clientWidth, H = el.clientHeight;
    _xCanvas.width = W; _xCanvas.height = H;
    const ctx = _xCanvas.getContext('2d');
    ctx.clearRect(0, 0, W, H);
    if (!showIndicators.x || !_xData?.items?.length) return;
    // ... draw
}
```

### Y-label collision guard (Elliott Wave pattern)
```javascript
const usedY = [];
const claimY = (y, gap = 14) => {
    let adj = y, tries = 0;
    while (usedY.some(uy => Math.abs(uy - adj) < gap) && tries++ < 20) adj -= gap;
    usedY.push(adj);
    return adj;
};
```

### Off-screen point filter
```javascript
const pts = items
    .map(([t, p]) => ({ x: t2x(t), y: p2y(p) }))
    .filter(pt => pt.x !== null && pt.y !== null);
if (pts.length < 2) return;
```

---

## 19. Test Suite

**File:** `tests/test_adv_trendlines.py`

| TC | Test | Status |
|----|------|--------|
| TC01 | cluster_trendlines deduplicates identical lines | pass |
| TC01b | cluster_trendlines empty input | pass |
| TC01c | cluster_trendlines single item | pass |
| TC02 | cluster_trendlines keeps noise lines | pass |
| TC03 | score_trendline returns [0,1] | pass |
| TC04 | extract_trendline_events detects TOUCH | pass |
| TC05 | extract_trendline_events detects BREAK | pass |
| TC06 | confidence_score clamps to [0,1] | pass |
| TC07 | extract_line_features returns 6 floats | pass |
| TC08 | /api/trendlines/{symbol} JSON shape | pass |
| TC09 | renderTrendlinesPanel JS guards | **skip** (JS-only, no runtime) |

Run: `C:\Python314\python.exe -m pytest tests/test_adv_trendlines.py -v`

---

## 20. Git History (last 8 commits)

```
d1a0bc8  fix_ew_labels                          ← EW: best pattern only for trade lines + claimY()
f76d458  feat: add Elliott Wave indicator        ← hybrid EW detector + canvas + panel
9ef8a86  fix: enrich df_lower with rsi+vol...   ← curve ML feature enrichment
9e5bb8b  feat: add Horizontal S/R indicator     ← DBSCAN S/R zones
e2bf221  feat: add Horizontal S/R indicator     ← (earlier iteration)
46c1d37  fix: harden _compute_adv_trendlines    ← pd.NA + outer try/except
48e5671  feat: add renderTrendlinesPanel         ← trendlines signal table
b720866  feat: implement drawTrendlinesCanvas    ← TOUCH circles + BREAK diamonds
```

Branch: `main` — 43 commits ahead of `origin/main` (not pushed to remote)
