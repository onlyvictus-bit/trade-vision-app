from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean

from ..models import (
    BehaviorMemoryRecord,
    CandleBar,
    DayOfWeekMemoryRecord,
    DayOfWeekMemoryResult,
    SessionMemoryProfile,
    SessionPhaseValue,
    SessionRhythmRequest,
    SessionRhythmResult,
    SessionSegmentScore,
    StockDNAProfile,
    StockDNASummary,
    now_iso,
)


SESSION_MEMORY_VERSION = "behavior-session-memory.v0.17"
MINIMUM_SAMPLE_SIZE = 30
STRONG_SAMPLE_SIZE = 100


SESSION_WINDOWS: list[tuple[SessionPhaseValue, str, str, int, int]] = [
    ("09:15-09:30_open_drive", "09:15", "09:30", 555, 570),
    ("09:30-10:15_real_trend_confirmation", "09:30", "10:15", 570, 615),
    ("10:15-11:30_continuation_or_fade", "10:15", "11:30", 615, 690),
    ("11:30-13:30_lunch_compression", "11:30", "13:30", 690, 810),
    ("13:30-14:30_post_lunch_expansion", "13:30", "14:30", 810, 870),
    ("14:30-15:15_closing_drive", "14:30", "15:15", 870, 915),
    ("15:15-15:30_squareoff_fake_spike", "15:15", "15:30", 915, 930),
]


def analyze_session_rhythm(request: SessionRhythmRequest) -> SessionRhythmResult:
    bars = _available_bars(request)
    grouped: dict[SessionPhaseValue, list[CandleBar]] = {phase: [] for phase, _, _, _, _ in SESSION_WINDOWS}
    outside: list[CandleBar] = []
    for bar in bars:
        phase = session_phase_for_timestamp(bar.timestamp_ns, request.timezone_offset_minutes)
        if phase == "outside_regular_session":
            outside.append(bar)
        else:
            grouped[phase].append(bar)

    segments = [
        _score_segment(phase, start, end, grouped[phase], request.minimum_bars_per_segment)
        for phase, start, end, _, _ in SESSION_WINDOWS
    ]
    if outside:
        segments.append(_score_segment("outside_regular_session", "outside", "outside", outside, request.minimum_bars_per_segment))

    latest = bars[-1] if bars else None
    current_phase = session_phase_for_timestamp(latest.timestamp_ns, request.timezone_offset_minutes) if latest else "outside_regular_session"
    day = _local_datetime(latest.timestamp_ns, request.timezone_offset_minutes) if latest else None
    best = max(segments, key=lambda item: item.trade_quality_score) if segments else None
    worst = max(segments, key=lambda item: item.fakeout_risk + (1.0 - item.trade_quality_score)) if segments else None
    continuation = max(segments, key=lambda item: item.continuation_score) if segments else None
    fakeout = max(segments, key=lambda item: item.fakeout_risk) if segments else None
    current_segment = next((segment for segment in segments if segment.session_phase == current_phase), None)
    score = _session_personality_score(segments)
    blocks = bool(current_segment and (current_segment.fakeout_risk >= 0.68 or current_segment.trade_quality_score <= 0.28))
    reasons = [
        f"Current session phase is {current_phase}.",
        f"Best window is {best.window_start}-{best.window_end}." if best else "No best window available.",
        f"Worst window is {worst.window_start}-{worst.window_end}." if worst else "No worst window available.",
        f"Session personality score is {round(score, 2)}.",
    ]
    no_trade_reason = None
    if blocks:
        no_trade_reason = "NO TRADE: current session rhythm is low-quality or fakeout-prone."
        reasons.append(no_trade_reason)

    return SessionRhythmResult(
        rhythm_version=SESSION_MEMORY_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        trading_date=day.date().isoformat() if day else None,
        day_of_week=day.strftime("%A") if day else "unknown",  # type: ignore[arg-type]
        current_session_phase=current_phase,
        segments=segments,
        usual_open_behavior=_usual_behavior_for_phase("open", segments),
        usual_midday_behavior=_usual_behavior_for_phase("midday", segments),
        usual_closing_behavior=_usual_behavior_for_phase("close", segments),
        best_trade_window=f"{best.window_start}-{best.window_end}" if best else "unknown",
        worst_trade_window=f"{worst.window_start}-{worst.window_end}" if worst else "unknown",
        fakeout_window=f"{fakeout.window_start}-{fakeout.window_end}" if fakeout else "unknown",
        continuation_window=f"{continuation.window_start}-{continuation.window_end}" if continuation else "unknown",
        session_personality_score=round(score, 4),
        blocks_trade=blocks,
        no_trade_reason=no_trade_reason,
        reasons=reasons,
    )


