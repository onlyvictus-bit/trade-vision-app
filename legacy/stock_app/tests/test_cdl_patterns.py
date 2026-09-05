import pandas as pd

from shared.indicators.pta import _cdl_patterns_raw, cdl_patterns
from shared.indicators.self_indc import _select_best_cdl_events, cdl_patterns_adv


def _frame(rows, start="2026-05-01 10:00"):
    idx = pd.date_range(start, periods=len(rows), freq="5min")
    return pd.DataFrame(rows, index=idx, columns=["Open", "High", "Low", "Close"])


def _overlap_frame():
    rows = [[100, 101, 99, 100.5] for _ in range(24)]
    rows.append([100.0, 101.0, 98.0, 99.0])
    rows.append([100.1, 100.106, 94.0, 100.105])
    return _frame(rows)


def test_raw_doji_threshold_is_exact():
    rows = [[100, 101, 99, 100.8] for _ in range(20)]
    rows.append([100.00, 101.00, 99.00, 100.19])
    rows.append([100.00, 101.00, 99.00, 100.21])
    events = cdl_patterns(_frame(rows), strict=False)
    doji_indexes = [e["index"] for e in events if e["name"] == "Doji"]
    assert 20 in doji_indexes
    assert 21 not in doji_indexes


def test_raw_emits_all_overlapping_patterns():
    raw = _cdl_patterns_raw(_overlap_frame())
    names = [e["name"] for e in raw if e["index"] == 25]
    assert "Doji" in names
    assert "Hammer" in names


def test_strict_priority_picks_higher_over_lower():
    events = cdl_patterns(_overlap_frame(), strict=True, cooldown_bars=1)
    names = [e["name"] for e in events if e["index"] == 25]
    assert names == ["Hammer"]


def test_strict_blocks_session_open_marker():
    rows = [[100, 101, 99, 100.8] for _ in range(20)]
    rows.append([100.00, 101.00, 99.00, 100.01])
    df = _frame(rows, start="2026-05-01 07:35")
    assert df.index[20].strftime("%H:%M") == "09:15"
    assert cdl_patterns(df, strict=True) == []


def test_strict_drops_inside_bar_spam():
    rows = [[100, 101, 99, 100.6] for _ in range(25)]
    rows.append([100.2, 100.8, 99.2, 100.4])
    raw = cdl_patterns(_frame(rows), strict=False)
    strict = cdl_patterns(_frame(rows), strict=True)
    assert any(e["name"] == "Inside Bar" for e in raw)
    assert not any(e["name"] == "Inside Bar" for e in strict)


def test_strict_keeps_contextual_bullish_engulfing():
    rows = []
    price = 120.0
    for _ in range(24):
        rows.append([price, price + 0.4, price - 1.2, price - 0.8])
        price -= 0.8
    rows.append([100.0, 100.4, 97.8, 98.4])
    rows.append([98.2, 102.4, 97.6, 101.8])
    events = cdl_patterns(_frame(rows), strict=True)
    assert any(e["name"] == "Bull Engulf" and e["index"] == 25 for e in events)


def test_strict_applies_cooldown_and_no_same_candle_conflict():
    rows = []
    price = 130.0
    for _ in range(24):
        rows.append([price, price + 0.3, price - 1.0, price - 0.6])
        price -= 0.6
    rows.extend([
        [100.0, 100.4, 97.8, 98.4],
        [98.2, 102.4, 97.6, 101.8],
        [101.8, 102.0, 101.0, 101.1],
        [101.0, 103.5, 100.8, 103.2],
    ])
    events = cdl_patterns(_frame(rows), strict=True, cooldown_bars=12)
    assert len(events) <= 1
    for event in events:
        same_time = [e for e in events if e["time"] == event["time"]]
        assert len({e["direction"] for e in same_time}) == 1


def test_cooldown_boundary_exact():
    events = [
        {"time": "2026-05-01 10:00", "name": "Bull Engulf", "direction": "bull", "index": 10},
        {"time": "2026-05-01 10:55", "name": "Bull Engulf", "direction": "bull", "index": 21},
        {"time": "2026-05-01 11:00", "name": "Bull Engulf", "direction": "bull", "index": 22},
    ]
    selected = _select_best_cdl_events(events, cooldown_bars=12)
    assert [e["index"] for e in selected] == [10, 22]


def test_adv_api_preserves_index_and_accepts_cooldown():
    events = [
        {"time": "2026-05-01 10:00", "name": "Doji", "direction": "neutral", "index": 20},
        {"time": "2026-05-01 10:00", "name": "Bull Engulf", "direction": "bull", "index": 20},
    ]
    selected = _select_best_cdl_events(events, cooldown_bars=1)
    assert selected == [{"time": "2026-05-01 10:00", "name": "Bull Engulf", "direction": "bull", "index": 20}]
    assert cdl_patterns_adv(_frame([[100, 101, 99, 100.5] for _ in range(25)]), cooldown_bars=1) == []


def test_flat_data_no_crash():
    df = _frame([[100, 100, 100, 100] for _ in range(40)])
    assert isinstance(cdl_patterns(df), list)
    assert isinstance(cdl_patterns(df, strict=False), list)


def test_strict_default_is_sparse_enough_for_chart():
    rows = []
    price = 120.0
    for _ in range(90):
        rows.append([price, price + 1.2, price - 0.3, price + 0.8])
        price += 0.2
        rows.append([price, price + 0.4, price - 1.1, price - 0.7])
        price -= 0.1
    events = cdl_patterns(_frame(rows), strict=True)
    assert len(events) <= len(rows) // 20
