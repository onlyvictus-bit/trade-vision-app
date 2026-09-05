from __future__ import annotations

import math
from statistics import mean, pstdev

from ..models import MarketRegimeFeedbackGate, MarketRegimeFeedbackReport, MarketRegimeFeedbackRequest


MARKET_REGIME_FEEDBACK_VERSION = "market-regime-breadth-rs-bayesian.v1.71"
ALLOWED_LIVE_UPDATES = ["new_labels", "failure_memory", "confidence_calibration", "drift_alerts", "analog_index_refresh"]
FORBIDDEN_LIVE_UPDATES = ["live_model_weight_mutation", "live_lightgbm_retraining", "live_feature_selection_changes"]


def build_market_regime_feedback_report(request: MarketRegimeFeedbackRequest) -> MarketRegimeFeedbackReport:
    unavailable = _unavailable_reasons(request)
    context_status = _context_status(unavailable)
    trend_state = _trend_state(request.index_return_pct, request.banknifty_return_pct, request.sector_return_pct)
    breadth_state = _breadth_state(request.advance_decline_ratio, request.sector_advance_decline_ratio)
    rs_score = _relative_strength_score(request)
    rs_position = _relative_strength_position(request)
    correlation = _rolling_correlation(request.stock_returns_pct, request.index_returns_pct)
    lead_lag = _leading_lagging_state(rs_score, rs_position, request.index_return_pct, request.sector_return_pct)
    minimum_pass = request.setup_sample_count >= request.minimum_sample_size
    posterior = _bayesian_posterior(request)
    edge = _stock_specific_edge(request)
    failure_penalty = _recent_failure_penalty(request.recent_signal_outcomes)
    cooldown = failure_penalty >= 0.60 or _recent_loss_streak(request.recent_signal_outcomes) >= 3
    confirmation = _dynamic_confirmation_requirement(request, context_status, trend_state, breadth_state, lead_lag, minimum_pass, cooldown)
    confidence_cap = _confidence_cap(context_status, breadth_state, cooldown, minimum_pass)
    reasons = _reasons(
        request=request,
        context_status=context_status,
        trend_state=trend_state,
        breadth_state=breadth_state,
        rs_score=rs_score,
        rs_position=rs_position,
        posterior=posterior,
        failure_penalty=failure_penalty,
        confidence_cap=confidence_cap,
    )
    gates = _gates(
        request=request,
        context_status=context_status,
        breadth_state=breadth_state,
        rs_score=rs_score,
        minimum_pass=minimum_pass,
        cooldown=cooldown,
        confidence_cap=confidence_cap,
    )
    return MarketRegimeFeedbackReport(
        feedback_version=MARKET_REGIME_FEEDBACK_VERSION,
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        direction=request.direction,
        market_context_status=context_status,
        trend_state=trend_state,
        breadth_state=breadth_state,
        relative_strength_score=round(rs_score, 6),
        relative_strength_position=round(rs_position, 6),
        rolling_correlation_to_index=round(correlation, 6),
        leading_lagging_state=lead_lag,
        prior_confidence=round(request.prior_confidence, 6),
        posterior_confidence=round(posterior, 6),
        stock_specific_edge=round(edge, 6),
        recent_failure_penalty=round(failure_penalty, 6),
        dynamic_confirmation_requirement=confirmation,
        cooldown_active=cooldown,
        confidence_cap=confidence_cap,
        minimum_sample_pass=minimum_pass,
        unavailable_reasons=unavailable,
        allowed_live_updates=ALLOWED_LIVE_UPDATES,
        forbidden_live_updates=FORBIDDEN_LIVE_UPDATES,
        no_live_weight_mutation=True,
        used_for_probability=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        reasons=reasons,
        failure_questions=_failure_questions(request, context_status),
        gates=gates,
    )


def _unavailable_reasons(request: MarketRegimeFeedbackRequest) -> list[str]:
    reasons: list[str] = []
    if request.index_return_pct is None:
        reasons.append("index_return_pct missing")
    if request.sector_return_pct is None:
        reasons.append("sector_return_pct missing")
    if request.advance_decline_ratio is None:
        reasons.append("advance_decline_ratio missing")
    return reasons


def _context_status(unavailable: list[str]) -> str:
    if len(unavailable) >= 3:
        return "unavailable"
    if unavailable:
        return "partial"
    return "available"


def _trend_state(index_return: float | None, banknifty_return: float | None, sector_return: float | None) -> str:
    index = index_return if index_return is not None else 0.0
    bank = banknifty_return if banknifty_return is not None else index
    sector = sector_return if sector_return is not None else 0.0
    if index >= 0.35 and bank >= 0.20 and sector >= 0.25:
        return "broad_uptrend"
    if index <= -0.35 and bank <= -0.20 and sector <= -0.25:
        return "distribution_downtrend"
    if sector <= -0.35 and index >= 0.0:
        return "sector_weakness_against_index"
    if index <= -0.35 and sector >= 0.25:
        return "relative_strength_against_weak_index"
    return "mixed_market"


