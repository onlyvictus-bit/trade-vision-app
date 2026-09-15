"""Canonical session membership and phase math over BUILD-2 session profiles.

Pure functions only: given a session profile, an optional calendar-record
interval override, and a timezone-aware timestamp, answer which session
interval contains it, which phase is active, the exchange trading-date
label, and elapsed tradable minutes. Half-open [start, end) semantics;
intervals may cross midnight. No candle aggregation happens here (that is
BUILD-3); no network; no wall clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .contracts import (
    CalendarRecordV1,
    SessionPhase,
    SessionProfileV1,
    SessionType,
    TradingIntervalV1,
)


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _minutes(text: str) -> int:
    return int(text[:2]) * 60 + int(text[3:])


def _zone(profile: SessionProfileV1) -> ZoneInfo:
    return ZoneInfo(profile.timezone_name)


def effective_intervals(
    profile: SessionProfileV1,
    calendar: CalendarRecordV1 | None = None,
) -> tuple[TradingIntervalV1, ...]:
    """Calendar-record interval overrides win over the profile when present."""
    if calendar is not None and calendar.tradable_intervals_override is not None:
        if not calendar.tradable_intervals_override:
            raise ValueError("calendar interval override must not be empty")
        return tuple(calendar.tradable_intervals_override)
    return tuple(profile.tradable_intervals)


def _interval_contains(start_min: int, end_min: int, minute: int) -> bool:
    if end_min > start_min:
        return start_min <= minute < end_min
    return minute >= start_min or minute < end_min


def locate_timestamp(
    profile: SessionProfileV1,
    moment: datetime,
    calendar: CalendarRecordV1 | None = None,
) -> dict[str, object]:
    """Locate one aware timestamp inside the session definition.

    Returns a dict with: in_session, interval_index (-1 when outside),
    phase, session_label (exchange trading-date label or "" when outside),
    interval_start_utc / interval_end_utc ISO strings (or None).
    """
    moment = _require_aware(moment, field_name="moment")
    zone = _zone(profile)
    local = moment.astimezone(zone)
    minute = local.hour * 60 + local.minute
    intervals = effective_intervals(profile, calendar)
    for index, interval in enumerate(intervals):
        if _interval_contains(_minutes(interval.start_local), _minutes(interval.end_local), minute):
            return {
                "in_session": True,
                "interval_index": index,
                "phase": interval.phase,
                "session_label": _session_label(profile, local, interval),
                "interval_start_utc": _interval_edge_utc(profile, local, interval, edge="start").isoformat(),
                "interval_end_utc": _interval_edge_utc(profile, local, interval, edge="end").isoformat(),
            }
    return {
        "in_session": False,
        "interval_index": -1,
        "phase": SessionPhase.CLOSED,
        "session_label": "",
        "interval_start_utc": None,
        "interval_end_utc": None,
    }


def _session_label(profile: SessionProfileV1, local: datetime, interval: TradingIntervalV1) -> str:
    """Exchange trading-date label. For cross-midnight intervals, timestamps
    after midnight still belong to the session that started the prior day."""
    minute = local.hour * 60 + local.minute
    label_day = local.date()
    if interval.crosses_midnight() and minute < _minutes(interval.end_local):
        label_day = label_day - timedelta(days=1)
    return label_day.isoformat()


def _interval_edge_utc(
    profile: SessionProfileV1, local: datetime, interval: TradingIntervalV1, *, edge: str
) -> datetime:
    zone = _zone(profile)
    text = interval.start_local if edge == "start" else interval.end_local
    edge_day = local.date()
    minute = local.hour * 60 + local.minute
    if interval.crosses_midnight():
        if edge == "start" and minute < _minutes(interval.end_local):
            edge_day = edge_day - timedelta(days=1)
        elif edge == "end" and minute >= _minutes(interval.start_local):
            edge_day = edge_day + timedelta(days=1)
    naive = datetime(edge_day.year, edge_day.month, edge_day.day, int(text[:2]), int(text[3:]))
    return zone.localize(naive).astimezone(timezone.utc) if hasattr(zone, "localize") else naive.replace(tzinfo=zone).astimezone(timezone.utc)


def elapsed_tradable_minutes(
    profile: SessionProfileV1,
    moment: datetime,
    calendar: CalendarRecordV1 | None = None,
) -> int:
    """Whole tradable minutes elapsed since the opening anchor (excludes
    registered breaks). Timestamps before the anchor yield 0."""
    moment = _require_aware(moment, field_name="moment")
    zone = _zone(profile)
    local = moment.astimezone(zone)
    anchor = _minutes(profile.opening_anchor_local)
    minute = local.hour * 60 + local.minute
    if minute < anchor and not any(i.crosses_midnight() for i in effective_intervals(profile, calendar)):
        return 0
    elapsed = 0
    for interval in effective_intervals(profile, calendar):
        start, end = _minutes(interval.start_local), _minutes(interval.end_local)
        span_end = end if end > start else end + 24 * 60
        cursor = minute if minute >= start or not interval.crosses_midnight() else minute + 24 * 60
        if cursor <= start:
            continue
        elapsed += max(0, min(cursor, span_end) - start)
    for gap in profile.break_intervals:
        start, end = _minutes(gap.start_local), _minutes(gap.end_local)
        span_end = end if end > start else end + 24 * 60
        cursor = minute if minute >= start or not gap.crosses_midnight() else minute + 24 * 60
        if cursor <= start:
            continue
        elapsed -= max(0, min(cursor, span_end) - start)
    return max(0, elapsed)


def is_mock_or_closed_session(calendar: CalendarRecordV1 | None) -> bool:
    """Mock/DR sessions and holidays must never be treated as regular."""
    if calendar is None:
        return False
    return calendar.session_type in (SessionType.MOCK, SessionType.CLOSED_HOLIDAY)
