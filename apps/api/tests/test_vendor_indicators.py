import warnings

import pandas as pd

from app.vendor.stock_app.shared.indicators.self_indc import _vwap_bands


def test_vwap_bands_weekly_timezone_aware_grouping_does_not_drop_timezone_warning():
    index = pd.date_range("2026-03-02 09:15", periods=30, freq="1min", tz="Asia/Kolkata")
    frame = pd.DataFrame(
        {
            "open": [100.0 + i * 0.1 for i in range(len(index))],
            "high": [100.4 + i * 0.1 for i in range(len(index))],
            "low": [99.8 + i * 0.1 for i in range(len(index))],
            "close": [100.2 + i * 0.1 for i in range(len(index))],
            "volume": [1000 + i for i in range(len(index))],
        },
        index=index,
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = _vwap_bands(frame, "W")

    warning_messages = [str(item.message) for item in caught]
    assert not any("drop timezone information" in message for message in warning_messages)
    assert list(result.index) == list(frame.index)
    assert len(result) == len(frame)
    assert {"vwap", "upper_1", "lower_1", "upper_2", "lower_2", "upper_3", "lower_3"} <= set(result.columns)
