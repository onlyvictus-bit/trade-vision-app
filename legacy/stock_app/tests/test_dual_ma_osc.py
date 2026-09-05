import numpy as np
import pandas as pd

from shared.indicators.self_indc import compute_all, dual_ma_osc


def _df(close):
    idx = pd.date_range("2026-01-01 09:15", periods=len(close), freq="5min")
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(len(close), 1000),
        },
        index=idx,
    )


def test_dual_ma_osc_output_contract_and_lengths():
    prices = np.r_[np.linspace(100, 130, 80), np.linspace(130, 95, 80)]
    out = dual_ma_osc(_df(prices))

    expected = {
        "signals",
        "fast_ma",
        "slow_ma",
        "spread",
        "smoothed_ma",
        "upper_band",
        "lower_band",
        "zero",
        "sq",
        "long_signal",
        "short_signal",
        "signal",
    }
    assert expected.issubset(out.keys())
    for key in expected - {"signals"}:
        assert len(out[key]) == len(prices)


def test_dual_ma_osc_generates_persistent_states_and_markers():
    prices = np.r_[
        np.full(30, 100.0),
        np.linspace(100, 140, 50),
        np.linspace(140, 90, 50),
    ]
    out = dual_ma_osc(_df(prices))

    assert 1 in out["sq"]
    assert -1 in out["sq"]
    assert any(sig == 1 for sig in out["signal"])
    assert any(sig == -1 for sig in out["signal"])
    assert any(evt["name"] == "DualMA Bull" for evt in out["signals"])
    assert any(evt["name"] == "DualMA Bear" for evt in out["signals"])


def test_compute_all_includes_dual_ma_osc():
    prices = np.linspace(100, 130, 90)
    out = compute_all(_df(prices))

    assert "si_dual_ma_osc" in out
    assert len(out["si_dual_ma_osc"]["smoothed_ma"]) == len(prices)
