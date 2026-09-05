# INFY 10-Year 5m 10-Indicator Production Readiness

Rows: 205033
Range: 2015-02-02 09:15:00 to 2026-03-20 15:25:00

## Verdict
NOT LIVE READY: 0 / 11 candidates passed gates.

No green result is allowed unless full, validation, and holdout gates pass.
Any split with less than 20 trades is marked unreliable.

## Results
- L_trend_dd_recovery: verdict=REJECT pass=False trades=60 ret=-16.52% pf=0.432 sharpe=-58.363 maxDD=-16.79% valTrades=2 holdTrades=2 fail=`full trades 60 < 100; validation trades 2 < 20; holdout trades 2 < 20; full PF 0.432 < 1.15`
- L_trend_macd_aroon: verdict=REJECT pass=False trades=1024 ret=-92.73% pf=0.398 sharpe=-58.929 maxDD=-92.78% valTrades=146 holdTrades=134 fail=`full PF 0.398 < 1.15; validation PF 0.447 < 1.0; holdout PF 0.531 < 1.0; full maxDD -92.78% <= -25%; validation return -25.76% <= -10%; holdout return -20.67% <= -10%`
- L_strict_long_run: verdict=REJECT pass=False trades=1828 ret=-99.21% pf=0.369 sharpe=-63.028 maxDD=-99.22% valTrades=265 holdTrades=273 fail=`full PF 0.369 < 1.15; validation PF 0.367 < 1.0; holdout PF 0.342 < 1.0; full maxDD -99.22% <= -25%; validation return -44.53% <= -10%; holdout return -53.95% <= -10%`
- L_trend_macd_rsi_mfi: verdict=REJECT pass=False trades=792 ret=-89.42% pf=0.355 sharpe=-66.475 maxDD=-89.34% valTrades=127 holdTrades=102 fail=`full PF 0.355 < 1.15; validation PF 0.325 < 1.0; holdout PF 0.372 < 1.0; full maxDD -89.34% <= -25%; validation return -28.13% <= -10%; holdout return -23.69% <= -10%`
- L_trend_pullback_willr: verdict=REJECT pass=False trades=480 ret=-74.96% pf=0.324 sharpe=-71.212 maxDD=-75.13% valTrades=72 holdTrades=88 fail=`full PF 0.324 < 1.15; validation PF 0.395 < 1.0; holdout PF 0.235 < 1.0; full maxDD -75.13% <= -25%; validation return -12.13% <= -10%; holdout return -27.74% <= -10%`
- S_strict_short_run: verdict=REJECT pass=False trades=1876 ret=-99.61% pf=0.32 sharpe=-72.262 maxDD=-99.61% valTrades=266 holdTrades=287 fail=`full PF 0.32 < 1.15; validation PF 0.348 < 1.0; holdout PF 0.267 < 1.0; full maxDD -99.61% <= -25%; validation return -50.1% <= -10%; holdout return -60.34% <= -10%`
- L_trend_pullback_cci: verdict=REJECT pass=False trades=109 ret=-29.26% pf=0.306 sharpe=-75.584 maxDD=-29.19% valTrades=19 holdTrades=21 fail=`validation trades 19 < 20; full PF 0.306 < 1.15; holdout PF 0.371 < 1.0; full maxDD -29.19% <= -25%`
- S_trend_macd_rsi_mfi: verdict=REJECT pass=False trades=837 ret=-92.91% pf=0.303 sharpe=-76.947 maxDD=-93.0% valTrades=109 holdTrades=120 fail=`full PF 0.303 < 1.15; validation PF 0.46 < 1.0; holdout PF 0.23 < 1.0; full maxDD -93.0% <= -25%; validation return -20.68% <= -10%; holdout return -33.75% <= -10%`
- S_trend_pullback_willr: verdict=REJECT pass=False trades=476 ret=-77.25% pf=0.292 sharpe=-77.629 maxDD=-77.22% valTrades=64 holdTrades=67 fail=`full PF 0.292 < 1.15; validation PF 0.221 < 1.0; holdout PF 0.256 < 1.0; full maxDD -77.22% <= -25%; validation return -19.03% <= -10%; holdout return -19.46% <= -10%`
- S_trend_macd_aroon: verdict=REJECT pass=False trades=1081 ret=-97.12% pf=0.287 sharpe=-80.325 maxDD=-97.1% valTrades=157 holdTrades=169 fail=`full PF 0.287 < 1.15; validation PF 0.285 < 1.0; holdout PF 0.289 < 1.0; full maxDD -97.1% <= -25%; validation return -37.86% <= -10%; holdout return -41.15% <= -10%`
- S_trend_pullback_cci: verdict=REJECT pass=False trades=103 ret=-30.95% pf=0.274 sharpe=-85.438 maxDD=-31.05% valTrades=12 holdTrades=16 fail=`validation trades 12 < 20; holdout trades 16 < 20; full PF 0.274 < 1.15; full maxDD -31.05% <= -25%`

## Gates
- full trades >=100
- validation trades >=20
- holdout trades >=20
- full PF >=1.15
- validation PF >=1.0
- holdout PF >=1.0
- full maxDD > -25%
- val/hold return > -10%
- next candle execution
- 0.15% cost per side

CSV: `D:\Projects\trading-platforms\stock-app\reports\indicator_audit\INFY_5m_10_indicator_strategy_readiness.csv`
JSON: `D:\Projects\trading-platforms\stock-app\reports\indicator_audit\INFY_5m_10_indicator_production_readiness.json`