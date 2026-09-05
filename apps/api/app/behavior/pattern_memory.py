from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from statistics import mean
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorMemoryRecord,
    CandleBar,
    CandleSeries,
    DayShapeVector,
    MarketEvent,
    PatternMemoryRequest,
    PatternMemoryResult,
    SimilarDayMatch,
    SimilarDayReplayResult,
)
from .constants import LOW_EVIDENCE_MESSAGE


PATTERN_MEMORY_VERSION = "behavior-pattern-memory.v0.18"
DAY_SHAPE_VECTOR_FIELDS = [
    "gap_pct",
    "first_15m_return",
    "first_30m_range",
    "vwap_position_score",
    "trend_slope",
    "pullback_depth",
    "volume_curve",
    "atr_expansion",
    "high_break_time",
    "low_break_time",
    "close_position",
    "rejection_count",
    "breakout_failure_count",
]
CONTINUATION_OUTCOMES = {"TARGET_HIT", "RETEST_SUCCESS", "PARTIAL_WIN"}
REVERSAL_OUTCOMES = {"SL_HIT", "RETEST_FAIL"}
FAKEOUT_OUTCOMES = {"FAKE_BREAKOUT"}
RANGE_OUTCOMES = {"CHOP_NO_FOLLOWTHROUGH", "TIME_EXIT", "BREAKEVEN"}


def analyze_pattern_memory(request: PatternMemoryRequest, memory: list[BehaviorMemoryRecord]) -> PatternMemoryResult:
    current = calculate_day_shape_vector(
        request.series,
        previous_close=request.previous_close,
        decision_time_ns=request.decision_time_ns,
        timezone_offset_minutes=request.timezone_offset_minutes,
    )
    matches = build_similar_day_matches(
        symbol=request.series.symbol,
        current=current,
        memory=memory,
        minimum_sample_size=request.minimum_sample_size,
        max_matches=request.max_matches,
    )
    evidence = _evidence_quality(len(memory), request.minimum_sample_size)
    minimum_pass = len(memory) >= request.minimum_sample_size
    probabilities = _outcome_probabilities(matches)
    average_next_move = _weighted_average([m.average_next_move_atr for m in matches], [m.similarity_score_pct for m in matches])
    top = matches[0] if matches else None
    no_trade_reason = None
    if not minimum_pass:
        no_trade_reason = LOW_EVIDENCE_MESSAGE
    elif probabilities["fakeout"] >= probabilities["continuation"]:
        no_trade_reason = "Similar-day memory shows fakeout/reversal risk is not lower than continuation edge."
    elif probabilities["range"] >= 45:
        no_trade_reason = "Similar-day memory is range/chop heavy; wait for clearer follow-through."

    result = PatternMemoryResult(
        memory_version=PATTERN_MEMORY_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        day_shape_vector=current,
        vector_fields=DAY_SHAPE_VECTOR_FIELDS,
        similarity_methods=["cosine_similarity", "dtw_distance", "time_decay_weight", "k_nearest_historical_days"],
        matches=matches,
        historical_match_count=len(memory),
        minimum_sample_size=request.minimum_sample_size,
        minimum_sample_pass=minimum_pass,
        evidence_quality=evidence,
        continuation_probability_pct=round(probabilities["continuation"], 4),
        reversal_probability_pct=round(probabilities["reversal"], 4),
        fakeout_probability_pct=round(probabilities["fakeout"], 4),
        range_probability_pct=round(probabilities["range"], 4),
        average_next_move_atr=round(average_next_move, 4),
        best_invalidation=_best_invalidation(top),
        similar_day_ids=[match.similar_day_id for match in matches],
        replay_ready=any(match.replay_available for match in matches),
        no_trade_reason=no_trade_reason,
        reason_tree={
            "shape": "Today is encoded with the exact 13-field day_shape_vector.",
            "matching": "Matches are ranked by cosine shape similarity, DTW path distance, and time decay.",
            "evidence": f"Historical match count is {len(memory)}; minimum required is {request.minimum_sample_size}.",
            "probability": _probability_reason(probabilities),
            "safety": no_trade_reason or "Pattern memory does not block by itself; downstream risk gates still apply.",
        },
    )
    return result


