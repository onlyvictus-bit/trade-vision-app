import pandas as pd

from shared.indicators.self_indc import inside_outside_bar


def test_inside_outside_mk_previous_candle_contract():
    idx = pd.date_range("2026-05-01 09:30", periods=5, freq="5min")
    df = pd.DataFrame({
        "Open": [100, 102, 101, 101.5, 101],
        "High": [105, 104, 106, 103, 102],
        "Low": [95, 96, 94, 98, 99],
        "Close": [102, 101, 103, 102, 101.5],
        "Volume": [1000] * 5,
    }, index=idx)

    out = inside_outside_bar(df, highlight_last_n=4)
    signals = out["signals"]

    assert out["prev_high"][1] == 105
    assert out["prev_low"][1] == 95
    assert out["prev_mid"][1] == 100
    assert any(e["name"] == "MK Out Bull" and e["index"] == 2 for e in signals)
    assert any(e["name"] == "MK Inside" and e["index"] == 3 for e in signals)
    assert all({"time", "name", "direction", "index"} <= set(e) for e in signals)
