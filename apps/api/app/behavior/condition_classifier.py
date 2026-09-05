from __future__ import annotations

from statistics import mean

from ..models import (
    CandleAnatomyResult,
    CandleConditionRecord,
    ConditionClassifierRequest,
    ConditionClassifierResult,
    MarketConditionValue,
)
from .candle_anatomy import analyze_candles


CLASSIFIER_VERSION = "condition-classifier.v0.15"


def classify_conditions(request: ConditionClassifierRequest) -> ConditionClassifierResult:
    anatomy = request.anatomy or analyze_candles(
        request=_anatomy_request_from_classifier_request(request)
    )
    records = [
        _classify_record(index=index, anatomy=anatomy, request=request)
        for index in range(len(anatomy.features))
    ]
    latest = records[-1] if records else None
    condition_tags = latest.condition_tags if latest else ["unclassified"]
    market_state = latest.dominant_condition if latest else "unclassified"
    blocks_trade = bool(latest.blocks_trade if latest else True)
    no_trade_reason = latest.no_trade_reason if latest else "No candles available for classification."
    final_signal_bias = _final_signal_bias(latest)

    return ConditionClassifierResult(
        classifier_version=CLASSIFIER_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        records=records,
        latest=latest,
        market_state=market_state,
        condition_tags=condition_tags,
        final_signal_bias=final_signal_bias,
        blocks_trade=blocks_trade,
        no_trade_reason=no_trade_reason,
        reason_tree={
            "candle_structure": latest.candle_behavior if latest else "No candle.",
            "pattern_family": latest.pattern_family if latest else "none",
            "risk_filter": no_trade_reason or "No structural block from candle classifier.",
            "classification_rule": "Deterministic v0.15 candle anatomy thresholds, not ML prediction.",
        },
    )


def _anatomy_request_from_classifier_request(request: ConditionClassifierRequest):
    from ..models import CandleAnatomyRequest

    return CandleAnatomyRequest(
        series=request.series,
        breakout_reference_high=request.resistance_level or request.opening_range_high,
        breakout_reference_low=request.support_level or request.opening_range_low,
    )


def _classify_record(index: int, anatomy: CandleAnatomyResult, request: ConditionClassifierRequest) -> CandleConditionRecord:
    feature = anatomy.features[index]
    tags: list[MarketConditionValue] = []
    reasons: list[str] = []
    recent = anatomy.features[max(0, index - 4) : index + 1]
    prior = anatomy.features[index - 1] if index > 0 else None

    trap_probability = _trap_probability(feature, request, prior)
    absorption_score = _absorption_score(feature)
    continuation_quality = _continuation_quality(feature, recent, request)
    uncertainty_score = _uncertainty_score(feature, recent)

    if _is_opening_drive_continuation(feature, recent, request):
        tags.append("opening_drive_continuation")
        reasons.append("Strong body, bullish close location, and early-session continuation context.")
    if _is_opening_drive_reversal(feature, request):
        tags.append("opening_drive_reversal")
        reasons.append("Early-session candle rejects opening/VWAP context with opposite pressure.")
    if _is_range_balance(recent):
        tags.append("range_balance_day")
        reasons.append("Recent candles show low body expansion and overlapping range behavior.")
    if _is_breakout_day(feature, request):
        tags.append("breakout_day")
        reasons.append("Candle closed beyond reference resistance/support with expansion.")
    if trap_probability >= 0.62 or feature.failed_follow_through:
        tags.append("fake_breakout")
        reasons.append("Breakout/follow-through quality failed or trap probability is elevated.")
    if _is_vwap_rejection(feature, request):
        tags.append("vwap_rejection")
        reasons.append("Price failed near VWAP with wick rejection.")
    if _is_vwap_support_trend(feature, request):
        tags.append("vwap_support_trend")
        reasons.append("Price is holding above VWAP with constructive close location.")
    if absorption_score >= 0.62:
        tags.append("absorption")
        reasons.append("Volume effort is high while candle body result is weak.")
    if _is_distribution(feature):
        tags.append("distribution")
        reasons.append("Upper wick and bearish close suggest selling pressure into strength.")
    if _is_accumulation(feature):
        tags.append("accumulation")
        reasons.append("Lower wick and stable close suggest demand absorbing dips.")
    if _is_compression_before_expansion(recent):
        tags.append("compression_before_expansion")
        reasons.append("Recent candles are compressed relative to ATR; expansion risk is building.")
    if uncertainty_score >= 0.72:
        tags.append("choppy_avoid")
        reasons.append("Uncertainty is high due to wickiness, low body control, or overlap.")
    if _is_manipulated_looking(feature):
        tags.append("manipulated_looking")
        reasons.append("Large wick/range/volume behavior lacks clean follow-through.")

    if not tags:
        tags.append("unclassified")
        reasons.append("No high-confidence structure condition matched.")

    dominant = _dominant_condition(tags)
    blocks_trade = dominant in {"fake_breakout", "choppy_avoid", "manipulated_looking", "range_balance_day"} or uncertainty_score >= 0.78
    no_trade_reason = None
    if blocks_trade:
        no_trade_reason = _no_trade_reason(dominant)

    return CandleConditionRecord(
        timestamp_ns=feature.timestamp_ns,
        sequence_number=feature.sequence_number,
        dominant_condition=dominant,
        condition_tags=tags,
        candle_behavior=", ".join(feature.candle_structure_types),
        pattern_family=_pattern_family(tags),
        trap_probability=round(trap_probability, 4),
        absorption_score=round(absorption_score, 4),
        continuation_quality=round(continuation_quality, 4),
        uncertainty_score=round(uncertainty_score, 4),
        blocks_trade=blocks_trade,
        no_trade_reason=no_trade_reason,
        reasons=reasons,
    )


