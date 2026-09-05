import pandas as pd

from shared.indicators.self_indc import outside_reversal


def _frame(rows, start="2026-05-01 10:00"):
    idx = pd.date_range(start, periods=len(rows), freq="5min")
    return pd.DataFrame(rows, index=idx, columns=["Open", "High", "Low", "Close"])


def test_outside_reversal_fixed_bullish_signal():
    df = _frame([
        [100, 105, 99, 98],
        [99, 106, 98, 106],
    ])
    events = outside_reversal(df, use_fixed_logic=True)
    assert events == [{
        "time": "2026-05-01 10:05",
        "name": "Out Rev Bull",
        "direction": "bull",
        "index": 1,
    }]


def test_outside_reversal_original_logic_can_differ_from_fixed():
    df = _frame([
        [100, 105, 99, 98],
        [99, 106, 98, 106],
    ])
    assert outside_reversal(df, use_fixed_logic=False) == []


def test_outside_reversal_bearish_signal():
    df = _frame([
        [100, 105, 99, 101],
        [101, 106, 98, 98],
    ])
    events = outside_reversal(df)
    assert events == [{
        "time": "2026-05-01 10:05",
        "name": "Out Rev Bear",
        "direction": "bear",
        "index": 1,
    }]


def test_outside_reversal_no_first_candle_signal_and_no_conflict():
    df = _frame([
        [100, 105, 99, 101],
        [101, 106, 98, 98],
        [97, 107, 97, 107],
    ], start="2026-05-01 09:15")
    events = outside_reversal(df)
    assert all(e["index"] > 0 for e in events)
    by_time = {}
    for event in events:
        by_time.setdefault(event["time"], set()).add(event["direction"])
    assert all(not {"bull", "bear"}.issubset(directions) for directions in by_time.values())


def test_outside_reversal_flat_data_safe():
    df = _frame([[100, 100, 100, 100] for _ in range(10)])
    assert outside_reversal(df) == []
