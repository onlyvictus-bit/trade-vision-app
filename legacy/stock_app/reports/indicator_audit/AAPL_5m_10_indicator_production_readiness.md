# 10 Indicator Production Readiness Report

Data: AAPL 5m, rows 4680
Range: 2026-02-17 09:30:00-05:00 to 2026-05-12 15:55:00-04:00

## Verdict
NOT LIVE READY: no strategy candidate passed all basic gates on available 60d 5m data.

## What Is Production Ready
- Indicator calculations: ready for filter use.
- Signal timing: next-candle execution enforced in test.
- Same-candle conflict: blocked in audit.

## Strategy Results
- L_trend_pullback_willr: pass=False trades=16 ret=-1.6% pf=0.734 sharpe=-20.493 maxDD=-1.45% valPF=1.701 holdPF=0.821
- S_trend_macd_aroon: pass=False trades=29 ret=-4.86% pf=0.568 sharpe=-36.276 maxDD=-4.81% valPF=0.085 holdPF=0.0
- S_trend_macd_rsi_mfi: pass=False trades=23 ret=-5.1% pf=0.454 sharpe=-50.584 maxDD=-4.74% valPF=0.335 holdPF=0.0
- S_trend_pullback_willr: pass=False trades=11 ret=-2.58% pf=0.427 sharpe=-52.393 maxDD=-2.99% valPF=0.0 holdPF=0.0
- S_trend_pullback_cci: pass=False trades=6 ret=-2.32% pf=0.271 sharpe=-82.79 maxDD=-2.22% valPF=0.0 holdPF=0.0
- L_trend_macd_aroon: pass=False trades=18 ret=-7.99% pf=0.238 sharpe=-104.724 maxDD=-7.9% valPF=0.0 holdPF=0.373
- L_trend_macd_rsi_mfi: pass=False trades=19 ret=-7.8% pf=0.214 sharpe=-104.774 maxDD=-8.46% valPF=999.0 holdPF=0.497
- L_trend_pullback_cci: pass=False trades=2 ret=-0.75% pf=0.06 sharpe=-87.921 maxDD=0.0% valPF=0.0 holdPF=0.06
- L_trend_dd_recovery: pass=False trades=1 ret=-0.8% pf=0.0 sharpe=0.0 maxDD=0.0% valPF=0.0 holdPF=0.0

## Gates Used
- min full trades >= 30
- validation trades >= 3
- holdout trades >= 3
- full PF >= 1.15
- validation PF >= 1.0
- holdout PF >= 1.0
- max drawdown > -20%
- validation/holdout return not worse than -5%

## Next Needed For Real Production
- Run on your 10-year 1m INFY/AAPL local data.
- Test multi-timeframe.
- Walk-forward + Monte Carlo + cost stress.
- Paper trade before live.

CSV: `D:\Projects\trading-platforms\stock-app\reports\indicator_audit\AAPL_5m_10_indicator_strategy_readiness.csv`
JSON: `D:\Projects\trading-platforms\stock-app\reports\indicator_audit\AAPL_5m_10_indicator_production_readiness.json`