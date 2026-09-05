import pandas as pd

from shared.indicators.self_indc import bahai_reversal_markers


def test_bahai_reversal_points_cc_19_9_logic():
    rows = []
    for i in range(90):
        open_ = 100.0
        high = 110.0
        low = 95.0
        close = 100.0

        # Produce 19 consecutive lower-low comparisons versus 9 bars back.
        if 0 <= i <= 34:
            low = 120.0 - i
            high = low + 12.0
            open_ = low + 6.0
            close = low + 7.0

        # Reset the lower-low state, then create 19 higher-high comparisons.
        if 45 <= i <= 78:
            high = 80.0 + i
            low = high - 12.0
            open_ = high - 7.0
            close = high - 6.0

        rows.append([open_, high, low, close, 1000])

    idx = pd.date_range("2026-01-01", periods=len(rows), freq="D")
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"], index=idx)

    events = bahai_reversal_markers(df)

    assert any(e["name"] == "Bahai Buy" and e["direction"] == "bull" and e["sig"] == 2 for e in events)
    assert any(e["name"] == "Bahai Sell" and e["direction"] == "bear" and e["sig"] == -2 for e in events)
    assert all({"time", "name", "direction", "index", "slo", "sig", "lpSum", "hpSum"} <= set(e) for e in events)
