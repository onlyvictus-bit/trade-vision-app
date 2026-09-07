from __future__ import annotations

import math
from statistics import mean

from ..models import (
    CandleBar,
    ExecutionEventOiRiskGate,
    ExecutionEventOiRiskReport,
    ExecutionEventOiRiskRequest,
)


EXECUTION_EVENT_OI_RISK_VERSION = "execution-event-oi-risk.v1.73"
EPSILON = 1e-9


def build_execution_event_oi_risk_report(request: ExecutionEventOiRiskRequest) -> ExecutionEventOiRiskReport:
    bars = sorted(request.series.bars, key=lambda bar: (bar.timestamp_ns, bar.sequence_number))
    latest = bars[-1] if bars else None
    latest_close = _latest_close(bars)
    entry = request.entry_price or latest_close
    atr = _atr(bars, 14)
    safe_atr = max(atr, latest_close * 0.001, EPSILON)
    depth_status = "available" if request.depth_available else ("ohlcv_proxy" if bars else "unavailable")
    single_tick_wick = _single_tick_wick_risk(bars, entry, safe_atr)
    gap_risk = _gap_through_entry_risk(bars, entry)
    volume_percentile = _latest_volume_percentile(bars)
    spread_pct = _effective_spread_pct(request, bars)
    slippage_pct = _effective_slippage_pct(request, bars, spread_pct)
    fill_probability = _fill_probability(
        request=request,
        spread_pct=spread_pct,
        slippage_pct=slippage_pct,
        volume_percentile=volume_percentile,
        single_tick_wick=single_tick_wick,
        gap_risk=gap_risk,
    )
    slippage_risk = _slippage_risk(spread_pct, slippage_pct, volume_percentile, request.market_cap_class)
    impact_cost_pct = _impact_cost_pct(request, bars)
    liquidity_grade = _liquidity_grade(fill_probability, slippage_risk, impact_cost_pct, volume_percentile)
    target_move_pct = _distance_pct(entry, request.target)
    stop_distance_pct = _distance_pct(entry, request.stop_loss)
    event_score = _event_risk_score(request)
    earnings = _earnings_adjustment(request)
    expiry = _expiry_pinning_risk(request, entry)
    expected_limit = _expected_move_limit(request.expected_move_pct, target_move_pct)
    gamma_context = _gamma_wall_context(request, entry)
    max_pain = _max_pain_magnet(request, entry)
    unavailable = _unavailable_reasons(request, depth_status)
    confidence_cap = _confidence_cap(
        request=request,
        source_bar_count=len(bars),
        liquidity_grade=liquidity_grade,
        single_tick_wick=single_tick_wick,
        gap_risk=gap_risk,
        impact_cost_pct=impact_cost_pct,
        expected_limit=expected_limit,
        event_score=event_score,
        unavailable=unavailable,
    )
    execution_status = _execution_plan_status(confidence_cap, liquidity_grade, fill_probability, impact_cost_pct)
    gates = _gates(
        request=request,
        source_bar_count=len(bars),
        depth_status=depth_status,
        spread_pct=spread_pct,
        fill_probability=fill_probability,
        single_tick_wick=single_tick_wick,
        volume_percentile=volume_percentile,
        impact_cost_pct=impact_cost_pct,
        expected_limit=expected_limit,
        event_score=event_score,
        gamma_context=gamma_context,
        unavailable=unavailable,
    )
    return ExecutionEventOiRiskReport(
        risk_version=EXECUTION_EVENT_OI_RISK_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        closed_candle_only=True,
        source_bar_count=len(bars),
        latest_timestamp_ns=latest.timestamp_ns if latest else None,
        latest_sequence_number=latest.sequence_number if latest else None,
        entry_price=round(entry, 6),
        target_move_pct=None if target_move_pct is None else round(target_move_pct, 6),
        stop_distance_pct=None if stop_distance_pct is None else round(stop_distance_pct, 6),
        fill_probability=round(fill_probability, 6),
        slippage_risk=round(slippage_risk, 6),
        impact_cost_pct=round(impact_cost_pct, 6),
        liquidity_grade=liquidity_grade,
        execution_plan_status=execution_status,
        depth_context_status=depth_status,
        event_context_status=request.event_context_status,
        options_context_status=request.options_context_status,
        single_tick_wick_risk=single_tick_wick,
        gap_through_entry_risk=gap_risk,
        event_risk_score=round(event_score, 6),
        earnings_adjustment=earnings,
        expiry_pinning_risk=expiry,
        expected_move_limit=expected_limit,
        expected_move_pct=request.expected_move_pct,
        gamma_wall_context=gamma_context,
        max_pain_magnet=max_pain,
        confidence_cap=confidence_cap,
        unavailable_reasons=unavailable,
        no_future_leakage=True,
        used_for_probability=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        reasons=_reasons(
            fill_probability=fill_probability,
            liquidity_grade=liquidity_grade,
            execution_status=execution_status,
            event_score=event_score,
            expected_limit=expected_limit,
            gamma_context=gamma_context,
            confidence_cap=confidence_cap,
        ),
        failure_questions=_failure_questions(request, depth_status, liquidity_grade, expected_limit),
        gates=gates,
    )


