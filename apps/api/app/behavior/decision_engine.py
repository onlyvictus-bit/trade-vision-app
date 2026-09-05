from __future__ import annotations

from .constants import LOW_EVIDENCE_MESSAGE, UNIVERSAL_AGREEMENT_RULE
from ..models import (
    BehaviorDecisionGate,
    BehaviorDecisionRequest,
    NoTradeDecisionRecord,
    ReasonTreeResult,
    TradeDecisionResult,
)


DECISION_ENGINE_VERSION = "behavior-decision-engine.v0.20"


def evaluate_trade_decision(request: BehaviorDecisionRequest) -> TradeDecisionResult:
    """Apply the universal-agreement rule and convert diagnostics into a safe decision."""

    gates = _decision_gates(request)
    blocking = [gate for gate in gates if not gate.passed and gate.severity == "block"]
    warnings = [gate for gate in gates if not gate.passed and gate.severity == "warning"]
    agreement_checks = {
        "signal_strength": request.rule_signal not in {"NO_TRADE", "WATCH_ONLY", "AVOID_CHOP", "FAKEOUT_WARNING"},
        "candle_structure": request.similar_history_fakeout_pct < 45.0,
        "level_context": _direction_matches_context(request),
        "session_rhythm": request.session_trade_quality_score >= 0.55 and not request.session_blocks_trade,
        "similar_history_outcome": request.pattern_minimum_sample_pass and request.similar_history_continuation_pct > request.similar_history_fakeout_pct,
        "market_regime": request.market_regime_favorable,
        "risk_quality": request.risk_reward >= 1.5 and request.liquidity_score >= 0.5,
    }
    universal_pass = all(agreement_checks.values()) and not blocking
    trade_allowed = universal_pass and request.trust_minimum_sample_pass and request.trust_score >= 0.55
    final_decision = _final_decision(request, trade_allowed, blocking, warnings)
    confidence = _confidence_pct(request, agreement_checks, blocking)
    reason_tree = _reason_tree(request, agreement_checks, gates, final_decision, confidence)
    no_trade = NoTradeDecisionRecord(
        symbol=request.symbol.upper(),
        active=not trade_allowed,
        no_trade_reason=None if trade_allowed else _no_trade_reason(request, blocking, warnings, agreement_checks),
        blocking_gates=[gate.gate for gate in blocking],
        wait_for=_wait_for(request, agreement_checks, blocking),
    )
    return TradeDecisionResult(
        decision_version=DECISION_ENGINE_VERSION,
        symbol=request.symbol.upper(),
        final_trade_decision=final_decision,
        trade_allowed=trade_allowed,
        universal_agreement_pass=universal_pass,
        confidence_pct=confidence,
        agreement_checks=agreement_checks,
        gates=gates,
        no_trade=no_trade,
        reason_tree=reason_tree,
        output_updates={
            "final_trade_decision": final_decision,
            "trade_allowed": trade_allowed,
            "no_trade_reason": no_trade.no_trade_reason,
            "reason": reason_tree.ordered_reasons[0] if reason_tree.ordered_reasons else "",
            "rule_confidence_pct": confidence,
            "memory_confidence_pct": round(request.trust_score * 100.0, 2),
            "minimum_sample_pass": request.pattern_minimum_sample_pass and request.trust_minimum_sample_pass,
            "evidence_quality": "MEDIUM" if request.pattern_minimum_sample_pass else "LOW",
        },
        narrative_explanation=_narrative(request, final_decision, no_trade.no_trade_reason, confidence),
        live_trade_route_attempted=False,
    )


