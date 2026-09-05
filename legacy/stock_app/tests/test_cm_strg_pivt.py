import pandas as pd

from shared.indicators.self_indc import _chrismoody_pivots, cm_strg_pivt, compute_all


def test_chrismoody_pivot_formula_matches_unfiltered_screenshot_default():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D")
    ohlc = pd.DataFrame(
        {
            "open": [100.0, 102.0, 99.0, 100.0, 100.001],
            "high": [102.0, 104.0, 101.0, 102.0, 102.0],
            "low": [98.0, 100.0, 97.0, 98.0, 98.0],
            "close": [100.0, 102.0, 99.0, 100.0, 100.003],
        },
        index=idx,
    )

    piv = _chrismoody_pivots(ohlc, show_r3_s3=True)

    assert round(piv["pivot"].iloc[1], 4) == 102.0
    assert round(piv["r1"].iloc[1], 4) == 104.0
    assert round(piv["s1"].iloc[1], 4) == 100.0
    assert round(piv["r3"].iloc[1], 4) == 108.0
    assert round(piv["s3"].iloc[1], 4) == 96.0

    assert round(piv["pivot"].iloc[2], 4) == 99.0
    assert round(piv["r1"].iloc[2], 4) == 101.0
    assert round(piv["s1"].iloc[2], 4) == 97.0
    assert round(piv["r3"].iloc[2], 4) == 105.0
    assert round(piv["s3"].iloc[2], 4) == 93.0

    assert round(piv["pivot"].iloc[4], 4) == 100.001
    assert round(piv["r1"].iloc[4], 4) == 102.002
    assert round(piv["s1"].iloc[4], 4) == 98.002
    assert round(piv["r3"].iloc[4], 4) == 106.002
    assert round(piv["s3"].iloc[4], 4) == 94.002
    assert round(piv["pivot_avg"].iloc[4], 4) == 99.667


def test_chrismoody_filtered_pivot_formula_still_available():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D")
    ohlc = pd.DataFrame(
        {
            "open": [100.0, 102.0, 99.0],
            "high": [102.0, 104.0, 101.0],
            "low": [98.0, 100.0, 97.0],
            "close": [100.0, 102.0, 99.0],
        },
        index=idx,
    )

    piv = _chrismoody_pivots(ohlc, show_r3_s3=True, show_filtered_pivots=True)

    assert round(piv["r1"].iloc[1], 4) == 106.0
    assert round(piv["s1"].iloc[1], 4) == 100.0
    assert round(piv["r1"].iloc[2], 4) == 101.0
    assert round(piv["s1"].iloc[2], 4) == 95.0


def test_cm_strg_pivt_outputs_all_expected_layers():
    idx = pd.date_range("2024-01-01 09:00", periods=24 * 28, freq="1h")
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

    out = cm_strg_pivt(df, tolerance_pct=100.0)

    for key in [
        "daily_pivot",
        "daily_pivot_avg",
        "daily_r3",
        "daily_s3",
        "weekly_pivot",
        "weekly_pivot_avg",
        "weekly_r3",
        "weekly_s3",
        "hourly_conf_pivot",
        "hourly_conf_pivot_avg",
        "hourly_vwap_conf_pivot",
        "hourly_vwap_conf_pivot_avg",
        "hourly_vwap_conf_r3",
        "daily_vwap_vwap",
        "weekly_vwap_vwap",
    ]:
        assert key in out
        assert len(out[key]) == len(df)

    assert out["daily_pivot_last"] is not None
    assert out["daily_pivot_avg_last"] is not None
    assert out["weekly_pivot_last"] is not None
    assert out["weekly_pivot_avg_last"] is not None
    assert out["hourly_conf_pivot_last"] is not None
    assert out["hourly_vwap_conf_pivot_last"] is not None
    assert out["daily_vwap_vwap_last"] is not None
    assert out["weekly_vwap_vwap_last"] is not None

    all_ind = compute_all(df)
    assert "si_cm_strg_pivt" in all_ind
    assert len(all_ind["si_cm_strg_pivt"]["daily_pivot"]) == len(df)


def test_cm_strg_pivt_can_disable_vwap_layers():
    idx = pd.date_range("2024-01-01 09:00", periods=48, freq="1h")
    df = pd.DataFrame(
        {
            "open": [100.0] * len(idx),
            "high": [101.0] * len(idx),
            "low": [99.0] * len(idx),
            "close": [100.0] * len(idx),
            "volume": [1000] * len(idx),
        },
        index=idx,
    )

    out = cm_strg_pivt(df, show_daily_vwap=False, show_weekly_vwap=False)

    assert all(v is None for v in out["daily_vwap_vwap"])
    assert all(v is None for v in out["weekly_vwap_vwap"])
    assert all(v is None for v in out["hourly_vwap_conf_pivot"])