def _breadth_state(advance_decline: float | None, sector_advance_decline: float | None) -> str:
    ratio = advance_decline if advance_decline is not None else 1.0
    sector_ratio = sector_advance_decline if sector_advance_decline is not None else ratio
    if ratio <= 0.70 or sector_ratio <= 0.70:
        return "weak_distribution"
    if ratio >= 1.50 and sector_ratio >= 1.20:
        return "healthy_breadth"
    return "mixed_breadth"


def _relative_strength_score(request: MarketRegimeFeedbackRequest) -> float:
    index = request.index_return_pct if request.index_return_pct is not None else request.stock_return_pct
    sector = request.sector_return_pct if request.sector_return_pct is not None else index
    benchmark = mean([index, sector])
    delta = request.stock_return_pct - benchmark
    return _clamp(0.50 + delta / 4.0, 0.0, 1.0)


def _relative_strength_position(request: MarketRegimeFeedbackRequest) -> float:
    pairs = min(len(request.stock_returns_pct), len(request.index_returns_pct))
    if pairs < 5:
        return _relative_strength_score(request) * 100.0
    rs_line = [request.stock_returns_pct[index] - request.index_returns_pct[index] for index in range(pairs)]
    current = rs_line[-1]
    history = rs_line[:-1]
    if not history:
        return 50.0
    below = sum(1 for item in history if item <= current)
    return _clamp((below / len(history)) * 100.0, 0.0, 100.0)


def _rolling_correlation(stock_returns: list[float], index_returns: list[float]) -> float:
    pairs = min(len(stock_returns), len(index_returns))
    if pairs < 3:
        return 0.0
    stock = stock_returns[-pairs:]
    index = index_returns[-pairs:]
    stock_std = pstdev(stock)
    index_std = pstdev(index)
    if stock_std <= 1e-9 or index_std <= 1e-9:
        return 0.0
    cov = mean([(s - mean(stock)) * (i - mean(index)) for s, i in zip(stock, index)])
    return _clamp(cov / (stock_std * index_std), -1.0, 1.0)


def _leading_lagging_state(rs_score: float, rs_position: float, index_return: float | None, sector_return: float | None) -> str:
    index = index_return if index_return is not None else 0.0
    sector = sector_return if sector_return is not None else 0.0
    if rs_score >= 0.65 and rs_position >= 70.0 and index <= 0.0:
        return "leading_weak_market"
    if rs_score >= 0.65 and rs_position >= 70.0:
        return "leading"
    if rs_score <= 0.35 or rs_position <= 30.0:
        return "lagging"
    if sector < -0.35:
        return "sector_lag_risk"
    return "neutral"


def _bayesian_posterior(request: MarketRegimeFeedbackRequest) -> float:
    observed = request.setup_success_count + request.setup_failure_count
    if observed <= 0:
        return request.prior_confidence
    prior_wins = request.prior_confidence * request.prior_sample_weight
    return _clamp((request.setup_success_count + prior_wins) / (observed + request.prior_sample_weight), 0.0, 1.0)


def _stock_specific_edge(request: MarketRegimeFeedbackRequest) -> float:
    observed = request.setup_success_count + request.setup_failure_count
    setup_edge = 0.0 if observed == 0 else (request.setup_success_count - request.setup_failure_count) / observed
    vwap_edge = 0.0 if request.vwap_sample_count == 0 else (request.vwap_respect_count / request.vwap_sample_count) * 2.0 - 1.0
    breakout_penalty = 0.0 if observed == 0 else min(request.breakout_failure_count / max(observed, 1), 1.0)
    return _clamp((setup_edge * 0.55) + (vwap_edge * 0.35) - (breakout_penalty * 0.45), -1.0, 1.0)


def _recent_failure_penalty(outcomes: list[str]) -> float:
    recent = [item for item in outcomes[-10:] if item in {"WIN", "LOSS", "BREAKEVEN"}]
    if not recent:
        return 0.0
    loss_weight = sum(1.0 for item in recent if item == "LOSS") + sum(0.35 for item in recent if item == "BREAKEVEN")
    return _clamp(loss_weight / len(recent), 0.0, 1.0)


def _recent_loss_streak(outcomes: list[str]) -> int:
    streak = 0
    for item in reversed(outcomes):
        if item == "LOSS":
            streak += 1
        elif item in {"WIN", "BREAKEVEN"}:
            break
    return streak


