from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    CandleBar,
    CandleSeries,
    OrbBuildRequest,
    OrbStrategyConfig,
)
from app.orb import build_orb_candidate


client = TestClient(app)
FIVE_MINUTES_NS = 300_000_000_000
SESSION_OPEN_UTC_NS = int(
    datetime(2026, 7, 20, 3, 45, tzinfo=timezone.utc).timestamp()
    * 1_000_000_000
)


def _bar(index: int, *, open_: float, high: float, low: float, close: float, volume: float = 1000.0, day_offset: int = 0):
    return CandleBar(
        symbol="RELIANCE",
        timeframe="5m",
        timestamp_ns=SESSION_OPEN_UTC_NS
        + day_offset * 86_400_000_000_000
        + index * FIVE_MINUTES_NS,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        source="user_csv",
        sequence_number=day_offset * 100 + index + 1,
    )


def _range_bars(day_offset: int = 0):
    return [
        _bar(0, open_=100.0, high=100.6, low=99.5, close=100.2, day_offset=day_offset),
        _bar(1, open_=100.2, high=101.0, low=99.8, close=100.7, day_offset=day_offset),
        _bar(2, open_=100.7, high=100.9, low=99.0, close=100.1, day_offset=day_offset),
    ]


def _request(bars, *, config: OrbStrategyConfig | None = None, decision_time_ns: int | None = None):
    series = CandleSeries(
        symbol="RELIANCE",
        timeframe="5m",
        bars=bars,
        snapshot_id="orb-fixture",
        schema_version="candles.v1",
    )
    decision = decision_time_ns or max(
        bar.timestamp_ns + FIVE_MINUTES_NS for bar in bars
    )
    return OrbBuildRequest(
        series=series,
        decision_time_ns=decision,
        source_snapshot_hash="a" * 64,
        config=config or OrbStrategyConfig(),
    )


def test_tv_v189_001_bar_count_range_locks_only_after_last_bar_close():
    bars = _range_bars()
    before_lock = build_orb_candidate(
        _request(bars, decision_time_ns=bars[-1].timestamp_ns + FIVE_MINUTES_NS - 1)
    )
    at_lock = build_orb_candidate(_request(bars))
    assert before_lock.opening_range is None
    assert before_lock.range_locked is False
    assert at_lock.opening_range
    assert at_lock.opening_range.opening_range_high == 101.0
    assert at_lock.opening_range.opening_range_low == 99.0
    assert at_lock.range_locked is True


def test_tv_v189_002_nse_session_alignment_uses_0915_local_open():
    result = build_orb_candidate(_request(_range_bars()))
    assert result.opening_range
    assert result.opening_range.range_start_local == "09:15"
    assert result.session.timezone_offset_minutes == 330
    assert result.session.open_time == "09:15"


def test_tv_v189_003_breakout_long_builder():
    bars = _range_bars() + [
        _bar(3, open_=100.8, high=101.6, low=100.7, close=101.4, volume=1800.0)
    ]
    result = build_orb_candidate(_request(bars))
    assert result.signal.signal_type == "BREAKOUT_LONG"
    assert result.signal.entry_price == 101.0
    assert result.signal.stop_price == 99.0
    assert result.signal.target_price == 105.0


def test_tv_v189_004_breakdown_short_builder():
    bars = _range_bars() + [
        _bar(3, open_=99.4, high=99.5, low=98.4, close=98.7, volume=1800.0)
    ]
    result = build_orb_candidate(_request(bars))
    assert result.signal.signal_type == "BREAKDOWN_SHORT"
    assert result.signal.entry_price == 99.0
    assert result.signal.stop_price == 101.0
    assert result.signal.target_price == 95.0


def test_tv_v189_005_reversal_short_builder():
    bars = _range_bars() + [
        _bar(3, open_=100.8, high=101.4, low=100.4, close=100.7, volume=1600.0)
    ]
    result = build_orb_candidate(
        _request(
            bars,
            config=OrbStrategyConfig(strategy_family="orr_reversal"),
        )
    )
    assert result.signal.signal_type == "REVERSAL_SHORT"
    assert result.features.false_break_high is True


