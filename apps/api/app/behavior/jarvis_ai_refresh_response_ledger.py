from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


JARVIS_AI_REFRESH_RESPONSE_LEDGER_VERSION = "jarvis-ai-refresh-response-ledger.v1.42"


def build_jarvis_ai_refresh_response_ledger(
    *,
    symbol: str,
    records: list[dict[str, Any]],
    current_evidence_packet_hash: str,
    stale_after_seconds: int = 900,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    normalized = symbol.upper()
    scoped = [record for record in records if str(record.get("symbol", normalized)).upper() == normalized]
    rows = [_summarize_record(record, current_evidence_packet_hash, now, stale_after_seconds) for record in scoped]
    provider_rows = [_provider_summary(provider, rows) for provider in ("gemini", "grok", "manual")]
    accepted = [row for row in rows if row["display_allowed"]]
    blocked = [row for row in rows if row["status"] == "blocked"]
    rejected = [row for row in rows if row["status"] == "rejected"]
    stale = [row for row in rows if row["stale"]]
    hash_mismatch = [row for row in rows if not row["matches_current_evidence"]]
    unsafe = [row for row in rows if row["unsafe_authority_detected"]]
    latest = rows[0] if rows else None
    latest_accepted = next((row for row in rows if row["display_allowed"]), None)
    gates = [
        _gate("AIRL-001", "Refresh response records exist", bool(rows), "downgrade", "No response history exists yet."),
        _gate("AIRL-002", "Latest accepted response matches current evidence", bool(latest_accepted and latest_accepted["matches_current_evidence"]), "downgrade", "Latest accepted response is stale or missing."),
        _gate("AIRL-003", "No response record has trading authority", not unsafe, "block", "Any external AI record with order authority is unsafe."),
        _gate("AIRL-004", "Accepted responses are fresh", not any(row["display_allowed"] and row["stale"] for row in rows), "downgrade", "Accepted response is older than the stale threshold."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    ledger_state = "unsafe_blocked" if blockers else "needs_refresh" if warnings else "fresh_display_history"
    return {
        "ledger_version": JARVIS_AI_REFRESH_RESPONSE_LEDGER_VERSION,
        "symbol": normalized,
        "generated_at": now.isoformat(),
        "current_evidence_packet_hash": current_evidence_packet_hash,
        "stale_after_seconds": max(1, int(stale_after_seconds)),
        "ledger_state": ledger_state,
        "record_count": len(rows),
        "accepted_count": len(accepted),
        "blocked_count": len(blocked),
        "rejected_count": len(rejected),
        "stale_count": len(stale),
        "hash_mismatch_count": len(hash_mismatch),
        "unsafe_authority_count": len(unsafe),
        "latest_record": latest,
        "latest_accepted_record": latest_accepted,
        "provider_summaries": provider_rows,
        "recent_records": rows[:10],
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message(ledger_state),
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


def _summarize_record(record: dict[str, Any], current_hash: str, now: datetime, stale_after_seconds: int) -> dict[str, Any]:
    created_at = _parse_time(record.get("created_at")) or now
    age_seconds = max(0, int((now - created_at).total_seconds()))
    record_hash = str(record.get("refresh_action_evidence_hash") or record.get("evidence_packet_hash") or "")
    matches_current = bool(record_hash and current_hash and record_hash == current_hash)
    status = str(record.get("intake_status") or record.get("display_status") or "unknown")
    unsafe_authority = any(bool(record.get(field)) for field in (
        "trade_allowed",
        "order_routing_enabled",
        "can_execute_orders",
        "can_export_to_openalgo",
        "can_override_no_trade",
        "can_override_risk",
    ))
    return {
        "review_id": record.get("review_id"),
        "source": str(record.get("source") or "manual").lower(),
        "created_at": created_at.isoformat(),
        "age_seconds": age_seconds,
        "stale": age_seconds > max(1, int(stale_after_seconds)),
        "status": status,
        "display_allowed": bool(record.get("display_allowed")),
        "safe_final_action": record.get("safe_final_action", "TRADE_VISION_ONLY"),
        "matches_current_evidence": matches_current,
        "evidence_packet_hash": record_hash,
        "refresh_packet_hash": record.get("refresh_packet_hash") or record.get("refresh_action_packet_hash"),
        "response_packet_hash_matches": bool(record.get("response_packet_hash_matches", record.get("packet_hash_matches", False))),
        "hallucination_detected": bool(record.get("validation", {}).get("hallucination_detected")),
        "unsafe_override_attempted": bool(record.get("validation", {}).get("unsafe_override_attempted")),
        "schema_validation_passed": bool(record.get("validation", {}).get("schema_validation_passed")),
        "unsafe_authority_detected": unsafe_authority,
        "operator_note": _record_note(status, matches_current, age_seconds, stale_after_seconds),
    }


def _provider_summary(provider: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    provider_rows = [row for row in rows if row["source"] == provider]
    accepted = [row for row in provider_rows if row["display_allowed"]]
    latest = provider_rows[0] if provider_rows else None
    return {
        "provider": provider,
        "record_count": len(provider_rows),
        "accepted_count": len(accepted),
        "blocked_count": sum(1 for row in provider_rows if row["status"] == "blocked"),
        "rejected_count": sum(1 for row in provider_rows if row["status"] == "rejected"),
        "stale_count": sum(1 for row in provider_rows if row["stale"]),
        "hash_mismatch_count": sum(1 for row in provider_rows if not row["matches_current_evidence"]),
        "latest_status": latest["status"] if latest else "none",
        "latest_age_seconds": latest["age_seconds"] if latest else None,
        "latest_matches_current": latest["matches_current_evidence"] if latest else False,
        "display_reliability_pct": round((len(accepted) / len(provider_rows)) * 100, 2) if provider_rows else 0.0,
        "safe_for_decision_boost": False,
    }


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _record_note(status: str, matches_current: bool, age_seconds: int, stale_after_seconds: int) -> str:
    if status == "blocked":
        return "Response was blocked by packet or safety gates."
    if status == "rejected":
        return "Response was rejected for schema, hallucination, or safety reasons."
    if not matches_current:
        return "Response belongs to older evidence and must not guide current decision."
    if age_seconds > stale_after_seconds:
        return "Response is stale and should be refreshed before review."
    return "Response is displayable evidence only; no confidence boost or order authority."


def _operator_message(state: str) -> str:
    if state == "fresh_display_history":
        return "Refresh response history is fresh enough for display, but still cannot boost confidence or route orders."
    if state == "unsafe_blocked":
        return "At least one external AI response record has unsafe authority flags; ignore external AI until remediated."
    return "External AI response history is missing, stale, or mismatched; refresh before using it as display evidence."