def _decision_gates(request: BehaviorDecisionRequest) -> list[BehaviorDecisionGate]:
    return [
        _gate("KILL_SWITCH", not request.kill_switch_active, "block", "Kill switch armed." if not request.kill_switch_active else "Kill switch is active; all trading-like paths are blocked."),
        _gate("DATA_QUALITY", request.data_quality_score >= 0.95, "block", f"Data quality {request.data_quality_score:.2f} is acceptable." if request.data_quality_score >= 0.95 else "Data quality is below 0.95."),
        _gate("LIQUIDITY", request.liquidity_score >= 0.5, "block", f"Liquidity score {request.liquidity_score:.2f} is acceptable." if request.liquidity_score >= 0.5 else "Liquidity is too weak for safe entry or exit."),
        _gate("CONTEXT", not request.context_blocks_trade and request.context_bias != "avoid", "block", f"Context bias is {request.context_bias}." if not request.context_blocks_trade and request.context_bias != "avoid" else "Context engine blocks or advises avoid."),
        _gate("SESSION", not request.session_blocks_trade, "block", "Session rhythm allows monitoring." if not request.session_blocks_trade else "Session rhythm blocks this setup."),
        _gate("DAILY_LOSS_LIMIT", not request.daily_loss_limit_hit, "block", "Daily loss limit is clear." if not request.daily_loss_limit_hit else "Daily loss limit has been hit."),
        _gate("COOLDOWN", not request.cooldown_active, "block", "Cooldown is clear." if not request.cooldown_active else "Cooldown is active after losses or chop."),
        _gate("OOD", request.ood_score <= 0.7, "block", f"OOD score {request.ood_score:.2f} is below threshold." if request.ood_score <= 0.7 else "Out-of-distribution score is above threshold."),
        _gate("DRIFT", request.drift_score <= 0.7, "block", f"Drift score {request.drift_score:.2f} is below threshold." if request.drift_score <= 0.7 else "Model drift score is above threshold."),
        _gate("MINIMUM_PATTERN_EVIDENCE", request.pattern_minimum_sample_pass, "warning", "Pattern memory sample count is sufficient." if request.pattern_minimum_sample_pass else LOW_EVIDENCE_MESSAGE),
        _gate("TRUST_TABLE_EVIDENCE", request.trust_minimum_sample_pass, "warning", "Learning trust table sample count is sufficient." if request.trust_minimum_sample_pass else "Learning trust table has not reached minimum sample count."),
        _gate("TRAP_PROBABILITY", request.similar_history_fakeout_pct < 55.0, "warning", f"Fakeout probability {request.similar_history_fakeout_pct:.2f}% is below warning threshold." if request.similar_history_fakeout_pct < 55.0 else "Similar history shows elevated fakeout probability."),
        _gate("FAILURE_MEMORY", request.failure_warning is None, "warning", request.failure_warning or "No active failure warning."),
    ]


def _gate(gate: str, passed: bool, severity: str, reason: str) -> BehaviorDecisionGate:
    return BehaviorDecisionGate(gate=gate, passed=passed, severity=severity, reason=reason)  # type: ignore[arg-type]


def _direction_matches_context(request: BehaviorDecisionRequest) -> bool:
    if request.direction == "long":
        return request.context_bias == "supports_long"
    if request.direction == "short":
        return request.context_bias == "supports_short"
    return False


def _final_decision(
    request: BehaviorDecisionRequest,
    trade_allowed: bool,
    blocking: list[BehaviorDecisionGate],
    warnings: list[BehaviorDecisionGate],
) -> str:
    if blocking:
        return "NO_TRADE"
    if request.similar_history_fakeout_pct >= 55.0 or request.failure_warning:
        return "FAKEOUT_WARNING"
    if warnings or not trade_allowed:
        return "WATCH_ONLY"
    return request.rule_signal


def _confidence_pct(
    request: BehaviorDecisionRequest,
    agreement_checks: dict[str, bool],
    blocking: list[BehaviorDecisionGate],
) -> float:
    agreement_score = sum(1 for passed in agreement_checks.values() if passed) / max(len(agreement_checks), 1)
    raw = (
        agreement_score * 0.40
        + request.trust_score * 0.25
        + min(request.similar_history_continuation_pct / 100.0, 1.0) * 0.15
        + request.data_quality_score * 0.10
        + request.liquidity_score * 0.10
    )
    penalty = 0.35 if blocking else 0.0
    penalty += min(request.similar_history_fakeout_pct / 100.0, 1.0) * 0.20
    return round(max(0.0, min((raw - penalty) * 100.0, 100.0)), 2)