def _is_opening_drive_continuation(feature, recent, request) -> bool:
    return (
        "09:15" in request.session_phase or "09:30" in request.session_phase or "open" in request.session_phase.lower()
    ) and feature.direction == "bullish" and feature.body_pct >= 55 and feature.close_location_value >= 0.7 and _avg_volume_z(recent) >= 0.0


def _is_opening_drive_reversal(feature, request) -> bool:
    if not ("09:15" in request.session_phase or "09:30" in request.session_phase or "open" in request.session_phase.lower()):
        return False
    return feature.upper_wick_pct >= 40 and feature.close_location_value <= 0.45


def _is_range_balance(recent) -> bool:
    if len(recent) < 4:
        return False
    avg_body = mean([feature.body_pct for feature in recent])
    avg_range = mean([feature.range_atr for feature in recent])
    wickiness = mean([feature.upper_wick_pct + feature.lower_wick_pct for feature in recent])
    return avg_body <= 35 and avg_range <= 1.05 and wickiness >= 45


def _is_breakout_day(feature, request) -> bool:
    long_breakout = bool(
        request.resistance_level
        and feature.close > request.resistance_level
        and feature.close_location_value >= 0.7
        and feature.direction == "bullish"
    )
    short_breakout = bool(
        request.support_level
        and feature.close < request.support_level
        and feature.close_location_value <= 0.3
        and feature.direction == "bearish"
    )
    return (long_breakout or short_breakout) and feature.body_pct >= 50 and feature.range_atr >= 1.05


def _is_vwap_rejection(feature, request) -> bool:
    if request.vwap is None:
        return False
    touched_vwap = feature.low <= request.vwap <= feature.high
    return touched_vwap and feature.upper_wick_pct >= 35 and feature.close < request.vwap


def _is_vwap_support_trend(feature, request) -> bool:
    if request.vwap is None:
        return False
    return feature.low <= request.vwap <= feature.close and feature.direction == "bullish" and feature.close_location_value >= 0.65 and feature.lower_wick_pct >= 18


def _is_distribution(feature) -> bool:
    return feature.upper_wick_pct >= 35 and feature.close_location_value <= 0.45 and (feature.volume_z or 0.0) >= 0.5


def _is_accumulation(feature) -> bool:
    return feature.lower_wick_pct >= 35 and feature.close_location_value >= 0.55 and (feature.volume_z or 0.0) >= 0.3


def _is_compression_before_expansion(recent) -> bool:
    if len(recent) < 3:
        return False
    return mean([feature.range_atr for feature in recent[-3:]]) <= 0.75 and mean([feature.body_pct for feature in recent[-3:]]) <= 35


def _is_manipulated_looking(feature) -> bool:
    volume_z = feature.volume_z or 0.0
    return (feature.upper_wick_pct >= 55 or feature.lower_wick_pct >= 55) and feature.range_atr >= 1.5 and feature.follow_through_count == 0 and volume_z >= 1.0


