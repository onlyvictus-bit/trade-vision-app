import pandas as pd

from shared.indicators.self_indc import n_bar_reversal_markers


def test_nbar_reversal_luxalgo_bullish_and_bearish_patterns():
    idx = pd.date_range("2024-01-01", periods=12, freq="D")
    df = pd.DataFrame(
        {
            "Open":  [98, 97, 96, 95, 96, 101, 102, 103, 102, 103, 99, 98],
            "High":  [100, 99, 98, 97, 101, 102, 103, 104, 103, 104, 100, 99],
            "Low":   [97, 96, 95, 94, 95, 100, 101, 102, 101, 101, 100, 98],
            "Close": [97, 96, 95, 94, 100, 102, 103, 104, 103, 104, 99, 98],
            "Volume": [1000] * 12,
        },
        index=idx,
    )

    events = n_bar_reversal_markers(
        df,
        num_bars=4,
        min_bars_pct=0.5,
        trend_filt="None",
        atr_period=2,
    )

    assert any(e["index"] == 4 and e["time"] == "2024-01-05" and e["direction"] == "bull" and e["support"] == 94.0 for e in events)
    assert any(e["index"] == 10 and e["time"] == "2024-01-11" and e["direction"] == "bear" and e["resistance"] == 104.0 for e in events)


def test_nbar_reversal_enhanced_requires_close_break():
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [98, 97, 96, 95, 96],
            "high": [100, 99, 98, 97, 101],
            "low": [97, 96, 95, 94, 95],
            "close": [97, 96, 95, 94, 99],
        },
        index=idx,
    )

    all_events = n_bar_reversal_markers(df, num_bars=4, trend_filt="None", atr_period=2)
    enhanced_events = n_bar_reversal_markers(df, num_bars=4, brp_type="Enhanced", trend_filt="None", atr_period=2)

    assert any(e["direction"] == "bull" for e in all_events)
    assert enhanced_events == []