def test_tv_v189_006_reversal_long_builder():
    bars = _range_bars() + [
        _bar(3, open_=99.2, high=99.6, low=98.6, close=99.3, volume=1600.0)
    ]
    result = build_orb_candidate(
        _request(
            bars,
            config=OrbStrategyConfig(strategy_family="orr_reversal"),
        )
    )
    assert result.signal.signal_type == "REVERSAL_LONG"
    assert result.features.false_break_low is True


def test_tv_v189_007_hybrid_requires_configured_volume_confirmation():
    bars = _range_bars() + [
        _bar(3, open_=100.8, high=101.6, low=100.7, close=101.4, volume=10.0)
    ]
    result = build_orb_candidate(
        _request(
            bars,
            config=OrbStrategyConfig(
                strategy_family="hybrid_orb",
                require_volume_confirmation=True,
            ),
        )
    )
    assert result.signal.signal_type == "NO_SETUP"


def test_tv_v189_008_clock_window_uses_only_fully_closed_bars():
    bars = _range_bars() + [
        _bar(3, open_=100.1, high=101.2, low=99.9, close=101.1)
    ]
    result = build_orb_candidate(
        _request(
            bars,
            config=OrbStrategyConfig(
                range_mode="clock_window",
                range_start="09:15",
                range_end="09:30",
            ),
        )
    )
    assert result.opening_range
    assert result.opening_range.range_bar_count == 3
    assert result.opening_range.last_bar_timestamp_ns == bars[2].timestamp_ns


def test_tv_v189_009_latest_session_resets_previous_day_range():
    previous = _range_bars(day_offset=0)
    current = [
        _bar(0, open_=200.0, high=201.0, low=199.0, close=200.2, day_offset=1),
        _bar(1, open_=200.2, high=202.0, low=200.0, close=201.7, day_offset=1),
        _bar(2, open_=201.7, high=201.9, low=198.5, close=200.0, day_offset=1),
    ]
    result = build_orb_candidate(_request(previous + current))
    assert result.opening_range
    assert result.opening_range.opening_range_high == 202.0
    assert result.opening_range.opening_range_low == 198.5


def test_tv_v189_010_duplicate_and_incomplete_bars_are_excluded():
    bars = _range_bars()
    duplicate = bars[1].model_copy(update={"sequence_number": 99})
    incomplete = _bar(3, open_=100.0, high=102.0, low=99.0, close=101.8)
    decision = incomplete.timestamp_ns + FIVE_MINUTES_NS - 1
    result = build_orb_candidate(
        _request(bars + [duplicate, incomplete], decision_time_ns=decision)
    )
    assert result.no_future_leakage is True
    assert any("duplicate" in item.lower() for item in result.warnings)
    assert any("incomplete/future" in item.lower() for item in result.warnings)


def test_tv_v189_011_same_input_is_hash_deterministic():
    request = _request(
        _range_bars()
        + [_bar(3, open_=100.8, high=101.6, low=100.7, close=101.4)]
    )
    first = build_orb_candidate(request)
    second = build_orb_candidate(request)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.deterministic_hash == second.deterministic_hash


def test_tv_v189_012_api_and_manifest_remain_research_only():
    request = _request(
        _range_bars()
        + [_bar(3, open_=100.8, high=101.6, low=100.7, close=101.4)]
    )
    response = client.post("/api/v1/orb/build", json=request.model_dump(mode="json"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trade_allowed"] is False
    assert data["paper_execution_attempted"] is False
    assert data["broker_order_created"] is False
    assert data["order_routing_enabled"] is False
    assert data["live_trading_blocked"] is True
    manifest = client.get("/api/system/features").json()["data"]["capabilities"]
    capability = next(item for item in manifest if item["name"] == "ORB Core Foundation")
    assert capability["status"] == "mock"
