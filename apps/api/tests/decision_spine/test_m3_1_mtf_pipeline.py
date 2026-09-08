from __future__ import annotations

import json

from app.behavior import paper_guidance_spine_legacy as legacy
from app.behavior.decision_spine.canonical_mtf_intelligence import (
    MTF_CONFIRMATION_VERSION,
    build_canonical_mtf_intelligence,
)
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import CandleBar, CandleSeries, PaperGuidanceRequest


BASE_NS = 1_714_815_600_000_000_000


def _series(timeframe: str, count: int, *, symbol: str = "RELIANCE", start: int = BASE_NS):
    duration = timeframe_duration_ns(timeframe)
    bars = []
    for index in range(count):
        close = 100.0 + index * 0.2
        bars.append(
            CandleBar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp_ns=start + index * duration,
                open=close - 0.05,
                high=close + 0.10,
                low=close - 0.10,
                close=close,
                volume=100_000.0 + index * 100.0,
                source="user_csv",
                sequence_number=index + 1,
            )
        )
    return CandleSeries(
        symbol=symbol,
        timeframe=timeframe,
        bars=bars,
        snapshot_id=f"{symbol}-{timeframe}",
        schema_version="candles.v1",
    )


def _primary(decision_time_ns: int):
    series = _series("5m", 30)
    request = PaperGuidanceRequest(
        symbol="RELIANCE",
        timeframe="5m",
        series=series,
        decision_time_ns=decision_time_ns,
    )
    return legacy.freeze_d2_closed_candle_snapshot(request, decision_time_ns=decision_time_ns)


def _freeze(decision_time_ns: int):
    return lambda request: legacy.freeze_d2_closed_candle_snapshot(
        request, decision_time_ns=decision_time_ns
    )


def _build(higher, *, decision_time_ns, required=None, direction="long"):
    primary = _primary(decision_time_ns)
    request = PaperGuidanceRequest(
        symbol="RELIANCE",
        timeframe="5m",
        series=_series("5m", 30),
        decision_time_ns=decision_time_ns,
        direction=direction,
        higher_timeframe_series=higher,
        required_higher_timeframes=required or [],
        indicator_ids=[],
    )
    return build_canonical_mtf_intelligence(
        request,
        primary,
        freeze_snapshot=_freeze(decision_time_ns),
        indicator_runtime=None,
    )


def test_m31e_001_partial_15m_bar_never_gets_authority():
    duration = timeframe_duration_ns("15m")
    decision = BASE_NS + 3 * duration + 7 * 60 * 1_000_000_000
    result = _build([_series("15m", 4)], decision_time_ns=decision, required=["15m"])
    record = result.records[0]
    assert record.timeframe == "15m"
    assert record.bars_used == 3
    assert record.last_closed_sequence == 3
    assert record.last_closed_ts == BASE_NS + 2 * duration
    assert record.excluded_incomplete_bars == 1
    assert result.usable_timeframes == ["15m"]
    assert result.missing_required_timeframes == []
    assert result.calculation_audit["future_or_incomplete_bar_authority_count"] == 0


def test_m31e_002_no_closed_htf_bar_is_typed_unavailable():
    duration = timeframe_duration_ns("30m")
    decision = BASE_NS + 7 * 60 * 1_000_000_000
    result = _build([_series("30m", 1)], decision_time_ns=decision, required=["30m"])
    record = result.records[0]
    assert record.availability == "UNAVAILABLE"
    assert record.reason_code == "HTF_NOT_CLOSED"
    assert record.bars_used == 0
    assert record.bias == "unavailable"
    assert "30m" in result.missing_required_timeframes
    assert result.blocks_promotion is True


def test_m31e_003_daily_uses_only_prior_completed_bar():
    day = timeframe_duration_ns("daily")
    decision = BASE_NS + day + 6 * 60 * 60 * 1_000_000_000
    daily = _series("daily", 2)
    result = _build([daily], decision_time_ns=decision, required=["daily"])
    record = result.records[0]
    assert record.bars_used == 1
    assert record.last_closed_sequence == 1
    assert record.excluded_incomplete_bars == 1
    assert record.source_snapshot_hash == result.snapshot_hashes["daily"]