def build_session_memory_profiles(symbol: str, memory: list[BehaviorMemoryRecord]) -> list[SessionMemoryProfile]:
    normalized = symbol.upper()
    by_phase: dict[SessionPhaseValue, list[BehaviorMemoryRecord]] = defaultdict(list)
    for record in memory:
        phase = _phase_from_text(record.session_phase)
        by_phase[phase].append(record)

    profiles: list[SessionMemoryProfile] = []
    for phase, start, end, _, _ in SESSION_WINDOWS:
        records = by_phase.get(phase, [])
        sample_count = len(records)
        continuation_count = sum(1 for record in records if record.outcome_label in {"TARGET_HIT", "RETEST_SUCCESS", "PARTIAL_WIN"})
        fakeout_count = sum(1 for record in records if record.outcome_label in {"FAKE_BREAKOUT", "RETEST_FAIL", "CHOP_NO_FOLLOWTHROUGH"})
        continuation_rate = _pct(continuation_count, sample_count)
        fakeout_rate = _pct(fakeout_count, sample_count)
        moves = [_safe_float(record.feature_snapshot.get("move_atr"), default=0.0) for record in records]
        evidence = _evidence_quality(sample_count)
        profile = SessionMemoryProfile(
            symbol=normalized,
            profile_version=SESSION_MEMORY_VERSION,
            updated_at=now_iso(),
            session_phase=phase,
            sample_count=sample_count,
            continuation_rate_pct=round(continuation_rate, 4),
            fakeout_rate_pct=round(fakeout_rate, 4),
            average_move_atr=round(mean(moves), 4) if moves else 0.0,
            usual_behavior=_usual_memory_behavior(phase, continuation_rate, fakeout_rate, sample_count),
            best_trade_window=f"{start}-{end}" if continuation_rate >= fakeout_rate else "none_until_more_evidence",
            worst_trade_window=f"{start}-{end}" if fakeout_rate > continuation_rate else "none_until_more_evidence",
            evidence_quality=evidence,
            minimum_sample_pass=sample_count >= MINIMUM_SAMPLE_SIZE,
            notes=_profile_notes(phase, sample_count, continuation_rate, fakeout_rate),
        )
        profiles.append(profile)
    return profiles


