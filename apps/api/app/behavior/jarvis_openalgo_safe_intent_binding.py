from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_OPENALGO_SAFE_INTENT_BINDING_VERSION = "jarvis-openalgo-safe-intent-binding.v1.46"


def build_openalgo_safe_intent_binding(
    *,
    symbol: str,
    jarvis_room: dict[str, Any],
    verified_review_packet: dict[str, Any],
    disagreement_explorer: dict[str, Any],
    openalgo_handoff_gate: dict[str, Any],
    openalgo_paper_bridge: dict[str, Any],
) -> dict[str, Any]:
    normalized = symbol.upper()
    intent_summary = openalgo_handoff_gate.get("intent_summary", {}) if isinstance(openalgo_handoff_gate.get("intent_summary"), dict) else {}
    package_summary = openalgo_handoff_gate.get("package_summary", {}) if isinstance(openalgo_handoff_gate.get("package_summary"), dict) else {}
    binding_payload = {
        "version": JARVIS_OPENALGO_SAFE_INTENT_BINDING_VERSION,
        "symbol": normalized,
        "jarvis": {
            "final_action": jarvis_room.get("final_action"),
            "decision": jarvis_room.get("trade_vision_decision", {}).get("final_trade_decision"),
            "safety_gates": jarvis_room.get("safety_summary", {}).get("blocking_gates", []),
        },
        "verified_packet_hash": verified_review_packet.get("copy_safe_export_hash"),
        "disagreement_state": disagreement_explorer.get("explorer_state"),
        "handoff_hash": openalgo_handoff_gate.get("handoff_hash"),
        "package_hash": package_summary.get("package_hash"),
        "paper_bridge_state": openalgo_paper_bridge.get("bridge_state"),
        "intent_signature": intent_summary.get("intent_signature"),
        "intent_duplicate_key": intent_summary.get("duplicate_key"),
        "intent_valid_until": intent_summary.get("valid_until"),
    }
    binding_hash = _hash(binding_payload)
    gates = [
        _gate("OASIB-001", "Jarvis room is present", bool(jarvis_room.get("symbol")), "block", "Jarvis decision evidence is required."),
        _gate("OASIB-002", "Verified provider packet is safe", verified_review_packet.get("blocking_count") == 0 and verified_review_packet.get("trade_allowed") is False, "block", "Provider packet must be review-only and secret-clean."),
        _gate("OASIB-003", "Provider disagreement has no hard block", disagreement_explorer.get("explorer_state") != "hard_conflict" and disagreement_explorer.get("blocking_count") == 0, "block", "Hard provider disagreement blocks OpenAlgo preview binding."),
        _gate("OASIB-004", "OpenAlgo handoff gate is dry-run safe", _handoff_safe(openalgo_handoff_gate), "block", "OpenAlgo handoff must remain a verified dry-run preview."),
        _gate("OASIB-005", "OpenAlgo paper bridge is inspectable", openalgo_paper_bridge.get("openalgo_may_inspect") is True and openalgo_paper_bridge.get("openalgo_may_execute") is False, "downgrade", "OpenAlgo may inspect only when bridge gates allow paper/sim review."),
        _gate("OASIB-006", "Intent remains preview-only", _intent_preview_only(intent_summary), "block", "Intent must not enable export, routing, broker credentials, or live trading."),
        _gate("OASIB-007", "Live trading remains blocked everywhere", _live_blocked(verified_review_packet, openalgo_handoff_gate, openalgo_paper_bridge), "block", "All bound artifacts must declare live trading blocked."),
        _gate("OASIB-008", "Binding hash is present", bool(binding_hash), "block", "Binding hash is required for replay/audit."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    preview_state = "blocked" if blockers else "paper_review_preview_ready" if not warnings else "paper_review_preview_warning"
    return {
        "binding_version": JARVIS_OPENALGO_SAFE_INTENT_BINDING_VERSION,
        "symbol": normalized,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preview_state": preview_state,
        "binding_hash": binding_hash,
        "binding_payload": binding_payload,
        "jarvis_summary": binding_payload["jarvis"],
        "verified_packet_summary": {
            "packet_state": verified_review_packet.get("packet_state"),
            "copy_safe_export_hash": verified_review_packet.get("copy_safe_export_hash"),
            "secret_clean": not verified_review_packet.get("secret_scan", {}).get("secret_like_value_detected", False),
            "blocking_count": verified_review_packet.get("blocking_count"),
        },
        "disagreement_summary": {
            "explorer_state": disagreement_explorer.get("explorer_state"),
            "categories": disagreement_explorer.get("categories", []),
            "blocking_count": disagreement_explorer.get("blocking_count"),
            "warning_count": disagreement_explorer.get("warning_count"),
        },
        "openalgo_summary": {
            "handoff_state": openalgo_handoff_gate.get("handoff_state"),
            "handoff_hash": openalgo_handoff_gate.get("handoff_hash"),
            "dry_run_handoff_allowed": openalgo_handoff_gate.get("dry_run_handoff_allowed"),
            "bridge_state": openalgo_paper_bridge.get("bridge_state"),
            "paper_intent_allowed": openalgo_paper_bridge.get("paper_intent_allowed"),
            "live_intent_allowed": openalgo_paper_bridge.get("live_intent_allowed"),
        },
        "intent_preview": {
            "intent_id": intent_summary.get("intent_id"),
            "intent_signature": intent_summary.get("intent_signature"),
            "side": intent_summary.get("side"),
            "mode_permission": intent_summary.get("mode_permission"),
            "valid_until": intent_summary.get("valid_until"),
            "expired": intent_summary.get("expired"),
            "duplicate_key": intent_summary.get("duplicate_key"),
            "export_allowed": False,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message(preview_state),
        "openalgo_may_inspect": not blockers and openalgo_paper_bridge.get("openalgo_may_inspect") is True,
        "openalgo_may_execute": False,
        "trading_bot_may_execute": False,
        "external_human_approval_required": True,
        "external_risk_check_required": True,
        "external_account_state_required": True,
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _handoff_safe(report: dict[str, Any]) -> bool:
    package = report.get("package_summary", {}) if isinstance(report.get("package_summary"), dict) else {}
    return (
        package.get("dry_run_only") is True
        and package.get("broker_credentials_present") is False
        and package.get("broker_order_created") is False
        and package.get("trade_allowed") is False
        and package.get("order_routing_enabled") is False
        and package.get("live_trading_blocked") is True
        and report.get("trade_allowed") is False
        and report.get("order_routing_enabled") is False
    )


def _intent_preview_only(intent: dict[str, Any]) -> bool:
    return (
        intent.get("export_allowed") is False
        and intent.get("broker_order_created") is False
        and intent.get("order_routing_enabled") is False
        and intent.get("live_trading_blocked") is True
    )


def _live_blocked(*reports: dict[str, Any]) -> bool:
    return all(report.get("live_trading_blocked") is True for report in reports)


def _hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(state: str) -> str:
    if state == "paper_review_preview_ready":
        return "OpenAlgo-safe intent preview is bound for external paper/sim inspection only; no execution authority is granted."
    if state == "paper_review_preview_warning":
        return "OpenAlgo-safe intent preview is structurally safe but still requires manual warning review."
    return "OpenAlgo-safe intent preview is blocked; do not send this package to an executor."
