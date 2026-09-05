from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


OPENALGO_HANDOFF_GATE_VERSION = "jarvis-openalgo-handoff-gate.v1.20"


def build_openalgo_handoff_gate_report(
    *,
    symbol: str,
    jarvis_room: dict[str, Any],
    dry_run_package: Any,
    package_verification: Any,
    transport_status: Any,
    adapter_harness: dict[str, Any],
) -> dict[str, Any]:
    package = _as_dict(dry_run_package)
    verification = _as_dict(package_verification)
    transport = _as_dict(transport_status)
    adapter = _as_dict(adapter_harness)
    intent = package.get("intent", {}) if isinstance(package.get("intent"), dict) else {}
    bot_verification = package.get("verification", {}) if isinstance(package.get("verification"), dict) else {}
    gates = _gates(package, verification, transport, adapter, intent, bot_verification)
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    handoff_allowed = not blockers and not warnings and bool(adapter.get("readiness", {}).get("dry_run_handoff_ready"))
    payload = {
        "version": OPENALGO_HANDOFF_GATE_VERSION,
        "symbol": symbol.upper(),
        "package_hash": package.get("package_hash"),
        "verification_hash": verification.get("verification_hash"),
        "transport": {
            "configured": transport.get("configured"),
            "health_ok": transport.get("health_ok"),
            "service_auth_configured": transport.get("service_auth_configured"),
            "circuit_state": transport.get("circuit_state"),
        },
        "gates": gates,
    }
    return {
        "handoff_gate_version": OPENALGO_HANDOFF_GATE_VERSION,
        "symbol": symbol.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "handoff_state": "dry_run_review_ready" if handoff_allowed else "blocked_manual_review" if blockers else "warning_manual_review",
        "handoff_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "intent_summary": {
            "intent_id": intent.get("intent_id"),
            "intent_signature": intent.get("intent_signature"),
            "side": intent.get("side"),
            "mode_permission": intent.get("mode_permission"),
            "valid_until": intent.get("valid_until"),
            "expired": intent.get("expired"),
            "duplicate_key": intent.get("duplicate_key"),
            "export_allowed": intent.get("export_allowed"),
            "broker_order_created": intent.get("broker_order_created"),
            "order_routing_enabled": intent.get("order_routing_enabled"),
            "live_trading_blocked": intent.get("live_trading_blocked"),
        },
        "package_summary": {
            "package_version": package.get("package_version"),
            "package_id": package.get("package_id"),
            "package_hash": package.get("package_hash"),
            "dry_run_only": package.get("dry_run_only"),
            "broker_credentials_present": package.get("broker_credentials_present"),
            "broker_order_created": package.get("broker_order_created"),
            "trade_allowed": package.get("trade_allowed"),
            "order_routing_enabled": package.get("order_routing_enabled"),
            "live_trading_blocked": package.get("live_trading_blocked"),
            "artifact_dir": package.get("artifact_dir"),
        },
        "package_verification": {
            "verification_version": verification.get("verification_version"),
            "verified": verification.get("verified"),
            "package_sha256_matches": verification.get("package_sha256_matches"),
            "manifest_sha256_matches": verification.get("manifest_sha256_matches"),
            "issues": verification.get("issues", []),
        },
        "bot_handoff_verification": {
            "verifier_version": bot_verification.get("verifier_version"),
            "accepted": bot_verification.get("accepted"),
            "rejected": bot_verification.get("rejected"),
            "rejection_reasons": bot_verification.get("rejection_reasons", []),
            "external_human_approval_present": bot_verification.get("external_human_approval_present"),
            "external_risk_check_passed": bot_verification.get("external_risk_check_passed"),
            "external_account_state_checked": bot_verification.get("external_account_state_checked"),
        },
        "transport_summary": {
            "status_version": transport.get("status_version"),
            "configured": transport.get("configured"),
            "health_ok": transport.get("health_ok"),
            "service_auth_configured": transport.get("service_auth_configured"),
            "circuit_state": transport.get("circuit_state"),
            "pending_count": transport.get("pending_count"),
            "manual_review_count": transport.get("manual_review_count"),
            "dead_letter_count": transport.get("dead_letter_count"),
            "order_routing_enabled": transport.get("order_routing_enabled"),
            "live_trading_blocked": transport.get("live_trading_blocked"),
        },
        "adapter_harness_summary": {
            "harness_version": adapter.get("harness_version"),
            "adapter_path": adapter.get("adapter_path"),
            "readiness": adapter.get("readiness", {}),
            "next_actions": adapter.get("next_actions", []),
        },
        "jarvis_context": {
            "final_action": jarvis_room.get("final_action"),
            "decision": jarvis_room.get("trade_vision_decision", {}).get("final_trade_decision"),
            "safety_blocking_gates": jarvis_room.get("safety_summary", {}).get("blocking_gates", []),
            "candle_pattern": jarvis_room.get("candle_structure", {}).get("pattern"),
            "timeframe": jarvis_room.get("timeframe"),
        },
        "gates": gates,
        "operator_message": _operator_message(blockers, warnings, adapter),
        "dry_run_handoff_allowed": handoff_allowed,
        "enqueue_allowed": False,
        "automatic_delivery_allowed": False,
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _gates(
    package: dict[str, Any],
    verification: dict[str, Any],
    transport: dict[str, Any],
    adapter: dict[str, Any],
    intent: dict[str, Any],
    bot_verification: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _gate("OA-HANDOFF-001", "Dry-run executor package exists", package.get("package_version") == "openalgo-executor-dry-run-package.v0.50", "block", "Use the signed dry-run package contract."),
        _gate("OA-HANDOFF-002", "Dry-run package verifies", verification.get("verified") is True, "block", "Package and manifest hashes must verify before handoff."),
        _gate("OA-HANDOFF-003", "Intent remains preview-only", _preview_only(intent), "block", "Intent must not claim export, routing, broker credentials, or broker order creation."),
        _gate("OA-HANDOFF-004", "Bot handoff verifier rejects missing external approvals", bot_verification.get("rejected") is True, "downgrade", "Current Trade Vision package should require external human, risk, and account-state checks."),
        _gate("OA-HANDOFF-005", "Adapter transport configured", transport.get("configured") is True, "downgrade", "Set adapter URL before dry-run handoff delivery."),
        _gate("OA-HANDOFF-006", "Adapter service auth configured", transport.get("service_auth_configured") is True, "block", "HMAC service identity must be configured before any delivery attempt."),
        _gate("OA-HANDOFF-007", "Adapter health is safe", transport.get("health_ok") is True, "downgrade", "Adapter health must confirm brokerless review mode."),
        _gate("OA-HANDOFF-008", "Adapter harness files and readiness pass", adapter.get("readiness", {}).get("dry_run_handoff_ready") is True, "downgrade", "Local OpenAlgo adapter harness must be ready before handoff."),
        _gate("OA-HANDOFF-009", "Transport circuit is not open", transport.get("circuit_state") != "open", "block", "Open circuit forces manual review."),
        _gate("OA-HANDOFF-010", "No trade authority", _read_only(package, transport, adapter, intent), "block", "OpenAlgo handoff gate is review-only and cannot create orders."),
    ]