def _trap_probability(feature, request, prior) -> float:
    score = 0.1
    if feature.failed_follow_through:
        score += 0.45
    if feature.upper_wick_pct >= 40 and feature.direction != "bullish":
        score += 0.18
    if request.resistance_level and feature.high >= request.resistance_level and feature.close <= request.resistance_level:
        score += 0.14
    if prior and prior.body_pct >= 50 and feature.body_pct <= 30:
        score += 0.11
    if feature.volume_z is not None and feature.volume_z >= 1.0 and feature.body_pct <= 30:
        score += 0.12
    return min(score, 1.0)


def _absorption_score(feature) -> float:
    volume_z = feature.volume_z or 0.0
    score = 0.0
    if volume_z > 0:
        score += min(volume_z / 3.0, 0.45)
    if feature.body_pct <= 30:
        score += 0.3
    if feature.upper_wick_pct >= 30 or feature.lower_wick_pct >= 30:
        score += 0.2
    if feature.effort_vs_result is not None and feature.effort_vs_result >= 0.03:
        score += 0.1
    return min(score, 1.0)


def _continuation_quality(feature, recent, request) -> float:
    score = 0.0
    if feature.body_pct >= 50:
        score += 0.25
    if feature.close_location_value >= 0.65:
        score += 0.2
    if feature.range_atr >= 1.0:
        score += 0.15
    if feature.follow_through_count >= 1:
        score += 0.2
    if _avg_volume_z(recent) >= 0:
        score += 0.1
    if request.vwap is not None:
        score += 0.1
    if feature.failed_follow_through:
        score -= 0.35
    return min(max(score, 0.0), 1.0)


def _uncertainty_score(feature, recent) -> float:
    score = 0.15
    if feature.body_pct <= 25:
        score += 0.2
    if feature.upper_wick_pct + feature.lower_wick_pct >= 60:
        score += 0.2
    if feature.wick_cluster_count >= 3:
        score += 0.2
    if _is_range_balance(recent):
        score += 0.2
    if feature.volume_z is None:
        score += 0.08
    return min(score, 1.0)


def _avg_volume_z(recent) -> float:
    values = [feature.volume_z for feature in recent if feature.volume_z is not None]
    if not values:
        return 0.0
    return mean(values)


def _dominant_condition(tags: list[MarketConditionValue]) -> MarketConditionValue:
    priority: list[MarketConditionValue] = [
        "manipulated_looking",
        "fake_breakout",
        "choppy_avoid",
        "range_balance_day",
        "breakout_day",
        "opening_drive_continuation",
        "opening_drive_reversal",
        "absorption",
        "distribution",
        "accumulation",
        "vwap_rejection",
        "vwap_support_trend",
        "compression_before_expansion",
        "unclassified",
    ]
    for condition in priority:
        if condition in tags:
            return condition
    return "unclassified"


def _pattern_family(tags: list[MarketConditionValue]) -> str:
    if "fake_breakout" in tags:
        return "breakout_failure"
    if "breakout_day" in tags:
        return "breakout_expansion"
    if "range_balance_day" in tags or "choppy_avoid" in tags:
        return "range_or_chop"
    if "opening_drive_continuation" in tags:
        return "opening_drive"
    if "absorption" in tags or "accumulation" in tags or "distribution" in tags:
        return "effort_vs_result"
    return "unclassified"


def _no_trade_reason(condition: MarketConditionValue) -> str:
    return {
        "fake_breakout": "NO TRADE: fakeout risk is elevated; wait for reclaim or retest confirmation.",
        "choppy_avoid": "NO TRADE: candle structure is noisy and uncertainty is high.",
        "manipulated_looking": "NO TRADE: wick/range/volume behavior looks abnormal without follow-through.",
        "range_balance_day": "NO TRADE: range/balance conditions reduce directional edge.",
    }.get(condition, "NO TRADE: condition classifier blocked this setup.")


def _final_signal_bias(latest: CandleConditionRecord | None) -> str:
    if latest is None or latest.blocks_trade:
        return "avoid"
    if latest.dominant_condition in {"opening_drive_continuation", "breakout_day", "vwap_support_trend", "accumulation"}:
        return "long"
    if latest.dominant_condition in {"opening_drive_reversal", "distribution", "vwap_rejection"}:
        return "short"
    return "wait"
