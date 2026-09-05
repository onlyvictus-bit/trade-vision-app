from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .gemini_provider import build_external_ai_review_intake


JARVIS_AI_REFRESH_RESPONSE_INTAKE_VERSION = "jarvis-ai-refresh-response-intake.v1.41"


def build_jarvis_ai_refresh_response_intake(
    *,
    symbol: str,
    provider: str,
    refresh_action: dict[str, Any],
    candidate_response: dict[str, Any],
    response_packet_hash: str | None = None,
) -> dict[str, Any]:
    normalized_provider = provider.strip().lower() if provider else "manual"
    if normalized_provider not in {"gemini", "grok", "manual"}:
        normalized_provider = "manual"
    refresh_packet = refresh_action.get("refresh_packet_preview", {})
    evidence_packet = _provider_evidence_packet(refresh_packet, normalized_provider)
    expected_packet_hash = str(refresh_action.get("packet_hash") or _hash_packet(refresh_packet))
    supplied_packet_hash = response_packet_hash or candidate_response.get("packet_hash") or candidate_response.get("refresh_packet_hash")
    packet_hash_matches = bool(supplied_packet_hash and supplied_packet_hash == expected_packet_hash)
    current_evidence_hash = str(refresh_action.get("current_evidence_packet_hash") or "")
    intake = build_external_ai_review_intake(
        evidence_packet=evidence_packet if isinstance(evidence_packet, dict) else {},
        candidate_response=candidate_response,
        source=normalized_provider,
    )
    validation = intake.get("validation", {})
    gates = [
        _gate("AIRI-001", "Refresh action harness is v1.40", refresh_action.get("harness_version") == "jarvis-ai-refresh-action-harness.v1.40", "block", "Responses must be tied to v1.40 refresh packet."),
        _gate("AIRI-002", "Response packet hash matches refresh packet", packet_hash_matches, "block", "Response was not produced from the current v1.40 refresh packet."),
        _gate("AIRI-003", "Provider is recognized", normalized_provider in {"gemini", "grok", "manual"}, "block", "Only Gemini, Grok, or manual review responses are allowed."),
        _gate("AIRI-004", "Response schema is valid", validation.get("schema_validation_passed") is True, "downgrade", "Invalid schema cannot be displayed."),
        _gate("AIRI-005", "Response cites only available evidence", validation.get("hallucination_detected") is False, "downgrade", "Hallucinated evidence keys are rejected."),
        _gate("AIRI-006", "No unsafe override attempted", validation.get("unsafe_override_attempted") is False, "block", "External AI cannot override NO_TRADE, risk, or safety."),
        _gate("AIRI-007", "Refresh action has no trading authority", _read_only(refresh_action), "block", "Refresh responses remain evidence-only."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    accepted = not blockers and not warnings and bool(intake.get("display_allowed"))
    replay_status = "accepted_for_display" if accepted else "blocked" if blockers else "rejected"
    enriched_record = {
        **intake,
        "symbol": symbol.upper(),
        "source": normalized_provider,
        "refresh_response_intake_version": JARVIS_AI_REFRESH_RESPONSE_INTAKE_VERSION,
        "refresh_packet_hash": expected_packet_hash,
        "response_packet_hash": supplied_packet_hash,
        "response_packet_hash_matches": packet_hash_matches,
        "refresh_action_packet_hash": expected_packet_hash,
        "refresh_action_evidence_hash": current_evidence_hash,
        "display_allowed": accepted,
        "intake_status": replay_status,
        "safe_final_action": "WAIT" if accepted and intake.get("safe_final_action") in {"WAIT", "NO_TRADE", "WATCH_ONLY", "TRADE_VISION_ONLY"} else "TRADE_VISION_ONLY",
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }
    return {
        "intake_replay_version": JARVIS_AI_REFRESH_RESPONSE_INTAKE_VERSION,
        "symbol": symbol.upper(),
        "provider": normalized_provider,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expected_refresh_packet_hash": expected_packet_hash,
        "supplied_response_packet_hash": supplied_packet_hash,
        "packet_hash_matches": packet_hash_matches,
        "current_evidence_packet_hash": current_evidence_hash,
        "replay_status": replay_status,
        "display_allowed": accepted,
        "candidate_response_hash": _hash_packet(candidate_response),
        "review_record": enriched_record,
        "validation": validation,
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message(replay_status, normalized_provider),
        "external_ai_reliable_for_decision": False,
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _provider_evidence_packet(refresh_packet: dict[str, Any], provider: str) -> dict[str, Any]:
    request = refresh_packet.get(f"{provider}_request", {})
    preview = request.get("outbound_request_preview", {})
    return preview.get("evidence_packet", {}) if isinstance(preview, dict) else {}


def _read_only(report: dict[str, Any]) -> bool:
    fields = (
        "trade_allowed",
        "order_routing_enabled",
        "can_execute_orders",
        "can_export_to_openalgo",
        "can_override_no_trade",
        "can_override_risk",
    )
    for field in fields:
        if bool(report.get(field)):
            return False
    return report.get("live_trading_blocked") is not False


def _hash_packet(packet: Any) -> str:
    canonical = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(replay_status: str, provider: str) -> str:
    if replay_status == "accepted_for_display":
        return f"{provider} refresh response is accepted for display only; it cannot boost confidence or route orders."
    if replay_status == "blocked":
        return f"{provider} refresh response is blocked by packet/safety gates; use Trade Vision-only evidence."
    return f"{provider} refresh response is rejected for display; request corrected strict JSON tied to the v1.40 packet."