def test_m31e_004_duplicate_timeframe_is_not_arbitrarily_overwritten():
    duration = timeframe_duration_ns("15m")
    decision = BASE_NS + 4 * duration
    first = _series("15m", 3)
    second = _series("15m", 3, start=BASE_NS + 1)
    result = _build([first, second], decision_time_ns=decision, required=["15m"])
    assert result.usable_timeframes == []
    assert result.missing_required_timeframes == ["15m"]
    assert len(result.records) == 1
    record = result.records[0]
    assert record.duplicate_timeframe is True
    assert record.reason_code == "DUPLICATE_TIMEFRAME"
    assert record.availability == "UNAVAILABLE"


def test_m31e_005_symbol_identity_mismatch_is_unavailable():
    duration = timeframe_duration_ns("15m")
    decision = BASE_NS + 4 * duration
    result = _build(
        [_series("15m", 3, symbol="TCS")],
        decision_time_ns=decision,
        required=["15m"],
    )
    record = result.records[0]
    assert record.symbol_identity_match is False
    assert record.availability == "UNAVAILABLE"
    assert record.reason_code == "SYMBOL_IDENTITY_MISMATCH"


def test_m31e_006_non_monotonic_clock_is_fail_closed():
    duration = timeframe_duration_ns("15m")
    decision = BASE_NS + 5 * duration
    series = _series("15m", 3)
    series.bars[2].timestamp_ns = series.bars[1].timestamp_ns
    result = _build([series], decision_time_ns=decision, required=["15m"])
    record = result.records[0]
    assert record.source_clock_monotonic is False
    assert record.reason_code == "NON_MONOTONIC_SOURCE_CLOCK"
    assert record.availability == "UNAVAILABLE"


def test_m31e_007_same_closed_facts_replay_same_hash():
    duration = timeframe_duration_ns("15m")
    decision = BASE_NS + 4 * duration
    first = _build([_series("15m", 3)], decision_time_ns=decision, required=["15m"])
    second = _build([_series("15m", 3)], decision_time_ns=decision, required=["15m"])
    assert first.mtf_hash == second.mtf_hash
    assert first.snapshot_hashes == second.snapshot_hashes
    assert first.records[0].source_series_hash == second.records[0].source_series_hash


def test_m31e_008_changed_closed_bar_changes_causal_hash():
    duration = timeframe_duration_ns("15m")
    decision = BASE_NS + 4 * duration
    first_series = _series("15m", 3)
    second_series = _series("15m", 3)
    second_series.bars[1].close += 0.05
    first = _build([first_series], decision_time_ns=decision, required=["15m"])
    second = _build([second_series], decision_time_ns=decision, required=["15m"])
    assert first.mtf_hash != second.mtf_hash
    assert first.records[0].source_series_hash != second.records[0].source_series_hash
    assert first.records[0].source_snapshot_hash != second.records[0].source_snapshot_hash


def test_m31e_009_bounded_receipt_contains_no_candles_or_dataframes():
    duration = timeframe_duration_ns("15m")
    decision = BASE_NS + 20 * duration
    result = _build([_series("15m", 19)], decision_time_ns=decision, required=["15m"])
    payload = result.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True)
    assert len(encoded.encode("utf-8")) < 20_000
    assert "closed_ohlcv_bars" not in encoded
    assert "dataframe" not in encoded.lower()
    assert result.calculation_audit["mtf_builder_count"] == 1
    assert result.calculation_audit["confirmation_compute_count"] == 1


def test_m31e_010_no_authority_and_epistemic_limits_are_explicit():
    duration = timeframe_duration_ns("15m")
    decision = BASE_NS + 4 * duration
    result = _build([_series("15m", 3)], decision_time_ns=decision, required=["15m"])
    assert result.calculation_version == MTF_CONFIRMATION_VERSION
    assert result.used_for_probability is False
    assert result.may_set_final_band is False
    assert result.may_execute is False
    assert result.trade_allowed is False
    assert result.order_routing_enabled is False
    assert result.live_trading_blocked is True
    assert result.epistemic["official_exchange_calendar_verified"] is False
    assert result.epistemic["corporate_action_adjustment_verified"] is False
    assert result.epistemic["freshness_verified"] is False
