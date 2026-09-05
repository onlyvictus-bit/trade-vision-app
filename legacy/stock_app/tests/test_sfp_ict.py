import pandas as pd

from shared.indicators.self_indc import sfp_markers


def test_sfp_ict_sweep_liquidity_contract():
    rows = []
    for i in range(80):
        base = 100 + (i % 7) * 0.1
        rows.append([base, base + 0.4, base - 0.4, base + 0.1])

    # Confirmed swing low at index 25.
    rows[25] = [100.0, 102.0, 90.0, 96.0]
    for j in range(20, 31):
        if j != 25:
            rows[j] = [102.0, 104.0, 96.0, 101.0]

    # Sweep below swing low, close back above level and below swing body bottom.
    rows[45] = [91.0, 94.0, 89.0, 92.0]

    # Confirmed swing high at index 55.
    rows[55] = [100.0, 110.0, 98.0, 104.0]
    for j in range(50, 61):
        if j != 55:
            rows[j] = [101.0, 105.0, 99.0, 102.0]

    # Sweep above swing high, close back below level and above swing body top.
    rows[75] = [106.5, 112.0, 105.0, 106.0]

    idx = pd.date_range("2026-05-01 09:30", periods=len(rows), freq="5min")
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)
    df["Volume"] = 1000

    events = sfp_markers(df)

    assert any(e["name"] == "SFP Long" and e["index"] == 45 for e in events)
    assert any(e["name"] == "SFP Short" and e["index"] == 75 for e in events)
    assert all({"time", "name", "direction", "index", "sweep_level", "swing_index", "atr"} <= set(e) for e in events)
