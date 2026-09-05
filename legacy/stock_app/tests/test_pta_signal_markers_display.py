import pandas as pd

from shared.indicators import pta_signal_markers as pta


def test_pta_signal_markers_include_candle_index(monkeypatch):
    idx = pd.date_range("2026-01-01 09:15", periods=40, freq="5min")
    df = pd.DataFrame(
        {
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 100,
        },
        index=idx,
    )
    mask = pd.Series(False, index=idx)
    mask.iloc[25] = True

    monkeypatch.setattr(pta, "_reg", lambda: {"fake_signal": lambda data: mask})

    events = pta._signal_to_markers(df, "fake_signal", "Fake Bull", "bull")

    assert events == [
        {
            "time": "2026-01-01 11:20",
            "index": 25,
            "name": "Fake Bull",
            "direction": "bull",
        }
    ]


def test_pta_compute_keys_keep_index_for_visible_markers(monkeypatch):
    idx = pd.date_range("2026-01-01 09:15", periods=45, freq="5min")
    df = pd.DataFrame(
        {
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 100,
        },
        index=idx,
    )
    mask = pd.Series(False, index=idx)
    mask.iloc[30] = True

    def fake_registry():
        return {
            "ebsw_bull": lambda data: mask,
            "dsp_bull": lambda data: mask,
            "entropy_low_bull": lambda data: mask,
        }

    monkeypatch.setattr(pta, "_reg", fake_registry)

    output = pta.compute_all(df)

    for key in ("pta_ebsw", "pta_dsp", "pta_entropy"):
        assert output[key]
        assert output[key][0]["index"] == 30
