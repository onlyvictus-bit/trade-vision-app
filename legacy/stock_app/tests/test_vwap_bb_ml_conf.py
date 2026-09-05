import numpy as np
import pandas as pd

from shared.indicators.self_indc import compute_all, vwap_bb_ml_conf


def _df():
    n = 180
    idx = pd.date_range("2026-01-01 09:15", periods=n, freq="5min")
    close = 100 + np.sin(np.linspace(0, 16, n)) * 2 + np.linspace(0, 3, n)
    volume = np.full(n, 1500.0)
    volume[60:90] = 3500.0
    return pd.DataFrame(
        {
            "open": close + np.sin(np.linspace(0, 6, n)) * 0.15,
            "high": close + 0.9,
            "low": close - 0.9,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )


def test_vwap_bb_ml_conf_output_contract():
    out = vwap_bb_ml_conf(_df())

    assert set(out) >= {"signals", "levels", "trade_lines", "trade_segments", "dashboard", "ml_meta"}
    assert set(out["trade_lines"]) == {"entry", "sl", "target"}
    assert set(out["levels"]) >= {"vwap", "VWU1", "VWU2", "VWU3", "VWL1", "VWL2", "VWL3", "BBU1a", "BBU1b", "BBL1a", "BBL1b"}
    assert len(out["levels"]["vwap"]) == len(_df())
    assert len(out["trade_lines"]["entry"]) == len(_df())
    assert "latest_regime" in out["dashboard"]


def test_vwap_bb_ml_conf_trade_segments_are_ordered():
    out = vwap_bb_ml_conf(_df())

    for seg in out["trade_segments"]:
        if seg["side"] == "buy":
            assert seg["sl"] < seg["entry"] < seg["target"]
        elif seg["side"] == "sell":
            assert seg["target"] < seg["entry"] < seg["sl"]


def test_compute_all_includes_vwap_bb_ml_conf():
    out = compute_all(_df())

    assert "si_vwap_bb_ml_conf" in out
    assert len(out["si_vwap_bb_ml_conf"]["levels"]["vwap"]) == len(_df())
