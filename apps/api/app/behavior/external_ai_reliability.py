from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


EXTERNAL_AI_RELIABILITY_VERSION = "jarvis-external-ai-consensus-reliability.v1.07"


def build_external_ai_reliability_report(
    *,
    symbol: str,
    room: dict[str, Any],
    records: list[dict[str, Any]],
    stale_after_seconds: int = 900,
) -> dict[str, Any]:
    bounded_stale = max(60, min(stale_after_seconds, 86_400))
    latest = records[0] if records else None
    accepted = [record for record in records if record.get("display_allowed")]
    rejected = [record for record in records if not record.get("display_allowed")]
    action_counts = _action_counts(records)
    disagreement = len([action for action, count in action_counts.items() if count > 0]) > 1
    latest_age = _age_seconds(latest.get("created_at")) if latest else None
    stale = latest_age is None or latest_age > bounded_stale
    low_evidence = _low_evidence(room, records)
    daily = _verified_daily_data(room, latest)
    gates = [
        _gate("EXTAI-REL-001", "External AI review history is fresh", not stale, "downgrade", "Review history is missing or stale."),
        _gate("EXTAI-REL-002", "External AI sources agree", not disagreement, "downgrade", "External AI actions disagree; do not boost confidence."),
        _gate("EXTAI-REL-003", "Trade Vision has enough similar-history evidence", not low_evidence["low_evidence"], "downgrade", low_evidence["reason"]),
        _gate("EXTAI-REL-004", "External AI did not miss verified daily-data facts", not daily["missed_verified_daily_facts"], "downgrade", "External AI omitted daily/HTF evidence that Trade Vision already verified."),
        _gate("EXTAI-REL-005", "External AI made no unverified daily-data claim", not daily["unverified_daily_claims"], "block", "External AI mentioned daily context without citing verified daily evidence."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    reliability_state = "blocked" if blockers else "downgraded" if warnings else "watch_only"
    return {
        "reliability_version": EXTERNAL_AI_RELIABILITY_VERSION,
        "symbol": symbol.upper(),
        "record_count": len(records),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "sources_seen": sorted({record.get("source", "manual") for record in records}),
        "action_counts": action_counts,
        "latest_review_id": latest.get("review_id") if latest else None,
        "latest_source": latest.get("source") if latest else None,
        "latest_safe_action": latest.get("safe_final_action") if latest else None,
        "latest_age_seconds": latest_age,
        "stale_after_seconds": bounded_stale,
        "disagreement_detected": disagreement,
        "low_evidence_detected": low_evidence["low_evidence"],
        "stale_review_history": stale,
        "verified_daily_data": daily,
        "gates": gates,
        "reliability_state": reliability_state,
        "external_ai_reliable_for_decision": False,
        "confidence_boost_allowed": False,
        "final_external_ai_effect": "trade_vision_only" if blockers else "display_only_no_boost",
        "operator_message": _operator_message(blockers, warnings, daily),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _action_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    actions = {"NO_TRADE": 0, "WAIT": 0, "WATCH_ONLY": 0, "TRADE_VISION_ONLY": 0, "OTHER": 0}
    for record in records:
        action = str(record.get("safe_final_action") or "OTHER")
        if action not in actions:
            action = "OTHER"
        actions[action] += 1
    return actions


def _age_seconds(value: str | None) -> int | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        created = datetime.fromisoformat(normalized)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds()))
    except ValueError:
        return None


def _low_evidence(room: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    similar = room.get("similar_history", {})
    matches = int(similar.get("matches_used") or similar.get("historical_match_count") or 0)
    minimum_pass = bool(similar.get("minimum_sample_pass"))
    accepted_count = len([record for record in records if record.get("display_allowed")])
    low = not minimum_pass or matches < 30 or accepted_count < 1
    reason = (
        f"matches={matches}, minimum_sample_pass={minimum_pass}, accepted_external_reviews={accepted_count}; "
        "probability and external-AI confidence remain capped."
    )
    return {"low_evidence": low, "matches": matches, "minimum_sample_pass": minimum_pass, "accepted_external_reviews": accepted_count, "reason": reason}


def _verified_daily_data(room: dict[str, Any], latest: dict[str, Any] | None) -> dict[str, Any]:
    multi_tf = room.get("multi_timeframe_alignment", {})
    timeframes = multi_tf.get("timeframes", {})
    daily_state = timeframes.get("daily", "not_available_closed_candle_only")
    weekly_state = timeframes.get("weekly", "not_available_closed_candle_only")
    htf_confirmation = bool(multi_tf.get("htf_confirmation_available"))
    facts = [
        {
            "fact_id": "DAILY-001",
            "label": "Daily closed-candle state",
            "value": daily_state,
            "verified": True,
            "source": "multi_timeframe_alignment.timeframes.daily",
        },
        {
            "fact_id": "DAILY-002",
            "label": "Weekly closed-candle state",
            "value": weekly_state,
            "verified": True,
            "source": "multi_timeframe_alignment.timeframes.weekly",
        },
        {
            "fact_id": "DAILY-003",
            "label": "Higher-timeframe confirmation availability",
            "value": htf_confirmation,
            "verified": True,
            "source": "multi_timeframe_alignment.htf_confirmation_available",
        },
    ]
    response = latest.get("sanitized_candidate_response", {}) if latest else {}
    cited = response.get("cited_evidence_keys", []) if isinstance(response, dict) else []
    cited_text = " ".join(str(item).lower() for item in cited) if isinstance(cited, list) else ""
    response_text = " ".join(str(value).lower() for value in _flatten_values(response)) if isinstance(response, dict) else ""
    cited_daily = any(token in cited_text for token in ("daily", "weekly", "multi_timeframe_alignment", "timeframes", "htf"))
    mentioned_daily = any(token in response_text for token in ("daily", "weekly", "higher-timeframe", "higher timeframe", "htf"))
    missed = [] if cited_daily else [fact["fact_id"] for fact in facts]
    unverified_claims = mentioned_daily and not cited_daily
    return {
        "only_verified_daily_data_used": True,
        "facts": facts,
        "external_ai_cited_daily_evidence": cited_daily,
        "external_ai_mentioned_daily_context": mentioned_daily,
        "missed_verified_daily_facts": missed,
        "unverified_daily_claims": unverified_claims,
        "policy": "External AI may discuss daily/weekly/HTF context only when it cites verified Trade Vision daily evidence keys.",
    }


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


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], daily: dict[str, Any]) -> str:
    if blockers:
        return "External AI review is blocked for decision use; use only Trade Vision verified evidence."
    if warnings:
        return "External AI review is display-only; disagreement, low evidence, stale history, or missed daily facts cap trust."
    if daily["external_ai_cited_daily_evidence"]:
        return "External AI cited verified daily evidence, but it still cannot boost confidence or route orders."
    return "External AI review remains display-only and Trade Vision verified evidence stays the authority."
