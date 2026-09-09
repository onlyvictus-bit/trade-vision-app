from __future__ import annotations

"""Canonical M3.2-B session intelligence.

This module interprets one already-approved M3.1 SnapshotFeatureKernel using
causal candle-close semantics. It does not read providers, learn probabilities,
set a final band, or authorize execution.

Important boundary:
regular NSE cash-session times are a versioned *semantic contract*, not proof of
an authoritative exchange holiday/special-session calendar. When no validated
CALENDAR source observation is supplied, the result remains explicitly
DEGRADED even when observed intraday bars are otherwise usable.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
import hashlib
import json
from typing import Any, Literal
from zoneinfo import ZoneInfo

from ..point_in_time_guard import timeframe_duration_ns
from .canonical_context_intelligence import ContextSourceObservation
from .snapshot_feature_kernel import SnapshotFeatureKernel


CANONICAL_SESSION_INTELLIGENCE_VERSION = "canonical-session-intelligence.v1"
SESSION_SEMANTICS_VERSION = "nse-cash-regular-session.v1"
NSE_TIMEZONE_NAME = "Asia/Kolkata"
NSE_TIMEZONE = ZoneInfo(NSE_TIMEZONE_NAME)
NSE_SESSION_OPEN = time(9, 15)
NSE_SESSION_CLOSE = time(15, 30)
MAX_SESSION_RECEIPT_BYTES = 24_000

SessionAvailability = Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE", "PENDING", "ERROR"]
SessionPhase = Literal[
    "PRE_OPEN",
    "OPEN_DRIVE",
    "REAL_TREND_CONFIRMATION",
    "CONTINUATION_OR_FADE",
    "LUNCH_COMPRESSION",
    "POST_LUNCH_EXPANSION",
    "CLOSING_DRIVE",
    "SQUAREOFF_FAKE_SPIKE",
    "POST_CLOSE",
]

_PHASE_WINDOWS: tuple[tuple[SessionPhase, int, int], ...] = (
    ("OPEN_DRIVE", 9 * 60 + 15, 9 * 60 + 30),
    ("REAL_TREND_CONFIRMATION", 9 * 60 + 30, 10 * 60 + 15),
    ("CONTINUATION_OR_FADE", 10 * 60 + 15, 11 * 60 + 30),
    ("LUNCH_COMPRESSION", 11 * 60 + 30, 13 * 60 + 30),
    ("POST_LUNCH_EXPANSION", 13 * 60 + 30, 14 * 60 + 30),
    ("CLOSING_DRIVE", 14 * 60 + 30, 15 * 60 + 15),
    ("SQUAREOFF_FAKE_SPIKE", 15 * 60 + 15, 15 * 60 + 30),
)


class CanonicalSessionIntelligenceError(ValueError):
    """Raised when session evidence cannot be bound to the D2 causal root."""


@dataclass(frozen=True, slots=True)
class SessionPhaseObservation:
    phase: SessionPhase
    window_start_local: str
    window_end_local: str
    time_window_complete: bool
    source_bar_count: int
    first_bar_timestamp_ns: int | None
    last_bar_timestamp_ns: int | None


@dataclass(frozen=True, slots=True)
class SessionDataQuality:
    starts_at_regular_open: bool
    contiguous_from_regular_open: bool
    missing_expected_bar_count: int
    unexpected_timestamp_count: int
    missing_volume_count: int
    calendar_authority_available: bool
    calendar_source_id: str | None
    calendar_source_snapshot_hash: str | None


@dataclass(frozen=True, slots=True)
class CanonicalSessionIntelligenceResult:
    calculation_version: str
    session_semantics_version: str
    symbol: str
    timeframe: str
    d2_snapshot_hash: str
    source_feature_kernel_hash: str
    decision_time_ns: int
    session_date: str
    session_id: str
    current_phase: SessionPhase
    availability: SessionAvailability
    source_bar_count: int
    first_bar_timestamp_ns: int | None
    last_bar_timestamp_ns: int | None
    last_bar_close_time_ns: int | None
    session_open: float | None
    session_high: float | None
    session_low: float | None
    session_close: float | None
    session_return_pct: float | None
    session_range_pct: float | None
    observed_progress: float
    phases: tuple[SessionPhaseObservation, ...]
    data_quality: SessionDataQuality
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    output_hash: str
    used_for_probability: bool = False
    may_propose: bool = False
    may_veto: bool = False
    may_downgrade: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["phases"] = [asdict(item) for item in self.phases]
        payload["data_quality"] = asdict(self.data_quality)
        payload["reason_codes"] = list(self.reason_codes)
        payload["warnings"] = list(self.warnings)
        return payload


def build_canonical_session_intelligence(
    *,
    feature_kernel: SnapshotFeatureKernel,
    calendar_source: ContextSourceObservation | None = None,
) -> CanonicalSessionIntelligenceResult:
    """Build a bounded causal session-state receipt from D2-closed bars.

    The decision-local date, rather than the last historical bar date, selects
    the current session. This prevents a previous trading day from masquerading
    as today's session when no current-date bars exist.
    """

    decision_time_ns = int(feature_kernel.identity.decision_time_ns)
    if decision_time_ns <= 0:
        raise CanonicalSessionIntelligenceError("INVALID_DECISION_TIME")

    try:
        duration_ns = int(timeframe_duration_ns(feature_kernel.identity.timeframe))  # type: ignore[arg-type]
    except (KeyError, TypeError) as exc:
        raise CanonicalSessionIntelligenceError("UNSUPPORTED_TIMEFRAME") from exc

    regular_session_ns = 375 * 60_000_000_000
    if duration_ns <= 0 or duration_ns >= regular_session_ns:
        raise CanonicalSessionIntelligenceError("SESSION_INTELLIGENCE_REQUIRES_INTRADAY_TIMEFRAME")

    decision_local = _datetime_from_ns(decision_time_ns)
    session_date = decision_local.date()
    open_ns = _local_time_ns(session_date, NSE_SESSION_OPEN)
    close_ns = _local_time_ns(session_date, NSE_SESSION_CLOSE)
    current_phase = _phase_for_local_datetime(decision_local)

    calendar_verified, calendar_id, calendar_hash = _validate_calendar_source(
        calendar_source,
        d2_snapshot_hash=feature_kernel.identity.snapshot_hash,
        decision_time_ns=decision_time_ns,
    )

    current_indices: list[int] = []
    unexpected_timestamp_count = 0
    for index, timestamp_ns in enumerate(feature_kernel.vectors.timestamps_ns):
        bar_close_ns = timestamp_ns + duration_ns
        if bar_close_ns > decision_time_ns:
            raise CanonicalSessionIntelligenceError("FEATURE_KERNEL_CONTAINS_INCOMPLETE_BAR")
        bar_local = _datetime_from_ns(timestamp_ns)
        if bar_local.date() != session_date:
            continue
        if timestamp_ns < open_ns or timestamp_ns >= close_ns:
            unexpected_timestamp_count += 1
            continue
        if bar_close_ns > close_ns:
            unexpected_timestamp_count += 1
            continue
        current_indices.append(index)

    timestamps = tuple(feature_kernel.vectors.timestamps_ns[index] for index in current_indices)
    continuity = _continuity_quality(timestamps, open_ns=open_ns, duration_ns=duration_ns)
    missing_volume_count = sum(1 for index in current_indices if feature_kernel.vectors.volumes[index] is None)

    reason_codes: list[str] = []
    warnings: list[str] = []
    if not calendar_verified:
        reason_codes.append("CALENDAR_AUTHORITY_UNAVAILABLE")
        warnings.append("Regular NSE session semantics are observed, but authoritative calendar identity is unavailable.")
    if unexpected_timestamp_count:
        reason_codes.append("OUTSIDE_REGULAR_SESSION_BARS_IGNORED")
        warnings.append("Current-date bars outside the regular-session contract were excluded from canonical session facts.")
    if not continuity[0] and current_indices:
        reason_codes.append("SESSION_DOES_NOT_START_AT_REGULAR_OPEN")
    if not continuity[1] and current_indices:
        reason_codes.append("SESSION_BAR_GAP_DETECTED")
    if missing_volume_count:
        reason_codes.append("SESSION_VOLUME_PARTIAL")

    if decision_time_ns < open_ns:
        availability: SessionAvailability = "PENDING"
        reason_codes.append("REGULAR_SESSION_NOT_STARTED")
    elif not current_indices:
        availability = "UNAVAILABLE"
        reason_codes.append("NO_CURRENT_SESSION_CLOSED_BARS")
    elif not calendar_verified or not continuity[0] or not continuity[1] or unexpected_timestamp_count:
        availability = "DEGRADED"
    else:
        availability = "AVAILABLE"

    session_open = feature_kernel.vectors.opens[current_indices[0]] if current_indices else None
    session_high = max((feature_kernel.vectors.highs[index] for index in current_indices), default=None)
    session_low = min((feature_kernel.vectors.lows[index] for index in current_indices), default=None)
    session_close = feature_kernel.vectors.closes[current_indices[-1]] if current_indices else None
    session_return_pct = _pct_change(session_open, session_close)
    session_range_pct = _range_pct(session_open, session_high, session_low)

    phases = tuple(
        _phase_observation(
            phase=phase,
            start_minute=start_minute,
            end_minute=end_minute,
            session_date=session_date,
            decision_time_ns=decision_time_ns,
            timestamps=timestamps,
        )
        for phase, start_minute, end_minute in _PHASE_WINDOWS
    )

    last_timestamp_ns = timestamps[-1] if timestamps else None
    last_bar_close_time_ns = last_timestamp_ns + duration_ns if last_timestamp_ns is not None else None
    progress = _observed_progress(
        decision_time_ns=decision_time_ns,
        open_ns=open_ns,
        close_ns=close_ns,
        last_bar_close_time_ns=last_bar_close_time_ns,
    )

    quality = SessionDataQuality(
        starts_at_regular_open=continuity[0],
        contiguous_from_regular_open=continuity[1],
        missing_expected_bar_count=continuity[2],
        unexpected_timestamp_count=unexpected_timestamp_count,
        missing_volume_count=missing_volume_count,
        calendar_authority_available=calendar_verified,
        calendar_source_id=calendar_id,
        calendar_source_snapshot_hash=calendar_hash,
    )

    deterministic = {
        "calculation_version": CANONICAL_SESSION_INTELLIGENCE_VERSION,
        "session_semantics_version": SESSION_SEMANTICS_VERSION,
        "symbol": feature_kernel.identity.symbol,
        "timeframe": feature_kernel.identity.timeframe,
        "d2_snapshot_hash": feature_kernel.identity.snapshot_hash,
        "source_feature_kernel_hash": feature_kernel.feature_hash,
        "decision_time_ns": decision_time_ns,
        "session_date": session_date.isoformat(),
        "session_id": f"NSE:{session_date.isoformat()}:REGULAR",
        "current_phase": current_phase,
        "availability": availability,
        "source_bar_count": len(current_indices),
        "first_bar_timestamp_ns": timestamps[0] if timestamps else None,
        "last_bar_timestamp_ns": last_timestamp_ns,
        "last_bar_close_time_ns": last_bar_close_time_ns,
        "session_open": session_open,
        "session_high": session_high,
        "session_low": session_low,
        "session_close": session_close,
        "session_return_pct": session_return_pct,
        "session_range_pct": session_range_pct,
        "observed_progress": progress,
        "phases": [asdict(item) for item in phases],
        "data_quality": asdict(quality),
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
    }
    output_hash = _stable_hash(deterministic)

    result = CanonicalSessionIntelligenceResult(
        calculation_version=CANONICAL_SESSION_INTELLIGENCE_VERSION,
        session_semantics_version=SESSION_SEMANTICS_VERSION,
        symbol=feature_kernel.identity.symbol,
        timeframe=feature_kernel.identity.timeframe,
        d2_snapshot_hash=feature_kernel.identity.snapshot_hash,
        source_feature_kernel_hash=feature_kernel.feature_hash,
        decision_time_ns=decision_time_ns,
        session_date=session_date.isoformat(),
        session_id=f"NSE:{session_date.isoformat()}:REGULAR",
        current_phase=current_phase,
        availability=availability,
        source_bar_count=len(current_indices),
        first_bar_timestamp_ns=timestamps[0] if timestamps else None,
        last_bar_timestamp_ns=last_timestamp_ns,
        last_bar_close_time_ns=last_bar_close_time_ns,
        session_open=session_open,
        session_high=session_high,
        session_low=session_low,
        session_close=session_close,
        session_return_pct=session_return_pct,
        session_range_pct=session_range_pct,
        observed_progress=progress,
        phases=phases,
        data_quality=quality,
        reason_codes=tuple(sorted(set(reason_codes))),
        warnings=tuple(sorted(set(warnings))),
        output_hash=output_hash,
    )
    encoded = json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_SESSION_RECEIPT_BYTES:
        raise CanonicalSessionIntelligenceError("BOUNDED_SESSION_RECEIPT_EXCEEDED")
    return result


def _validate_calendar_source(
    source: ContextSourceObservation | None,
    *,
    d2_snapshot_hash: str,
    decision_time_ns: int,
) -> tuple[bool, str | None, str | None]:
    if source is None:
        return False, None, None
    if source.source_kind != "CALENDAR":
        raise CanonicalSessionIntelligenceError("SESSION_CALENDAR_SOURCE_KIND_MISMATCH")
    if source.d2_decision_time_ns != decision_time_ns:
        raise CanonicalSessionIntelligenceError("SESSION_CALENDAR_DECISION_TIME_MISMATCH")
    if source.synthetic:
        raise CanonicalSessionIntelligenceError("SESSION_CALENDAR_SYNTHETIC")
    if not source.identity_match:
        raise CanonicalSessionIntelligenceError("SESSION_CALENDAR_IDENTITY_MISMATCH")
    if source.availability not in {"AVAILABLE", "DEGRADED"}:
        return False, source.source_id, source.source_snapshot_hash
    if source.source_snapshot_hash is None:
        raise CanonicalSessionIntelligenceError("SESSION_CALENDAR_HASH_MISSING")
    if source.available_at_ns is None or source.available_at_ns > decision_time_ns:
        raise CanonicalSessionIntelligenceError("SESSION_CALENDAR_NOT_CAUSALLY_AVAILABLE")
    # Calendar is independently sourced, so its hash must not be forced to equal
    # the stock D2 hash. Binding is by decision time plus its own source identity.
    if not d2_snapshot_hash:
        raise CanonicalSessionIntelligenceError("SESSION_D2_HASH_MISSING")
    return True, source.source_id, source.source_snapshot_hash.lower()


def _continuity_quality(
    timestamps: tuple[int, ...],
    *,
    open_ns: int,
    duration_ns: int,
) -> tuple[bool, bool, int]:
    if not timestamps:
        return False, False, 0
    starts_at_open = timestamps[0] == open_ns
    if timestamps[0] < open_ns:
        return False, False, 0
    expected_count = ((timestamps[-1] - open_ns) // duration_ns) + 1
    if expected_count <= 0:
        return starts_at_open, False, 0
    expected = {open_ns + offset * duration_ns for offset in range(int(expected_count))}
    actual = set(timestamps)
    missing_count = len(expected - actual)
    unexpected_grid_count = sum(1 for value in timestamps if (value - open_ns) % duration_ns != 0)
    contiguous = starts_at_open and missing_count == 0 and unexpected_grid_count == 0 and len(actual) == len(timestamps)
    return starts_at_open, contiguous, missing_count + unexpected_grid_count


def _phase_observation(
    *,
    phase: SessionPhase,
    start_minute: int,
    end_minute: int,
    session_date: date,
    decision_time_ns: int,
    timestamps: tuple[int, ...],
) -> SessionPhaseObservation:
    start_ns = _minute_of_day_ns(session_date, start_minute)
    end_ns = _minute_of_day_ns(session_date, end_minute)
    in_phase = tuple(value for value in timestamps if start_ns <= value < end_ns)
    return SessionPhaseObservation(
        phase=phase,
        window_start_local=_minute_label(start_minute),
        window_end_local=_minute_label(end_minute),
        time_window_complete=decision_time_ns >= end_ns,
        source_bar_count=len(in_phase),
        first_bar_timestamp_ns=in_phase[0] if in_phase else None,
        last_bar_timestamp_ns=in_phase[-1] if in_phase else None,
    )


def _phase_for_local_datetime(value: datetime) -> SessionPhase:
    minute = value.hour * 60 + value.minute
    if minute < 9 * 60 + 15:
        return "PRE_OPEN"
    if minute >= 15 * 60 + 30:
        return "POST_CLOSE"
    for phase, start_minute, end_minute in _PHASE_WINDOWS:
        if start_minute <= minute < end_minute:
            return phase
    return "POST_CLOSE"


def _observed_progress(
    *,
    decision_time_ns: int,
    open_ns: int,
    close_ns: int,
    last_bar_close_time_ns: int | None,
) -> float:
    if decision_time_ns < open_ns or last_bar_close_time_ns is None:
        return 0.0
    observed_ns = min(last_bar_close_time_ns, decision_time_ns, close_ns)
    if observed_ns <= open_ns:
        return 0.0
    return round(min(max((observed_ns - open_ns) / (close_ns - open_ns), 0.0), 1.0), 6)


def _pct_change(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or start == 0:
        return None
    return round(((end - start) / start) * 100.0, 6)


def _range_pct(
    start: float | None,
    high: float | None,
    low: float | None,
) -> float | None:
    if start is None or high is None or low is None or start == 0:
        return None
    return round(((high - low) / start) * 100.0, 6)


def _datetime_from_ns(timestamp_ns: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc).astimezone(NSE_TIMEZONE)


def _local_time_ns(day: date, local_time: time) -> int:
    local = datetime.combine(day, local_time, tzinfo=NSE_TIMEZONE)
    return int(local.timestamp() * 1_000_000_000)


def _minute_of_day_ns(day: date, minute_of_day: int) -> int:
    hour, minute = divmod(minute_of_day, 60)
    return _local_time_ns(day, time(hour, minute))


def _minute_label(minute_of_day: int) -> str:
    hour, minute = divmod(minute_of_day, 60)
    return f"{hour:02d}:{minute:02d}"


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