def calculate_day_shape_vector(
    series: CandleSeries,
    *,
    previous_close: float | None = None,
    decision_time_ns: int | None = None,
    timezone_offset_minutes: int = 330,
) -> DayShapeVector:
    bars = _available_bars(series, decision_time_ns)
    if not bars:
        return DayShapeVector(
            gap_pct=0.0,
            first_15m_return=0.0,
            first_30m_range=0.0,
            vwap_position_score=0.0,
            trend_slope=0.0,
            pullback_depth=0.0,
            volume_curve=0.0,
            atr_expansion=0.0,
            high_break_time="unknown",
            low_break_time="unknown",
            close_position=0.0,
            rejection_count=0,
            breakout_failure_count=0,
            vector_values=[0.0] * len(DAY_SHAPE_VECTOR_FIELDS),
        )

    first = bars[0]
    latest = bars[-1]
    high = max(bar.high for bar in bars)
    low = min(bar.low for bar in bars)
    gap_pct = _pct_change(first.open, previous_close) if previous_close else 0.0
    first_15 = bars[: min(3, len(bars))]
    first_30 = bars[: min(6, len(bars))]
    first_15m_return = _pct_change(first_15[-1].close, first.open)
    first_30m_range = _range_pct(first_30, first.open)
    vwap = _vwap(bars)
    vwap_position_score = _pct_change(latest.close, vwap) if vwap else 0.0
    trend_slope = _pct_change(latest.close, first.open)
    pullback_depth = _pullback_depth(bars)
    volume_curve = _volume_curve_score(bars)
    atr_expansion = _atr_expansion(bars)
    high_idx = max(range(len(bars)), key=lambda idx: bars[idx].high)
    low_idx = min(range(len(bars)), key=lambda idx: bars[idx].low)
    high_break_time = _local_time_label(bars[high_idx].timestamp_ns, timezone_offset_minutes)
    low_break_time = _local_time_label(bars[low_idx].timestamp_ns, timezone_offset_minutes)
    close_position = 0.0 if high == low else (latest.close - low) / (high - low)
    rejection_count = sum(1 for bar in bars if _wick_rejection_ratio(bar) >= 0.45)
    breakout_failure_count = _breakout_failure_count(bars)
    vector_values = [
        round(gap_pct, 4),
        round(first_15m_return, 4),
        round(first_30m_range, 4),
        round(vwap_position_score, 4),
        round(trend_slope, 4),
        round(pullback_depth, 4),
        round(volume_curve, 4),
        round(atr_expansion, 4),
        round(_minutes_of_day(bars[high_idx].timestamp_ns, timezone_offset_minutes) / 1000.0, 4),
        round(_minutes_of_day(bars[low_idx].timestamp_ns, timezone_offset_minutes) / 1000.0, 4),
        round(close_position, 4),
        float(rejection_count),
        float(breakout_failure_count),
    ]
    return DayShapeVector(
        gap_pct=round(gap_pct, 4),
        first_15m_return=round(first_15m_return, 4),
        first_30m_range=round(first_30m_range, 4),
        vwap_position_score=round(vwap_position_score, 4),
        trend_slope=round(trend_slope, 4),
        pullback_depth=round(pullback_depth, 4),
        volume_curve=round(volume_curve, 4),
        atr_expansion=round(atr_expansion, 4),
        high_break_time=high_break_time,
        low_break_time=low_break_time,
        close_position=round(close_position, 4),
        rejection_count=rejection_count,
        breakout_failure_count=breakout_failure_count,
        vector_values=vector_values,
    )


