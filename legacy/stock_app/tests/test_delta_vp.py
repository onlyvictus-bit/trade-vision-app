import pandas as pd

from shared.indicators.self_indc import compute_all, delta_vp


def _ohlcv(n=180):
    idx = pd.date_range("2026-05-01 09:15", periods=n, freq="5min")
    rows = []
    price = 100.0
    for i in range(n):
        drift = 0.01 if i > 40 else 0.0
        open_ = price
        close = open_ + drift
        high = max(open_, close) + 0.12
        low = min(open_, close) - 0.12
        rows.append([open_, high, low, close, 1000 + i])
        price = close
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=idx)


def test_delta_vp_output_contract():
    out = delta_vp(_ohlcv())

    assert set(out) >= {"signals", "levels", "trade_lines", "poc", "vah", "pal", "answers", "latest"}
    assert set(out["trade_lines"]) == {"entry", "sl", "target", "level"}
    assert len(out["poc"]) == 180
    assert len(out["vah"]) == 180
    assert len(out["pal"]) == 180
    assert len(out["trade_lines"]["entry"]) == 180
    assert {
        "breakout_confirmed",
        "should_i_enter",
        "entry",
        "sl",
        "target",
        "retest_addon_available",
        "fake_or_weak",
        "poc",
        "pal",
    }.issubset(out["answers"])


def test_compute_all_includes_delta_vp():
    all_ind = compute_all(_ohlcv())

    assert "si_delta_vp" in all_ind
    assert set(all_ind["si_delta_vp"]) >= {"signals", "levels", "trade_lines", "poc", "vah", "pal", "answers"}
