import numpy as np
import pandas as pd

from shared.indicators.self_indc import HybridMlCprConfig, compute_all, hybrid_ml_cpr


def _df():
    n = 90
    idx = pd.date_range("2026-01-01 09:15", periods=n, freq="5min")
    close = np.full(n, 100.0)
    close[20:40] = np.linspace(100, 98, 20)
    close[40:60] = np.linspace(98, 102, 20)
    close[60:] = np.linspace(102, 101, 30)
    return pd.DataFrame(
        {
            "open": close + 0.1,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": np.r_[np.full(20, 1000), np.full(n - 20, 2000)],
        },
        index=idx,
    )


def test_hybrid_ml_cpr_output_contract():
    out = hybrid_ml_cpr(_df(), HybridMlCprConfig(enable_global_ml=False, ml_min_confidence=0))

    assert set(out) >= {"signals", "levels", "trade_lines", "trade_segments", "confidence", "dashboard", "signal"}
    assert set(out["levels"]) >= {"vwap", "vwap_up", "vwap_dn", "bb_up", "bb_dn", "bb_basis"}
    assert set(out["trade_lines"]) == {"entry", "sl", "target"}
    assert set(out["confidence"]) >= {"buy", "sell", "confluence", "reversal", "success_rate"}
    assert len(out["levels"]["vwap"]) == len(_df())
    assert len(out["trade_lines"]["entry"]) == len(_df())


def test_hybrid_ml_cpr_can_emit_trade_signal_and_levels():
    out = hybrid_ml_cpr(_df(), HybridMlCprConfig(enable_global_ml=False, ml_min_confidence=0))

    assert any(evt["signal"] in {"BUY", "SELL", "UP_REV", "DOWN_REV", "UPPER_CONFL", "LOWER_CONFL"} for evt in out["signals"])
    assert "current_confidence" in out["dashboard"]
    assert "success_rate" in out["dashboard"]
    for seg in out["trade_segments"]:
        if seg["side"] == "buy":
            assert seg["sl"] < seg["entry"] < seg["target"]
        elif seg["side"] == "sell":
            assert seg["target"] < seg["entry"] < seg["sl"]


def test_compute_all_includes_hybrid_ml_cpr():
    out = compute_all(_df())

    assert "si_hybrid_ml_cpr" in out
    assert len(out["si_hybrid_ml_cpr"]["levels"]["vwap"]) == len(_df())
