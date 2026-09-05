from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .gemini_provider import (
    ALLOWED_FINAL_ACTIONS,
    REQUIRED_REVIEW_FIELDS,
    build_gemini_prompt_policy,
    _hash_packet,
    _sanitize_external_ai_payload,
)


CORRECTION_PACKET_VERSION = "jarvis-correction-review-packet.v1.10"


def build_jarvis_correction_review_packet(
    *,
    symbol: str,
    verified_evidence: dict[str, Any],
    review_preflight: dict[str, Any],
    provider_status: dict[str, Any],
) -> dict[str, Any]:
    """Build the safe dry-run packet for external correction review."""
    correction_target = _target_allowed(review_preflight, "gemini_correction_review")
    packet = _raw_packet(symbol, verified_evidence, review_preflight)
    sanitized_packet, redacted_paths = _sanitize_external_ai_payload(packet)
    request_preview = {
        "model": provider_status.get("selected_model", "gemini-2.0-flash"),
        "temperature": 0.0,
        "timeout_ms": provider_status.get("timeout_ms", 2000),
        "response_format": "strict_json",
        "system_prompt": _correction_prompt(),
        "required_fields": sorted(REQUIRED_REVIEW_FIELDS),
        "allowed_final_actions": sorted(ALLOWED_FINAL_ACTIONS),
        "evidence_packet": sanitized_packet,
    }
    gates = [
        _gate("CORR-PKT-001", "Correction review target is allowed", correction_target, "block", "Review preflight must allow correction review."),
        _gate("CORR-PKT-002", "Packet uses verified evidence certificate", verified_evidence.get("certificate_version") == "jarvis-verified-evidence-certificate.v1.08", "block", "Use only v1.08 verified evidence."),
        _gate("CORR-PKT-003", "No secrets remain after sanitization", True, "block", "Sanitizer redacts API keys, tokens, sessions, cookies, and broker credentials."),
        _gate("CORR-PKT-004", "External AI final actions are constrained", True, "block", "Only NO_TRADE, WAIT, WATCH_ONLY, or TRADE_VISION_ONLY are allowed."),
        _gate("CORR-PKT-005", "Network call is disabled", True, "block", "This packet is a dry-run preview only."),
        _gate("CORR-PKT-006", "No OpenAlgo export or order route is possible", True, "block", "Packet is evidence-only and cannot become an order."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    return {
        "packet_version": CORRECTION_PACKET_VERSION,
        "symbol": symbol.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "packet_hash": _hash_packet(sanitized_packet),
        "request_hash": _hash_packet(request_preview),
        "provider_version": provider_status.get("provider_version"),
        "review_schema_version": provider_status.get("review_schema_version"),
        "dry_run_only": True,
        "network_call_allowed": False,
        "live_call_performed": False,
        "ready_for_correction_review": correction_target and not blockers,
        "ready_for_decision_trust": False,
        "ready_for_openalgo": False,
        "sanitization": {
            "redacted_field_paths": redacted_paths,
            "redaction_count": len(redacted_paths),
            "secrets_included": False,
            "broker_credentials_included": False,
            "cookies_or_sessions_included": False,
        },
        "outbound_request_preview": request_preview,
        "correction_contract": {
            "must_cite_allowed_keys": verified_evidence.get("allowed_evidence_keys", []),
            "must_address_missing_items": [item.get("item_id") for item in verified_evidence.get("external_ai_missed_items", [])],
            "must_remove_blocked_claims": [claim.get("claim_id") for claim in verified_evidence.get("external_ai_blocked_claims", [])],
            "must_return_json_only": True,
            "cannot_raise_confidence": True,
            "cannot_change_trade_vision_decision": True,
            "cannot_export_to_openalgo": True,
        },
        "required_before_send": review_preflight.get("required_before_resubmission", []),
        "gates": gates,
        "packet_state": "blocked" if blockers else "ready_for_correction_review",
        "operator_message": _operator_message(blockers),
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _raw_packet(symbol: str, verified_evidence: dict[str, Any], review_preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_type": "external_ai_correction_review",
        "symbol": symbol.upper(),
        "verified_evidence": verified_evidence,
        "review_preflight": review_preflight,
        "instructions": [
            "Use only allowed_evidence_keys and evidence_sections.",
            "If daily/weekly/HTF context is mentioned, cite verified daily evidence keys.",
            "Return corrected strict JSON using the required schema.",
            "If evidence is weak, stale, conflicting, or incomplete, return WAIT or NO_TRADE.",
            "Do not recommend broker routing, OpenAlgo export, live trading, or confidence boost.",
        ],
    }


def _correction_prompt() -> str:
    return (
        build_gemini_prompt_policy()["system_prompt"]
        + " You are performing correction review only. You must identify missed verified evidence, remove unsupported daily/weekly/HTF claims, and keep final_action within the safe allowed set."
    )


def _target_allowed(review_preflight: dict[str, Any], target_id: str) -> bool:
    for target in review_preflight.get("review_targets", []):
        if target.get("target_id") == target_id:
            return bool(target.get("allowed"))
    return False


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blockers: list[dict[str, Any]]) -> str:
    if blockers:
        return "Correction review packet is blocked; rebuild verified evidence and review preflight first."
    return "Correction review packet is ready for dry-run operator review only; no network call, route, export, or trade is allowed."
