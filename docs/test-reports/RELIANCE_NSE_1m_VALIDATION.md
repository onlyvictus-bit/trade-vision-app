# RELIANCE NSE 1-Minute Historical Validation

## Test Scope

- Source: `C:\Users\sakth\Downloads\HSTRY\RELIANCE_NSE_1m.csv`
- Purpose: validate Trade Vision ingestion, quality, point-in-time, indicator, chart, candle-structure, condition-classification, and session-rhythm paths using user-supplied real historical candles.
- This test is research-only. It creates no broker order and enables no order route.

## Full-History Results

| Check | Result |
|---|---:|
| Rows read | 1,029,981 |
| Rows parsed | 1,029,981 |
| Date range | 2015-02-02 to 2026-03-20 |
| Trading days | 2,759 |
| Invalid OHLC | 0 |
| Missing volume | 0 |
| Duplicate timestamps | 0 |
| Non-monotonic timestamps | 0 |
| Intraday gap events | 52 |
| Estimated missing intraday minutes | 658 |
| Abnormal prints over 25% range | 0 |
| Same-session split suspects | 0 |

The gap events are warnings requiring source review. They are not overnight, weekend, or holiday closures. Several occur in older 2015 records and include irregular timestamps.

## Latest Session Results

- Session date: `2026-03-20`
- Bars: `375`
- Close: `1414.0`
- Session VWAP: `1419.044`
- Data-quality score: `1.0`
- Point-in-time guard: passed
- Chart points: `375`
- Indicator overlays: `6`
- Latest RSI(5): `62.5`
- Latest EMA(5): `1413.4732`
- Latest MACD fast/slow: `0.4779`
- Latest volume z-score: `-1.0794`
- Session phase: `15:15-15:30_squareoff_fake_spike`
- Classified condition: `choppy_avoid`
- Result: `NO TRADE`
- Reason: candle structure is noisy and uncertainty is high.

The latest candle was classified as a rejection candle. Across the session, the anatomy engine found:

- 154 rejection candles
- 96 inside bars
- 63 outside bars
- 40 expansion candles
- 39 compression candles
- 38 trend candles
- 23 absorption-looking candles
- 8 distribution-looking candles

## Determinism

The complete validation was executed twice.

- Full-history counts matched.
- Latest indicators matched.
- Behavior condition matched.
- Chart output hash matched:
  `d776fc54eecd6178c296b38bb5797562128a1c88925c9dec863531002ec3ec62`

## Code Corrections Made

1. Added guarded CSV support for separate `date` and `time` columns.
2. Added explicit timezone-offset handling so NSE timestamps are interpreted as IST.
3. Added a streaming validator for histories too large for the bounded HTTP text-import endpoint.
4. Kept the canonical `user_csv` provenance contract.
5. Added a regression test for the RELIANCE-style schema.

## Verification

- Historical validation run 1: passed in `14.305` seconds.
- Historical validation run 2: passed in `14.877` seconds.
- Date/time import tests: `3 passed`.
- Full backend regression: `148 passed`.
- Trade permission: false.
- Order routing: false.
- Live trading: blocked.

## Remaining Limitation

The data is successfully read and analyzed, but all 2,759 historical sessions have not yet been converted into:

- outcome labels
- per-day pattern-memory records
- similar-day indexes
- calibrated continuation/reversal/fakeout probabilities
- Stock DNA trust tables

Therefore, this test proves the ingestion and current-session analytical pipeline. It does not yet prove profitability or the complete historical Stock DNA learning requirement.

## Generated Evidence

- `data/validation/RELIANCE_NSE_1m_validation.json`
- `data/validation/RELIANCE_NSE_1m_validation_repeat.json`
- `scripts/validate_historical_ohlcv.py`