def _preview_only(intent: dict[str, Any]) -> bool:
    return all(
        [
            intent.get("broker_credentials_present") is False,
            intent.get("broker_order_created") is False,
            intent.get("order_routing_enabled") is False,
            intent.get("live_trading_blocked") is True,
            intent.get("trade_allowed") is False,
            intent.get("export_allowed") is False,
        ]
    )


def _read_only(package: dict[str, Any], transport: dict[str, Any], adapter: dict[str, Any], intent: dict[str, Any]) -> bool:
    return all(
        [
            package.get("broker_credentials_present") is False,
            package.get("broker_order_created") is False,
            package.get("trade_allowed") is False,
            package.get("order_routing_enabled") is False,
            package.get("live_trading_blocked") is True,
            transport.get("order_routing_enabled") is False,
            transport.get("live_trading_blocked") is True,
            adapter.get("order_routing_enabled") is False,
            adapter.get("live_trading_blocked") is True,
            _preview_only(intent),
        ]
    )


def _operator_message(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], adapter: dict[str, Any]) -> str:
    if blockers:
        return "OpenAlgo handoff is blocked; keep this as manual research evidence only."
    if warnings:
        return "OpenAlgo handoff package is structurally safe, but adapter readiness or external approval warnings require manual review."
    if adapter.get("readiness", {}).get("dry_run_handoff_ready"):
        return "OpenAlgo dry-run review is ready for operator-controlled adapter testing; no broker order can be created."
    return "OpenAlgo handoff remains manual review only until adapter and approvals are complete."


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}
