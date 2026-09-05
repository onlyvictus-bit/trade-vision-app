from __future__ import annotations

from typing import Any

from .gemini_provider import build_gemini_live_review_report
from .grok_provider import build_grok_live_review_report


JARVIS_AI_COMPARISON_ROOM_VERSION = "jarvis-ai-comparison-room.v1.37"


async def build_jarvis_ai_comparison_room(
    *,
    symbol: str,
    evidence_packet: dict[str, Any],
    execute_gemini: bool = False,
    execute_grok: bool = False,
) -> dict[str, Any]:
    gemini = await build_gemini_live_review_report(evidence_packet=evidence_packet, execute=execute_gemini)
    grok = await build_grok_live_review_report(evidence_packet=evidence_packet, execute=execute_grok)
    matrix = _agreement_matrix(evidence_packet=evidence_packet, gemini=gemini, grok=grok)
    safe_action = _safe_action(evidence_packet=evidence_packet, matrix=matrix, gemini=gemini, grok=grok)
    gates = [
        _gate("AICR-001", "Both providers used the same evidence packet", gemini.get("evidence_packet_hash") == grok.get("evidence_packet_hash"), "block", "Provider comparison is invalid if evidence differs."),
        _gate("AICR-002", "Gemini cannot execute or override", _cannot_override(gemini), "block", "Gemini is evidence-only."),
        _gate("AICR-003", "Grok cannot execute or override", _cannot_override(grok), "block", "Grok is evidence-only."),
        _gate("AICR-004", "At least one provider produced displayable evidence", matrix["displayable_provider_count"] >= 1, "downgrade", "No external AI can be trusted for display when both are invalid/unavailable."),
        _gate("AICR-005", "External AI did not disagree", matrix["agreement_state"] in {"AGREE", "BOTH_UNAVAILABLE"}, "downgrade", "Disagreement removes any confidence boost and forces wait/review."),
        _gate("AICR-006", "No hallucinated evidence keys", not matrix["hallucinated_evidence_keys"], "block", "Unsupported claims must be discarded."),
        _gate("AICR-007", "No missing required cited evidence", not matrix["missing_core_evidence"], "downgrade", "External AI missed core Trade Vision evidence."),
    ]
    return {
        "comparison_version": JARVIS_AI_COMPARISON_ROOM_VERSION,
        "symbol": symbol.upper(),
        "evidence_packet_hash": gemini.get("evidence_packet_hash") or grok.get("evidence_packet_hash"),
        "execute_requested": {"gemini": bool(execute_gemini), "grok": bool(execute_grok)},
        "gemini": _public_provider_report(gemini),
        "grok": _public_provider_report(grok),
        "agreement_matrix": matrix,
        "safe_final_action": safe_action,
        "confidence_boost_allowed": False,
        "final_interpretation": _final_interpretation(matrix=matrix, safe_action=safe_action),
        "gates": gates,
        "blocking_count": sum(1 for gate in gates if gate["effect"] == "block" and not gate["passed"]),
        "warning_count": sum(1 for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _public_provider_report(report: dict[str, Any]) -> dict[str, Any]:
    intake = report.get("review_intake", {})
    validation = intake.get("validation", {})
    provider = report.get("provider_status", {}).get("provider", "unknown")
    return {
        "provider": provider,
        "status": report.get("provider_status", {}).get("status"),
        "model": report.get("provider_status", {}).get("selected_model"),
        "display_allowed": bool(report.get("display_allowed")),
        "safe_final_action": report.get("safe_final_action"),
        "review_status": report.get("candidate_response", {}).get("review_status"),
        "schema_validation_passed": bool(validation.get("schema_validation_passed")),
        "hallucination_detected": bool(validation.get("hallucination_detected")),
        "hallucinated_evidence_keys": validation.get("hallucinated_evidence_keys", []),
        "missing_fields": validation.get("missing_fields", []),
        "cited_evidence_keys": report.get("candidate_response", {}).get("cited_evidence_keys", []),
        "candidate_response": report.get("candidate_response", {}),
        "review_intake": intake,
        "live_call_performed": bool(report.get("live_call_performed")),
        "raw_response_preview": report.get("raw_response_preview"),
    }


def _agreement_matrix(*, evidence_packet: dict[str, Any], gemini: dict[str, Any], grok: dict[str, Any]) -> dict[str, Any]:
    gemini_public = _public_provider_report(gemini)
    grok_public = _public_provider_report(grok)
    gemini_action = gemini_public["safe_final_action"] or "TRADE_VISION_ONLY"
    grok_action = grok_public["safe_final_action"] or "TRADE_VISION_ONLY"
    displayable = [item for item in (gemini_public, grok_public) if item["display_allowed"]]
    if not displayable:
        agreement = "BOTH_UNAVAILABLE"
    elif gemini_action == grok_action:
        agreement = "AGREE"
    elif gemini_action in {"TRADE_VISION_ONLY"} or grok_action in {"TRADE_VISION_ONLY"}:
        agreement = "SOFT_CONFLICT"
    else:
        agreement = "HARD_CONFLICT"
    hallucinated = sorted(set(gemini_public["hallucinated_evidence_keys"] + grok_public["hallucinated_evidence_keys"]))
    required = _core_evidence_keys(evidence_packet)
    cited = set(str(key) for key in gemini_public["cited_evidence_keys"] + grok_public["cited_evidence_keys"])
    missing_core = sorted(key for key in required if key not in cited)
    return {
        "agreement_state": agreement,
        "gemini_action": gemini_action,
        "grok_action": grok_action,
        "displayable_provider_count": len(displayable),
        "gemini_display_allowed": gemini_public["display_allowed"],
        "grok_display_allowed": grok_public["display_allowed"],
        "hallucinated_evidence_keys": hallucinated,
        "missing_core_evidence": missing_core,
        "external_ai_disagreement_detected": agreement in {"SOFT_CONFLICT", "HARD_CONFLICT"},
        "trade_vision_final_action": evidence_packet.get("final_action") or evidence_packet.get("trade_vision_decision", {}).get("final_trade_decision"),
    }


def _safe_action(*, evidence_packet: dict[str, Any], matrix: dict[str, Any], gemini: dict[str, Any], grok: dict[str, Any]) -> str:
    tv_action = str(matrix.get("trade_vision_final_action") or "WAIT")
    if _trade_vision_blocks(evidence_packet):
        return "NO_TRADE" if tv_action == "NO_TRADE" else "WAIT"
    if matrix["agreement_state"] in {"HARD_CONFLICT", "SOFT_CONFLICT"}:
        return "WAIT"
    if matrix["hallucinated_evidence_keys"]:
        return "TRADE_VISION_ONLY"
    if matrix["displayable_provider_count"] == 0:
        return "TRADE_VISION_ONLY"
    if matrix["agreement_state"] == "AGREE":
        candidate = gemini.get("safe_final_action") if gemini.get("display_allowed") else grok.get("safe_final_action")
        return candidate if candidate in {"NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"} else "WAIT"
    return "TRADE_VISION_ONLY"


def _trade_vision_blocks(packet: dict[str, Any]) -> bool:
    if packet.get("final_action") == "NO_TRADE":
        return True
    if packet.get("trade_vision_decision", {}).get("final_trade_decision") == "NO_TRADE":
        return True
    return bool(packet.get("safety_summary", {}).get("blocking_gates"))


def _core_evidence_keys(packet: dict[str, Any]) -> list[str]:
    core = ["trade_vision_decision", "indicator_snapshot", "safety_summary"]
    if packet.get("candle_structure"):
        core.append("candle_structure")
    if packet.get("multi_timeframe_alignment"):
        core.append("multi_timeframe_alignment")
    if packet.get("similar_history"):
        core.append("similar_history")
    return core


def _cannot_override(report: dict[str, Any]) -> bool:
    for key in ("can_execute_orders", "can_override_no_trade", "can_override_risk", "order_routing_enabled"):
        if key in report and report[key] is not False:
            return False
    return True


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _final_interpretation(*, matrix: dict[str, Any], safe_action: str) -> str:
    if matrix["external_ai_disagreement_detected"]:
        return "Gemini and Grok disagree or one provider is unavailable; Jarvis forces WAIT/Trade Vision-only review."
    if matrix["hallucinated_evidence_keys"]:
        return "At least one external AI cited unsupported evidence; external review is discarded."
    if matrix["displayable_provider_count"] == 0:
        return "No external AI response is displayable; Trade Vision remains the only authority."
    return f"External AI comparison is displayable as research only. Jarvis safe action is {safe_action}."
