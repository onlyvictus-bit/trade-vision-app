from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_AI_REVIEW_REFRESH_GUARD_VERSION = "jarvis-ai-review-refresh-guard.v1.39"


def build_jarvis_ai_review_refresh_guard(
    *,
    symbol: str,
    current_evidence_packet: dict[str, Any],
    comparison_history: dict[str, Any],
    comparison_records: list[dict[str, Any]],
    external_review_records: list[dict[str, Any]],
    correction_response_records: list[dict[str, Any]],
    stale_after_seconds: int = 900,
) -> dict[str, Any]:
    bounded_stale = max(60, min(stale_after_seconds, 86_400))
    current_hash = _hash_packet(current_evidence_packet)
    latest_comparison = comparison_records[0] if comparison_records else None
    latest_external = external_review_records[0] if external_review_records else None
    latest_correction = correction_response_records[0] if correction_response_records else None
    latest_comparison_hash = str(latest_comparison.get("evidence_packet_hash") or "") if latest_comparison else ""
    latest_external_hash = str(latest_external.get("evidence_packet_hash") or "") if latest_external else ""
    latest_comparison_age = _age_seconds(latest_comparison.get("created_at")) if latest_comparison else None
    latest_external_age = _age_seconds(latest_external.get("created_at")) if latest_external else None
    latest_correction_age = _age_seconds(latest_correction.get("created_at") or latest_correction.get("validated_at")) if latest_correction else None
    comparison_hash_matches = bool(latest_comparison_hash and latest_comparison_hash == current_hash)
    external_hash_matches = bool(latest_external_hash and latest_external_hash == current_hash)
    comparison_stale = latest_comparison_age is None or latest_comparison_age > bounded_stale
    external_stale = latest_external_age is None or latest_external_age > bounded_stale
    latest_state = latest_comparison.get("agreement_matrix", {}).get("agreement_state") if latest_comparison else "none"
    needs_refresh = (
        not comparison_hash_matches
        or not external_hash_matches
        or comparison_stale
        or external_stale
        or latest_state in {"HARD_CONFLICT", "SOFT_CONFLICT", "BOTH_UNAVAILABLE"}
        or comparison_history.get("history_state") in {"blocked", "warning"}
    )
    gates = [
        _gate("AIRG-001", "Current evidence packet is hashable", bool(current_hash), "block", "Current Trade Vision evidence packet must be deterministic."),
        _gate("AIRG-002", "Latest comparison matches current evidence", comparison_hash_matches, "downgrade", "Latest Gemini-vs-Grok comparison was generated from a different evidence packet."),
        _gate("AIRG-003", "Latest external review matches current evidence", external_hash_matches, "downgrade", "Latest individual external-AI review was generated from a different evidence packet."),
        _gate("AIRG-004", "Latest comparison is fresh", not comparison_stale, "downgrade", "Latest comparison is stale or missing."),
        _gate("AIRG-005", "Latest external review is fresh", not external_stale, "downgrade", "Latest external review is stale or missing."),
        _gate("AIRG-006", "Latest comparison is not conflicted", latest_state not in {"HARD_CONFLICT", "SOFT_CONFLICT"}, "downgrade", "Conflicted comparison must be refreshed or treated as WAIT."),
        _gate("AIRG-007", "Comparison history has no warning/block state", comparison_history.get("history_state") == "display_only", "downgrade", "Comparison history warning/block keeps external AI display-only."),
        _gate("AIRG-008", "No review/correction record grants authority", _no_authority_violations(comparison_records + external_review_records + correction_response_records), "block", "Saved AI records must not grant trading authority."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    refresh_state = "blocked" if blockers else "refresh_required" if needs_refresh or warnings else "fresh_display_only"
    return {
        "refresh_guard_version": JARVIS_AI_REVIEW_REFRESH_GUARD_VERSION,
        "symbol": symbol.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_evidence_packet_hash": current_hash,
        "latest_comparison_id": latest_comparison.get("comparison_id") if latest_comparison else None,
        "latest_comparison_evidence_hash": latest_comparison_hash or None,
        "latest_comparison_age_seconds": latest_comparison_age,
        "latest_comparison_agreement_state": latest_state,
        "latest_external_review_id": latest_external.get("review_id") if latest_external else None,
        "latest_external_evidence_hash": latest_external_hash or None,
        "latest_external_age_seconds": latest_external_age,
        "latest_correction_validation_id": latest_correction.get("validation_id") if latest_correction else None,
        "latest_correction_age_seconds": latest_correction_age,
        "stale_after_seconds": bounded_stale,
        "comparison_hash_matches_current": comparison_hash_matches,
        "external_review_hash_matches_current": external_hash_matches,
        "comparison_stale": comparison_stale,
        "external_review_stale": external_stale,
        "needs_external_ai_refresh": needs_refresh or bool(warnings),
        "refresh_state": refresh_state,
        "refresh_targets": _refresh_targets(comparison_hash_matches, external_hash_matches, comparison_stale, external_stale, latest_state),
        "comparison_history_summary": {
            "history_version": comparison_history.get("history_version"),
            "history_state": comparison_history.get("history_state"),
            "record_count": comparison_history.get("record_count", 0),
            "conflict_rate": comparison_history.get("conflict_rate", 0.0),
            "unavailable_rate": comparison_history.get("unavailable_rate", 0.0),
        },
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message(refresh_state, latest_state),
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


def _refresh_targets(
    comparison_hash_matches: bool,
    external_hash_matches: bool,
    comparison_stale: bool,
    external_stale: bool,
    latest_state: str,
) -> list[dict[str, Any]]:
    targets = []
    if not comparison_hash_matches or comparison_stale or latest_state in {"HARD_CONFLICT", "SOFT_CONFLICT", "BOTH_UNAVAILABLE"}:
        targets.append(_target("gemini_grok_comparison", "Re-run Gemini-vs-Grok comparison from current Trade Vision evidence."))
    if not external_hash_matches or external_stale:
        targets.append(_target("individual_external_reviews", "Refresh individual Gemini/Grok reviews before showing them beside the chart."))
    if latest_state in {"HARD_CONFLICT", "SOFT_CONFLICT"}:
        targets.append(_target("correction_review", "Ask providers to explain disagreement and return WAIT/NO_TRADE when evidence conflicts."))
    if not targets:
        targets.append(_target("none", "No refresh is required, but external AI remains display-only."))
    return targets


def _target(target_id: str, reason: str) -> dict[str, Any]:
    return {"target_id": target_id, "reason": reason, "order_authority": False}


def _no_authority_violations(records: list[dict[str, Any]]) -> bool:
    authority_fields = (
        "trade_allowed",
        "order_routing_enabled",
        "can_execute_orders",
        "can_export_to_openalgo",
        "can_override_no_trade",
        "can_override_risk",
    )
    for record in records:
        for field in authority_fields:
            if bool(record.get(field)):
                return False
        if record.get("live_trading_blocked") is False:
            return False
    return True


def _hash_packet(packet: dict[str, Any]) -> str:
    canonical = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _age_seconds(value: Any) -> int | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()))
    except ValueError:
        return None


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(refresh_state: str, latest_state: str) -> str:
    if refresh_state == "blocked":
        return "External AI refresh guard found unsafe authority in saved records; use Trade Vision only."
    if refresh_state == "refresh_required":
        if latest_state in {"HARD_CONFLICT", "SOFT_CONFLICT"}:
            return "Latest Gemini/Grok comparison conflicted; refresh or request correction before display."
        return "External AI review is stale or based on old evidence; refresh before using it beside the decision room."
    return "External AI review matches current evidence and is fresh, but remains display-only with no confidence boost."
