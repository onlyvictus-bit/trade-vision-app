# AAPL 5m Last 5 Indicator Formula Notes

CSV: `D:\Projects\trading-platforms\stock-app\reports\indicator_audit\AAPL_5m_last5_indicators_audit.csv`
Rows: 4680
Start: 2026-02-17 09:30:00-05:00
End: 2026-05-12 15:55:00-04:00

## RSI 14
Wilder RSI 14: delta close, avg gain/loss with alpha=1/14, RSI=100-(100/(1+RS)). Signal label only: RSI<30 oversold_buy_watch, RSI>70 overbought_sell_watch.

Use: warning/filter only. Show subpanel line + overbought/oversold label.
Action: KEEP. For live trade, execute next candle only.

## MACD 12/26/9
MACD standard 12/26/9: EMA12(close)-EMA26(close), signal=EMA9(MACD), hist=MACD-signal. bull_cross when MACD crosses above signal, bear_cross when below.

Use: momentum confirmation. Show subpanel lines/hist + cross marker.
Action: FILTER ONLY on 5m. Execute next candle only.

## Long Run Bull
Custom trend filter: EMA21>EMA55, close>EMA21, EMA21 slope up over 8 bars, EMA55 slope up over 8 bars, EMA21-EMA55 > 0.15*ATR14, all true for 5 bars, fire first confirmed bar only.

Use: strong bull trend filter. Show main chart marker/background.
Action: KEEP AS TREND FILTER. Not standalone entry.

## Short Run Bear
Custom trend filter: EMA21<EMA55, close<EMA21, EMA21 slope down over 8 bars, EMA55 slope down over 8 bars, EMA55-EMA21 > 0.15*ATR14, all true for 5 bars, fire first confirmed bar only.

Use: strong bear trend filter. Show main chart marker/background.
Action: KEEP AS TREND FILTER. Not standalone entry.

## Drawdown Recovery
Custom recovery filter: rolling 50-bar max, drawdown=(close-rollmax)/rollmax. Signal when last 3 bars had drawdown<-1%, current drawdown improves vs prior candle, and current drawdown > -0.5%.

Use: bounce/re-entry warning. Show marker plus drawdown_pct value.
Action: FILTER ONLY. Not standalone entry.

## Live Rule
For real/live trading, do not enter on same candle close. Use signal candle close as confirmation and execute earliest on next candle/open.
