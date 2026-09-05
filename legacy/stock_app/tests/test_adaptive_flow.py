import numpy as np
import pandas as pd

from shared.indicators.self_indc import adaptive_flow


def _frame(n=260):
    idx = pd.date_range("2026-05-01 10:00", periods=n, freq="5min")
    x = np.linspace(0, 10 * np.pi, n)
    close = 100 + np.sin(x) * 5 + np.linspace(0, 8, n)
    open_ = close + np.cos(x) * 0.25
    high = np.maximum(open_, close) + 0.7
    low = np.minimum(open_, close) - 0.7
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": 1000}, index=idx)


def test_adaptive_flow_outputs_strategy_overlay():
    out = adaptive_flow(_frame(), flow_len=8, slow_len=18, stop_lookback=10, pivot_left=4, pivot_right=4)
    assert set(out) == {"kama", "stop", "upper", "lower", "ema200", "vwap", "signals", "structure"}
    assert out["kama"]
    assert out["stop"]
    assert out["upper"]
    assert out["lower"]
    assert all("time" in row and "value" in row for row in out["kama"])
    assert all("index" in row for row in out["signals"])
    assert len({row["time"] for row in out["signals"]}) == len(out["signals"])


def test_adaptive_flow_flat_data_safe():
    idx = pd.date_range("2026-05-01 10:00", periods=120, freq="5min")
    df = pd.DataFrame({"Open": 100, "High": 100, "Low": 100, "Close": 100, "Volume": 1000}, index=idx)
    out = adaptive_flow(df, flow_len=6, slow_len=15)
    assert isinstance(out, dict)
    assert out["signals"] == []
