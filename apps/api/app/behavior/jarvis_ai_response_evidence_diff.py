from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .jarvis_ai_refresh_action_harness import _hash_packet


JARVIS_AI_RESPONSE_EVIDENCE_DIFF_VERSION = "jarvis-ai-response-evidence-diff.v1.43"


def build_jarvis_ai_response_evidence_diff(
    *,
    symbol: str,
    evidence_packet: dict[str, Any],
    records: list[dict[str, Any]],
    current_evidence_packet_hash: str | None = None,
) -> dict[str, Any]:
    normalized = symbol.upper()
    evidence_hash = current_evidence_packet_hash or _hash_packet(evidence_packet)
    available_keys = _available_evidence_keys(evidence_packet)
    latest_record = _latest_displayable_record(records, normalized)
    candidate = _candidate(latest_record)
    cited_diffs = _cited_key_diffs(candidate, available_keys, evidence_packet)
    indicator_diffs = _indicator_diffs(candidate, evidence_packet)
    action_diff = _action_diff(candidate, evidence_packet)
    risk_diff = _risk_diff(candidate, evidence_packet)
    stale = _record_hash(latest_record) != evidence_hash if latest_record else True
    conflicts = [item for item in [action_diff, risk_diff] if item["status"] == "conflict"]
    missing = [item for item in cited_diffs + indicator_diffs if item["status"] in {"missing", "unverifiable"}]
    supported = [item for item in cited_diffs + indicator_diffs if item["status"] == "supported"]
    gates = [
        _gate("AIRD-001", "Displayable external AI response exists", latest_record is not None, "downgrade", "No accepted external AI response exists."),
        _gate("AIRD-002", "Response hash matches current evidence", not stale, "downgrade", "External AI response belongs to older evidence."),
        _gate("AIRD-003", "No unsupported cited evidence", not any(item["status"] == "missing" for item in cited_diffs), "downgrade", "External AI cited unavailable evidence."),
        _gate("AIRD-004", "No action conflict with Trade Vision", action_diff["status"] != "conflict", "block", "External AI action conflicts with Trade Vision or safety."),
        _gate("AIRD-005", "No risk conflict", risk_diff["status"] != "conflict", "block", "External AI risk guidance conflicts with safety summary."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    diff_state = "conflict_blocked" if blockers else "needs_review" if warnings else "supported_for_display"
    return {
        "diff_version": JARVIS_AI_RESPONSE_EVIDENCE_DIFF_VERSION,
        "symbol": normalized,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_evidence_packet_hash": evidence_hash,
        "record_review_id": latest_record.get("review_id") if latest_record else None,
        "record_source": latest_record.get("source") if latest_record else None,
        "record_hash_matches_current": not stale,
        "diff_state": diff_state,
        "supported_count": len(supported),
        "missing_count": len(missing),
        "conflict_count": len(conflicts),
        "available_evidence_key_count": len(available_keys),
        "cited_key_diffs": cited_diffs,
        "indicator_diffs": indicator_diffs,
        "action_diff": action_diff,
        "risk_diff": risk_diff,
        "claim_summary": {
            "pattern_interpretation": candidate.get("pattern_interpretation"),
            "entry_guidance": candidate.get("entry_guidance"),
            "risk_warning": candidate.get("risk_warning"),
            "confidence_comment": candidate.get("confidence_comment"),
            "final_action": candidate.get("final_action"),
        },
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message(diff_state),
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


def _latest_displayable_record(records: list[dict[str, Any]], symbol: str) -> dict[str, Any] | None:
    for record in records:
        if str(record.get("symbol", symbol)).upper() != symbol:
            continue
        if bool(record.get("display_allowed")):
            return record
    return None


def _candidate(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    candidate = record.get("sanitized_candidate_response")
    if isinstance(candidate, dict):
        return candidate
    candidate = record.get("candidate_response")
    return candidate if isinstance(candidate, dict) else {}


def _record_hash(record: dict[str, Any] | None) -> str:
    if not record:
        return ""
    return str(record.get("refresh_action_evidence_hash") or record.get("evidence_packet_hash") or "")


def _cited_key_diffs(candidate: dict[str, Any], available_keys: set[str], evidence_packet: dict[str, Any]) -> list[dict[str, Any]]:
    cited = candidate.get("cited_evidence_keys", [])
    if not isinstance(cited, list):
        return [{
            "claim": "cited_evidence_keys",
            "status": "unverifiable",
            "evidence_key": "cited_evidence_keys",
            "evidence_value": None,
            "reason": "External AI did not return a list of cited evidence keys.",
        }]
    diffs: list[dict[str, Any]] = []
    for key in cited:
        evidence_key = str(key)
        status = "supported" if evidence_key in available_keys else "missing"
        diffs.append({
            "claim": "cited evidence",
            "status": status,
            "evidence_key": evidence_key,
            "evidence_value": _lookup_evidence_value(evidence_packet, evidence_key) if status == "supported" else None,
            "reason": "Evidence key was present in Trade Vision packet." if status == "supported" else "Evidence key was not present in Trade Vision packet.",
        })
    return diffs


def _indicator_diffs(candidate: dict[str, Any], evidence_packet: dict[str, Any]) -> list[dict[str, Any]]:
    indicators = evidence_packet.get("indicator_snapshot", {}) if isinstance(evidence_packet.get("indicator_snapshot"), dict) else {}
    requested = candidate.get("best_indicator_for_pattern", [])
    if not isinstance(requested, list):
        return [{
            "claim": "best_indicator_for_pattern",
            "status": "unverifiable",
            "indicator": "best_indicator_for_pattern",
            "evidence_value": None,
            "reason": "External AI did not return a list of indicators.",
        }]
    diffs: list[dict[str, Any]] = []
    for item in requested:
        indicator = str(item)
        if indicator in indicators:
            status = "supported"
            value = indicators.get(indicator)
            reason = "Indicator exists in current Trade Vision snapshot."
        else:
            status = "unverifiable"
            value = None
            reason = "Indicator is not present in current Trade Vision snapshot."
        diffs.append({
            "claim": "best indicator",
            "status": status,
            "indicator": indicator,
            "evidence_value": value,
            "reason": reason,
        })
    return diffs


def _action_diff(candidate: dict[str, Any], evidence_packet: dict[str, Any]) -> dict[str, Any]:
    ai_action = candidate.get("final_action")
    tv_action = (
        evidence_packet.get("trade_vision_decision", {}).get("final_trade_decision")
        if isinstance(evidence_packet.get("trade_vision_decision"), dict)
        else None
    ) or evidence_packet.get("final_action")
    safety = evidence_packet.get("safety_summary", {}) if isinstance(evidence_packet.get("safety_summary"), dict) else {}
    safe_actions = {"NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"}
    conflict = False
    reason = "External AI action is compatible with Trade Vision safety."
    if ai_action not in safe_actions:
        conflict = True
        reason = "External AI action is not a safe display-only action."
    if tv_action == "NO_TRADE" and ai_action not in {"NO_TRADE", "TRADE_VISION_ONLY"}:
        conflict = True
        reason = "Trade Vision says NO_TRADE; external AI cannot recommend a more aggressive action."
    if safety.get("blocking_gates") and ai_action not in {"NO_TRADE", "TRADE_VISION_ONLY"}:
        conflict = True
        reason = "Safety gates are blocking; external AI cannot recommend action."
    return {
        "claim": "final_action",
        "status": "conflict" if conflict else "supported",
        "external_ai_action": ai_action,
        "trade_vision_action": tv_action,
        "reason": reason,
    }


def _risk_diff(candidate: dict[str, Any], evidence_packet: dict[str, Any]) -> dict[str, Any]:
    risk_warning = str(candidate.get("risk_warning") or "")
    safety = evidence_packet.get("safety_summary", {}) if isinstance(evidence_packet.get("safety_summary"), dict) else {}
    blocking = bool(safety.get("blocking_gates"))
    acknowledges_risk = any(token in risk_warning.lower() for token in ("risk", "block", "wait", "no trade", "safety", "avoid"))
    conflict = blocking and not acknowledges_risk
    return {
        "claim": "risk_warning",
        "status": "conflict" if conflict else "supported" if risk_warning else "unverifiable",
        "external_ai_risk_warning": risk_warning,
        "blocking_gates": safety.get("blocking_gates", []),
        "reason": "External AI acknowledged safety/risk constraints." if not conflict else "Safety gates are blocking but external AI risk warning did not acknowledge them.",
    }


def _available_evidence_keys(value: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            keys.add(path)
            keys.add(str(key))
            keys.update(_available_evidence_keys(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value[:20]):
            keys.update(_available_evidence_keys(item, f"{prefix}.{index}" if prefix else str(index)))
    return keys


def _lookup_evidence_value(packet: dict[str, Any], key: str) -> Any:
    if key in packet:
        return packet.get(key)
    current: Any = packet
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(state: str) -> str:
    if state == "supported_for_display":
        return "External AI claims are supported by current Trade Vision evidence for display only."
    if state == "conflict_blocked":
        return "External AI claims conflict with Trade Vision or safety; ignore the external response."
    return "External AI claims need review because evidence is missing, stale, or unverifiable."
