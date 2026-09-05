from __future__ import annotations

import hashlib
import json
from typing import Any


JARVIS_DECISION_FUSION_VERSION = "jarvis-decision-fusion.v0.97"


def build_jarvis_decision_fusion(room: dict[str, Any], gemini_status: dict[str, Any]) -> dict[str, Any]:
    """Build an additive, read-only command-room summary from existing Jarvis evidence."""
    decision = room.get("trade_vision_decision", {})
    arbiter = room.get("decision_arbiter", {})
    safety = room.get("safety_summary", {})
    gemini = room.get("gemini_summary", {})
    gemini_review = room.get("gemini_review_summary", {})
    kronos = room.get("kronos_summary", {})
    openalgo = room.get("openalgo_summary", {})
    paper = room.get("paper_reality_check", {})
    chart = room.get("chart_context", {})
    candle = room.get("candle_structure", {})
    indicators = room.get("indicator_snapshot", {})
    similar = room.get("similar_history", {})
    multi_tf = room.get("multi_timeframe_alignment", {})

    evidence_votes = [
        _vote("trade_vision", decision.get("final_trade_decision", "WAIT"), decision.get("confidence_cap_pct", 0), decision.get("reason_tree", [])),
        _vote("gemini", gemini_review.get("safe_final_action", "TRADE_VISION_ONLY"), 0, _gemini_reasons(gemini_review)),
        _vote("kronos", _kronos_vote(kronos), 0, [kronos.get("status", "reserved")]),
        _vote("openalgo_report", _openalgo_vote(openalgo), 0, openalgo.get("warnings", []) + openalgo.get("rejection_reasons", [])),
        _vote("paper_reality", paper.get("jarvis_effect", {}).get("effect", "REVIEW_ONLY"), 0, paper.get("jarvis_effect", {}).get("reasons", [])),
    ]
    safety_gates = _new_minimal_safety_chain(room)
    blocking = [gate for gate in safety_gates if gate["effect"] == "block" and not gate["passed"]]
    downgrade = [gate for gate in safety_gates if gate["effect"] == "downgrade" and not gate["passed"]]
    conflicts = _conflicts(evidence_votes, arbiter, safety_gates)
    wait_for = list(dict.fromkeys((decision.get("wait_for") or []) + _wait_for_from_gates(safety_gates)))
    avoid_if = list(dict.fromkeys((decision.get("avoid_if") or []) + _avoid_if_from_gates(safety_gates)))
    if blocking:
        final_view = "NO_TRADE"
        room_state = "blocked"
    elif downgrade or conflicts:
        final_view = "WAIT"
        room_state = "conflict_or_low_evidence"
    else:
        final_view = arbiter.get("final_action", decision.get("final_trade_decision", "WAIT"))
        room_state = "research_aligned"

    payload = {
        "symbol": room.get("symbol"),
        "timeframe": room.get("timeframe"),
        "final_view": final_view,
        "votes": evidence_votes,
        "safety_gates": safety_gates,
        "conflicts": conflicts,
        "latest_close": chart.get("latest_close"),
        "candle": candle.get("pattern"),
        "indicators": {
            "rsi14": indicators.get("rsi14"),
            "ema_state": indicators.get("ema_state"),
            "vwap_position": indicators.get("vwap_position"),
            "volume_z": indicators.get("volume_z"),
        },
    }
    fusion_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "fusion_version": JARVIS_DECISION_FUSION_VERSION,
        "room_version": room.get("room_version"),
        "symbol": room.get("symbol"),
        "timeframe": room.get("timeframe"),
        "room_state": room_state,
        "final_view": final_view,
        "fusion_hash": fusion_hash,
        "single_panel_purpose": "Combine chart evidence, indicator signals, Gemini review, Kronos prior, OpenAlgo report, paper reality, and safety gates into one read-only decision guide.",
        "chart_and_indicator_focus": {
            "bar_count": chart.get("bar_count", 0),
            "latest_close": chart.get("latest_close"),
            "candle_pattern": candle.get("pattern", "unknown"),
            "body_pct": candle.get("body_pct"),
            "upper_wick_pct": candle.get("upper_wick_pct"),
            "lower_wick_pct": candle.get("lower_wick_pct"),
            "rsi14": indicators.get("rsi14"),
            "ema_state": indicators.get("ema_state"),
            "vwap_position": indicators.get("vwap_position"),
            "volume_z": indicators.get("volume_z"),
            "full_indicator_matrix_status": indicators.get("full_indicator_matrix_status"),
        },
        "engine_votes": evidence_votes,
        "agreement": {
            "arbiter_state": arbiter.get("arbiter_state", "unknown"),
            "trade_vision_action": arbiter.get("trade_vision_action", decision.get("final_trade_decision", "WAIT")),
            "gemini_safe_action": arbiter.get("gemini_safe_action", "TRADE_VISION_ONLY"),
            "kronos_status": kronos.get("status", "reserved"),
            "openalgo_status": openalgo.get("status", "reserved"),
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
        },
        "gemini_fallback": {
            "provider": "gemini",
            "configured_key_slots": gemini_status.get("configured_key_slots", gemini.get("configured_key_slots", 0)),
            "fallback_key_slots_supported": gemini_status.get("fallback_key_slots_supported", gemini.get("fallback_key_slots_supported", 5)),
            "backend_only_keys": gemini_status.get("security", {}).get("backend_only_keys", True),
            "keys_exposed_to_frontend": gemini_status.get("security", {}).get("keys_exposed_to_frontend", False),
            "rotate_on_rate_limit": gemini_status.get("quota_policy", {}).get("rotate_on_rate_limit", True),
            "rotate_on_quota": gemini_status.get("quota_policy", {}).get("rotate_on_quota", True),
            "timeout_ms": gemini_status.get("timeout_ms", gemini.get("timeout_ms", 2000)),
            "live_enabled": gemini_status.get("mode") == "live_enabled_backend_only",
        },
        "safety_gate_chain": safety_gates,
        "decision_guide": {
            "entry_zone": decision.get("best_entry_zone", []),
            "entry_condition": decision.get("entry_condition", "Wait for validated evidence."),
            "stop_loss": decision.get("stop_loss"),
            "target": decision.get("target"),
            "invalidation_level": decision.get("invalidation_level"),
            "risk_reward": decision.get("risk_reward"),
            "wait_for": wait_for,
            "avoid_if": avoid_if,
            "no_trade_reason": decision.get("no_trade_reason") or _first_block_reason(safety_gates),
        },
        "evidence_quality": {
            "data_quality_score": safety.get("data_quality_score"),
            "minimum_evidence_pass": safety.get("minimum_evidence_pass", False),
            "similar_matches": similar.get("matches_used", 0),
            "similar_total_found": similar.get("total_matches_found", 0),
            "multi_timeframe_alignment_score": multi_tf.get("alignment_score", 0.0),
            "paper_reality_effect": paper.get("jarvis_effect", {}).get("effect", "REVIEW_ONLY"),
        },
        "ui_rule": {
            "new_panel_only": True,
            "old_panels_preserved": True,
            "do_not_edit_existing_panel_behavior": True,
            "narrative_read_only": True,
        },
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _vote(engine: str, action: Any, confidence_pct: Any, reasons: list[Any]) -> dict[str, Any]:
    numeric_confidence = float(confidence_pct or 0)
    return {
        "engine": engine,
        "action": str(action or "UNKNOWN"),
        "confidence_pct": round(max(0.0, min(numeric_confidence, 100.0)), 2),
        "reasons": [str(reason) for reason in reasons[:5]],
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _gemini_reasons(review: dict[str, Any]) -> list[str]:
    candidate = review.get("candidate_response", {})
    reasons = []
    if candidate.get("pattern_interpretation"):
        reasons.append(candidate["pattern_interpretation"])
    if candidate.get("risk_warning"):
        reasons.append(candidate["risk_warning"])
    if review.get("validation", {}).get("hallucination_detected"):
        reasons.append("Gemini hallucination validation failed.")
    if not review.get("display_allowed", False):
        reasons.append("Gemini review is not accepted for display.")
    return reasons or ["Gemini remains external review only."]


def _kronos_vote(kronos: dict[str, Any]) -> str:
    status = kronos.get("status", "reserved")
    if status in {"ready", "mock_ready"}:
        return "FORECAST_PRIOR_AVAILABLE"
    return "RESERVED_OR_UNAVAILABLE"


def _openalgo_vote(openalgo: dict[str, Any]) -> str:
    if not openalgo.get("report_available"):
        return "NO_REPORT"
    effect = str(openalgo.get("effect", "REVIEW_ONLY")).upper()
    if "WAIT" in effect or "DOWNGRADE" in effect:
        return "DOWNGRADE_OR_WAIT"
    return "REPORT_EVIDENCE_ONLY"


def _new_minimal_safety_chain(room: dict[str, Any]) -> list[dict[str, Any]]:
    safety = room.get("safety_summary", {})
    gemini = room.get("gemini_summary", {})
    gemini_review = room.get("gemini_review_summary", {})
    kronos = room.get("kronos_summary", {})
    openalgo = room.get("openalgo_summary", {})
    paper = room.get("paper_reality_check", {})
    return [
        _gate("FUSION-001", "Existing Trade Vision safety has no blocking gate", not bool(safety.get("blocking_gates")), "block", "Reuse existing safety blocks; do not duplicate older gates."),
        _gate("FUSION-002", "Gemini has 4 or 5 fallback slots available in backend manager", int(gemini.get("fallback_key_slots_supported", 0)) >= 4, "downgrade", "Gemini fallback must support multiple backend-only API key slots."),
        _gate("FUSION-003", "External engines cannot execute or override risk", _external_engines_read_only(gemini, gemini_review, kronos, openalgo), "block", "Gemini, Kronos, and OpenAlgo report are evidence only."),
        _gate("FUSION-004", "Paper execution reality check does not downgrade", paper.get("jarvis_effect", {}).get("effect") not in {"WAIT", "NO_TRADE"}, "downgrade", "Poor fill, cost, or adjusted R:R keeps the idea in wait/review."),
        _gate("FUSION-005", "Order routing remains disabled in Trade Vision", room.get("order_routing_enabled") is False and room.get("live_trading_blocked") is True, "block", "This project is decision research/safety; OpenAlgo execution is external and later."),
    ]


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _external_engines_read_only(
    gemini: dict[str, Any],
    gemini_review: dict[str, Any],
    kronos: dict[str, Any],
    openalgo: dict[str, Any],
) -> bool:
    flags = [
        gemini.get("can_execute_orders") is not True,
        gemini.get("can_override_no_trade") is not True,
        gemini.get("can_override_risk") is not True,
        gemini_review.get("can_execute_orders") is not True,
        gemini_review.get("can_override_no_trade") is not True,
        gemini_review.get("can_override_risk") is not True,
        kronos.get("can_execute_orders") is not True,
        kronos.get("can_override_no_trade") is not True,
        kronos.get("can_override_risk") is not True,
        openalgo.get("can_execute_orders") is not True,
        openalgo.get("live_broker_routing_in_trade_vision") is not True,
    ]
    return all(flags)


def _conflicts(votes: list[dict[str, Any]], arbiter: dict[str, Any], gates: list[dict[str, Any]]) -> list[str]:
    conflicts = list(arbiter.get("conflict_reasons", []))
    conflicts.extend(gate["reason"] for gate in gates if not gate["passed"])
    actions = {vote["engine"]: vote["action"] for vote in votes}
    if actions.get("trade_vision") == "NO_TRADE" and actions.get("gemini") not in {"NO_TRADE", "TRADE_VISION_ONLY"}:
        conflicts.append("Trade Vision no-trade cannot be upgraded by Gemini.")
    return list(dict.fromkeys(str(conflict) for conflict in conflicts if conflict))


def _wait_for_from_gates(gates: list[dict[str, Any]]) -> list[str]:
    return [f"{gate['gate_id']} must pass: {gate['name']}" for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]


def _avoid_if_from_gates(gates: list[dict[str, Any]]) -> list[str]:
    return [f"{gate['gate_id']} fails: {gate['reason']}" for gate in gates if gate["effect"] == "block" and not gate["passed"]]


def _first_block_reason(gates: list[dict[str, Any]]) -> str | None:
    for gate in gates:
        if gate["effect"] == "block" and not gate["passed"]:
            return gate["reason"]
    return None