def build_day_of_week_memory(symbol: str, memory: list[BehaviorMemoryRecord]) -> DayOfWeekMemoryResult:
    normalized = symbol.upper()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    by_day: dict[str, list[BehaviorMemoryRecord]] = {day: [] for day in day_names}
    for record in memory:
        try:
            day = datetime.fromisoformat(record.trade_date).strftime("%A")
        except ValueError:
            day = "Monday"
        if day in by_day:
            by_day[day].append(record)

    records: list[DayOfWeekMemoryRecord] = []
    for day in day_names:
        day_records = by_day[day]
        sample_count = len(day_records)
        continuation = sum(1 for record in day_records if record.outcome_label in {"TARGET_HIT", "RETEST_SUCCESS", "PARTIAL_WIN"})
        reversal = sum(1 for record in day_records if record.outcome_label in {"SL_HIT", "FAKE_BREAKOUT", "RETEST_FAIL"})
        fakeout = sum(1 for record in day_records if record.outcome_label in {"FAKE_BREAKOUT", "CHOP_NO_FOLLOWTHROUGH"})
        best_phase, worst_phase = _best_worst_phase(day_records)
        moves = [_safe_float(record.feature_snapshot.get("move_atr"), default=0.0) for record in day_records]
        records.append(
            DayOfWeekMemoryRecord(
                day_of_week=day,  # type: ignore[arg-type]
                sample_count=sample_count,
                continuation_rate_pct=round(_pct(continuation, sample_count), 4),
                reversal_rate_pct=round(_pct(reversal, sample_count), 4),
                fakeout_rate_pct=round(_pct(fakeout, sample_count), 4),
                average_next_move_atr=round(mean(moves), 4) if moves else 0.0,
                best_session_phase=best_phase,
                worst_session_phase=worst_phase,
                behavior_note=_day_note(day, sample_count, continuation, fakeout),
                minimum_sample_pass=sample_count >= MINIMUM_SAMPLE_SIZE,
            )
        )

    total_samples = sum(record.sample_count for record in records)
    blocks = total_samples < MINIMUM_SAMPLE_SIZE
    reasons = [
        f"Total day-of-week samples for {normalized}: {total_samples}.",
        f"Minimum sample size for strong probability: {MINIMUM_SAMPLE_SIZE}.",
    ]
    if blocks:
        reasons.append("Low evidence. Similar history is not enough.")
    dominant = max(records, key=lambda item: item.sample_count) if records else None
    return DayOfWeekMemoryResult(
        memory_version=SESSION_MEMORY_VERSION,
        symbol=normalized,
        records=records,
        dominant_day_note=dominant.behavior_note if dominant else "No day-of-week memory available.",
        minimum_sample_size=MINIMUM_SAMPLE_SIZE,
        total_samples=total_samples,
        blocks_strong_probability=blocks,
        reasons=reasons,
    )


def build_stock_dna_summary(
    *,
    stock_dna: StockDNAProfile,
    rhythm: SessionRhythmResult,
    memory: list[BehaviorMemoryRecord],
) -> StockDNASummary:
    profiles = build_session_memory_profiles(stock_dna.symbol, memory)
    day_memory = build_day_of_week_memory(stock_dna.symbol, memory)
    minimum_evidence = day_memory.total_samples >= MINIMUM_SAMPLE_SIZE and any(profile.minimum_sample_pass for profile in profiles)
    behavior_edges = _behavior_edges(rhythm, profiles)
    risk_warnings = _risk_warnings(rhythm, profiles, day_memory)
    return StockDNASummary(
        symbol=stock_dna.symbol,
        profile_version=SESSION_MEMORY_VERSION,
        updated_at=now_iso(),
        session_rhythm=rhythm,
        session_memory=profiles,
        day_of_week_memory=day_memory,
        stock_dna=stock_dna,
        stock_personality_summary=_stock_personality_summary(stock_dna, rhythm, profiles),
        behavior_edges=behavior_edges,
        risk_warnings=risk_warnings,
        minimum_evidence_pass=minimum_evidence,
        learning_status="mock_seeded",
    )


def session_phase_for_timestamp(timestamp_ns: int, timezone_offset_minutes: int = 330) -> SessionPhaseValue:
    local = _local_datetime(timestamp_ns, timezone_offset_minutes)
    minute = local.hour * 60 + local.minute
    for phase, _, _, start_minute, end_minute in SESSION_WINDOWS:
        if start_minute <= minute < end_minute:
            return phase
    return "outside_regular_session"


def _available_bars(request: SessionRhythmRequest) -> list[CandleBar]:
    bars = sorted(request.series.bars, key=lambda item: item.timestamp_ns)
    if request.decision_time_ns is None:
        return bars
    return [bar for bar in bars if bar.timestamp_ns <= request.decision_time_ns]


