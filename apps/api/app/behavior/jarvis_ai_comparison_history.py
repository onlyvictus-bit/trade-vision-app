from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


JARVIS_AI_COMPARISON_HISTORY_VERSION = "jarvis-ai-comparison-history.v1.38"


def build_jarvis_ai_comparison_history_report(
    *,
    symbol: str,
    comparison_records: list[dict[str, Any]],
    stale_after_seconds: int = 900,
) -> dict[str, Any]:
    bounded_stale = max(60, min(stale_after_seconds, 86_400))
    latest = comparison_records[0] if comparison_records else None
    latest_age = _age_seconds(latest.get("created_at")) if latest else None
    stale = latest_age is None or latest_age > bounded_stale
    states = _agreement_counts(comparison_records)
    actions = _action_counts(comparison_records)
    total = len(comparison_records)
    conflict_count = states["HARD_CONFLICT"] + states["SOFT_CONFLICT"]
    agreement_rate = round(states["AGREE"] / total, 4) if total else 0.0
    conflict_rate = round(conflict_count / total, 4) if total else 0.0
    unavailable_rate = round(states["BOTH_UNAVAILABLE"] / total, 4) if total else 1.0
    latest_matrix = latest.get("agreement_matrix", {}) if latest else {}
    latest_displayable = int(latest_matrix.get("displayable_provider_count") or 0)
    gates = [
        _gate("AICH-001", "At least one comparison event exists", total > 0, "downgrade", "No Gemini-vs-Grok comparison history exists yet."),
        _gate("AICH-002", "Latest comparison is fresh", not stale, "downgrade", "Latest Gemini-vs-Grok comparison is stale or missing."),
        _gate("AICH-003", "Latest comparison has displayable external evidence", latest_displayable >= 1, "downgrade", "Both external providers were unavailable or invalid."),
        _gate("AICH-004", "Latest comparison did not hard-conflict", latest_matrix.get("agreement_state") != "HARD_CONFLICT", "downgrade", "Hard conflict forces WAIT and blocks confidence boost."),
        _gate("AICH-005", "Historical conflict rate is acceptable", conflict_rate <= 0.25, "downgrade", "Gemini/Grok conflict too often for trust boosting."),
        _gate("AICH-006", "No comparison grants trading authority", _no_authority_violations(comparison_records), "block", "Comparison records must never grant order authority."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    history_state = "blocked" if blockers else "warning" if warnings else "display_only"
    return {
        "history_version": JARVIS_AI_COMPARISON_HISTORY_VERSION,
        "symbol": symbol.upper(),
        "record_count": total,
        "latest_comparison_id": latest.get("comparison_id") if latest else None,
        "latest_created_at": latest.get("created_at") if latest else None,
        "latest_age_seconds": latest_age,
        "stale_after_seconds": bounded_stale,
        "stale_comparison_history": stale,
        "latest_agreement_state": latest_matrix.get("agreement_state") if latest else "none",
        "latest_safe_final_action": latest.get("safe_final_action") if latest else "TRADE_VISION_ONLY",
        "latest_displayable_provider_count": latest_displayable,
        "agreement_counts": states,
        "safe_action_counts": actions,
        "agreement_rate": agreement_rate,
        "conflict_rate": conflict_rate,
        "unavailable_rate": unavailable_rate,
        "provider_health": _provider_health(comparison_records),
        "gates": gates,
        "history_state": history_state,
        "external_ai_reliable_for_decision": False,
        "confidence_boost_allowed": False,
        "final_external_ai_effect": "trade_vision_only" if blockers else "display_only_no_boost",
        "operator_message": _operator_message(history_state, stale, latest_matrix, conflict_rate),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _agreement_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"AGREE": 0, "SOFT_CONFLICT": 0, "HARD_CONFLICT": 0, "LOW_CONFIDENCE": 0, "BOTH_UNAVAILABLE": 0, "OTHER": 0}
    for record in records:
        state = str(record.get("agreement_matrix", {}).get("agreement_state") or "OTHER")
        counts[state if state in counts else "OTHER"] += 1
    return counts


def _action_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"NO_TRADE": 0, "WAIT": 0, "WATCH_ONLY": 0, "TRADE_VISION_ONLY": 0, "OTHER": 0}
    for record in records:
        action = str(record.get("safe_final_action") or "OTHER")
        counts[action if action in counts else "OTHER"] += 1
    return counts


def _provider_health(records: list[dict[str, Any]]) -> dict[str, Any]:
    providers = {"gemini": {"displayable": 0, "unavailable": 0}, "grok": {"displayable": 0, "unavailable": 0}}
    for record in records:
        for provider in providers:
            report = record.get(provider, {})
            if report.get("display_allowed"):
                providers[provider]["displayable"] += 1
            else:
                providers[provider]["unavailable"] += 1
    total = max(1, len(records))
    for provider in providers.values():
        provider["displayable_rate"] = round(provider["displayable"] / total, 4)
        provider["unavailable_rate"] = round(provider["unavailable"] / total, 4)
    return providers


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


def _age_seconds(value: str | None) -> int | None:
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


def _operator_message(history_state: str, stale: bool, latest_matrix: dict[str, Any], conflict_rate: float) -> str:
    if history_state == "blocked":
        return "Gemini-vs-Grok comparison history contains authority violations; use Trade Vision only."
    if stale:
        return "Gemini-vs-Grok comparison history is stale; request a fresh comparison before display."
    if latest_matrix.get("agreement_state") == "HARD_CONFLICT":
        return "Gemini and Grok hard-conflicted on the latest comparison; Jarvis forces WAIT."
    if conflict_rate > 0.25:
        return "Gemini and Grok conflict too often; external AI remains display-only with no confidence boost."
    return "Gemini-vs-Grok history is displayable as research evidence only. Trade Vision remains the authority."
