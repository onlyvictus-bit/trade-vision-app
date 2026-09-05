import pandas as pd

from shared.indicators.self_indc import compute_all, sfp_hybrid_markers


def test_sfb_hybrid_contract_and_frontend_params():
    rows = []
    for i in range(90):
        base = 100 + i * 0.08
        rows.append([base, base + 0.5, base - 0.5, base + 0.2, 1000])

    # A clear swing low with later liquidity sweep.
    rows[30] = [101.0, 102.0, 90.0, 96.0, 1500]
    for j in range(25, 36):
        if j != 30:
            rows[j] = [104.0, 106.0, 98.0, 105.0, 1200]
    rows[52] = [94.0, 103.5, 89.0, 100.0, 1800]

    idx = pd.date_range("2026-05-01 09:30", periods=len(rows), freq="5min")
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"], index=idx)

    out = sfp_hybrid_markers(df, trend_fast_len=2, trend_slow_len=4)

    assert out["params"]["trend_fast_len"] == 2
    assert out["params"]["trend_slow_len"] == 4
    assert out["params"]["trend_filter_type"] == "EMA"
    assert len(out["trend_fast"]) == len(df)
    assert len(out["trend_slow"]) == len(df)
    assert "signals" in out
    assert all({"time", "name", "direction", "index", "sweep_level", "swing_index", "atr"} <= set(e) for e in out["signals"])

    all_ind = compute_all(df, params={"sfb_trend_fast_len": 3, "sfb_trend_slow_len": 6})
    assert all_ind["si_sfb_hybrid"]["params"]["trend_fast_len"] == 3
    assert all_ind["si_sfb_hybrid"]["params"]["trend_slow_len"] == 6
