from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


EXTERNAL_AI_AUDIT_INTEGRITY_VERSION = "jarvis-external-ai-audit-integrity.v1.13"

AUTHORITY_FIELDS = (
    "confidence_boost_allowed",
    "trade_allowed",
    "order_routing_enabled",
    "can_execute_orders",
    "can_export_to_openalgo",
    "can_override_no_trade",
    "can_override_risk",
)


def build_external_ai_audit_integrity_report(
    *,
    symbol: str | None,
    external_review_records: list[dict[str, Any]],
    correction_response_records: list[dict[str, Any]],
    stale_after_seconds: int = 86_400,
) -> dict[str, Any]:
    bounded_stale = max(60, min(stale_after_seconds, 604_800))
    external_issues = _record_issues(
        records=external_review_records,
        record_type="external_review",
        id_field="review_id",
        id_prefix="external-ai-review:",
        required_fields=("review_hash", "evidence_packet_hash", "candidate_response_hash", "source", "intake_status"),
    )
    correction_issues = _record_issues(
        records=correction_response_records,
        record_type="correction_response",
        id_field="validation_id",
        id_prefix="correction-response:",
        required_fields=("validation_hash", "correction_packet_hash", "candidate_response_hash", "source", "display_status"),
    )
    authority_issues = _authority_issues(external_review_records, "external_review") + _authority_issues(correction_response_records, "correction_response")
    external_accepted = [record for record in external_review_records if record.get("display_allowed")]
    external_rejected = [record for record in external_review_records if not record.get("display_allowed")]
    correction_accepted = [record for record in correction_response_records if record.get("accepted_for_correction_display")]
    correction_rejected = [record for record in correction_response_records if not record.get("accepted_for_correction_display")]
    latest_created_at = _latest_created_at(external_review_records + correction_response_records)
    latest_age_seconds = _age_seconds(latest_created_at)
    ledger_empty_warning = not external_review_records and not correction_response_records
    stale_review_history = latest_age_seconds is None or latest_age_seconds > bounded_stale
    counts_consistent = (
        len(external_accepted) + len(external_rejected) == len(external_review_records)
        and len(correction_accepted) + len(correction_rejected) == len(correction_response_records)
    )
    gates = [
        _gate("AUDIT-INT-001", "External review ledger records are well formed", not external_issues, "block", "Every external review needs ids, hashes, source, and status."),
        _gate("AUDIT-INT-002", "Correction response ledger records are well formed", not correction_issues, "block", "Every correction response needs ids, hashes, source, and status."),
        _gate("AUDIT-INT-003", "No audit record grants trading/OpenAlgo authority", not authority_issues, "block", "Audit records must remain display-only and cannot enable routing."),
        _gate("AUDIT-INT-004", "Accepted and rejected counts are internally consistent", counts_consistent, "block", "Ledger count mismatch indicates corrupted or ambiguous audit state."),
        _gate("AUDIT-INT-005", "Ledger has review history for this symbol", not ledger_empty_warning, "downgrade", "No external AI/correction reviews are saved yet; use Trade Vision-only evidence."),
        _gate("AUDIT-INT-006", "Review history is fresh enough for display", not stale_review_history, "downgrade", "Review history is stale or missing; request a fresh correction review before display."),
        _gate("AUDIT-INT-007", "Live trading remains blocked", True, "block", "This verifier is audit-only and cannot unlock live trading."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    integrity_state = "blocked" if blockers else "warning" if warnings else "pass"
    return {
        "integrity_version": EXTERNAL_AI_AUDIT_INTEGRITY_VERSION,
        "symbol": symbol.upper() if symbol else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "external_review_count": len(external_review_records),
        "correction_response_count": len(correction_response_records),
        "accepted_external_review_count": len(external_accepted),
        "rejected_external_review_count": len(external_rejected),
        "accepted_correction_response_count": len(correction_accepted),
        "rejected_correction_response_count": len(correction_rejected),
        "latest_record_created_at": latest_created_at,
        "latest_record_age_seconds": latest_age_seconds,
        "stale_after_seconds": bounded_stale,
        "ledger_empty_warning": ledger_empty_warning,
        "stale_review_history": stale_review_history,
        "external_review_issues": external_issues,
        "correction_response_issues": correction_issues,
        "authority_issues": authority_issues,
        "gates": gates,
        "integrity_state": integrity_state,
        "operator_message": _operator_message(integrity_state, ledger_empty_warning, stale_review_history),
        "verified_daily_data_policy": {
            "only_trade_vision_verified_daily_data_allowed": True,
            "external_ai_daily_claims_require_cited_evidence_keys": True,
            "uncited_daily_or_htf_claims_remain_blocked": True,
        },
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


def _record_issues(
    *,
    records: list[dict[str, Any]],
    record_type: str,
    id_field: str,
    id_prefix: str,
    required_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        record_id = str(record.get(id_field) or "")
        if not record_id.startswith(id_prefix):
            issues.append(_issue(record_type, record_id or f"index:{index}", "invalid_id", f"{id_field} must start with {id_prefix}"))
        for field in required_fields:
            if not record.get(field):
                issues.append(_issue(record_type, record_id or f"index:{index}", "missing_field", f"{field} is required"))
    return issues


def _authority_issues(records: list[dict[str, Any]], record_type: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        record_id = str(record.get("review_id") or record.get("validation_id") or f"index:{index}")
        for field in AUTHORITY_FIELDS:
            if bool(record.get(field)):
                issues.append(_issue(record_type, record_id, "authority_violation", f"{field} must remain false"))
        if record.get("live_trading_blocked") is False:
            issues.append(_issue(record_type, record_id, "authority_violation", "live_trading_blocked must never be false"))
    return issues


def _latest_created_at(records: list[dict[str, Any]]) -> str | None:
    sortable = []
    for record in records:
        created_at = record.get("created_at") or record.get("validated_at")
        parsed = _parse_datetime(created_at)
        if parsed:
            sortable.append((parsed, str(created_at)))
    if not sortable:
        return None
    return max(sortable, key=lambda item: item[0])[1]


def _age_seconds(value: str | None) -> int | None:
    parsed = _parse_datetime(value)
    if not parsed:
        return None
    return max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _issue(record_type: str, record_id: str, issue_type: str, detail: str) -> dict[str, Any]:
    return {
        "record_type": record_type,
        "record_id": record_id,
        "issue_type": issue_type,
        "detail": detail,
    }


def _operator_message(integrity_state: str, ledger_empty_warning: bool, stale_review_history: bool) -> str:
    if integrity_state == "blocked":
        return "External AI audit history is malformed or unsafe; use only Trade Vision verified evidence."
    if ledger_empty_warning:
        return "No external AI review history exists for this symbol; use Trade Vision verified evidence only."
    if stale_review_history:
        return "External AI review history is stale; refresh review before displaying it beside the decision room."
    return "External AI audit history is intact, but it remains display-only with no confidence boost or routing authority."