def _reason_tree(
    request: BehaviorDecisionRequest,
    agreement_checks: dict[str, bool],
    gates: list[BehaviorDecisionGate],
    final_decision: str,
    confidence: float,
) -> ReasonTreeResult:
    failed_agreement = [name for name, passed in agreement_checks.items() if not passed]
    failed_gates = [gate.gate for gate in gates if not gate.passed]
    nodes = {
        "universal_agreement_rule": UNIVERSAL_AGREEMENT_RULE,
        "final_decision": f"{final_decision} with {confidence}% confidence.",
        "agreement": "All agreement checks passed." if not failed_agreement else f"Failed agreement checks: {', '.join(failed_agreement)}.",
        "safety_gates": "All safety gates passed." if not failed_gates else f"Open gates: {', '.join(failed_gates)}.",
        "memory": f"Continuation {request.similar_history_continuation_pct}%, fakeout {request.similar_history_fakeout_pct}%, trust {round(request.trust_score * 100, 2)}%.",
        "failure_memory": request.failure_warning or "No active failure warning.",
        "execution": "No live route was attempted; output is mock/replay decision support only.",
    }
    ordered = [
        nodes["final_decision"],
        nodes["agreement"],
        nodes["safety_gates"],
        nodes["memory"],
        nodes["execution"],
    ]
    return ReasonTreeResult(
        reason_version=DECISION_ENGINE_VERSION,
        symbol=request.symbol.upper(),
        nodes=nodes,
        ordered_reasons=ordered,
    )


def _no_trade_reason(
    request: BehaviorDecisionRequest,
    blocking: list[BehaviorDecisionGate],
    warnings: list[BehaviorDecisionGate],
    agreement_checks: dict[str, bool],
) -> str:
    if blocking:
        return blocking[0].reason
    if not request.pattern_minimum_sample_pass:
        return LOW_EVIDENCE_MESSAGE
    if request.similar_history_fakeout_pct >= 55.0:
        return "Similar history shows fakeout risk is too high; wait for retest confirmation."
    if request.failure_warning:
        return request.failure_warning
    failed = [name for name, passed in agreement_checks.items() if not passed]
    if failed:
        return f"Universal agreement failed: {', '.join(failed)}."
    if warnings:
        return warnings[0].reason
    return "Decision remains watch-only until all safety and evidence gates pass."


def _wait_for(
    request: BehaviorDecisionRequest,
    agreement_checks: dict[str, bool],
    blocking: list[BehaviorDecisionGate],
) -> list[str]:
    waits: list[str] = []
    if blocking:
        waits.append("Resolve blocking safety gate before any trade-like action.")
    if not request.pattern_minimum_sample_pass or not request.trust_minimum_sample_pass:
        waits.append("Collect at least 30 comparable labeled outcomes before trusting probability.")
    if request.similar_history_fakeout_pct >= 55.0:
        waits.append("Wait for VWAP reclaim, retest success, or fakeout risk reduction.")
    if not agreement_checks.get("level_context", False):
        waits.append("Wait for higher-timeframe and level context to align with direction.")
    if request.risk_reward < 1.5:
        waits.append("Wait for a better invalidation level or wider reward window.")
    return waits or ["Maintain monitoring; no additional wait condition."]


def _narrative(request: BehaviorDecisionRequest, final_decision: str, no_trade_reason: str | None, confidence: float) -> str:
    if final_decision in {"NO_TRADE", "WATCH_ONLY", "FAKEOUT_WARNING"}:
        return (
            f"{final_decision}. {no_trade_reason or 'Conditions do not have universal agreement.'} "
            f"Confidence is {confidence}%. Narrative is read-only and cannot execute or override risk."
        )
    return (
        f"{final_decision} candidate only after all gates pass. Confidence is {confidence}%. "
        "Narrative is read-only and cannot execute or override risk."
    )