def build_report_with_derivatives_context(request: ExecutionEventOiRiskRequest, context) -> ExecutionEventOiRiskReport:
    """G9: v1.73 report with options fields auto-populated from a DerivativesContext.

    The overlay maps computed context values onto the request (never overwriting
    caller fields with None), then builds through the identical report path, so a
    context-fed report differs from a hand-typed one only in its evidence source.
    `context` is a DerivativesContext (untyped here to keep this module free of an
    orb import at module load; validated structurally by the overlay keys).
    """
    from app.orb.derivatives.bridges import v173_payload_overlay

    merged = v173_payload_overlay(context, request.model_dump(mode="json"))
    return build_execution_event_oi_risk_report(ExecutionEventOiRiskRequest.model_validate(merged))


def _effective_spread_pct(request: ExecutionEventOiRiskRequest, bars: list[CandleBar]) -> float:
    if request.spread_pct is not None:
        return request.spread_pct
    if len(bars) < 2:
        return 0.35
    latest = bars[-1]
    candle_range_pct = ((latest.high - latest.low) / max(latest.close, EPSILON)) * 100.0
    return _clamp(candle_range_pct * 0.18, 0.02, 1.25)


def _effective_slippage_pct(request: ExecutionEventOiRiskRequest, bars: list[CandleBar], spread_pct: float) -> float:
    if request.average_slippage_pct is not None:
        return request.average_slippage_pct
    instability = _range_instability(bars)
    return _clamp(spread_pct * 0.70 + instability * 0.12, 0.01, 2.5)


def _fill_probability(
    *,
    request: ExecutionEventOiRiskRequest,
    spread_pct: float,
    slippage_pct: float,
    volume_percentile: float,
    single_tick_wick: bool,
    gap_risk: bool,
) -> float:
    depth_ratio = 1.0
    if request.depth_available and request.visible_depth_value is not None and request.intended_position_value > 0:
        depth_ratio = min(request.visible_depth_value / max(request.intended_position_value, EPSILON), 2.0)
    elif not request.depth_available:
        depth_ratio = 0.75
    market_cap_penalty = {"largecap": 0.00, "midcap": 0.08, "smallcap": 0.18, "unknown": 0.10}[request.market_cap_class]
    score = 0.92
    score -= min(spread_pct / 1.25, 0.40)
    score -= min(slippage_pct / 1.80, 0.35)
    score += (volume_percentile - 50.0) / 250.0
    score += min(depth_ratio - 1.0, 0.50) * 0.12
    score -= market_cap_penalty
    if single_tick_wick:
        score -= 0.22
    if gap_risk:
        score -= 0.18
    return _clamp(score, 0.0, 1.0)


