from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_PAPER_READY_SAFETY_AUDIT_VERSION = "jarvis-paper-ready-safety-audit.v1.47"


def build_jarvis_paper_ready_safety_audit(
    *,
    symbol: str,
    jarvis_room: dict[str, Any],
    realtime_freshness: dict[str, Any],
    decision_quality: dict[str, Any],
    verified_review_packet: dict[str, Any],
    provider_disagreement: dict[str, Any],
    openalgo_safe_binding: dict[str, Any],
    final_production_audit: dict[str, Any],
) -> dict[str, Any]:
    normalized = symbol.upper()
    gates = [
        _gate("PAPER-AUDIT-001", "Jarvis decision room exists and is non-routing", _non_routing(jarvis_room), "block", "Jarvis decision room must be research-only."),
        _gate("PAPER-AUDIT-002", "Realtime freshness forces safe display", realtime_freshness.get("safe_display_action") in {"WAIT", "RESEARCH_ONLY"}, "block", "Stale or slow evidence must force WAIT/research-only."),
        _gate("PAPER-AUDIT-003", "Decision quality is non-executable", _non_routing(decision_quality), "block", "Decision quality cannot route orders or allow live trading."),
        _gate("PAPER-AUDIT-004", "Gemini/Grok verified packet is secret-clean", verified_review_packet.get("blocking_count") == 0 and verified_review_packet.get("secret_scan", {}).get("secret_like_value_detected") is False, "block", "Provider packets must be secret-clean and review-only."),
        _gate("PAPER-AUDIT-005", "Provider disagreement has no hard block", provider_disagreement.get("explorer_state") != "hard_conflict" and provider_disagreement.get("blocking_count") == 0, "block", "Hard disagreement blocks paper review."),
        _gate("PAPER-AUDIT-006", "OpenAlgo binding is inspect-only", _binding_inspect_only(openalgo_safe_binding), "block", "OpenAlgo binding must remain inspect-only and non-executable."),
        _gate("PAPER-AUDIT-007", "Legacy final audit keeps live blocked", final_production_audit.get("live_ready") is False and final_production_audit.get("live_trading_blocked") is True, "block", "Legacy final audit must keep live trading blocked."),
        _gate("PAPER-AUDIT-008", "All artifacts block live trading", _live_blocked(jarvis_room, realtime_freshness, decision_quality, verified_review_packet, provider_disagreement, openalgo_safe_binding, final_production_audit), "block", "Every artifact must declare live_trading_blocked=true when present."),
        _gate("PAPER-AUDIT-009", "No artifact can execute orders", _cannot_execute(jarvis_room, decision_quality, verified_review_packet, provider_disagreement, openalgo_safe_binding, final_production_audit), "block", "No current Trade Vision artifact may execute orders."),
        _gate("PAPER-AUDIT-010", "Paper review still requires external approvals", _external_approvals_required(openalgo_safe_binding), "downgrade", "Human, risk, and account-state checks must happen outside Trade Vision before any executor action."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    paper_ready = not blockers and openalgo_safe_binding.get("openalgo_may_inspect") is True
    if blockers:
        final_state = "blocked"
    elif paper_ready:
        final_state = "paper_review_ready_live_blocked"
    else:
        final_state = "research_ready_live_blocked"
    payload = {
        "version": JARVIS_PAPER_READY_SAFETY_AUDIT_VERSION,
        "symbol": normalized,
        "final_state": final_state,
        "gates": gates,
        "binding_hash": openalgo_safe_binding.get("binding_hash"),
        "verified_packet_hash": verified_review_packet.get("copy_safe_export_hash"),
        "decision_quality_hash": decision_quality.get("quality_hash"),
    }
    return {
        "paper_ready_audit_version": JARVIS_PAPER_READY_SAFETY_AUDIT_VERSION,
        "symbol": normalized,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_state": final_state,
        "audit_hash": _hash(payload),
        "paper_review_ready": paper_ready,
        "research_ready": not blockers,
        "live_ready": False,
        "broker_connection_ready": False,
        "autonomous_execution_ready": False,
        "go_no_go": {
            "research_dashboard": "GO" if not blockers else "NO_GO",
            "openalgo_paper_inspection": "GO" if paper_ready else "NO_GO",
            "live_broker_trading": "NO_GO",
            "autonomous_trading_bot": "NO_GO",
        },
        "artifact_summary": {
            "jarvis_final_action": jarvis_room.get("final_action"),
            "freshness_state": realtime_freshness.get("freshness_state"),
            "decision_quality_state": decision_quality.get("quality_state"),
            "verified_packet_state": verified_review_packet.get("packet_state"),
            "provider_disagreement_state": provider_disagreement.get("explorer_state"),
            "openalgo_binding_state": openalgo_safe_binding.get("preview_state"),
            "legacy_final_state": final_production_audit.get("overall_state"),
        },
        "binding_evidence": {
            "openalgo_binding_hash": openalgo_safe_binding.get("binding_hash"),
            "verified_review_packet_hash": verified_review_packet.get("copy_safe_export_hash"),
            "legacy_audit_state": final_production_audit.get("overall_state"),
        },
        "remaining_before_live": [
            "Separate broker adapter architecture review",
            "Signed human approval workflow outside Trade Vision",
            "External risk-manager approval",
            "External account-state and position reconciliation",
            "Paper fill/slippage/rejection validation against OpenAlgo",
            "Kill-switch and broker-disconnect proof in executor environment",
            "Exchange reconciliation and orphan-position recovery proof",
            "Production secrets management and audit logging proof",
        ],
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message(final_state),
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _non_routing(report: dict[str, Any]) -> bool:
    return (
        report.get("trade_allowed") is False
        and report.get("order_routing_enabled") is False
        and report.get("live_trading_blocked") is True
    )


def _binding_inspect_only(report: dict[str, Any]) -> bool:
    return (
        report.get("openalgo_may_inspect") is True
        and report.get("openalgo_may_execute") is False
        and report.get("trading_bot_may_execute") is False
        and report.get("trade_allowed") is False
        and report.get("order_routing_enabled") is False
        and report.get("live_trading_blocked") is True
    )


def _live_blocked(*reports: dict[str, Any]) -> bool:
    return all(report.get("live_trading_blocked") is True for report in reports if "live_trading_blocked" in report)


def _cannot_execute(*reports: dict[str, Any]) -> bool:
    for report in reports:
        if report.get("can_execute_orders") is True:
            return False
        if report.get("openalgo_may_execute") is True:
            return False
        if report.get("trading_bot_may_execute") is True:
            return False
        if report.get("order_routing_enabled") is True:
            return False
    return True


def _external_approvals_required(report: dict[str, Any]) -> bool:
    return (
        report.get("external_human_approval_required") is True
        and report.get("external_risk_check_required") is True
        and report.get("external_account_state_required") is True
    )


def _hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(state: str) -> str:
    if state == "paper_review_ready_live_blocked":
        return "Jarvis is paper-review ready for external OpenAlgo inspection only. Live trading remains blocked."
    if state == "research_ready_live_blocked":
        return "Jarvis is research-ready, but OpenAlgo paper inspection is not fully ready. Live trading remains blocked."
    return "Jarvis paper-ready audit is blocked. Keep the system in research-only mode."
