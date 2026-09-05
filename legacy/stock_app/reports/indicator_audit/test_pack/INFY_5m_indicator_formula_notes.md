# Indicator Formula Notes

Symbol: INFY
TF: 5m_from_1m
Source: `C:\Users\sakth\Downloads\HSTRY\INFY_NSE_1m.csv`
Range: 2025-07-29 10:15:00 to 2026-03-20 15:25:00

## Doji
Candle body <= 10% of high-low range. Neutral marker. Use as warning/filter only.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## HMA
Hull Moving Average length 20 from pandas-ta-classic: WMA(2*WMA(close,n/2)-WMA(close,n),sqrt(n)). Overlay line.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Skew Reversal
Rolling return skew period 30 crosses below -0.5. Contrarian bullish marker.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## ZScore
z=(close-rolling_mean_50)/rolling_std_50. Bull if crosses below -2. Bear if crosses above +2.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## TTM Trend
pandas-ta-classic TTM Trend length 6. Marker when trend state flips bullish.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Aroon
Aroon Up/Down length 25 from pandas-ta-classic. Subpanel lines.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## ADX
Wilder ADX14 with +DI/-DI. Subpanel. Trend strength, not standalone entry.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Williams %R
%R14=-100*(HH14-close)/(HH14-LL14). Bull crosses up -80. Bear crosses down -20.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## CCI
CCI20=(typical_price-SMA20)/(0.015*mean_abs_dev20). Bull crosses up -100. Bear crosses down +100.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## RSI
Wilder RSI14. Bull crosses up 30. Bear crosses down 70. Filter/warning only.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## MACD
EMA12-EMA26, signal EMA9, histogram. Bull/bear cross markers.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Short Run Bear
EMA21<EMA55, close<EMA21, both EMA slopes down 8 bars, spread>0.15*ATR14, sustained 5 bars, first confirmed bar only.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Long Run Bull
EMA21>EMA55, close>EMA21, both EMA slopes up 8 bars, spread>0.15*ATR14, sustained 5 bars, first confirmed bar only.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Drawdown Recovery
Rolling 50-bar drawdown recovers after deep pullback. Bullish bounce filter.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Trend Signal
UAlgo trend signal wrapper from self-indc. Markers sanitized and cooldown applied.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## EBSW Cycle
Even Better Sine Wave from pandas-ta-classic. Bull/bear when cycle crosses zero.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## TS Signal
Trend Signal TP/SL wrapper from self-indc. Marker only; exact TP/SL requires strategy validation.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## AMAT Bull
Adaptive Moving Average Trend from pandas-ta-classic. Bull/bear trend-state flips.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## HLC3 MA
HLC3=(high+low+close)/3. Fast SMA10 crosses slow SMA30.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Aroon Signal
Aroon Up crosses above/down crosses above, length 25.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Vortex Signal
Vortex VI+/VI- length 14 cross.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## CMF Signal
Chaikin Money Flow length 20 crosses zero.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## MFI Signal
MFI14 crosses up 30/down 70.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Long Return Momentum
Rolling mean log return period 10 crosses threshold 0.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## TSI Signal
True Strength Index fast13 slow25 signal13 cross.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## KDJ Signal
KDJ stochastic-derived K/D cross length 9.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Fisher Signal
Fisher Transform length 9 line/signal cross.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## RSX Signal
RSX threshold/cross wrapper from pandas-ta-classic. Momentum marker.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.

## Market Profile VA
Previous-session Market Profile Value Area. VAH/VAL/POC from prior session volume profile, 24 bins, 70% value area. Bull when close crosses above prior VAH; bear when close crosses below prior VAL.
Chart rule: backend calculates value/signal, frontend only displays it.
Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.
