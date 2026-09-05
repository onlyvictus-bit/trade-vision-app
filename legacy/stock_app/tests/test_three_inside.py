import pandas as pd

from shared.indicators.self_indc import three_inside, three_inside_filtered


def _frame(rows, start="2026-05-01 10:00"):
    idx = pd.date_range(start, periods=len(rows), freq="5min")
    return pd.DataFrame(rows, index=idx, columns=["Open", "High", "Low", "Close", "Volume"])


def test_three_inside_strong_bullish():
    df = _frame([
        [110, 112, 100, 101, 1000],
        [103, 111, 99, 106, 1000],
        [102, 112.5, 101, 111.5, 1500],
    ])
    assert three_inside(df) == [{
        "time": "2026-05-01 10:10",
        "name": "3-In Bull",
        "direction": "bull",
        "index": 2,
    }]


def test_three_inside_strong_bearish():
    df = _frame([
        [100, 112, 100, 111, 1000],
        [108, 113, 101, 106, 1000],
        [110, 111, 99, 100, 1500],
    ])
    assert three_inside(df) == [{
        "time": "2026-05-01 10:10",
        "name": "3-In Bear",
        "direction": "bear",
        "index": 2,
    }]


def test_three_inside_filter_mode_off_includes_weak():
    df = _frame([
        [110, 112, 100, 101, 1000],
        [103, 111, 99, 106, 1000],
        [105, 113, 103, 112, 1500],
    ])
    assert three_inside(df, filter_mode="On") == []
    assert three_inside(df, filter_mode="Off")[0]["name"] == "3-In Bull"


def test_three_inside_filtered_addon_requires_ema_and_volume():
    rows = [[100 + i, 101 + i, 99 + i, 100.8 + i, 1000] for i in range(60)]
    rows.extend([
        [170, 172, 160, 161, 1000],
        [163, 171, 159, 166, 1000],
        [162, 173, 161, 172, 5000],
    ])
    df = _frame(rows)
    base = three_inside(df)
    filtered = three_inside_filtered(df)
    assert base
    assert filtered
    assert filtered[-1]["name"] == "3-In Bull+"


def test_three_inside_flat_data_safe():
    df = _frame([[100, 100, 100, 100, 1000] for _ in range(10)])
    assert three_inside(df) == []
    assert three_inside_filtered(df) == []