def _slippage_risk(spread_pct: float, slippage_pct: float, volume_percentile: float, market_cap_class: str) -> float:
    market_cap_penalty = {"largecap": 0.05, "midcap": 0.15, "smallcap": 0.30, "unknown": 0.20}[market_cap_class]
    volume_penalty = max(0.0, (45.0 - volume_percentile) / 100.0)
    return _clamp((spread_pct / 1.5) * 0.45 + (slippage_pct / 1.5) * 0.35 + market_cap_penalty + volume_penalty, 0.0, 1.0)


def _impact_cost_pct(request: ExecutionEventOiRiskRequest, bars: list[CandleBar]) -> float:
    if request.intended_position_value <= 0:
        return 0.0
    if request.depth_available and request.visible_depth_value is not None and request.visible_depth_value > 0:
        return _clamp((request.intended_position_value / request.visible_depth_value) * 0.08, 0.0, 5.0)
    avg_value = _average_bar_value(bars)
    if avg_value <= EPSILON:
        return 1.0
    return _clamp((request.intended_position_value / max(avg_value * 10.0, EPSILON)) * 0.10, 0.0, 5.0)


def _liquidity_grade(fill_probability: float, slippage_risk: float, impact_cost_pct: float, volume_percentile: float) -> str:
    if fill_probability >= 0.72 and slippage_risk <= 0.35 and impact_cost_pct <= 0.25 and volume_percentile >= 35.0:
        return "A"
    if fill_probability >= 0.45 and slippage_risk <= 0.65 and impact_cost_pct <= 0.75:
        return "B"
    return "C"


def _single_tick_wick_risk(bars: list[CandleBar], entry: float, atr: float) -> bool:
    if not bars:
        return False
    latest = bars[-1]
    body = abs(latest.close - latest.open)
    upper_wick = latest.high - max(latest.open, latest.close)
    lower_wick = min(latest.open, latest.close) - latest.low
    wick_ratio = max(upper_wick, lower_wick) / max(latest.high - latest.low, EPSILON)
    close_far_from_entry = abs(latest.close - entry) > atr * 0.25
    entry_near_extreme = min(abs(entry - latest.high), abs(entry - latest.low)) <= atr * 0.12
    return wick_ratio >= 0.62 and body <= (latest.high - latest.low) * 0.35 and entry_near_extreme and close_far_from_entry


def _gap_through_entry_risk(bars: list[CandleBar], entry: float) -> bool:
    if len(bars) < 2:
        return False
    prior = bars[-2]
    latest = bars[-1]
    crossed_without_trade = latest.open > entry and prior.close < entry
    crossed_down_without_trade = latest.open < entry and prior.close > entry
    gap_pct = abs(latest.open - prior.close) / max(prior.close, EPSILON) * 100.0
    return gap_pct >= 0.40 and (crossed_without_trade or crossed_down_without_trade)


def _event_risk_score(request: ExecutionEventOiRiskRequest) -> float:
    if request.event_context_status == "unavailable":
        return 0.35
    score = 0.0
    if request.days_to_earnings is not None and request.days_to_earnings <= 3:
        score += 0.45
    if request.macro_event_minutes is not None and request.macro_event_minutes <= request.target_holding_minutes:
        score += 0.35
    if request.expiry_day:
        score += 0.20
    if request.event_context_status == "partial":
        score += 0.15
    return _clamp(score, 0.0, 1.0)


def _earnings_adjustment(request: ExecutionEventOiRiskRequest) -> str:
    if request.event_context_status == "unavailable":
        return "unavailable"
    if request.days_to_earnings is not None and request.days_to_earnings <= 1:
        return "watch_only"
    if request.days_to_earnings is not None and request.days_to_earnings <= 3:
        return "reduce_size"
    return "none"


def _expiry_pinning_risk(request: ExecutionEventOiRiskRequest, entry: float) -> str:
    if request.options_context_status == "unavailable":
        return "unavailable"
    if not request.expiry_day:
        return "none"
    if request.max_pain is not None:
        distance = abs(entry - request.max_pain) / max(entry, EPSILON) * 100.0
        if distance <= 0.40:
            return "high"
        if distance <= 1.00:
            return "moderate"
    if request.oi_concentration_pct is not None and request.oi_concentration_pct >= 65.0:
        return "moderate"
    return "none"