def _dynamic_confirmation_requirement(
    request: MarketRegimeFeedbackRequest,
    context_status: str,
    trend_state: str,
    breadth_state: str,
    lead_lag: str,
    minimum_pass: bool,
    cooldown: bool,
) -> str:
    requirements: list[str] = []
    if context_status != "available":
        requirements.append("require_verified_index_sector_breadth_context")
    if breadth_state == "weak_distribution":
        requirements.append("require_breadth_recovery_or_no_paper_candidate")
    if trend_state == "sector_weakness_against_index":
        requirements.append("require_sector_confirmation")
    if lead_lag == "lagging":
        requirements.append("require_relative_strength_reclaim")
    if not minimum_pass:
        requirements.append("require_minimum_30_stock_specific_samples")
    if request.vwap_sample_count and request.vwap_respect_count / max(request.vwap_sample_count, 1) < 0.45:
        requirements.append("require_extra_vwap_confirmation")
    if cooldown:
        requirements.append("cooldown_active_require_manual_review")
    return " + ".join(requirements) if requirements else "standard_confirmation"


def _confidence_cap(context_status: str, breadth_state: str, cooldown: bool, minimum_pass: bool) -> str:
    if cooldown or breadth_state == "weak_distribution":
        return "WAIT"
    if context_status != "available" or not minimum_pass:
        return "WATCH"
    return "PAPER_CANDIDATE_ALLOWED"


def _reasons(
    *,
    request: MarketRegimeFeedbackRequest,
    context_status: str,
    trend_state: str,
    breadth_state: str,
    rs_score: float,
    rs_position: float,
    posterior: float,
    failure_penalty: float,
    confidence_cap: str,
) -> list[str]:
    return [
        f"Market context status is {context_status}; missing context caps confidence before paper-candidate promotion.",
        f"Trend state is {trend_state}; breadth state is {breadth_state}.",
        f"Relative strength score is {rs_score:.2f}; RS position is {rs_position:.2f}.",
        f"Bayesian posterior is {posterior:.2f} from {request.setup_success_count + request.setup_failure_count} labeled setup outcomes.",
        f"Recent failure penalty is {failure_penalty:.2f}; confidence cap is {confidence_cap}.",
        "Live update is limited to labels, failure memory, calibration, drift alerts, and analog refresh. Model weights remain fixed.",
    ]


def _gates(
    *,
    request: MarketRegimeFeedbackRequest,
    context_status: str,
    breadth_state: str,
    rs_score: float,
    minimum_pass: bool,
    cooldown: bool,
    confidence_cap: str,
) -> list[MarketRegimeFeedbackGate]:
    return [
        _gate("REG-003", "Index/sector/breadth availability cap", context_status == "available", "warn", f"context={context_status}; cap={confidence_cap}."),
        _gate("REG-004", "Weak breadth blocks paper candidate", breadth_state != "weak_distribution", "block", f"breadth_state={breadth_state}."),
        _gate("REG-005", "Relative strength measured", 0.0 <= rs_score <= 1.0, "info", f"rs_score={rs_score:.2f}."),
        _gate("BAYES-001", "Minimum sample Bayesian shrinkage", minimum_pass, "warn", f"samples={request.setup_sample_count}/{request.minimum_sample_size}."),
        _gate("BAYES-002", "Recent failure cooldown", not cooldown, "block", f"recent_loss_streak={_recent_loss_streak(request.recent_signal_outcomes)}."),
        _gate("BAYES-005", "No live model weight mutation", True, "info", "Only memory/calibration metadata can update live."),
        _gate("V171-SAFE-001", "Research-only safety lock", True, "info", "trade_allowed=false; order_routing_enabled=false; live_trading_blocked=true."),
    ]


def _gate(gate_id: str, name: str, passed: bool, severity: str, evidence: str) -> MarketRegimeFeedbackGate:
    return MarketRegimeFeedbackGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity=severity,  # type: ignore[arg-type]
        evidence=evidence,
        remediation=None if passed else "Keep output capped at WAIT/WATCH until the failed market-regime feedback gate is resolved.",
    )


def _failure_questions(request: MarketRegimeFeedbackRequest, context_status: str) -> list[str]:
    questions = [
        "Is NIFTY, BANKNIFTY, sector, and breadth data from the same decision timestamp?",
        "Is the stock being compared to the correct sector benchmark?",
        "Are recent outcomes labeled with the same entry/SL/target rules as the current setup?",
        "Is per-stock feedback stale after a regime shift or corporate action?",
        "Could low sample count make the Bayesian posterior look more precise than it is?",
    ]
    if context_status != "available":
        questions.append("Market context is incomplete: do not allow PAPER-CANDIDATE from this layer.")
    if request.setup_sample_count < request.minimum_sample_size:
        questions.append("Stock-specific edge is low evidence: shrink confidence toward the prior.")
    return questions


def _clamp(value: float, minimum: float, maximum: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return minimum
    return max(minimum, min(maximum, value))
