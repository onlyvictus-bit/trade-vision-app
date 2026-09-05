import pandas as pd

from shared.indicators.self_indc import dark_cloud_piercing


def _frame(rows, start="2026-05-01 10:00"):
    idx = pd.date_range(start, periods=len(rows), freq="5min")
    return pd.DataFrame(rows, index=idx, columns=["Open", "High", "Low", "Close", "Volume"])


def test_strong_dark_cloud_overrides_weak():
    df = _frame([
        [100, 111, 99, 110, 1000],
        [112, 113, 100, 104, 1200],
    ])
    assert dark_cloud_piercing(df) == [{
        "time": "2026-05-01 10:05",
        "name": "Dark Cloud",
        "direction": "bear",
        "index": 1,
    }]


def test_weak_dark_cloud():
    df = _frame([
        [100, 111, 99, 110, 1000],
        [110, 112, 105, 105.5, 1200],
    ])
    assert dark_cloud_piercing(df)[0]["name"] == "Weak D.Cloud"


def test_strong_piercing_line_overrides_weak():
    df = _frame([
        [110, 111, 99, 100, 1000],
        [98, 107, 97, 106, 1200],
    ])
    assert dark_cloud_piercing(df) == [{
        "time": "2026-05-01 10:05",
        "name": "Piercing Line",
        "direction": "bull",
        "index": 1,
    }]


def test_weak_piercing_line():
    df = _frame([
        [110, 111, 99, 100, 1000],
        [100, 104.5, 98, 104, 1200],
    ])
    assert dark_cloud_piercing(df)[0]["name"] == "Weak Pierce"


def test_dark_cloud_piercing_flat_data_safe():
    df = _frame([[100, 100, 100, 100, 1000] for _ in range(5)])
    assert dark_cloud_piercing(df) == []