def _expected_move_limit(expected_move_pct: float | None, target_move_pct: float | None) -> str:
    if expected_move_pct is None or target_move_pct is None:
        return "unavailable"
    return "target_beyond_expected_move" if target_move_pct > expected_move_pct * 1.10 else "within_expected_move"


def _gamma_wall_context(request: ExecutionEventOiRiskRequest, entry: float) -> str:
    if request.options_context_status == "unavailable":
        return "unavailable"
    walls: list[str] = []
    if request.call_gamma_wall is not None:
        distance = (request.call_gamma_wall - entry) / max(entry, EPSILON) * 100.0
        if 0.0 <= distance <= 1.25:
            walls.append("call_gamma_wall_near_above_resistance")
    if request.put_gamma_wall is not None:
        distance = (entry - request.put_gamma_wall) / max(entry, EPSILON) * 100.0
        if 0.0 <= distance <= 1.25:
            walls.append("put_gamma_wall_near_below_support")
    if request.call_gamma_wall is not None and request.put_gamma_wall is not None and request.put_gamma_wall < entry < request.call_gamma_wall:
        walls.append("between_gamma_walls_pinning_range")
    return "none" if not walls else "|".join(walls)


def _max_pain_magnet(request: ExecutionEventOiRiskRequest, entry: float) -> str:
    if request.options_context_status == "unavailable" or request.max_pain is None:
        return "unavailable"
    distance = abs(entry - request.max_pain) / max(entry, EPSILON) * 100.0
    if distance <= 0.40:
        return "active_pin_zone"
    if distance <= 1.25:
        return "nearby_magnet"
    return "distant"


def _confidence_cap(
    *,
    request: ExecutionEventOiRiskRequest,
    source_bar_count: int,
    liquidity_grade: str,
    single_tick_wick: bool,
    gap_risk: bool,
    impact_cost_pct: float,
    expected_limit: str,
    event_score: float,
    unavailable: list[str],
) -> str:
    if source_bar_count < request.minimum_bars:
        return "WAIT"
    if liquidity_grade == "C" or single_tick_wick or gap_risk:
        return "WAIT"
    if impact_cost_pct > 0.75 or expected_limit == "target_beyond_expected_move" or event_score >= 0.70:
        return "WAIT"
    if event_score >= 0.35 or unavailable:
        return "WATCH"
    return "RESEARCH_CONTEXT_ONLY"


def _execution_plan_status(confidence_cap: str, liquidity_grade: str, fill_probability: float, impact_cost_pct: float) -> str:
    if confidence_cap == "WAIT" or liquidity_grade == "C" or fill_probability < 0.45 or impact_cost_pct > 0.75:
        return "BLOCKED"
    if confidence_cap == "WATCH":
        return "WATCH_ONLY"
    return "RESEARCH_ONLY"


def _unavailable_reasons(request: ExecutionEventOiRiskRequest, depth_status: str) -> list[str]:
    reasons: list[str] = []
    if depth_status != "available":
        reasons.append("depth/order-book data unavailable; using OHLCV proxy" if depth_status == "ohlcv_proxy" else "depth/order-book data unavailable")
    if request.event_context_status == "unavailable":
        reasons.append("event calendar unavailable")
    if request.options_context_status == "unavailable":
        reasons.append("options/OI/gamma context unavailable")
    if request.spread_pct is None:
        reasons.append("spread_pct missing; estimated from closed candle range")
    if request.average_slippage_pct is None:
        reasons.append("average_slippage_pct missing; estimated from range instability")
    return reasons


