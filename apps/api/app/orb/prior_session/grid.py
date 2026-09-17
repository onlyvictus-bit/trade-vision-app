"""BUILD-3A expected session grid: what bars SHOULD exist.

Pure functions over BUILD-2 identity facts. The grouping key is never the
civil calendar day: it is (instrument, contract, session label, profile
version/hash, calendar record/hash, data basis, timeframe). Half-open
[start, end) semantics; cross-midnight intervals label by start day.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo

from ..candidate_intake import canonical_sha256
from ..market_identity.contracts import (
    CalendarRecordV1,
    DataBasis,
    RegistryLifecycle,
    SessionProfileV1,
    SessionType,
    TradingIntervalV1,
    describe_record,
)
from ..market_identity.session import effective_intervals
from .contracts import (
    ORB_EXPECTED_GRID_VERSION,
    OrbExpectedSessionGridV1,
    SourceCadence,
)

_LIVE_CALENDAR_LIFECYCLES = frozenset({RegistryLifecycle.VERIFIED, RegistryLifecycle.ACTIVE})


def _minutes(text: str) -> int:
    return int(text[:2]) * 60 + int(text[3:])


def _profile_hash(profile: SessionProfileV1) -> str:
    if profile.record_hash:
        return profile.record_hash
    return canonical_sha256(describe_record(profile))


def _calendar_hash(calendar: CalendarRecordV1 | None) -> str | None:
    if calendar is None:
        return None
    if calendar.record_hash:
        return calendar.record_hash
    return canonical_sha256(describe_record(calendar))


def _require_live_calendar(calendar: CalendarRecordV1) -> None:
    if calendar.lifecycle not in _LIVE_CALENDAR_LIFECYCLES:
        raise ValueError(
            f"calendar {calendar.record_id} lifecycle {calendar.lifecycle.value} "
            "is not authoritative; only VERIFIED/ACTIVE records drive BUILD-3"
        )


def _local_edge_ns(zone: ZoneInfo, day: date, clock: str) -> int:
    hour, minute = int(clock[:2]), int(clock[3:])
    return int(datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone).timestamp() * 1_000_000_000)


def _interval_edges_ns(
    zone: ZoneInfo, label_day: date, interval: TradingIntervalV1
) -> tuple[int, int]:
    start_ns = _local_edge_ns(zone, label_day, interval.start_local)
    end_day = label_day + timedelta(days=1) if interval.crosses_midnight() else label_day
    end_ns = _local_edge_ns(zone, end_day, interval.end_local)
    return start_ns, end_ns


class GridUnavailable(Exception):
    """Raised with a machine-readable reason when no expected grid can be
    built (holiday without override, unknown timing, untileable session)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def resolve_effective_intervals(
    profile: SessionProfileV1,
    calendar: CalendarRecordV1 | None,
) -> tuple[TradingIntervalV1, ...]:
    if calendar is not None:
        _require_live_calendar(calendar)
    return effective_intervals(profile, calendar)


