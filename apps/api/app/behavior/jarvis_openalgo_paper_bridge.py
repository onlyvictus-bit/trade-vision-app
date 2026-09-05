from __future__ import annotations

from typing import Any


OPENALGO_PAPER_BRIDGE_VERSION = "jarvis-openalgo-paper-bridge-hardening.v1.31"


def build_openalgo_paper_bridge_report(
    *,
    symbol: str,
    handoff_gate: dict[str, Any],
    decision_quality: dict[str, Any],
    realtime_freshness: dict[str, Any],
    gemini_decision_room: dict[str, Any],
) -> dict[str, Any]:
    intent = handoff_gate.get("intent_summary", {})
    package = handoff_gate.get("package_summary", {})
    verification = handoff_gate.get("package_verification", {})
    transport = handoff_gate.get("transport_summary", {})
    bot = handoff_gate.get("bot_handoff_verification", {})
    gates = [
        _gate("OA-BRIDGE-001", "Dry-run package exists and verifies", package.get("dry_run_only") is True and verification.get("verified") is True, "block", "OpenAlgo bridge can inspect only verified dry-run package artifacts."),
        _gate("OA-BRIDGE-002", "Intent is preview-only", _preview_only(intent), "block", "Intent must have export/routing/broker order disabled."),
        _gate("OA-BRIDGE-003", "External executor must still reject without approvals", bot.get("rejected") is True, "block", "Missing external human approval, risk check, or account state must keep package non-actionable."),
        _gate("OA-BRIDGE-004", "Realtime freshness does not promote action", realtime_freshness.get("safe_display_action") in {"WAIT", "RESEARCH_ONLY"}, "downgrade", "Freshness may allow display but never execution promotion."),
        _gate("OA-BRIDGE-005", "Decision quality requires manual review or blocks routing", decision_quality.get("order_routing_enabled") is False and decision_quality.get("live_trading_blocked") is True, "block", "Decision quality gate must keep routing disabled."),
        _gate("OA-BRIDGE-006", "Gemini cannot promote OpenAlgo handoff", gemini_decision_room.get("confidence_boost_allowed") is False and gemini_decision_room.get("order_routing_enabled") is False, "block", "External AI review cannot turn a paper intent into an executable order."),
        _gate("OA-BRIDGE-007", "Transport is review-only", transport.get("order_routing_enabled") is False and transport.get("live_trading_blocked") is True, "block", "Transport cannot carry broker credentials or live routing."),
        _gate("OA-BRIDGE-008", "Live trading is explicitly blocked everywhere", _live_blocked(package, intent, transport, handoff_gate), "block", "Every bridge artifact must declare live_trading_blocked=true."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    bridge_state = "blocked" if blockers else "paper_review_ready" if not warnings else "paper_review_warning"
    return {
        "bridge_version": OPENALGO_PAPER_BRIDGE_VERSION,
        "symbol": symbol.upper(),
        "bridge_state": bridge_state,
        "safe_external_scope": "paper_or_sim_review_only",
        "openalgo_may_inspect": not blockers,
        "openalgo_may_execute": False,
        "trading_bot_may_execute": False,
        "paper_intent_allowed": not blockers,
        "live_intent_allowed": False,
        "intent_signature": intent.get("intent_signature"),
        "intent_duplicate_key": intent.get("duplicate_key"),
        "intent_valid_until": intent.get("valid_until"),
        "intent_expired": intent.get("expired"),
        "package_hash": package.get("package_hash"),
        "handoff_hash": handoff_gate.get("handoff_hash"),
        "transport_circuit_state": transport.get("circuit_state"),
        "external_approval_required": True,
        "external_risk_check_required": True,
        "external_account_state_required": True,
        "manual_operator_review_required": True,
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "required_external_executor_checks": [
            "verify package hash and manifest hash",
            "verify intent signature and duplicate key",
            "reject expired intent",
            "reject missing human approval",
            "reject missing external risk check",
            "reject missing external account-state check",
            "reject any broker credentials in payload",
            "reject any live/order-routing flag",
        ],
        "operator_message": _operator_message(blockers, warnings),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _preview_only(intent: dict[str, Any]) -> bool:
    return all(
        [
            intent.get("export_allowed") is False,
            intent.get("broker_order_created") is False,
            intent.get("order_routing_enabled") is False,
            intent.get("live_trading_blocked") is True,
        ]
    )


def _live_blocked(*reports: dict[str, Any]) -> bool:
    for report in reports:
        if "live_trading_blocked" in report and report.get("live_trading_blocked") is not True:
            return False
    return True


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
    if blockers:
        return "OpenAlgo paper bridge is blocked. Keep the intent as local research evidence only."
    if warnings:
        return "OpenAlgo paper bridge is structurally safe but must remain operator-reviewed paper/sim only."
    return "OpenAlgo paper bridge is ready for external adapter inspection only; live execution remains impossible."
