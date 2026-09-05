import numpy as np
import pandas as pd

from shared.indicators.self_indc import liquid_reversal_bands


def _frame(n=180):
    idx = pd.date_range("2026-05-01 10:00", periods=n, freq="5min")
    x = np.linspace(0, 8 * np.pi, n)
    close = 100 + np.sin(x) * 6 + np.linspace(0, 2, n)
    open_ = close + np.cos(x) * 0.3
    high = np.maximum(open_, close) + 0.8
    low = np.minimum(open_, close) - 0.8
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": 1000}, index=idx)


def test_liquid_reversal_bands_outputs_overlay_and_signals():
    out = liquid_reversal_bands(_frame(), fair_len=20, z_len=30, smooth_len=8, cooldown_bars=3)
    assert set(out) == {"fair", "upper", "lower", "outer_upper", "outer_lower", "signals"}
    assert out["fair"]
    assert out["upper"]
    assert out["lower"]
    assert len(out["upper"]) == len(out["lower"])
    assert all("time" in row and "value" in row for row in out["fair"])
    assert all("index" in row for row in out["signals"])
    assert len({row["time"] for row in out["signals"]}) == len(out["signals"])


def test_liquid_reversal_bands_flat_data_safe():
    idx = pd.date_range("2026-05-01 10:00", periods=120, freq="5min")
    df = pd.DataFrame({"Open": 100, "High": 100, "Low": 100, "Close": 100, "Volume": 1000}, index=idx)
    out = liquid_reversal_bands(df, fair_len=10, z_len=20, smooth_len=5)
    assert isinstance(out, dict)
    assert out["signals"] == []