def _score_segment(
    phase: SessionPhaseValue,
    start: str,
    end: str,
    bars: list[CandleBar],
    minimum_bars: int,
) -> SessionSegmentScore:
    if not bars:
        return SessionSegmentScore(
            session_phase=phase,
            window_start=start,
            window_end=end,
            bar_count=0,
            return_pct=0.0,
            range_pct=0.0,
            avg_volume=None,
            volume_curve="unknown",
            trend_bias="unknown",
            continuation_score=0.0,
            fakeout_risk=0.5,
            trade_quality_score=0.0,
            notes=["No bars available for this session segment."],
        )
    first, latest = bars[0], bars[-1]
    high = max(bar.high for bar in bars)
    low = min(bar.low for bar in bars)
    return_pct = ((latest.close - first.open) / first.open) * 100.0
    range_pct = ((high - low) / first.open) * 100.0
    volumes = [bar.volume for bar in bars if bar.volume is not None]
    avg_volume = mean(volumes) if volumes else None
    curve = _volume_curve(volumes)
    trend_bias = _trend_bias(return_pct, range_pct, bars)
    continuation = _continuation_score(return_pct, range_pct, curve, bars, minimum_bars)
    fakeout = _fakeout_risk(return_pct, range_pct, bars, phase, minimum_bars)
    quality = min(max((continuation * 0.65) + ((1.0 - fakeout) * 0.35), 0.0), 1.0)
    notes = [
        f"{phase} return is {round(return_pct, 4)}%.",
        f"{phase} range is {round(range_pct, 4)}%.",
        f"Volume curve is {curve}.",
    ]
    if len(bars) < minimum_bars:
        notes.append("Insufficient bars for reliable segment scoring.")
    if phase == "11:30-13:30_lunch_compression" and quality < 0.45:
        notes.append("Lunch compression reduces trade quality.")
    if phase == "15:15-15:30_squareoff_fake_spike":
        notes.append("Square-off window has elevated fake-spike risk.")

    return SessionSegmentScore(
        session_phase=phase,
        window_start=start,
        window_end=end,
        bar_count=len(bars),
        return_pct=round(return_pct, 4),
        range_pct=round(range_pct, 4),
        avg_volume=round(avg_volume, 4) if avg_volume is not None else None,
        volume_curve=curve,
        trend_bias=trend_bias,
        continuation_score=round(continuation, 4),
        fakeout_risk=round(fakeout, 4),
        trade_quality_score=round(quality, 4),
        notes=notes,
    )


