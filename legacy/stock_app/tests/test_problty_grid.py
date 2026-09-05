import pandas as pd

from shared.indicators.self_indc import compute_all, problty_grid


def _frame(n=160):
    idx = pd.date_range("2026-05-01 09:30", periods=n, freq="5min")
    rows = []
    price = 100.0
    for i in range(n):
        open_ = price
        close = open_ + (0.02 if i % 12 < 8 else -0.01)
        high = max(open_, close) + 0.15
        low = min(open_, close) - 0.15
        rows.append([open_, high, low, close, 1000 + i * 5])
        price = close
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=idx)


def test_problty_grid_output_contract():
    out = problty_grid(_frame())

    assert set(out) >= {"signals", "events", "levels", "probabilities", "vwap_distance", "projection_boxes", "dashboard", "config"}
    for key in ["session_open", "session_vwap", "opening_high", "opening_low", "up_4", "dn_4"]:
        assert key in out["levels"]
        assert len(out["levels"][key]) == 160
    assert "u100_probability" in out["dashboard"]
    assert "d100_probability" in out["dashboard"]
    assert len(out["vwap_distance"]) == 160


def test_compute_all_includes_problty_grid():
    all_ind = compute_all(_frame())

    assert "si_problty_grid" in all_ind
    assert set(all_ind["si_problty_grid"]) >= {"signals", "levels", "probabilities", "dashboard"}
