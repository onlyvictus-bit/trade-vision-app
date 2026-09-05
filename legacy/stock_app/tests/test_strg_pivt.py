import pandas as pd

from shared.indicators.self_indc import strg_pivt


def test_strg_pivt_outputs_pivots_and_vwap_bands():
    idx = pd.date_range("2024-01-01 09:00", periods=24 * 14, freq="1h")
    close = [100 + (i % 12) * 0.5 for i in range(len(idx))]
    df = pd.DataFrame(
        {
            "open": close,
            "high": [x + 1.0 for x in close],
            "low": [x - 1.0 for x in close],
            "close": [x + 0.2 for x in close],
            "volume": [1000 + i for i in range(len(idx))],
        },
        index=idx,
    )

    out = strg_pivt(df, tolerance_pct=100.0)

    for key in [
        "daily_pivot",
        "daily_r3",
        "daily_s3",
        "weekly_pivot",
        "weekly_r3",
        "weekly_s3",
        "hourly_conf_pivot",
        "hourly_conf_r3",
        "hourly_conf_s3",
        "hourly_vwap_conf_pivot",
        "hourly_vwap_conf_r3",
        "hourly_vwap_conf_s3",
        "daily_vwap_vwap",
        "daily_vwap_upper_1",
        "daily_vwap_lower_3",
        "weekly_vwap_vwap",
        "weekly_vwap_upper_2",
        "weekly_vwap_lower_2",
    ]:
        assert key in out
        assert len(out[key]) == len(df)

    assert out["daily_pivot_last"] is not None
    assert out["weekly_pivot_last"] is not None
    assert out["daily_r3_last"] is not None
    assert out["weekly_r3_last"] is not None
    assert out["hourly_conf_pivot_last"] is not None
    assert out["hourly_vwap_conf_pivot_last"] is not None
    assert out["daily_vwap_vwap_last"] is not None
    assert out["weekly_vwap_vwap_last"] is not None


def test_strg_pivt_can_disable_vwap_layers():
    idx = pd.date_range("2024-01-01 09:00", periods=24, freq="1h")
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

    out = strg_pivt(df, show_daily_vwap=False, show_weekly_vwap=False)

    assert all(v is None for v in out["daily_vwap_vwap"])
    assert all(v is None for v in out["weekly_vwap_vwap"])
    assert all(v is None for v in out["hourly_vwap_conf_pivot"])
