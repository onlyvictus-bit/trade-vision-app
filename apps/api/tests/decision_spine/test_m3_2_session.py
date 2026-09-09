from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.behavior.decision_spine.canonical_context_intelligence import ContextSourceObservation
from app.behavior.decision_spine.canonical_session_intelligence import (
    CANONICAL_SESSION_INTELLIGENCE_VERSION,
    CanonicalSessionIntelligenceError,
    build_canonical_session_intelligence,
)
from app.behavior.decision_spine.snapshot_feature_kernel import build_snapshot_feature_kernel
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import CandleBar, ClosedCandleSnapshot


IST = ZoneInfo("Asia/Kolkata")


def _ns(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)


def _snapshot(
    *,
    start_local: datetime,
    bars: int,
    timeframe: str = "5m",
    decision_local: datetime | None = None,
    omit_indices: set[int] | None = None,
    missing_volume_index: int | None = None,
    snapshot_hash: str = "a" * 64,
) -> ClosedCandleSnapshot:
    duration_ns = timeframe_duration_ns(timeframe)
    omit_indices = omit_indices or set()
    rows: list[CandleBar] = []
    for index in range(bars):
        if index in omit_indices:
            continue
        timestamp_ns = _ns(start_local) + index * duration_ns
        open_price = 100.0 + index * 0.1
        close = open_price + 0.05
        rows.append(
            CandleBar(
                symbol="RELIANCE",
                timeframe=timeframe,
                timestamp_ns=timestamp_ns,
                open=open_price,
                high=close + 0.1,
                low=open_price - 0.1,
                close=close,
                volume=None if index == missing_volume_index else 100_000.0 + index,
                source="user_csv",
                sequence_number=index + 1,
            )
        )
    if not rows:
        raise AssertionError("fixture requires at least one bar")
    if decision_local is None:
        decision_time_ns = rows[-1].timestamp_ns + duration_ns
    else:
        decision_time_ns = _ns(decision_local)
    return ClosedCandleSnapshot(
        snapshot_version="closed-candle-snapshot.v1.87",
        snapshot_id="m3-2-session-test",
        snapshot_hash=snapshot_hash,
        symbol="RELIANCE",
        timeframe=timeframe,
        decision_time_ns=decision_time_ns,
        decision_time=decision_local.isoformat() if decision_local else "2026-09-08T10:00:00+05:30",
        timezone_offset_minutes=330,
        bar_count=len(rows),
        first_bar_timestamp_ns=rows[0].timestamp_ns,
        last_bar_timestamp_ns=rows[-1].timestamp_ns,
        last_bar_close_time_ns=rows[-1].timestamp_ns + duration_ns,
        closed_ohlcv_bars=rows,
        source_schema_version="candles.v1",
        immutable=True,
        closed_candle_only=True,
        point_in_time_safe=True,
    )


def _calendar(decision_time_ns: int, *, availability: str = "AVAILABLE") -> ContextSourceObservation:
    return ContextSourceObservation(
        source_id="CALENDAR:NSE:2026-09-08",
        source_kind="CALENDAR",
        symbol_or_universe="NSE",
        provider_id="verified-calendar-fixture",
        provider_contract_version="nse-calendar-fixture.v1",
        source_snapshot_hash="c" * 64,
        source_timeframe=None,
        source_bar_close_time_ns=None,
        available_at_ns=decision_time_ns - 1,
        d2_decision_time_ns=decision_time_ns,
        sequence_or_watermark="2026-09-08",
        freshness_state="FRESH",
        clock_skew_state="ALIGNED",
        availability=availability,  # type: ignore[arg-type]
    )


def test_m32b_001_contiguous_closed_session_bars_build_available_zero_authority_receipt():
    start = datetime(2026, 9, 8, 9, 15, tzinfo=IST)
    snapshot = _snapshot(start_local=start, bars=6)
    kernel = build_snapshot_feature_kernel(snapshot)
    result = build_canonical_session_intelligence(
        feature_kernel=kernel,
        calendar_source=_calendar(kernel.identity.decision_time_ns),
    )
    payload = result.as_dict()

    assert result.calculation_version == CANONICAL_SESSION_INTELLIGENCE_VERSION
    assert result.availability == "AVAILABLE"
    assert result.current_phase == "REAL_TREND_CONFIRMATION"
    assert result.source_bar_count == 6
    assert result.data_quality.starts_at_regular_open is True
    assert result.data_quality.contiguous_from_regular_open is True
    assert result.data_quality.calendar_authority_available is True
    assert len(result.output_hash) == 64
    assert payload["used_for_probability"] is False
    assert payload["may_set_final_band"] is False
    assert payload["may_execute"] is False
    assert payload["trade_allowed"] is False
    assert payload["order_routing_enabled"] is False
    assert payload["live_trading_blocked"] is True


