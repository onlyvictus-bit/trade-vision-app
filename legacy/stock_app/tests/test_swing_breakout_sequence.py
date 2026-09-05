import pandas as pd

from shared.indicators.self_indc import swing_breakout_sequence


def test_swing_breakout_sequence_contract():
    closes = [
        100, 96, 92, 88, 84, 80, 86, 92, 98, 104, 110,
        106, 101, 96, 91, 88, 94, 101, 108, 114, 120,
        116, 111, 105, 99, 93, 88, 95, 103, 112, 122,
        126, 129, 131, 133, 134, 135, 136, 137, 138, 139, 140,
    ]
    idx = pd.date_range("2026-05-01 09:30", periods=len(closes), freq="5min")
    df = pd.DataFrame({
        "Open": [v - 0.2 for v in closes],
        "High": [v + 1.0 for v in closes],
        "Low": [v - 1.0 for v in closes],
        "Close": closes,
        "Volume": 1000,
    }, index=idx)

    out = swing_breakout_sequence(df, swing_length=2, internal_length=2)
    signals = out["signals"]

    assert signals
    assert all({"time", "name", "direction", "index", "entry", "stop", "target", "points"} <= set(e) for e in signals)
    assert all(0 <= e["index"] < len(df) for e in signals)
    assert any(e["direction"] == "bull" for e in signals)