def _volume_curve(volumes: list[float]) -> str:
    if len(volumes) < 2:
        return "unknown"
    first_half = mean(volumes[: max(1, len(volumes) // 2)])
    second_half = mean(volumes[max(1, len(volumes) // 2) :])
    if second_half > first_half * 1.08:
        return "rising"
    if second_half < first_half * 0.92:
        return "falling"
    return "flat"


def _trend_bias(return_pct: float, range_pct: float, bars: list[CandleBar]) -> str:
    if len(bars) < 2:
        return "unknown"
    wick_rejections = sum(1 for bar in bars if _upper_or_lower_wick_ratio(bar) >= 0.5)
    if wick_rejections >= max(2, len(bars) // 2):
        return "choppy"
    if abs(return_pct) <= 0.12 or range_pct <= 0.2:
        return "range"
    return "bullish" if return_pct > 0 else "bearish"


def _continuation_score(return_pct: float, range_pct: float, curve: str, bars: list[CandleBar], minimum_bars: int) -> float:
    score = 0.2
    if len(bars) >= minimum_bars:
        score += 0.15
    if abs(return_pct) >= 0.25:
        score += 0.25
    if range_pct >= 0.35:
        score += 0.12
    if curve == "rising":
        score += 0.18
    if _close_position(bars[-1]) >= 0.68 or _close_position(bars[-1]) <= 0.32:
        score += 0.1
    return min(score, 1.0)


def _fakeout_risk(return_pct: float, range_pct: float, bars: list[CandleBar], phase: SessionPhaseValue, minimum_bars: int) -> float:
    score = 0.15
    latest = bars[-1]
    if len(bars) < minimum_bars:
        score += 0.18
    if _upper_or_lower_wick_ratio(latest) >= 0.45:
        score += 0.2
    if range_pct >= 0.7 and abs(return_pct) <= 0.15:
        score += 0.18
    if phase in {"11:30-13:30_lunch_compression", "15:15-15:30_squareoff_fake_spike"}:
        score += 0.14
    if latest.high > max(bar.high for bar in bars[:-1] or [latest]) and latest.close < latest.high:
        score += 0.1
    return min(score, 1.0)


def _upper_or_lower_wick_ratio(bar: CandleBar) -> float:
    body_high = max(bar.open, bar.close)
    body_low = min(bar.open, bar.close)
    candle_range = max(bar.high - bar.low, 0.0001)
    upper = max(bar.high - body_high, 0.0) / candle_range
    lower = max(body_low - bar.low, 0.0) / candle_range
    return max(upper, lower)


def _close_position(bar: CandleBar) -> float:
    candle_range = max(bar.high - bar.low, 0.0001)
    return (bar.close - bar.low) / candle_range


def _session_personality_score(segments: list[SessionSegmentScore]) -> float:
    usable = [segment.trade_quality_score for segment in segments if segment.bar_count > 0]
    if not usable:
        return 0.0
    return min(max(mean(usable), 0.0), 1.0)


def _usual_behavior_for_phase(group: str, segments: list[SessionSegmentScore]) -> str:
    if group == "open":
        candidates = [s for s in segments if s.session_phase in {"09:15-09:30_open_drive", "09:30-10:15_real_trend_confirmation"}]
    elif group == "midday":
        candidates = [s for s in segments if s.session_phase in {"10:15-11:30_continuation_or_fade", "11:30-13:30_lunch_compression"}]
    else:
        candidates = [s for s in segments if s.session_phase in {"14:30-15:15_closing_drive", "15:15-15:30_squareoff_fake_spike"}]
    if not candidates or all(candidate.bar_count == 0 for candidate in candidates):
        return "unknown"
    best = max(candidates, key=lambda item: item.trade_quality_score)
    if best.trend_bias == "bullish":
        return f"{best.window_start}-{best.window_end} bullish continuation tendency"
    if best.trend_bias == "bearish":
        return f"{best.window_start}-{best.window_end} bearish/fade tendency"
    if best.trend_bias == "choppy":
        return f"{best.window_start}-{best.window_end} choppy or fakeout-prone"
    return f"{best.window_start}-{best.window_end} range/compression tendency"


def _phase_from_text(text: str) -> SessionPhaseValue:
    lower = text.lower()
    for phase, start, end, _, _ in SESSION_WINDOWS:
        if start in text or end in text or phase.split("_", 1)[1] in lower:
            return phase
    if "open" in lower:
        return "09:30-10:15_real_trend_confirmation"
    if "lunch" in lower:
        return "11:30-13:30_lunch_compression"
    if "close" in lower:
        return "14:30-15:15_closing_drive"
    return "outside_regular_session"


def _evidence_quality(sample_count: int) -> str:
    if sample_count >= STRONG_SAMPLE_SIZE:
        return "STRONG"
    if sample_count >= MINIMUM_SAMPLE_SIZE:
        return "MEDIUM"
    return "LOW"


def _usual_memory_behavior(phase: SessionPhaseValue, continuation_rate: float, fakeout_rate: float, sample_count: int) -> str:
    if sample_count == 0:
        return "No stored behavior memory yet."
    if sample_count < MINIMUM_SAMPLE_SIZE:
        return "Low evidence. Similar history is not enough."
    if continuation_rate > fakeout_rate + 15:
        return f"{phase} has continuation edge in stored memory."
    if fakeout_rate > continuation_rate + 15:
        return f"{phase} is fakeout-prone in stored memory."
    return f"{phase} is mixed and needs extra confirmation."


def _profile_notes(phase: SessionPhaseValue, sample_count: int, continuation_rate: float, fakeout_rate: float) -> list[str]:
    notes = [f"{phase} samples: {sample_count}."]
    if sample_count < MINIMUM_SAMPLE_SIZE:
        notes.append("Minimum evidence guard blocks strong probability claims.")
    if fakeout_rate > continuation_rate:
        notes.append("Fakeout outcomes are more common than continuation outcomes in current memory.")
    return notes


def _best_worst_phase(records: list[BehaviorMemoryRecord]) -> tuple[SessionPhaseValue, SessionPhaseValue]:
    if not records:
        return "outside_regular_session", "outside_regular_session"
    grouped: dict[SessionPhaseValue, list[BehaviorMemoryRecord]] = defaultdict(list)
    for record in records:
        grouped[_phase_from_text(record.session_phase)].append(record)

    def score(items: list[BehaviorMemoryRecord]) -> float:
        wins = sum(1 for item in items if item.outcome_label in {"TARGET_HIT", "RETEST_SUCCESS", "PARTIAL_WIN"})
        losses = sum(1 for item in items if item.outcome_label in {"FAKE_BREAKOUT", "SL_HIT", "CHOP_NO_FOLLOWTHROUGH"})
        return wins - losses

    best = max(grouped, key=lambda phase: score(grouped[phase]))
    worst = min(grouped, key=lambda phase: score(grouped[phase]))
    return best, worst


def _day_note(day: str, sample_count: int, continuation: int, fakeout: int) -> str:
    if sample_count == 0:
        return f"{day}: no stored behavior yet."
    if sample_count < MINIMUM_SAMPLE_SIZE:
        return f"{day}: low evidence; do not trust day-specific probability yet."
    if continuation > fakeout:
        return f"{day}: continuation has historically exceeded fakeout outcomes."
    if fakeout > continuation:
        return f"{day}: fakeout/chop has historically exceeded continuation outcomes."
    return f"{day}: mixed behavior; require context confirmation."


def _behavior_edges(rhythm: SessionRhythmResult, profiles: list[SessionMemoryProfile]) -> list[str]:
    edges = [
        f"Best current session window: {rhythm.best_trade_window}.",
        f"Continuation window: {rhythm.continuation_window}.",
    ]
    for profile in profiles:
        if profile.minimum_sample_pass and profile.continuation_rate_pct > profile.fakeout_rate_pct:
            edges.append(f"{profile.session_phase}: stored continuation edge {profile.continuation_rate_pct}%.")
    return edges


def _risk_warnings(rhythm: SessionRhythmResult, profiles: list[SessionMemoryProfile], day_memory: DayOfWeekMemoryResult) -> list[str]:
    warnings: list[str] = []
    if rhythm.blocks_trade and rhythm.no_trade_reason:
        warnings.append(rhythm.no_trade_reason)
    if day_memory.blocks_strong_probability:
        warnings.append("Day-of-week memory is below minimum sample size.")
    for profile in profiles:
        if profile.fakeout_rate_pct > profile.continuation_rate_pct:
            warnings.append(f"{profile.session_phase}: fakeout memory currently exceeds continuation memory.")
    return warnings or ["No session-memory warning in mock context."]


def _stock_personality_summary(stock_dna: StockDNAProfile, rhythm: SessionRhythmResult, profiles: list[SessionMemoryProfile]) -> str:
    low_evidence = all(not profile.minimum_sample_pass for profile in profiles)
    if low_evidence:
        return (
            f"{stock_dna.symbol} has mock Stock DNA only: {rhythm.usual_open_behavior}; "
            "minimum evidence guard remains active."
        )
    return (
        f"{stock_dna.symbol} tends toward {rhythm.usual_open_behavior}, "
        f"with {rhythm.best_trade_window} as the highest-quality observed window."
    )


def _pct(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (count / total) * 100.0


def _safe_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _local_datetime(timestamp_ns: int, offset_minutes: int) -> datetime:
    utc = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc)
    return utc + timedelta(minutes=offset_minutes)
