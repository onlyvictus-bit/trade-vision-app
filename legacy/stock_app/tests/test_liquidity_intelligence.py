import numpy as np
import pandas as pd

from shared.indicators.self_indc import liquidity_intelligence


def _frame(n=260):
    idx = pd.date_range("2026-05-01 10:00", periods=n, freq="5min")
    x = np.linspace(0, 8 * np.pi, n)
    close = 100 + np.sin(x) * 4 + np.linspace(0, 3, n)
    open_ = close + np.cos(x) * 0.25
    high = np.maximum(open_, close) + 0.8
    low = np.minimum(open_, close) - 0.8
    volume = 1000 + (np.sin(x) + 1) * 500
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)


def test_liquidity_intelligence_outputs_contract():
    out = liquidity_intelligence(_frame(), pivot_len=3, ema_slow_len=40)
    assert set(out) == {"signals", "levels", "latest"}
    assert isinstance(out["signals"], list)
    assert isinstance(out["levels"], list)
    assert all("index" in row for row in out["signals"])
    assert all("time" in row and "name" in row for row in out["levels"])
    assert len({row["time"] for row in out["signals"]}) == len(out["signals"])
    if out["signals"]:
        sig = out["signals"][0]
        assert {"entry", "sl", "tp1", "tp2", "tp3", "quality", "regime", "bias"} <= set(sig)


def test_liquidity_intelligence_flat_data_safe():
    idx = pd.date_range("2026-05-01 10:00", periods=120, freq="5min")
    df = pd.DataFrame({"Open": 100, "High": 100, "Low": 100, "Close": 100, "Volume": 1000}, index=idx)
    out = liquidity_intelligence(df, ema_slow_len=40)
    assert isinstance(out, dict)
    assert out["signals"] == []
