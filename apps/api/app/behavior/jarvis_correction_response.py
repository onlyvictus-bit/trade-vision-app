from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .gemini_provider import (
    _hash_packet,
    _sanitize_external_ai_payload,
    validate_gemini_review_response,
)


CORRECTION_RESPONSE_VERSION = "jarvis-correction-response-validator.v1.11"
SAFE_CORRECTION_ACTIONS = {"NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"}


def build_sample_correction_response(correction_packet: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic valid sample response for the correction validator."""
    contract = correction_packet.get("correction_contract", {})
    missing = [item for item in contract.get("must_address_missing_items", []) if item]
    blocked = [item for item in contract.get("must_remove_blocked_claims", []) if item]
    cited_keys = [
        "verified_evidence",
        "allowed_evidence_keys",
        "evidence_sections",
        "verified_daily_data",
        "review_preflight",
        "required_before_resubmission",
    ]
    return {
        "review_status": "valid",
        "agrees_with_trade_vision": True,
        "pattern_interpretation": "Correction review used only verified Trade Vision evidence and keeps the setup in WAIT.",
        "entry_guidance": "Wait for Trade Vision-only confirmation; no external-AI entry is approved.",
        "risk_warning": "Low evidence, stale/disagreement warnings, or missed facts keep confidence capped.",
        "best_indicator_for_pattern": ["verified_evidence", "multi_timeframe_alignment", "safety_summary"],
        "avoid_if": ["Any Trade Vision safety gate fails.", "Daily/HTF evidence is not cited."],
        "confidence_comment": "External AI cannot boost confidence; this response only corrects evidence usage.",
        "final_action": "WAIT",
        "cited_evidence_keys": cited_keys,
        "addressed_missing_items": missing,
        "removed_blocked_claims": blocked,
        "correction_summary": "All listed missing evidence items were acknowledged and unsupported daily/HTF claims were removed.",
    }


def validate_correction_response(
    *,
    correction_packet: dict[str, Any],
    candidate_response: dict[str, Any],
    source: str = "manual",
) -> dict[str, Any]:
    """Validate external correction output before it can be displayed."""
    sanitized_response, redacted_paths = _sanitize_external_ai_payload(candidate_response)
    response = sanitized_response if isinstance(sanitized_response, dict) else {}
    evidence_packet = correction_packet.get("outbound_request_preview", {}).get("evidence_packet", {})
    base_validation = validate_gemini_review_response(evidence_packet if isinstance(evidence_packet, dict) else {}, response)
    citation = _citation_validation(correction_packet, response)
    missing = _missing_item_validation(correction_packet, response)
    blocked = _blocked_claim_validation(correction_packet, response)
    action = _action_validation(response)
    daily = _daily_claim_validation(response)
    gates = [
        _gate("CORR-RESP-001", "Base review schema passes", bool(base_validation.get("schema_validation_passed")), "block", "Correction response must satisfy the strict review schema."),
        _gate("CORR-RESP-002", "No hallucinated evidence keys", not bool(base_validation.get("hallucination_detected")), "block", "Cited keys must exist in the correction packet."),
        _gate("CORR-RESP-003", "Only allowed correction citations are used", citation["passed"], "block", citation["reason"]),
        _gate("CORR-RESP-004", "Required missing items were addressed", missing["passed"], "downgrade", missing["reason"]),
        _gate("CORR-RESP-005", "Blocked claims were removed", blocked["passed"], "block", blocked["reason"]),
        _gate("CORR-RESP-006", "Final action remains safe", action["passed"], "block", action["reason"]),
        _gate("CORR-RESP-007", "Daily/HTF claims cite verified daily evidence", daily["passed"], "block", daily["reason"]),
        _gate("CORR-RESP-008", "No trading or OpenAlgo authority is granted", True, "block", "Validator is display-only and cannot create routes or orders."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    accepted = not blockers and not warnings
    return {
        "validation_version": CORRECTION_RESPONSE_VERSION,
        "source": _normalize_source(source),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_response_hash": _hash_packet(response),
        "correction_packet_hash": correction_packet.get("packet_hash"),
        "sanitized_candidate_response": response,
        "base_validation": base_validation,
        "citation_validation": citation,
        "missing_item_validation": missing,
        "blocked_claim_validation": blocked,
        "action_validation": action,
        "daily_claim_validation": daily,
        "gates": gates,
        "accepted_for_correction_display": accepted,
        "display_status": "accepted_for_correction_display" if accepted else "blocked" if blockers else "needs_resubmission",
        "safe_final_action": response.get("final_action") if accepted and response.get("final_action") in SAFE_CORRECTION_ACTIONS else "TRADE_VISION_ONLY",
        "required_resubmission_items": _required_resubmission_items(blockers, warnings, missing, blocked, citation, daily),
        "sanitization": {
            "redacted_field_paths": redacted_paths,
            "redaction_count": len(redacted_paths),
            "secrets_included": False,
            "broker_credentials_included": False,
            "cookies_or_sessions_included": False,
        },
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _citation_validation(correction_packet: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    cited = [str(item) for item in response.get("cited_evidence_keys", [])] if isinstance(response.get("cited_evidence_keys"), list) else []
    allowed = set(_allowed_citation_keys(correction_packet))
    invalid = sorted(key for key in cited if key not in allowed)
    return {
        "passed": not invalid,
        "invalid_citations": invalid,
        "allowed_citation_count": len(allowed),
        "reason": "All citations are allowed by the correction packet." if not invalid else f"Invalid citations: {', '.join(invalid)}",
    }


def _missing_item_validation(correction_packet: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    required = set(correction_packet.get("correction_contract", {}).get("must_address_missing_items", []))
    addressed = set(str(item) for item in response.get("addressed_missing_items", [])) if isinstance(response.get("addressed_missing_items"), list) else set()
    missing = sorted(required.difference(addressed))
    return {
        "passed": not missing,
        "required_missing_items": sorted(required),
        "addressed_missing_items": sorted(addressed),
        "unaddressed_missing_items": missing,
        "reason": "All required missing items were addressed." if not missing else f"Unaddressed missing items: {', '.join(missing)}",
    }


def _blocked_claim_validation(correction_packet: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    required_removed = set(correction_packet.get("correction_contract", {}).get("must_remove_blocked_claims", []))
    removed = set(str(item) for item in response.get("removed_blocked_claims", [])) if isinstance(response.get("removed_blocked_claims"), list) else set()
    still_blocked = sorted(required_removed.difference(removed))
    return {
        "passed": not still_blocked,
        "required_removed_claims": sorted(required_removed),
        "removed_blocked_claims": sorted(removed),
        "still_blocked_claims": still_blocked,
        "reason": "All blocked claims were removed." if not still_blocked else f"Blocked claims not removed: {', '.join(still_blocked)}",
    }


def _action_validation(response: dict[str, Any]) -> dict[str, Any]:
    action = response.get("final_action")
    passed = action in SAFE_CORRECTION_ACTIONS
    return {
        "passed": passed,
        "final_action": action,
        "safe_actions": sorted(SAFE_CORRECTION_ACTIONS),
        "reason": "Final action is correction-safe." if passed else f"Final action {action!r} is not correction-safe.",
    }


def _daily_claim_validation(response: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(value).lower() for value in _flatten_values(response))
    mentions_daily = any(token in text for token in ("daily", "weekly", "higher-timeframe", "higher timeframe", "htf"))
    cited = " ".join(str(item).lower() for item in response.get("cited_evidence_keys", [])) if isinstance(response.get("cited_evidence_keys"), list) else ""
    cites_daily = any(token in cited for token in ("daily", "weekly", "multi_timeframe_alignment", "timeframes", "htf", "verified_daily_data"))
    passed = not mentions_daily or cites_daily
    return {
        "passed": passed,
        "mentions_daily_or_htf": mentions_daily,
        "cites_verified_daily_evidence": cites_daily,
        "reason": "Daily/HTF claims are cited." if passed else "Daily/HTF claim appeared without verified daily citation.",
    }


def _allowed_citation_keys(correction_packet: dict[str, Any]) -> list[str]:
    allowed = {
        "verified_evidence",
        "review_preflight",
        "required_before_resubmission",
        "correction_contract",
        "required_before_send",
        "allowed_evidence_keys",
        "evidence_sections",
        "verified_daily_data",
        "daily_data_authority",
        "external_ai_missed_items",
        "external_ai_blocked_claims",
        "required_external_ai_corrections",
        "multi_timeframe_alignment",
        "timeframes",
        "daily",
        "weekly",
        "htf_confirmation_available",
    }
    allowed.update(str(item) for item in correction_packet.get("correction_contract", {}).get("must_cite_allowed_keys", []))
    for section in correction_packet.get("outbound_request_preview", {}).get("evidence_packet", {}).get("verified_evidence", {}).get("evidence_sections", []):
        allowed.add(str(section.get("section_id")))
        allowed.update(str(item) for item in section.get("citable_keys", []))
    return sorted(allowed)


def _required_resubmission_items(
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    missing: dict[str, Any],
    blocked: dict[str, Any],
    citation: dict[str, Any],
    daily: dict[str, Any],
) -> list[str]:
    items: list[str] = []
    if citation.get("invalid_citations"):
        items.append("Remove invalid citations or cite only keys from the correction packet.")
    if missing.get("unaddressed_missing_items"):
        items.append("Address every required missing evidence item.")
    if blocked.get("still_blocked_claims"):
        items.append("Remove or correctly cite every blocked claim.")
    if not daily.get("passed"):
        items.append("Cite verified daily/weekly/HTF evidence or remove daily/HTF claims.")
    for gate in blockers + warnings:
        items.append(f"{gate['gate_id']}: {gate['reason']}")
    deduped: list[str] = []
    for item in items:
        if item and item not in deduped:
            deduped.append(item)
    return deduped


def _flatten_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        items: list[Any] = []
        for child in value.values():
            items.extend(_flatten_values(child))
        return items
    if isinstance(value, list):
        items = []
        for child in value:
            items.extend(_flatten_values(child))
        return items
    return [value]


def _normalize_source(source: str) -> str:
    value = source.strip().lower() if source else "manual"
    return value if value in {"gemini", "grok", "manual"} else "manual"


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }
