# Stock-App Vendored Migration Snapshot

## Purpose

This folder is an internal copy of the useful chart, indicator, research, validation, and backtest assets from:

```text
D:\Projects\trading-platforms\stock-app
```

Trade Vision must not depend on the external stock-app path at runtime. Future work should port/adapt files from this snapshot into typed Trade Vision modules.

## Copied Source Areas

| Area | Path | Use |
|---|---|---|
| Chart/UI screens | `static/` | Reference for chart, realtime, research, backtest, compare, and portfolio screens. |
| Backtest engines | `backtest/` | Reference for backtrader, HMM filter, and random-forest strategy logic. |
| Shared indicators | `shared/indicators/` | Reference for shared indicator formulas and signal markers. |
| Custom indicators | `indicators/` | Reference for custom candle, trend, harmonic, VWAP, CPR, SMC, and pattern indicators. |
| Research engine | `research/engine/` | Reference for runner, scorer, risk matrix, combinator, agent, and backtester design. |
| Research signals | `research/signals/` | Reference for momentum, volume, volatility, pattern, structure, trend, and PTA signals. |
| Validation bridge | `validation/` | Reference for backtrader bridge and validation helpers. |
| Indicator audit fixtures | `reports/indicator_audit/` | Reference outputs for indicator readiness and formula/signal audits. |
| Legacy tests | `tests/` and root `test_*.py` files | Reference tests to port into Trade Vision behavior tests. |
| Project docs | `README.md`, `ARCHITECTURE.md`, `API.md`, `PWA_MOBILE_UPGRADE.md` | Reference architecture and UI behavior from the old app. |

## Excluded Runtime Artifacts

The copy intentionally excludes:

```text
.venv
__pycache__
.pytest_cache
logs
old SQLite DBs
temporary files
compiled Python files
Numba cache files
```

## Migration Rules

1. Do not import from `D:\Projects\trading-platforms\stock-app`.
2. Do not import directly from `legacy.stock_app` in production paths.
3. Port useful logic into Trade Vision modules under `apps/api/app/behavior`.
4. Every ported indicator must pass point-in-time and lookahead-bias tests.
5. Every ported backtest feature must be replay-deterministic.
6. Every chart concept must be rebuilt as React components, not served as old HTML.
7. No live broker or real-money order path may be added from stock-app.
8. Any migrated signal must map to the 74-column behavior output registry or a supporting contract.

## First Porting Targets

1. `shared/indicators/pta.py`
2. `shared/indicators/pta_signal_markers.py`
3. `shared/indicators/patterns.py`
4. `research/signals/trend.py`
5. `research/signals/momentum.py`
6. `research/signals/volume.py`
7. `research/signals/volatility.py`
8. `research/engine/backtester.py`
9. `backtest/backtrader_engine.py`
10. `static/research.html` and `static/backtest.html` as UI references only

