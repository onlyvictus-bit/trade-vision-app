from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


VERIFIED_EVIDENCE_VERSION = "jarvis-verified-evidence-certificate.v1.08"


def build_jarvis_verified_evidence_certificate(
    *,
    symbol: str,
    room: dict[str, Any],
    external_ai_reliability: dict[str, Any],
) -> dict[str, Any]:
    """Build the only evidence pack external AI may use for daily/HTF claims."""
    verified_daily = external_ai_reliability.get("verified_daily_data", {})
    allowed_keys = _allowed_evidence_keys(room)
    evidence_sections = _evidence_sections(room, verified_daily)
    missing_items = _missing_external_ai_items(external_ai_reliability)
    blocked_claims = _blocked_claims(external_ai_reliability)
    gates = [
        _gate("VER-EVID-001", "Only point-in-time Trade Vision evidence is included", True, "block", "Evidence is copied from the current Jarvis room and reliability gate."),
        _gate("VER-EVID-002", "Daily/weekly/HTF facts are closed-candle facts only", bool(verified_daily.get("only_verified_daily_data_used")), "block", "Daily facts must come from Trade Vision verified daily evidence."),
        _gate("VER-EVID-003", "External AI missed items are explicitly listed", True, "downgrade", "Missing items become a prompt correction, not a confidence boost."),
        _gate("VER-EVID-004", "Unverified daily claims are blocked", not bool(verified_daily.get("unverified_daily_claims")), "block", "External AI mentioned daily/HTF context without verified daily citations."),
        _gate("VER-EVID-005", "External AI cannot export or route an intent", True, "block", "Certificate is evidence-only and cannot become an order."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    return {
        "certificate_version": VERIFIED_EVIDENCE_VERSION,
        "symbol": symbol.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_policy": "External AI may use only this certificate and cited keys; unsupported daily/weekly/HTF claims are blocked.",
        "allowed_evidence_keys": allowed_keys,
        "evidence_sections": evidence_sections,
        "verified_daily_data": verified_daily,
        "external_ai_missed_items": missing_items,
        "external_ai_blocked_claims": blocked_claims,
        "required_external_ai_corrections": _required_corrections(missing_items, blocked_claims),
        "daily_data_authority": {
            "source": "Trade Vision multi_timeframe_alignment + External AI Reliability Gate",
            "closed_candle_only": True,
            "frontend_may_display": True,
            "external_ai_may_infer_beyond_facts": False,
            "daily_claim_requires_citation": True,
        },
        "gates": gates,
        "certificate_state": "blocked" if blockers else "needs_review" if warnings or missing_items else "verified_display_only",
        "operator_message": _operator_message(blockers, missing_items, blocked_claims),
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _allowed_evidence_keys(room: dict[str, Any]) -> list[str]:
    base_keys = [
        "symbol",
        "timeframe",
        "packet_metadata",
        "chart_context",
        "candle_structure",
        "indicator_snapshot",
        "multi_timeframe_alignment",
        "trade_vision_decision",
        "similar_history",
        "safety_summary",
        "kronos_summary",
        "openalgo_summary",
        "paper_reality_check",
        "decision_arbiter",
    ]
    return [key for key in base_keys if key in room]


def _evidence_sections(room: dict[str, Any], verified_daily: dict[str, Any]) -> list[dict[str, Any]]:
    sections = [
        _section(
            "EV-CHART-001",
            "Chart and Candle Evidence",
            ["chart_context", "candle_structure"],
            {
                "bars_available": len(room.get("chart_context", {}).get("bars", [])),
                "pattern": room.get("candle_structure", {}).get("pattern") or room.get("candle_structure", {}).get("candle_behavior"),
                "wick_body_available": bool(room.get("candle_structure")),
            },
        ),
        _section(
            "EV-IND-001",
            "Indicator Evidence",
            ["indicator_snapshot"],
            {
                "indicator_count": len(room.get("indicator_snapshot", {})),
                "sample_keys": sorted(room.get("indicator_snapshot", {}).keys())[:12],
            },
        ),
        _section(
            "EV-DAILY-001",
            "Verified Daily/Weekly/HTF Evidence",
            ["multi_timeframe_alignment", "timeframes", "daily", "weekly", "htf_confirmation_available"],
            {
                "facts": verified_daily.get("facts", []),
                "only_verified_daily_data_used": verified_daily.get("only_verified_daily_data_used", False),
            },
        ),
        _section(
            "EV-MEM-001",
            "Memory and Similar History Evidence",
            ["similar_history"],
            {
                "matches_used": room.get("similar_history", {}).get("matches_used") or room.get("similar_history", {}).get("historical_match_count", 0),
                "minimum_sample_pass": room.get("similar_history", {}).get("minimum_sample_pass", False),
            },
        ),
        _section(
            "EV-SAFE-001",
            "Safety and Arbiter Evidence",
            ["safety_summary", "decision_arbiter"],
            {
                "blocking_gates": room.get("safety_summary", {}).get("blocking_gates", []),
                "final_action": room.get("decision_arbiter", {}).get("final_action") or room.get("final_action"),
                "order_routing_enabled": bool(room.get("decision_arbiter", {}).get("order_routing_enabled", False)),
            },
        ),
    ]
    return sections


def _section(section_id: str, name: str, keys: list[str], facts: dict[str, Any]) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "name": name,
        "citable_keys": keys,
        "facts": facts,
        "verified": True,
        "external_ai_use": "cite_keys_or_do_not_claim",
    }


def _missing_external_ai_items(external_ai_reliability: dict[str, Any]) -> list[dict[str, Any]]:
    daily = external_ai_reliability.get("verified_daily_data", {})
    missed = daily.get("missed_verified_daily_facts", [])
    items = [
        {
            "item_id": fact_id,
            "severity": "medium",
            "reason": "External AI did not cite this verified daily/HTF fact.",
            "required_citation_keys": ["multi_timeframe_alignment", "timeframes", "daily", "weekly", "htf_confirmation_available"],
        }
        for fact_id in missed
    ]
    if external_ai_reliability.get("disagreement_detected"):
        items.append(
            {
                "item_id": "EXTAI-MISS-AGREEMENT",
                "severity": "medium",
                "reason": "External AI sources disagree; request a conflict explanation before display trust.",
                "required_citation_keys": ["final_action", "risk_warning", "confidence_comment"],
            }
        )
    if external_ai_reliability.get("low_evidence_detected"):
        items.append(
            {
                "item_id": "EXTAI-MISS-EVIDENCE",
                "severity": "high",
                "reason": "Trade Vision similar-history evidence is below the strong sample threshold.",
                "required_citation_keys": ["similar_history", "minimum_sample_pass", "historical_match_count"],
            }
        )
    if external_ai_reliability.get("stale_review_history"):
        items.append(
            {
                "item_id": "EXTAI-MISS-FRESHNESS",
                "severity": "medium",
                "reason": "External review history is stale or missing.",
                "required_citation_keys": ["latest_review_id", "latest_age_seconds"],
            }
        )
    return items


def _blocked_claims(external_ai_reliability: dict[str, Any]) -> list[dict[str, Any]]:
    daily = external_ai_reliability.get("verified_daily_data", {})
    if not daily.get("unverified_daily_claims"):
        return []
    return [
        {
            "claim_id": "BLOCKED-DAILY-CLAIM",
            "claim_type": "daily_weekly_htf_context",
            "reason": "External AI mentioned daily/weekly/HTF context without citing verified daily evidence keys.",
            "repair": "Cite multi_timeframe_alignment.timeframes.daily/weekly or remove the claim.",
        }
    ]


def _required_corrections(missing_items: list[dict[str, Any]], blocked_claims: list[dict[str, Any]]) -> list[str]:
    corrections: list[str] = []
    if missing_items:
        corrections.append("Return a corrected review that cites every relevant verified daily/HTF fact and explains low-evidence limits.")
    if blocked_claims:
        corrections.append("Remove or recite daily/weekly/HTF claims with verified Trade Vision citation keys only.")
    corrections.append("Keep final_action within NO_TRADE, WAIT, WATCH_ONLY, or TRADE_VISION_ONLY.")
    corrections.append("Do not raise confidence, create an order, export to OpenAlgo, or override risk/no-trade gates.")
    return corrections


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blockers: list[dict[str, Any]], missing_items: list[dict[str, Any]], blocked_claims: list[dict[str, Any]]) -> str:
    if blockers or blocked_claims:
        return "Verified evidence certificate is blocked for external-AI decision trust; correct unsupported daily/HTF claims first."
    if missing_items:
        return "Verified evidence certificate is display-only; external AI missed required evidence and must be corrected."
    return "Verified evidence certificate is complete for display, but still cannot approve trades or route orders."