def _gates(
    *,
    request: ExecutionEventOiRiskRequest,
    source_bar_count: int,
    depth_status: str,
    spread_pct: float,
    fill_probability: float,
    single_tick_wick: bool,
    volume_percentile: float,
    impact_cost_pct: float,
    expected_limit: str,
    event_score: float,
    gamma_context: str,
    unavailable: list[str],
) -> list[ExecutionEventOiRiskGate]:
    return [
        _gate("EXEC-001", "Single-tick wick entry risk is blocked", not single_tick_wick, "block" if single_tick_wick else "info", f"single_tick_wick_risk={single_tick_wick}."),
        _gate("EXEC-002", "High spread blocks paper-candidate", spread_pct < 0.60, "block" if spread_pct >= 0.60 else "info", f"spread_pct={spread_pct:.4f}."),
        _gate("EXEC-003", "Low volume blocks position sizing", volume_percentile >= 20.0, "block" if volume_percentile < 20.0 else "info", f"volume_percentile={volume_percentile:.4f}."),
        _gate("EXEC-004", "Impact cost must not exceed expected edge", impact_cost_pct <= 0.75, "block" if impact_cost_pct > 0.75 else "info", f"impact_cost_pct={impact_cost_pct:.4f}."),
        _gate("EXEC-005", "Missing depth is explicitly marked as proxy", depth_status in {"available", "ohlcv_proxy"}, "warn" if depth_status == "ohlcv_proxy" else "info", f"depth_context_status={depth_status}."),
        _gate("EVENT-001", "Earnings proximity downgrades size", not (request.days_to_earnings is not None and request.days_to_earnings <= 3), "warn" if request.days_to_earnings is not None and request.days_to_earnings <= 3 else "info", f"days_to_earnings={request.days_to_earnings}."),
        _gate("EVENT-002", "Macro event before target window caps confidence", not (request.macro_event_minutes is not None and request.macro_event_minutes <= request.target_holding_minutes), "warn" if request.macro_event_minutes is not None and request.macro_event_minutes <= request.target_holding_minutes else "info", f"macro_event_minutes={request.macro_event_minutes}."),
        _gate("EVENT-003", "Unavailable event data is not marked clean", request.event_context_status != "unavailable", "warn" if request.event_context_status == "unavailable" else "info", f"event_context_status={request.event_context_status}."),
        _gate("OPT-001", "Expected move caps unrealistic target", expected_limit != "target_beyond_expected_move", "block" if expected_limit == "target_beyond_expected_move" else "info", f"expected_move_limit={expected_limit}."),
        _gate("OPT-002", "Gamma wall context is surfaced when available", not gamma_context.startswith("call_gamma_wall"), "warn" if gamma_context.startswith("call_gamma_wall") else "info", f"gamma_wall_context={gamma_context}."),
        # Research-context only until separately proved. These gates consume
        # the previously-unused fields without turning them into direction votes.
        _gate("OPT-003", "Elevated IV percentile is surfaced as uncertainty context",
              request.iv_percentile is None or request.iv_percentile < 80.0,
              "warn" if request.iv_percentile is not None and request.iv_percentile >= 80.0 else "info",
              f"iv_percentile={request.iv_percentile}."),
        _gate("OPT-005", "Large IV skew is surfaced without inferring direction",
              request.iv_skew is None or abs(request.iv_skew) < 5.0,
              "warn" if request.iv_skew is not None and abs(request.iv_skew) >= 5.0 else "info",
              f"iv_skew={request.iv_skew}."),
        _gate("OPT-004", "Missing OI does not fabricate options context", request.options_context_status != "unavailable", "warn" if request.options_context_status == "unavailable" else "info", f"options_context_status={request.options_context_status}."),
        _gate("V173-SAFE-001", "Closed-candle minimum history is present", source_bar_count >= request.minimum_bars, "block" if source_bar_count < request.minimum_bars else "info", f"source_bar_count={source_bar_count}."),
        _gate("V173-SAFE-002", "Unavailable constraints cap confidence", not unavailable, "warn" if unavailable else "info", f"unavailable_reasons={len(unavailable)}."),
        _gate("V173-SAFE-003", "Execution risk cannot route orders", True, "info", f"fill_probability={fill_probability:.4f}."),
    ]