def build_similar_day_matches(
    *,
    symbol: str,
    current: DayShapeVector,
    memory: list[BehaviorMemoryRecord],
    minimum_sample_size: int = 30,
    max_matches: int = 5,
) -> list[SimilarDayMatch]:
    normalized = symbol.upper()
    total_memory = len(memory)
    evidence = _evidence_quality(total_memory, minimum_sample_size)
    scored: list[SimilarDayMatch] = []
    for record in memory:
        matched = _record_day_shape_vector(record)
        cosine = _cosine_similarity_pct(current.vector_values, matched.vector_values)
        dtw = _dtw_similarity_pct(current.vector_values, matched.vector_values)
        decay = _time_decay_weight(record.trade_date)
        score = (cosine * 0.55) + (dtw * 0.25) + ((decay * 100.0) * 0.20)
        match = SimilarDayMatch(
            match_id=f"{normalized}-similar-{record.trade_date}-{_safe_id(record.pattern_id)}",
            symbol=normalized,
            similar_day_id=f"mock-day-{record.trade_date}",
            similarity_score_pct=round(score, 4),
            outcome_label=record.outcome_label,
            average_next_move_atr=round(_safe_float(record.feature_snapshot.get("move_atr"), default=_outcome_default_move(record.outcome_label)), 4),
            failure_reason=_failure_reason(record),
            replay_available=True,
            pattern_id=record.pattern_id,
            market_state=record.market_state,
            session_phase=record.session_phase,
            similarity_method="cosine_dtw_decay",
            cosine_similarity_pct=round(cosine, 4),
            dtw_similarity_pct=round(dtw, 4),
            time_decay_weight=round(decay, 4),
            evidence_quality=evidence,
            minimum_sample_pass=total_memory >= minimum_sample_size,
            feature_match_summary=_feature_match_summary(record),
            current_day_shape_vector=current,
            matched_day_shape_vector=matched,
            no_trade_reason=None if total_memory >= minimum_sample_size else LOW_EVIDENCE_MESSAGE,
        )
        scored.append(match)
    return sorted(scored, key=lambda item: item.similarity_score_pct, reverse=True)[:max_matches]


def build_similar_day_replay(symbol: str, match: SimilarDayMatch, *, event_count: int = 16) -> SimilarDayReplayResult:
    seed = uuid5(NAMESPACE_URL, f"tradevision:similar-day:{symbol}:{match.similar_day_id}:{match.match_id}").int % 1_000_000
    events: list[MarketEvent] = []
    base = 1_714_724_800_000_000_000
    direction = 1.0 if match.outcome_label in CONTINUATION_OUTCOMES else -1.0 if match.outcome_label in FAKEOUT_OUTCOMES | REVERSAL_OUTCOMES else 0.15
    for idx in range(event_count):
        price = 100.0 + (direction * idx * 0.12) + math.sin((idx + seed % 7) / 3.0) * 0.35
        volume = 1200 + ((seed + idx * 137) % 2800)
        payload = {
            "price": round(price, 4),
            "volume": volume,
            "outcome_label": match.outcome_label,
            "similar_day_id": match.similar_day_id,
            "pattern_id": match.pattern_id,
        }
        raw = json.dumps({"idx": idx, "payload": payload, "seed": seed, "match": match.match_id}, sort_keys=True)
        events.append(
            MarketEvent(
                event_id=str(uuid5(NAMESPACE_URL, f"tradevision:similar-replay:{match.match_id}:{seed}:{idx}")),
                parent_event_id=events[-1].event_id if events else None,
                virtual_timestamp_ns=base + idx * 300_000_000_000,
                source_mode="REPLAY",
                sequence_number=idx + 1,
                symbol=symbol.upper(),
                payload=payload,
                watermark=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            )
        )
    return SimilarDayReplayResult(
        replay_version=PATTERN_MEMORY_VERSION,
        symbol=symbol.upper(),
        similar_day_id=match.similar_day_id,
        match=match,
        day_shape_vector=match.matched_day_shape_vector,
        events=events,
        deterministic=True,
        replay_notes=[
            "Replay is deterministic for the same symbol and similar_day_id.",
            "Replay is mock/simulation only and cannot route orders.",
            "Outcome path is shaped from the stored similar-day label for visual analysis.",
        ],
    )


def _available_bars(series: CandleSeries, decision_time_ns: int | None) -> list[CandleBar]:
    bars = sorted(series.bars, key=lambda item: item.timestamp_ns)
    if decision_time_ns is None:
        return bars
    return [bar for bar in bars if bar.timestamp_ns <= decision_time_ns]


def _record_day_shape_vector(record: BehaviorMemoryRecord) -> DayShapeVector:
    raw = record.feature_snapshot.get("day_shape_vector")
    if isinstance(raw, dict):
        try:
            return DayShapeVector.model_validate(raw)
        except Exception:
            pass
    return _fallback_day_shape(record)


