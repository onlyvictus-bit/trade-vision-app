from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


JARVIS_PROVIDER_DISAGREEMENT_EXPLORER_VERSION = "jarvis-provider-disagreement-explorer.v1.44"


def build_jarvis_provider_disagreement_explorer(
    *,
    symbol: str,
    evidence_packet: dict[str, Any],
    ai_comparison: dict[str, Any] | None = None,
    evidence_diff: dict[str, Any] | None = None,
    kronos_report: dict[str, Any] | None = None,
    openalgo_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = symbol.upper()
    views = _provider_views(
        evidence_packet=evidence_packet,
        ai_comparison=ai_comparison or {},
        evidence_diff=evidence_diff or {},
        kronos_report=kronos_report or {},
        openalgo_summary=openalgo_summary or {},
    )
    reasons = _disagreement_reasons(views=views, evidence_packet=evidence_packet, evidence_diff=evidence_diff or {}, openalgo_summary=openalgo_summary or {})
    categories = sorted({reason["category"] for reason in reasons})
    severity_rank = {"block": 3, "review": 2, "info": 1}
    highest = max((severity_rank[reason["severity"]] for reason in reasons), default=1)
    explorer_state = "hard_conflict" if highest >= 3 else "needs_review" if highest == 2 else "aligned_or_insufficient"
    gates = [
        _gate("PDR-001", "Trade Vision view exists", bool(views["trade_vision"]["action"]), "block", "Trade Vision action is required as authority."),
        _gate("PDR-002", "No provider action conflict", "action" not in categories, "downgrade", "Provider action disagreement requires WAIT/review."),
        _gate("PDR-003", "No stale evidence conflict", "stale_data" not in categories, "downgrade", "Stale provider evidence must be refreshed."),
        _gate("PDR-004", "No risk or execution conflict", not {"risk", "execution"}.intersection(categories), "block", "Risk/execution conflict blocks paper promotion."),
        _gate("PDR-005", "No invented indicator/evidence conflict", "indicator" not in categories, "downgrade", "Provider cited missing or unverifiable evidence."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    return {
        "explorer_version": JARVIS_PROVIDER_DISAGREEMENT_EXPLORER_VERSION,
        "symbol": normalized,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "explorer_state": "hard_conflict" if blockers else explorer_state,
        "provider_views": views,
        "disagreement_count": len(reasons),
        "categories": categories,
        "reason_cards": reasons,
        "next_verification_steps": _next_steps(reasons),
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message("hard_conflict" if blockers else explorer_state),
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _provider_views(
    *,
    evidence_packet: dict[str, Any],
    ai_comparison: dict[str, Any],
    evidence_diff: dict[str, Any],
    kronos_report: dict[str, Any],
    openalgo_summary: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    tv_decision = evidence_packet.get("trade_vision_decision", {}) if isinstance(evidence_packet.get("trade_vision_decision"), dict) else {}
    tv_action = tv_decision.get("final_trade_decision") or evidence_packet.get("final_action") or "WAIT"
    gemini = ai_comparison.get("gemini", {}) if isinstance(ai_comparison.get("gemini"), dict) else {}
    grok = ai_comparison.get("grok", {}) if isinstance(ai_comparison.get("grok"), dict) else {}
    kronos_action = _kronos_action(kronos_report)
    return {
        "trade_vision": {
            "action": tv_action,
            "confidence": tv_decision.get("confidence_pct") or tv_decision.get("confidence_cap_pct"),
            "reason": tv_decision.get("reason") or tv_decision.get("no_trade_reason") or "Trade Vision authority view.",
            "authority": "primary",
        },
        "gemini": _ai_view("gemini", gemini),
        "grok": _ai_view("grok", grok),
        "kronos": {
            "action": kronos_action,
            "status": kronos_report.get("service_status") or kronos_report.get("status") or kronos_report.get("forecast_status", "unknown"),
            "reason": _kronos_reason(kronos_report),
            "authority": "forecast_prior_only",
        },
        "openalgo": {
            "action": _openalgo_action(openalgo_summary),
            "status": openalgo_summary.get("status", "no_report"),
            "reason": openalgo_summary.get("effect") or "No OpenAlgo report evidence.",
            "authority": "execution_report_only",
        },
        "evidence_diff": {
            "action": evidence_diff.get("diff_state", "unknown"),
            "status": evidence_diff.get("diff_state", "unknown"),
            "reason": evidence_diff.get("operator_message", "No evidence diff available."),
            "authority": "claim_validation_only",
        },
    }


def _ai_view(provider: str, report: dict[str, Any]) -> dict[str, Any]:
    candidate = report.get("candidate_response", {}) if isinstance(report.get("candidate_response"), dict) else {}
    return {
        "action": report.get("safe_final_action") or candidate.get("final_action") or "TRADE_VISION_ONLY",
        "status": report.get("status") or report.get("review_status") or "unknown",
        "display_allowed": bool(report.get("display_allowed")),
        "reason": candidate.get("pattern_interpretation") or f"{provider} evidence unavailable or not displayable.",
        "authority": "external_review_only",
    }


def _kronos_action(report: dict[str, Any]) -> str:
    path = report.get("forecast_path", {}) if isinstance(report.get("forecast_path"), dict) else {}
    direction = str(path.get("trend_direction") or report.get("trend_direction") or "").upper()
    if direction in {"LONG", "UP", "BULLISH"}:
        return "WATCH_LONG"
    if direction in {"SHORT", "DOWN", "BEARISH"}:
        return "WATCH_SHORT"
    if direction in {"SIDEWAYS", "RANGE"}:
        return "WAIT"
    return "UNAVAILABLE"


def _kronos_reason(report: dict[str, Any]) -> str:
    if not report:
        return "Kronos report unavailable."
    path = report.get("forecast_path", {}) if isinstance(report.get("forecast_path"), dict) else {}
    return f"Kronos prior direction={path.get('trend_direction', report.get('trend_direction', 'unknown'))}; research-only forecast."


def _openalgo_action(summary: dict[str, Any]) -> str:
    effect = str(summary.get("effect") or "").lower()
    if effect in {"downgrade_to_wait", "downgrade_execution_confidence"}:
        return "WAIT"
    if summary.get("report_available"):
        return "REVIEW_ONLY"
    return "NO_REPORT"


def _disagreement_reasons(
    *,
    views: dict[str, dict[str, Any]],
    evidence_packet: dict[str, Any],
    evidence_diff: dict[str, Any],
    openalgo_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    tv_action = str(views["trade_vision"]["action"])
    for provider in ("gemini", "grok"):
        view = views[provider]
        action = str(view["action"])
        if action not in {"TRADE_VISION_ONLY", tv_action} and not (tv_action == "NO_TRADE" and action == "NO_TRADE"):
            reasons.append(_reason("action", "review", provider, f"{provider} action {action} differs from Trade Vision {tv_action}.", "Refresh provider response and require human review."))
        if not view.get("display_allowed"):
            reasons.append(_reason("availability", "info", provider, f"{provider} has no displayable response.", "Use Trade Vision-only evidence or refresh provider."))
    kronos_action = views["kronos"]["action"]
    if tv_action in {"BUY", "BUY BREAKOUT", "BUY RETEST"} and kronos_action == "WATCH_SHORT":
        reasons.append(_reason("action", "review", "kronos", "Kronos forecast prior leans short while Trade Vision leans long.", "Replay similar days and inspect target-before-stop path."))
    if tv_action in {"SELL", "SELL BREAKDOWN", "SELL RETEST"} and kronos_action == "WATCH_LONG":
        reasons.append(_reason("action", "review", "kronos", "Kronos forecast prior leans long while Trade Vision leans short.", "Replay similar days and inspect target-before-stop path."))
    if evidence_diff.get("record_hash_matches_current") is False:
        reasons.append(_reason("stale_data", "review", "external_ai", "Latest accepted external AI response is tied to older evidence.", "Generate a new v1.40 refresh packet and re-intake the response."))
    if int(evidence_diff.get("missing_count") or 0) > 0:
        reasons.append(_reason("indicator", "review", "external_ai", "External AI cited missing or unverifiable evidence.", "Open the evidence diff and remove unsupported claims."))
    if evidence_diff.get("action_diff", {}).get("status") == "conflict":
        reasons.append(_reason("risk", "block", "external_ai", "External AI final action conflicts with Trade Vision safety.", "Ignore provider response and keep WAIT/NO_TRADE."))
    safety = evidence_packet.get("safety_summary", {}) if isinstance(evidence_packet.get("safety_summary"), dict) else {}
    if safety.get("blocking_gates"):
        reasons.append(_reason("risk", "block", "trade_vision", "Trade Vision safety gates are blocking.", "Resolve safety gates before any paper/export review."))
    if openalgo_summary.get("effect") in {"downgrade_to_wait", "downgrade_execution_confidence"}:
        reasons.append(_reason("execution", "block", "openalgo", f"OpenAlgo report effect is {openalgo_summary.get('effect')}.", "Inspect fill quality, slippage, rejection reason, and reconciliation before paper promotion."))
    if not reasons:
        reasons.append(_reason("availability", "info", "jarvis", "No hard disagreement found; evidence may still be insufficient for trading.", "Continue paper/replay validation; do not grant live authority."))
    return reasons


def _reason(category: str, severity: str, source: str, description: str, next_step: str) -> dict[str, Any]:
    return {
        "category": category,
        "severity": severity,
        "source": source,
        "description": description,
        "next_verification_step": next_step,
    }


def _next_steps(reasons: list[dict[str, Any]]) -> list[str]:
    steps: list[str] = []
    for reason in reasons:
        step = reason["next_verification_step"]
        if step not in steps:
            steps.append(step)
    return steps


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(state: str) -> str:
    if state == "hard_conflict":
        return "Provider disagreement includes risk/execution conflict; Jarvis forces review and no routing."
    if state == "needs_review":
        return "Provider disagreement is explainable but must be reviewed before any paper handoff."
    return "No hard provider disagreement found, but Jarvis remains research-only."