def test_m32b_002_missing_calendar_authority_degrades_instead_of_fabricating_exchange_truth():
    start = datetime(2026, 9, 8, 9, 15, tzinfo=IST)
    kernel = build_snapshot_feature_kernel(_snapshot(start_local=start, bars=4))
    result = build_canonical_session_intelligence(feature_kernel=kernel)

    assert result.availability == "DEGRADED"
    assert result.data_quality.calendar_authority_available is False
    assert "CALENDAR_AUTHORITY_UNAVAILABLE" in result.reason_codes


def test_m32b_003_gap_in_session_bars_is_detected_and_degrades():
    start = datetime(2026, 9, 8, 9, 15, tzinfo=IST)
    snapshot = _snapshot(start_local=start, bars=6, omit_indices={2})
    kernel = build_snapshot_feature_kernel(snapshot)
    result = build_canonical_session_intelligence(
        feature_kernel=kernel,
        calendar_source=_calendar(kernel.identity.decision_time_ns),
    )

    assert result.availability == "DEGRADED"
    assert result.data_quality.contiguous_from_regular_open is False
    assert result.data_quality.missing_expected_bar_count >= 1
    assert "SESSION_BAR_GAP_DETECTED" in result.reason_codes


def test_m32b_004_previous_day_bars_do_not_masquerade_as_current_session():
    previous = datetime(2026, 9, 7, 9, 15, tzinfo=IST)
    decision = datetime(2026, 9, 8, 10, 0, tzinfo=IST)
    snapshot = _snapshot(start_local=previous, bars=6, decision_local=decision)
    kernel = build_snapshot_feature_kernel(snapshot)
    result = build_canonical_session_intelligence(
        feature_kernel=kernel,
        calendar_source=_calendar(kernel.identity.decision_time_ns),
    )

    assert result.session_date == "2026-09-08"
    assert result.availability == "UNAVAILABLE"
    assert result.source_bar_count == 0
    assert result.session_open is None
    assert "NO_CURRENT_SESSION_CLOSED_BARS" in result.reason_codes


def test_m32b_005_phase_windows_use_decision_time_and_closed_bars_only():
    start = datetime(2026, 9, 8, 9, 15, tzinfo=IST)
    decision = datetime(2026, 9, 8, 9, 30, tzinfo=IST)
    snapshot = _snapshot(start_local=start, bars=3, decision_local=decision)
    kernel = build_snapshot_feature_kernel(snapshot)
    result = build_canonical_session_intelligence(
        feature_kernel=kernel,
        calendar_source=_calendar(kernel.identity.decision_time_ns),
    )
    open_drive = next(item for item in result.phases if item.phase == "OPEN_DRIVE")

    assert result.current_phase == "REAL_TREND_CONFIRMATION"
    assert open_drive.time_window_complete is True
    assert open_drive.source_bar_count == 3
    assert result.last_bar_close_time_ns == _ns(decision)


def test_m32b_006_replay_is_deterministic():
    start = datetime(2026, 9, 8, 9, 15, tzinfo=IST)
    kernel = build_snapshot_feature_kernel(_snapshot(start_local=start, bars=10))
    calendar = _calendar(kernel.identity.decision_time_ns)

    first = build_canonical_session_intelligence(feature_kernel=kernel, calendar_source=calendar)
    second = build_canonical_session_intelligence(feature_kernel=kernel, calendar_source=calendar)

    assert first.output_hash == second.output_hash
    assert first.as_dict() == second.as_dict()


def test_m32b_007_missing_volume_is_visible_but_does_not_invent_volume_facts():
    start = datetime(2026, 9, 8, 9, 15, tzinfo=IST)
    kernel = build_snapshot_feature_kernel(
        _snapshot(start_local=start, bars=4, missing_volume_index=1)
    )
    result = build_canonical_session_intelligence(
        feature_kernel=kernel,
        calendar_source=_calendar(kernel.identity.decision_time_ns),
    )

    assert result.data_quality.missing_volume_count == 1
    assert "SESSION_VOLUME_PARTIAL" in result.reason_codes


def test_m32b_008_rejects_non_intraday_session_timeframe():
    start = datetime(2026, 9, 8, 0, 0, tzinfo=IST)
    snapshot = _snapshot(start_local=start, bars=2, timeframe="daily")
    kernel = build_snapshot_feature_kernel(snapshot)

    with pytest.raises(CanonicalSessionIntelligenceError, match="REQUIRES_INTRADAY_TIMEFRAME"):
        build_canonical_session_intelligence(feature_kernel=kernel)


def test_m32b_009_calendar_decision_time_mismatch_fails_closed():
    start = datetime(2026, 9, 8, 9, 15, tzinfo=IST)
    kernel = build_snapshot_feature_kernel(_snapshot(start_local=start, bars=3))
    calendar = _calendar(kernel.identity.decision_time_ns - 1)

    with pytest.raises(CanonicalSessionIntelligenceError, match="DECISION_TIME_MISMATCH"):
        build_canonical_session_intelligence(feature_kernel=kernel, calendar_source=calendar)
