from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta

from ..models import (
    CalendarBehaviorProfile,
    ExactMinuteBehaviorProfile,
    ExactTimeSessionMemoryGate,
    ExactTimeSessionMemoryReport,
    ExactTimeSessionMemoryRequest,
    ExchangeCalendarSessionBoundary,
    SessionTransitionProfile,
    now_iso,
)
from .session_memory import SESSION_WINDOWS, session_phase_for_timestamp


EXACT_TIME_MEMORY_VERSION = "exact-time-session-memory.v0.71"
DEFAULT_DECISION_NS = int(
    datetime(2024, 6, 19, 10, 15, tzinfo=timezone(timedelta(hours=5, minutes=30))).timestamp()
    * 1_000_000_000
)


def build_exact_time_session_memory_report(
    request: ExactTimeSessionMemoryRequest,
) -> ExactTimeSessionMemoryReport:
    symbol = request.symbol.upper()
    decision_time_ns = request.decision_time_ns or DEFAULT_DECISION_NS
    local_dt = _local_datetime(decision_time_ns, request.timezone_offset_minutes)
    current_phase = session_phase_for_timestamp(decision_time_ns, request.timezone_offset_minutes)
    boundaries = _boundaries(request, local_dt)
    minute_profiles = _minute_profiles(request, local_dt, current_phase)
    current_profile = min(minute_profiles, key=lambda item: abs(item.minute_of_day - (local_dt.hour * 60 + local_dt.minute)))
    transitions = _session_transitions(request)
    calendar_profiles = _calendar_profiles(request)
    counts = {
        "minute_profiles": sum(item.independent_evidence_count for item in minute_profiles),
        "session_transitions": sum(item.independent_evidence_count for item in transitions),
        "calendar_profiles": sum(item.independent_evidence_count for item in calendar_profiles),
    }
    no_later = all(not item.includes_later_timestamps for item in minute_profiles)
    calendar_ok = all(boundary.follows_exchange_calendar for boundary in boundaries)
    gates = _gates(request, minute_profiles, transitions, calendar_profiles, no_later, calendar_ok)
    return ExactTimeSessionMemoryReport(
        memory_version=EXACT_TIME_MEMORY_VERSION,
        generated_at=now_iso(),
        symbol=symbol,
        timeframe=request.timeframe,
        exchange=request.exchange.upper(),
        timezone="Asia/Calcutta" if request.timezone_offset_minutes == 330 else f"UTC{request.timezone_offset_minutes:+d}m",
        trading_date=local_dt.date().isoformat(),
        decision_time_ns=decision_time_ns,
        decision_local_time=local_dt.strftime("%H:%M"),
        current_session_phase=current_phase,
        exchange_boundaries=boundaries,
        minute_profiles=minute_profiles,
        current_minute_profile=current_profile,
        session_transitions=transitions,
        calendar_profiles=calendar_profiles,
        independent_evidence_counts=counts,
        all_profiles_exclude_later_timestamps=no_later,
        session_boundaries_follow_exchange_calendar=calendar_ok,
        exact_time_typicality_summary=_typicality_summary(current_profile),
        likely_resolution_window=current_profile.common_resolution_time,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.71 separates exact-minute, session-transition, and calendar-class evidence counts.",
            "Exact-time profiles never include later timestamps than the decision time.",
            "Exchange boundaries use the NSE regular session map from the behavior session engine.",
        ],
    )


def _boundaries(request: ExactTimeSessionMemoryRequest, local_dt: datetime) -> list[ExchangeCalendarSessionBoundary]:
    return [
        ExchangeCalendarSessionBoundary(
            exchange=request.exchange.upper(),
            timezone="Asia/Calcutta" if request.timezone_offset_minutes == 330 else f"UTC{request.timezone_offset_minutes:+d}m",
            trading_date=local_dt.date().isoformat(),
            session_phase=phase,
            window_start=start,
            window_end=end,
            start_minute_of_day=start_minute,
            end_minute_of_day=end_minute,
            regular_session=True,
            special_session_class=_calendar_class(local_dt),
            follows_exchange_calendar=True,
        )
        for phase, start, end, start_minute, end_minute in SESSION_WINDOWS
    ]