def _fallback_day_shape(record: BehaviorMemoryRecord) -> DayShapeVector:
    rsi = _safe_float(record.feature_snapshot.get("rsi"), default=55.0)
    adx = _safe_float(record.feature_snapshot.get("adx"), default=20.0)
    volume_z = _safe_float(record.feature_snapshot.get("volume_z"), default=0.0)
    move = _safe_float(record.feature_snapshot.get("move_atr"), default=_outcome_default_move(record.outcome_label))
    fakeout = 1 if record.outcome_label in FAKEOUT_OUTCOMES else 0
    rejection = 3 if fakeout else 1
    values = [
        0.0,
        round((rsi - 50.0) / 10.0, 4),
        round(max(adx / 20.0, 0.0), 4),
        round(volume_z, 4),
        round(move, 4),
        round(abs(move) / 2.0, 4),
        round(1.0 if volume_z > 0.5 else -0.5 if volume_z < -0.2 else 0.0, 4),
        round(max(abs(move), 0.2), 4),
        0.585,
        0.615,
        0.7 if move > 0 else 0.3 if move < 0 else 0.5,
        float(rejection),
        float(fakeout),
    ]
    return DayShapeVector(
        gap_pct=values[0],
        first_15m_return=values[1],
        first_30m_range=values[2],
        vwap_position_score=values[3],
        trend_slope=values[4],
        pullback_depth=values[5],
        volume_curve=values[6],
        atr_expansion=values[7],
        high_break_time="09:45",
        low_break_time="10:15",
        close_position=values[10],
        rejection_count=int(values[11]),
        breakout_failure_count=int(values[12]),
        vector_values=values,
    )


def _outcome_probabilities(matches: list[SimilarDayMatch]) -> dict[str, float]:
    weights = [max(match.similarity_score_pct, 0.0) for match in matches]
    total = sum(weights)
    if total <= 0:
        return {"continuation": 0.0, "reversal": 0.0, "fakeout": 0.0, "range": 0.0}
    buckets = {"continuation": 0.0, "reversal": 0.0, "fakeout": 0.0, "range": 0.0}
    for match, weight in zip(matches, weights):
        if match.outcome_label in CONTINUATION_OUTCOMES:
            buckets["continuation"] += weight
        elif match.outcome_label in FAKEOUT_OUTCOMES:
            buckets["fakeout"] += weight
        elif match.outcome_label in REVERSAL_OUTCOMES:
            buckets["reversal"] += weight
        else:
            buckets["range"] += weight
    return {key: (value / total) * 100.0 for key, value in buckets.items()}


def _probability_reason(probabilities: dict[str, float]) -> str:
    top = max(probabilities, key=probabilities.get)
    return f"Dominant weighted outcome bucket is {top} at {round(probabilities[top], 2)}%."


def _best_invalidation(match: SimilarDayMatch | None) -> str:
    if match is None:
        return "insufficient memory; no invalidation derived"
    if match.outcome_label in FAKEOUT_OUTCOMES:
        return "above morning high after failed breakout, or wait for VWAP reclaim"
    if match.outcome_label in CONTINUATION_OUTCOMES:
        return "below VWAP and opening range midpoint"
    if match.outcome_label in RANGE_OUTCOMES:
        return "outside range boundary with follow-through volume"
    return "beyond recent swing level with closed-candle confirmation"


def _feature_match_summary(record: BehaviorMemoryRecord) -> str:
    rsi = record.feature_snapshot.get("rsi", "unknown")
    adx = record.feature_snapshot.get("adx", "unknown")
    volume_z = record.feature_snapshot.get("volume_z", "unknown")
    vwap_state = record.feature_snapshot.get("vwap_state", "unknown")
    return f"RSI={rsi}, ADX={adx}, volume_z={volume_z}, VWAP={vwap_state}, outcome={record.outcome_label}."


def _failure_reason(record: BehaviorMemoryRecord) -> str | None:
    if record.outcome_label in CONTINUATION_OUTCOMES:
        return None
    return record.reason


def _evidence_quality(count: int, minimum_sample_size: int) -> str:
    if count >= 100:
        return "STRONG"
    if count >= minimum_sample_size:
        return "MEDIUM"
    return "LOW"


def _weighted_average(values: list[float], weights: list[float]) -> float:
    total = sum(max(weight, 0.0) for weight in weights)
    if total <= 0:
        return 0.0
    return sum(value * max(weight, 0.0) for value, weight in zip(values, weights)) / total


