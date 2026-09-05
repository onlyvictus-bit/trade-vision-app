import numpy as np
import pandas as pd

from shared.indicators.self_indc import compute_all, ctz_gann_swing


def test_ctz_gann_swing_indicator_contract():
    n = 180
    x = np.arange(n)
    close = 100 + np.sin(x / 6) * 8 + x * 0.03
    open_ = close + np.sin(x / 3) * 0.4
    high = np.maximum(open_, close) + 1.2
    low = np.minimum(open_, close) - 1.2
    volume = np.where((x % 23) == 0, 3000, 1000)

    idx = pd.date_range("2026-01-01 09:30", periods=n, freq="5min")
    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )

    out = ctz_gann_swing(df, label_layer="F1", min_swing_pct=0.5)

    assert "signals" in out
    assert "long" in out and "short" in out
    assert "layers" in out and {"F1", "SF1", "F2", "SF2", "F3", "SF3"} <= set(out["layers"])
    assert len(out["long"]) == len(df)
    assert len(out["short"]) == len(df)
    assert len(out["q_mid"]) == len(df)
    assert len(out["rsi"]) == len(df)
    assert all("index" in e and "time" in e and "direction" in e for e in out["signals"])

    all_ind = compute_all(df)
    assert "si_ctz_gann" in all_ind
    assert "signals" in all_ind["si_ctz_gann"]
