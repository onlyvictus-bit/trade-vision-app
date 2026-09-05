Review these indicator calculations like a strict trading-system auditor.

Goal:
Check formula correctness, signal correctness, no lookahead, no repeated false signal, no buy+sell same candle, and whether chart output should match backend output.

Data source:
C:\Users\sakth\Downloads\HSTRY\INFY_NSE_1m.csv

Timeframe:
INFY 1m resampled to 5m.

Files I will paste/upload:
1. Formula notes: INFY_5m_indicator_formula_notes.md
2. Sample calculated rows: INFY_5m_indicator_test_sample.csv
3. Audit summary: INFY_5m_indicator_formula_signal_audit.csv

Indicators to review:
Doji, HMA, Skew Reversal, ZScore, TTM Trend, Aroon, ADX, Williams %R, CCI, RSI, MACD, Short Run Bear, Long Run Bull, Drawdown Recovery, Trend Signal, EBSW Cycle, TS Signal, AMAT Bull, HLC3 MA, Aroon Signal, Vortex Signal, CMF Signal, MFI Signal, Long Return Momentum, TSI Signal, KDJ Signal, Fisher Signal, RSX Signal, Market Profile VA

For each indicator return this exact format:

Indicator:
Formula correct: YES/NO/UNCLEAR
Signal timing correct: YES/NO/UNCLEAR
Lookahead risk: YES/NO/UNCLEAR
Chart display should be: overlay/subpanel/marker/level/filter
TradingView match expected: YES/NO/PARTIAL/NO_STANDARD_EQUIVALENT
Problem found:
Fix needed:
Trader use: entry/filter/warning only
Final status: READY / FIX / DO NOT USE

Rules:
- Do not assume. Use only formula notes and sample rows.
- First candle of each session is intentionally blocked from chart marker output. If a debug cross is true on 09:15 but marker is blank, mark it as EXPECTED_BLOCKED, not a formula bug.
- If sample rows are not enough, say exactly what extra rows/columns are needed.
- Standard indicators must match common formula unless notes say custom.
- Custom indicators must be judged by source formula and signal behavior.