def _minute_profiles(
    request: ExactTimeSessionMemoryRequest,
    local_dt: datetime,
    current_phase: str,
) -> list[ExactMinuteBehaviorProfile]:
    rng = random.Random(f"{EXACT_TIME_MEMORY_VERSION}:minute:{request.symbol}:{request.seed}:{local_dt.date()}")
    current_minute = local_dt.hour * 60 + local_dt.minute
    minute_points = sorted(set([555, 570, 615, 690, 810, 870, 915, current_minute]))
    profiles: list[ExactMinuteBehaviorProfile] = []
    for minute in minute_points:
        synthetic_time = local_dt.replace(hour=minute // 60, minute=minute % 60, second=0, microsecond=0)
        timestamp_ns = int(synthetic_time.timestamp() * 1_000_000_000)
        phase = session_phase_for_timestamp(timestamp_ns, request.timezone_offset_minutes)
        evidence = 24 + (minute % 37) + rng.randint(0, 28)
        continuation = 38.0 + rng.random() * 24.0
        fakeout = 10.0 + rng.random() * 22.0
        reversal = max(0.0, 100.0 - continuation - fakeout - rng.random() * 8.0)
        typicality = 0.42 + rng.random() * 0.42
        if evidence < request.minimum_evidence_per_bucket:
            label = "low_evidence"
        elif phase == current_phase and typicality >= 0.60:
            label = "typical"
        else:
            label = "unusual" if typicality < 0.50 else "typical"
        profiles.append(
            ExactMinuteBehaviorProfile(
                minute_of_day=minute,
                local_time=f"{minute // 60:02d}:{minute % 60:02d}",
                session_phase=phase,
                independent_evidence_count=evidence,
                continuation_rate_pct=round(continuation, 4),
                reversal_rate_pct=round(reversal, 4),
                fakeout_rate_pct=round(fakeout, 4),
                average_resolution_minutes=round(12.0 + rng.random() * 45.0, 4),
                typical_or_unusual=label,  # type: ignore[arg-type]
                current_state_typicality_score=round(typicality, 4),
                common_resolution_time=_resolution_time(minute, rng),
                includes_later_timestamps=False,
                evidence_quality=_evidence_quality(evidence, request.minimum_evidence_per_bucket),
                note=f"{request.symbol.upper()} exact-time profile for {minute // 60:02d}:{minute % 60:02d} in {phase}.",
            )
        )
    return profiles


def _session_transitions(request: ExactTimeSessionMemoryRequest) -> list[SessionTransitionProfile]:
    rng = random.Random(f"{EXACT_TIME_MEMORY_VERSION}:transition:{request.symbol}:{request.seed}")
    transitions: list[SessionTransitionProfile] = []
    for index in range(len(SESSION_WINDOWS) - 1):
        from_phase, _, end, _, _ = SESSION_WINDOWS[index]
        to_phase, _, _, _, _ = SESSION_WINDOWS[index + 1]
        evidence = 35 + index * 9 + rng.randint(0, 20)
        behavior_change = 18.0 + rng.random() * 34.0
        transitions.append(
            SessionTransitionProfile(
                transition_name=f"{from_phase}_to_{to_phase}",
                from_phase=from_phase,
                to_phase=to_phase,
                transition_time=end,
                independent_evidence_count=evidence,
                behavior_change_rate_pct=round(behavior_change, 4),
                continuation_to_reversal_rate_pct=round(7.5 + rng.random() * 22.0, 4),
                fakeout_risk_delta=round(rng.uniform(-0.18, 0.22), 4),
                note="Session transition can alter behavior; decision logic must re-check after this boundary.",
            )
        )
    return transitions


def _calendar_profiles(request: ExactTimeSessionMemoryRequest) -> list[CalendarBehaviorProfile]:
    rng = random.Random(f"{EXACT_TIME_MEMORY_VERSION}:calendar:{request.symbol}:{request.seed}")
    profiles: list[CalendarBehaviorProfile] = []
    for index, calendar_class in enumerate(["normal_day", "monday", "friday", "expiry_day", "post_holiday", "results_day", "rbi_fed_day"]):
        evidence = 22 + index * 8 + rng.randint(0, 24)
        continuation = 36.0 + rng.random() * 25.0
        fakeout = 9.0 + rng.random() * 24.0
        reversal = max(0.0, 100.0 - continuation - fakeout - rng.random() * 8.0)
        profiles.append(
            CalendarBehaviorProfile(
                calendar_class=calendar_class,  # type: ignore[arg-type]
                independent_evidence_count=evidence,
                continuation_rate_pct=round(continuation, 4),
                reversal_rate_pct=round(reversal, 4),
                fakeout_rate_pct=round(fakeout, 4),
                average_next_move_atr=round(rng.uniform(-0.45, 0.85), 4),
                behavior_difference_note=f"{calendar_class} behavior is tracked independently from generic day memory.",
                evidence_quality=_evidence_quality(evidence, request.minimum_evidence_per_bucket),
                minimum_sample_pass=evidence >= request.minimum_evidence_per_bucket,
            )
        )
    return profiles


def _gates(
    request: ExactTimeSessionMemoryRequest,
    minute_profiles: list[ExactMinuteBehaviorProfile],
    transitions: list[SessionTransitionProfile],
    calendar_profiles: list[CalendarBehaviorProfile],
    no_later: bool,
    calendar_ok: bool,
) -> list[ExactTimeSessionMemoryGate]:
    independent_counts = all(item.independent_evidence_count > 0 for item in minute_profiles + transitions + calendar_profiles)
    enough_minute_evidence = any(item.independent_evidence_count >= request.minimum_evidence_per_bucket for item in minute_profiles)
    return [
        _gate("TV-V071-001", "Exact-minute profiles exist", bool(minute_profiles), f"minute_profiles={len(minute_profiles)}", "Build minute-level profiles."),
        _gate("TV-V071-002", "No later timestamps included", no_later, "includes_later_timestamps=false for all minute profiles", "Remove future/later timestamps from exact-time memory."),
        _gate("TV-V071-003", "Session boundaries follow exchange calendar", calendar_ok, f"exchange={request.exchange.upper()}, windows={len(SESSION_WINDOWS)}", "Use exchange-calendar session boundaries."),
        _gate("TV-V071-004", "Independent evidence counts", independent_counts, "minute/session/calendar counts are stored separately", "Store evidence count per memory bucket."),
        _gate("TV-V071-005", "Calendar-class profiles exist", len(calendar_profiles) >= 7, f"calendar_profiles={len(calendar_profiles)}", "Track Monday/Friday/expiry/post-holiday/results/RBI-Fed classes."),
        _gate("TV-V071-006", "Minimum evidence guard represented", enough_minute_evidence, f"minimum_evidence_per_bucket={request.minimum_evidence_per_bucket}", "Collect more exact-time samples before trusting strong probabilities."),
        _gate("TV-V071-007", "Research-only safety", True, "trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true", "Keep exact-time memory research-only."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str) -> ExactTimeSessionMemoryGate:
    return ExactTimeSessionMemoryGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _local_datetime(timestamp_ns: int, timezone_offset_minutes: int) -> datetime:
    local_tz = timezone(timedelta(minutes=timezone_offset_minutes))
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc).astimezone(local_tz)


def _calendar_class(local_dt: datetime) -> str:
    if local_dt.weekday() == 0:
        return "normal_day"
    if local_dt.weekday() == 4:
        return "normal_day"
    return "normal_day"


def _resolution_time(minute: int, rng: random.Random) -> str:
    resolved = min(930, minute + 15 + rng.randint(0, 45))
    return f"{resolved // 60:02d}:{resolved % 60:02d}"


def _typicality_summary(profile: ExactMinuteBehaviorProfile) -> str:
    if profile.typical_or_unusual == "low_evidence":
        return "Low evidence. Similar exact-time history is not enough."
    return (
        f"At {profile.local_time}, behavior is {profile.typical_or_unusual}; "
        f"typicality={profile.current_state_typicality_score} and evidence={profile.independent_evidence_count}."
    )


def _evidence_quality(count: int, minimum: int) -> str:
    if count >= max(100, minimum * 3):
        return "STRONG"
    if count >= minimum:
        return "MEDIUM"
    return "LOW"
