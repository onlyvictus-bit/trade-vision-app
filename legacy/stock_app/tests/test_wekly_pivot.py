import pandas as pd

from shared.indicators.self_indc import wekly_pivot


def test_wekly_pivot_returns_weekly_daily_and_hourly_confluence_arrays():
    idx = pd.date_range("2024-01-01 09:00", periods=20 * 24, freq="1h")
    close = [100 + (i % 24) * 0.2 + (i // 24) for i in range(len(idx))]
    df = pd.DataFrame(
        {
            "open": close,
            "high": [x + 1.0 for x in close],
            "low": [x - 1.0 for x in close],
            "close": [x + 0.2 for x in close],
        },
        index=idx,
    )

    out = wekly_pivot(df, tolerance_pct=100.0)

    assert len(out["weekly_pivot"]) == len(df)
    assert len(out["daily_pivot"]) == len(df)
    assert len(out["hourly_conf_pivot"]) == len(df)
    assert out["daily_pivot_last"] is not None
    assert out["weekly_pivot_last"] is None
    assert out["hourly_conf_pivot_last"] is not None
    assert out["weekly_r3_last"] is None
    assert out["daily_s3_last"] is None


def test_wekly_pivot_can_disable_daily_and_weekly():
    idx = pd.date_range("2024-01-01 09:00", periods=72, freq="1h")
    df = pd.DataFrame(
        {
            "Open": [100.0] * len(idx),
            "High": [101.0] * len(idx),
            "Low": [99.0] * len(idx),
            "Close": [100.0] * len(idx),
            "Volume": [1000] * len(idx),
        },
        index=idx,
    )

    out = wekly_pivot(df, show_weekly=False, show_daily=False)

    assert all(v is None for v in out["weekly_pivot"])
    assert all(v is None for v in out["daily_pivot"])