def build_expected_grid(
    *,
    instrument_key: str,
    contract_key: str | None,
    session_label: str,
    profile: SessionProfileV1,
    calendar: CalendarRecordV1 | None,
    timeframe: str,
    timeframe_duration_ns: int,
    data_basis: DataBasis,
    source_cadence: SourceCadence,
    market_as_of: datetime,
    knowledge_cutoff: datetime,
    source_id: str,
    session_type_override: SessionType | None = None,
) -> OrbExpectedSessionGridV1:
    """Construct the expected tradable bar windows for one exchange session.

    Raises GridUnavailable (never a silent guess) when the session cannot be
    tiled: closed holidays, non-positive/untileable spans, or a source
    timeframe that cannot exactly tile any interval.
    """
    label_day = date.fromisoformat(session_label.strip())
    if timeframe_duration_ns <= 0:
        raise ValueError("timeframe_duration_ns must be positive")
    for moment, name in ((market_as_of, "market_as_of"), (knowledge_cutoff, "knowledge_cutoff")):
        if not isinstance(moment, datetime) or moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError(f"{name} must be timezone-aware")

    intervals = resolve_effective_intervals(profile, calendar)
    if not intervals:
        raise GridUnavailable("CLOSED_HOLIDAY_OR_EMPTY_SESSION: no tradable intervals are effective")
    session_type = session_type_override or (calendar.session_type if calendar is not None else profile.session_type)

    zone = ZoneInfo(profile.timezone_name)
    break_windows: list[tuple[int, int]] = []
    if calendar is None or calendar.tradable_intervals_override is None:
        for gap in profile.break_intervals:
            if gap.crosses_midnight():
                raise GridUnavailable("UNKNOWN_BREAK_GEOMETRY: cross-midnight breaks are not supported")
            break_windows.append((_local_edge_ns(zone, label_day, gap.start_local),
                                  _local_edge_ns(zone, label_day, gap.end_local)))

    slots: list[int] = []
    untiled_tail_minutes = 0
    span_start_ns: int | None = None
    span_end_ns: int | None = None
    for interval in intervals:
        start_ns, end_ns = _interval_edges_ns(zone, label_day, interval)
        span_start_ns = start_ns if span_start_ns is None else min(span_start_ns, start_ns)
        span_end_ns = end_ns if span_end_ns is None else max(span_end_ns, end_ns)
        span_minutes = (end_ns - start_ns) // 60_000_000_000
        step_minutes = timeframe_duration_ns // 60_000_000_000
        if timeframe_duration_ns % 60_000_000_000 != 0 or step_minutes <= 0:
            raise GridUnavailable(
                f"UNTILEABLE_TIMEFRAME: {timeframe} is not a whole-minute cadence"
            )
        if span_minutes <= 0:
            raise GridUnavailable("EMPTY_INTERVAL: tradable interval has no positive span")
        if span_minutes % step_minutes != 0:
            untiled_tail_minutes += span_minutes % step_minutes
        cursor = start_ns
        while cursor + timeframe_duration_ns <= end_ns:
            slot_close = cursor + timeframe_duration_ns
            in_break = any(bstart <= cursor and slot_close <= bend for bstart, bend in break_windows)
            if not in_break:
                slots.append(cursor)
            cursor += timeframe_duration_ns

    assert span_start_ns is not None and span_end_ns is not None
    if not slots:
        raise GridUnavailable("NO_EXPECTED_SLOTS: session has no tileable expected bars")

    slots_are_required = source_cadence is SourceCadence.FIXED_INTERVAL_BAR_CADENCE
    identity = {
        "schema_version": ORB_EXPECTED_GRID_VERSION,
        "instrument_key": instrument_key.strip(),
        "contract_key": contract_key,
        "session_label": label_day.isoformat(),
        "session_profile_id": profile.profile_id,
        "session_profile_hash": _profile_hash(profile),
        "calendar_record_id": calendar.record_id if calendar is not None else None,
        "calendar_hash": _calendar_hash(calendar),
        "timeframe": timeframe,
        "data_basis": data_basis.value,
        "source_cadence": source_cadence.value,
        "expected_slot_opens_ns": slots,
    }
    grid_hash = canonical_sha256(identity)
    grid_id = f"orb-grid:{canonical_sha256({k: v for k, v in identity.items() if k != 'expected_slot_opens_ns'})[:24]}"
    return OrbExpectedSessionGridV1(
        schema_version=ORB_EXPECTED_GRID_VERSION,
        grid_id=grid_id,
        grid_hash=grid_hash,
        instrument_key=instrument_key.strip(),
        contract_key=contract_key,
        session_label=label_day.isoformat(),
        session_type=session_type,
        session_profile_id=profile.profile_id,
        session_profile_hash=_profile_hash(profile),
        calendar_record_id=calendar.record_id if calendar is not None else None,
        calendar_hash=_calendar_hash(calendar),
        timezone_name=profile.timezone_name,
        timeframe=timeframe,
        timeframe_duration_ns=timeframe_duration_ns,
        data_basis=data_basis,
        source_cadence=source_cadence,
        slots_are_required=slots_are_required,
        expected_slot_opens_ns=tuple(slots),
        session_market_start_ns=span_start_ns,
        session_market_end_ns=span_end_ns,
        break_windows_ns=tuple(break_windows),
        untiled_tail_minutes=untiled_tail_minutes,
        market_as_of=market_as_of,
        knowledge_cutoff=knowledge_cutoff,
        source_id=source_id.strip(),
    )


def assign_session_label(
    *,
    bar_open_ns: int,
    profile: SessionProfileV1,
    calendars_by_date: Mapping[date, CalendarRecordV1 | None],
) -> str | None:
    """Assign one bar open to an exchange session label using BUILD-2 rules.

    Returns None when the bar belongs to no session. Cross-midnight bars
    after midnight resolve to the prior start-day label. Only live calendars
    are consulted; a non-live calendar for a date is skipped as if absent.
    """
    zone = ZoneInfo(profile.timezone_name)
    moment = datetime.fromtimestamp(bar_open_ns / 1_000_000_000, tz=timezone.utc)
    local = moment.astimezone(zone)
    for label_day in (local.date(), local.date() - timedelta(days=1)):
        calendar = calendars_by_date.get(label_day)
        if calendar is not None and calendar.lifecycle not in _LIVE_CALENDAR_LIFECYCLES:
            calendar = None
        try:
            intervals = effective_intervals(profile, calendar)
        except ValueError:
            continue
        for interval in intervals:
            start_ns, end_ns = _interval_edges_ns(zone, label_day, interval)
            if start_ns <= bar_open_ns < end_ns:
                return label_day.isoformat()
    return None
