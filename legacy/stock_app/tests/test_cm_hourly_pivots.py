import pandas as pd

from shared.indicators.self_indc import cm_hourly_pivots


def test_cm_hourly_pivots_projects_previous_hour_levels():
    idx = pd.date_range("2024-01-01 09:00", periods=24, freq="5min")
    df = pd.DataFrame(
        {
            "Open": [100 + i * 0.1 for i in range(24)],
            "High": [101 + i * 0.1 for i in range(24)],
            "Low": [99 + i * 0.1 for i in range(24)],
            "Close": [100.5 + i * 0.1 for i in range(24)],
            "Volume": [1000] * 24,
        },
        index=idx,
    )

    out = cm_hourly_pivots(df)

    assert len(out["hourly_pivot"]) == len(df)
    assert out["hourly_pivot"][0] is None
    expected_prev_hour_pivot = round((102.1 + 99.0 + 101.6) / 3.0, 4)
    assert out["hourly_pivot"][12] == expected_prev_hour_pivot
    assert out["hourly_r1"][12] == round(expected_prev_hour_pivot + (expected_prev_hour_pivot - 99.0), 4)
    assert out["hourly_s1"][12] == round(expected_prev_hour_pivot - (102.1 - expected_prev_hour_pivot), 4)
    assert out["hourly_r3"][12] is None
    assert out["hourly_s3"][12] is None
    assert out["hourly_pivot_last"] == expected_prev_hour_pivot


def test_cm_hourly_pivots_can_enable_r3_s3():
    idx = pd.date_range("2024-01-01 09:00", periods=24, freq="5min")
    df = pd.DataFrame(
        {
            "open": [100.0] * 24,
            "high": [101.0] * 24,
            "low": [99.0] * 24,
            "close": [100.0] * 24,
        },
        index=idx,
    )

    out = cm_hourly_pivots(df, show_r3_s3=True)

    assert out["hourly_r3"][12] == 103.0
    assert out["hourly_s3"][12] == 97.0
