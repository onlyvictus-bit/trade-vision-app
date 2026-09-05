import numpy as np
import pandas as pd

from shared.indicators.self_indc import rsi_div_auto


def _frame(freq="5min", n=260):
    idx = pd.date_range("2026-05-01 10:00", periods=n, freq=freq)
    x = np.linspace(0, 8 * np.pi, n)
    close = 100 + np.sin(x) * 5 + np.sin(x * 0.37) * 2
    open_ = close + np.cos(x) * 0.2
    high = np.maximum(open_, close) + 0.7
    low = np.minimum(open_, close) - 0.7
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": 1000}, index=idx)


def test_rsi_div_auto_uses_5m_params_and_contract():
    out = rsi_div_auto(_frame("5min"))
    assert set(out) == {"signals", "params", "rsi"}
    assert out["params"]["timeframe"] == "5m"
    assert out["params"]["rsi_length"] == 9
    assert out["params"]["pivot_left"] == 12
    assert out["params"]["pivot_right"] == 10
    assert len(out["rsi"]) == 260
    assert all("index" in row and "pivot_index" in row for row in out["signals"])
    assert len({row["time"] for row in out["signals"]}) == len(out["signals"])


def test_rsi_div_auto_timeframe_mapping():
    assert rsi_div_auto(_frame("15min", 180))["params"]["timeframe"] == "15m"
    assert rsi_div_auto(_frame("1h", 180))["params"]["timeframe"] == "1h"


def test_rsi_div_auto_flat_data_safe():
    idx = pd.date_range("2026-05-01 10:00", periods=100, freq="5min")
    df = pd.DataFrame({"Open": 100, "High": 100, "Low": 100, "Close": 100, "Volume": 1000}, index=idx)
    out = rsi_div_auto(df)
    assert isinstance(out, dict)
    assert out["signals"] == []
