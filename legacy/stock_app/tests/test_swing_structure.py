import numpy as np
import pandas as pd

from shared.indicators.self_indc import swing_structure


def test_swing_structure_no_name_error_and_contract():
    idx = pd.date_range("2026-05-01 10:00", periods=220, freq="5min")
    x = np.linspace(0, 8 * np.pi, len(idx))
    close = 100 + np.sin(x) * 5 + np.linspace(0, 4, len(idx))
    df = pd.DataFrame({
        "Open": close + np.cos(x) * 0.2,
        "High": close + 0.8,
        "Low": close - 0.8,
        "Close": close,
        "Volume": 1000,
    }, index=idx)
    events = swing_structure(df)
    assert isinstance(events, list)
    assert all({"time", "name", "direction"} <= set(e) for e in events)
    assert events
    assert all({"index", "confirmed_index", "price"} <= set(e) for e in events)
    assert len({e["time"] for e in events}) == len(events)
    assert {e["name"] for e in events} <= {"HH Structure", "HL Structure", "LH Structure", "LL Structure"}
