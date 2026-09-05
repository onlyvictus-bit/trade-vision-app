# AAPL 5m Next 5 Indicator Formula Notes

CSV: `D:\Projects\trading-platforms\stock-app\reports\indicator_audit\AAPL_5m_next5_indicators_audit.csv`
Rows: 4680
Period used: 60d_fallback
Start: 2026-02-17 09:30:00-05:00
End: 2026-05-12 15:55:00-04:00

## Signal Counts
- ADX trend on: 70
- ADX bull DI cross: 65
- ADX bear DI cross: 69
- Williams bull: 336
- Williams bear: 296
- CCI bull: 148
- CCI bear: 136
- MFI bull: 133
- MFI bear: 151
- Aroon bull: 116
- Aroon bear: 121

## ADX
ADX 14 Wilder: +DM/-DM from high/low movement, TR/ATR Wilder EMA alpha=1/14, +DI/-DI, DX, ADX. Signals: trend_strength_on when ADX crosses above 25; bull/bear DI cross only if ADX>20.
Use: trend strength filter, not entry alone.

## Williams %R
Williams %R 14: -100*(highest_high14-close)/(highest_high14-lowest_low14). Bull when crosses above -80, bear when crosses below -20.
Use: momentum/reversal timing, filter only.

## CCI
CCI 20: typical price=(H+L+C)/3, SMA20, mean absolute deviation, CCI=(TP-SMA)/(0.015*MAD). Bull when crosses above -100, bear when crosses below +100.
Use: momentum extreme/recovery, filter only.

## MFI
MFI 14: typical price*volume positive/negative money flow sums. MFI=100-(100/(1+PMF/NMF)). Bull when crosses above 30, bear when crosses below 70.
Use: volume momentum confirmation.

## Aroon
Aroon 25: bars since highest high/lowest low converted to 0-100. Bull when Aroon Up crosses above Down, bear when Down crosses above Up.
Use: trend direction filter.

## Live Rule
Signal candle close = confirmation only. Earliest live entry = next candle/open. No same-candle execution.
