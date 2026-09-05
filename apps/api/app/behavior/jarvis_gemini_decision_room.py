from __future__ import annotations

from typing import Any


JARVIS_GEMINI_DECISION_ROOM_VERSION = "jarvis-gemini-decision-room.v1.30"


def build_gemini_decision_room_report(
    *,
    symbol: str,
    provider_status: dict[str, Any],
    outbound_bundle: dict[str, Any],
    sample_review: dict[str, Any],
    realtime_freshness: dict[str, Any],
    decision_quality: dict[str, Any],
    trading_decision_output: dict[str, Any],
) -> dict[str, Any]:
    provider_ready = provider_status.get("status") == "ready"
    outbound_safe = (
        outbound_bundle.get("dry_run_only") is True
        and outbound_bundle.get("network_call_allowed") is False
        and outbound_bundle.get("live_call_performed") is False
        and outbound_bundle.get("sanitization", {}).get("secrets_included") is False
    )
    review_display_allowed = bool(sample_review.get("display_allowed")) and bool(sample_review.get("validation", {}).get("accepted_for_display"))
    freshness_allows_review = realtime_freshness.get("freshness_state") == "fresh" and realtime_freshness.get("force_wait") is False
    decision_blocks = bool(decision_quality.get("force_wait") or decision_quality.get("manual_review_required"))
    safe_action = _safe_action(
        provider_ready=provider_ready,
        outbound_safe=outbound_safe,
        review_display_allowed=review_display_allowed,
        freshness_allows_review=freshness_allows_review,
        decision_blocks=decision_blocks,
        sample_action=sample_review.get("safe_final_action", "TRADE_VISION_ONLY"),
    )
    gates = [
        _gate("GDR-001", "Gemini provider is backend-only", provider_status.get("security", {}).get("backend_only_keys") is True, "block", "Gemini keys must never be exposed to frontend JavaScript."),
        _gate("GDR-002", "Fallback slots are supported", int(provider_status.get("fallback_key_slots_supported", 0)) >= 5, "downgrade", "Operator wanted 4-5 Gemini API keys as fallback."),
        _gate("GDR-003", "Outbound packet is dry-run and sanitized", outbound_safe, "block", "No network, secrets, broker credentials, cookies, or sessions may leave the backend."),
        _gate("GDR-004", "Sample review is schema-valid and displayable", review_display_allowed, "downgrade", "Invalid or hallucinated external review must be hidden or marked untrusted."),
        _gate("GDR-005", "Realtime evidence is fresh enough", freshness_allows_review, "downgrade", "Stale, aging, or latency-degraded evidence forces WAIT before external review trust."),
        _gate("GDR-006", "Gemini cannot execute or override", _cannot_override(provider_status, outbound_bundle, sample_review), "block", "Gemini is reviewer only; it cannot route orders, raise confidence, or override no-trade/risk."),
    ]
    return {
        "decision_room_version": JARVIS_GEMINI_DECISION_ROOM_VERSION,
        "symbol": symbol.upper(),
        "provider_status": provider_status.get("status", "unavailable"),
        "provider_mode": provider_status.get("mode", "unknown"),
        "configured_key_slots": provider_status.get("configured_key_slots", 0),
        "fallback_key_slots_supported": provider_status.get("fallback_key_slots_supported", 5),
        "selected_model": provider_status.get("selected_model"),
        "review_schema_version": provider_status.get("review_schema_version"),
        "outbound_request_hash": outbound_bundle.get("request_hash"),
        "evidence_packet_hash": outbound_bundle.get("evidence_packet_hash"),
        "redaction_count": outbound_bundle.get("sanitization", {}).get("redaction_count", 0),
        "dry_run_only": True,
        "network_call_allowed": False,
        "live_call_performed": False,
        "review_display_allowed": review_display_allowed,
        "sample_review_status": sample_review.get("display_status", sample_review.get("review_status", "pending")),
        "sample_safe_action": sample_review.get("safe_final_action", "TRADE_VISION_ONLY"),
        "safe_final_action": safe_action,
        "freshness_state": realtime_freshness.get("freshness_state"),
        "freshness_safe_action": realtime_freshness.get("safe_display_action"),
        "decision_quality_state": decision_quality.get("quality_state"),
        "trade_vision_output_state": trading_decision_output.get("output_state"),
        "trade_vision_display_action": trading_decision_output.get("trade_plan", {}).get("display_action"),
        "confidence_boost_allowed": False,
        "gemini_can_execute_orders": False,
        "gemini_can_override_no_trade": False,
        "gemini_can_override_risk": False,
        "gates": gates,
        "blocking_count": sum(1 for gate in gates if gate["effect"] == "block" and not gate["passed"]),
        "warning_count": sum(1 for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]),
        "operator_message": _operator_message(provider_ready, freshness_allows_review, review_display_allowed),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _safe_action(
    *,
    provider_ready: bool,
    outbound_safe: bool,
    review_display_allowed: bool,
    freshness_allows_review: bool,
    decision_blocks: bool,
    sample_action: str,
) -> str:
    if decision_blocks:
        return "WAIT"
    if not outbound_safe:
        return "TRADE_VISION_ONLY"
    if not provider_ready:
        return "TRADE_VISION_ONLY"
    if not freshness_allows_review:
        return "WAIT"
    if not review_display_allowed:
        return "TRADE_VISION_ONLY"
    return sample_action if sample_action in {"NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"} else "WAIT"


def _cannot_override(*reports: dict[str, Any]) -> bool:
    for report in reports:
        if report.get("can_execute_orders") is not False and "can_execute_orders" in report:
            return False
        if report.get("can_override_no_trade") is not False and "can_override_no_trade" in report:
            return False
        if report.get("can_override_risk") is not False and "can_override_risk" in report:
            return False
        if report.get("order_routing_enabled") is not False and "order_routing_enabled" in report:
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


def _operator_message(provider_ready: bool, freshness_allows_review: bool, review_display_allowed: bool) -> str:
    if not provider_ready:
        return "Gemini decision room is Trade Vision-only because live Gemini provider is unavailable or disabled."
    if not freshness_allows_review:
        return "Gemini decision room is forced to WAIT because evidence freshness or latency is not strong enough."
    if not review_display_allowed:
        return "Gemini decision room cannot display external review because validation failed or review is unavailable."
    return "Gemini review may be displayed as evidence only; it cannot execute, override risk, or export to OpenAlgo."