def _cosine_similarity_pct(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[idx] * b[idx] for idx in range(n))
    norm_a = math.sqrt(sum(a[idx] ** 2 for idx in range(n)))
    norm_b = math.sqrt(sum(b[idx] ** 2 for idx in range(n)))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(100.0, ((dot / (norm_a * norm_b)) + 1.0) * 50.0))


def _dtw_similarity_pct(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n, m = len(a), len(b)
    dp = [[math.inf] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(a[i - 1] - b[j - 1])
            dp[i][j] = cost + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    normalized = dp[n][m] / max(n, m)
    return max(0.0, min(100.0, 100.0 / (1.0 + normalized)))


def _time_decay_weight(trade_date: str) -> float:
    try:
        day = datetime.fromisoformat(trade_date).replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.35
    anchor = datetime(2024, 6, 1, tzinfo=timezone.utc)
    age_days = max((anchor - day).days, 0)
    return math.exp(-age_days / 180.0)


def _pct_change(value: float, baseline: float | None) -> float:
    if baseline is None or baseline == 0:
        return 0.0
    return ((value - baseline) / baseline) * 100.0


def _range_pct(bars: list[CandleBar], baseline: float) -> float:
    if not bars or baseline == 0:
        return 0.0
    return ((max(bar.high for bar in bars) - min(bar.low for bar in bars)) / baseline) * 100.0


def _vwap(bars: list[CandleBar]) -> float | None:
    weighted = 0.0
    total_volume = 0.0
    for bar in bars:
        volume = bar.volume if bar.volume is not None else 0.0
        typical = (bar.high + bar.low + bar.close) / 3.0
        weighted += typical * volume
        total_volume += volume
    if total_volume <= 0:
        return None
    return weighted / total_volume


def _pullback_depth(bars: list[CandleBar]) -> float:
    high_idx = max(range(len(bars)), key=lambda idx: bars[idx].high)
    after_high = bars[high_idx:]
    if not after_high:
        return 0.0
    high = bars[high_idx].high
    low_after = min(bar.low for bar in after_high)
    return _pct_change(high, low_after) if high else 0.0


def _volume_curve_score(bars: list[CandleBar]) -> float:
    volumes = [bar.volume for bar in bars if bar.volume is not None]
    if len(volumes) < 2:
        return 0.0
    split = max(1, len(volumes) // 2)
    first = mean(volumes[:split])
    second = mean(volumes[split:])
    if first <= 0:
        return 0.0
    return (second - first) / first


def _atr_expansion(bars: list[CandleBar]) -> float:
    ranges = [max(bar.high - bar.low, 0.0) for bar in bars]
    if len(ranges) < 2:
        return 0.0
    split = max(1, len(ranges) // 3)
    early = mean(ranges[:split])
    late = mean(ranges[-split:])
    if early <= 0:
        return 0.0
    return late / early


def _wick_rejection_ratio(bar: CandleBar) -> float:
    body_high = max(bar.open, bar.close)
    body_low = min(bar.open, bar.close)
    candle_range = max(bar.high - bar.low, 0.0001)
    upper = max(bar.high - body_high, 0.0) / candle_range
    lower = max(body_low - bar.low, 0.0) / candle_range
    return max(upper, lower)


def _breakout_failure_count(bars: list[CandleBar]) -> int:
    failures = 0
    prior_high = bars[0].high
    prior_low = bars[0].low
    for bar in bars[1:]:
        if bar.high > prior_high and bar.close < prior_high:
            failures += 1
        if bar.low < prior_low and bar.close > prior_low:
            failures += 1
        prior_high = max(prior_high, bar.high)
        prior_low = min(prior_low, bar.low)
    return failures


def _local_time_label(timestamp_ns: int, offset_minutes: int) -> str:
    local = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc) + timedelta(minutes=offset_minutes)
    return local.strftime("%H:%M")


def _minutes_of_day(timestamp_ns: int, offset_minutes: int) -> int:
    local = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc) + timedelta(minutes=offset_minutes)
    return local.hour * 60 + local.minute


def _outcome_default_move(outcome_label: str) -> float:
    if outcome_label in CONTINUATION_OUTCOMES:
        return 1.2
    if outcome_label in FAKEOUT_OUTCOMES | REVERSAL_OUTCOMES:
        return -0.65
    return -0.12


def _safe_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)