def _reasons(
    *,
    fill_probability: float,
    liquidity_grade: str,
    execution_status: str,
    event_score: float,
    expected_limit: str,
    gamma_context: str,
    confidence_cap: str,
) -> list[str]:
    reasons = [
        f"Execution plan status is {execution_status}; liquidity grade {liquidity_grade}; fill probability {fill_probability:.2f}.",
        f"Event risk score is {event_score:.2f}; expected move limit is {expected_limit}.",
        f"Gamma/max-pain context is {gamma_context}.",
        f"Final confidence cap is {confidence_cap}.",
    ]
    if execution_status == "BLOCKED":
        reasons.append("Trade idea must remain WAIT because fill, spread, impact, event, or expected-move risk is unfavorable.")
    return reasons


def _failure_questions(request: ExecutionEventOiRiskRequest, depth_status: str, liquidity_grade: str, expected_limit: str) -> list[str]:
    questions = [
        "Is the intended entry actually fillable at the shown price, or is it only a wick?",
        "Does spread, slippage, and impact cost destroy the expected R after cost?",
        "Is an earnings, macro, expiry, OI, or gamma constraint close enough to cap confidence?",
    ]
    if depth_status != "available":
        questions.append("Would live depth confirm the OHLCV proxy, or is this a no-fill setup?")
    if liquidity_grade == "C":
        questions.append("Should this idea be WATCH only because liquidity grade is C?")
    if expected_limit == "target_beyond_expected_move":
        questions.append("Is the target unrealistic versus the expected move?")
    if request.options_context_status == "unavailable":
        questions.append("Would OI/max-pain/gamma data change the target or range-risk assessment?")
    if request.iv_percentile is not None and request.iv_percentile >= 80.0:
        questions.append("Is elevated IV increasing both breakout and failure magnitude enough to invalidate static risk assumptions?")
    if request.iv_skew is not None and abs(request.iv_skew) >= 5.0:
        questions.append("Does large skew indicate asymmetric tail demand that conflicts with this setup, without treating skew as a direction vote?")
    return questions


def _gate(gate_id: str, name: str, passed: bool, severity: str, evidence: str, remediation: str | None = None) -> ExecutionEventOiRiskGate:
    return ExecutionEventOiRiskGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity=severity,  # type: ignore[arg-type]
        evidence=evidence,
        remediation=remediation,
    )


def _latest_close(bars: list[CandleBar]) -> float:
    return bars[-1].close if bars else 1.0


def _distance_pct(entry: float, level: float | None) -> float | None:
    if level is None:
        return None
    return abs(level - entry) / max(entry, EPSILON) * 100.0


def _latest_volume_percentile(bars: list[CandleBar]) -> float:
    if not bars:
        return 0.0
    latest = float(bars[-1].volume or 0.0)
    history = [float(bar.volume or 0.0) for bar in bars[:-1]]
    return _percentile_rank(latest, history)


def _range_instability(bars: list[CandleBar]) -> float:
    if len(bars) < 4:
        return 1.0
    ranges = [max(bar.high - bar.low, 0.0) / max(bar.close, EPSILON) * 100.0 for bar in bars[-20:]]
    avg = mean(ranges)
    if avg <= EPSILON:
        return 0.0
    return _clamp(max(ranges[-3:]) / avg, 0.0, 5.0)


def _average_bar_value(bars: list[CandleBar]) -> float:
    if not bars:
        return 0.0
    values = [bar.close * float(bar.volume or 0.0) for bar in bars[-20:]]
    return mean(values) if values else 0.0


def _atr(bars: list[CandleBar], period: int) -> float:
    if not bars:
        return 0.0
    true_ranges: list[float] = []
    previous_close: float | None = None
    for bar in bars[-period:]:
        if previous_close is None:
            true_ranges.append(max(bar.high - bar.low, 0.0))
        else:
            true_ranges.append(max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close)))
        previous_close = bar.close
    return mean(true_ranges) if true_ranges else 0.0


def _percentile_rank(value: float, history: list[float]) -> float:
    clean = [item for item in history if math.isfinite(item)]
    if not clean:
        return 50.0
    below = sum(1 for item in clean if item <= value)
    return _clamp((below / len(clean)) * 100.0, 0.0, 100.0)


def _clamp(value: float, lower: float, upper: float) -> float:
    if not math.isfinite(value):
        return lower
    return max(lower, min(upper, value))
