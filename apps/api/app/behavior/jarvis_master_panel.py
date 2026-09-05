from __future__ import annotations

import hashlib
import json
from typing import Any


JARVIS_MASTER_PANEL_VERSION = "jarvis-master-decision-panel.v1.03"


def build_jarvis_master_panel(
    room: dict[str, Any],
    fusion: dict[str, Any],
    gemini_status: dict[str, Any],
) -> dict[str, Any]:
    """Build the additive all-evidence decision panel without replacing older panels."""
    decision = room.get("trade_vision_decision", {})
    chart = room.get("chart_context", {})
    indicators = room.get("indicator_snapshot", {})
    candle = room.get("candle_structure", {})
    similar = room.get("similar_history", {})
    kronos = room.get("kronos_summary", {})
    openalgo = room.get("openalgo_summary", {})
    paper = room.get("paper_reality_check", {})
    safety = room.get("safety_summary", {})
    arbiter = room.get("decision_arbiter", {})
    packet = room.get("packet_metadata", {})

    evidence_stack = [
        _evidence("trade_vision_behavior", decision.get("final_trade_decision", "WAIT"), decision.get("reason_tree", []), True),
        _evidence("chart_candle_structure", candle.get("pattern", "unknown"), _chart_reasons(chart, candle), True),
        _evidence("indicator_matrix", indicators.get("ema_state", "unknown"), _indicator_reasons(indicators), True),
        _evidence("similar_history_memory", f"{similar.get('matches_used', 0)} matches", _similar_reasons(similar), True),
        _evidence("gemini_review", _gemini_state(gemini_status, room), _gemini_reasons(gemini_status, room), False),
        _evidence("kronos_prior", kronos.get("status", "reserved"), _as_list(kronos.get("notes")) or [kronos.get("status", "reserved")], False),
        _evidence("openalgo_report", openalgo.get("status", "reserved"), _openalgo_reasons(openalgo), False),
        _evidence("paper_reality", paper.get("jarvis_effect", {}).get("effect", "review_only"), paper.get("jarvis_effect", {}).get("reasons", []), False),
    ]
    gates = _minimal_master_gates(room, fusion, gemini_status)
    blocking_gates = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    downgrade_gates = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    conflicts = list(dict.fromkeys(str(item) for item in (fusion.get("agreement", {}).get("conflicts") or []) if item))

    if blocking_gates:
        final_action = "NO_TRADE"
        decision_state = "blocked_by_master_gate"
    elif downgrade_gates or conflicts:
        final_action = "WAIT"
        decision_state = "wait_for_confirmation"
    else:
        final_action = fusion.get("final_view", decision.get("final_trade_decision", "WAIT"))
        decision_state = "research_aligned"

    payload = {
        "symbol": room.get("symbol"),
        "timeframe": room.get("timeframe"),
        "decision_state": decision_state,
        "final_action": final_action,
        "evidence_stack": evidence_stack,
        "gates": gates,
        "conflicts": conflicts,
    }
    panel_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "panel_version": JARVIS_MASTER_PANEL_VERSION,
        "symbol": room.get("symbol"),
        "timeframe": room.get("timeframe"),
        "panel_hash": panel_hash,
        "decision_state": decision_state,
        "final_action": final_action,
        "purpose": "One new Jarvis panel combines Trade Vision behavior evidence, chart/candle/indicator evidence, Gemini review, Kronos prior, OpenAlgo report, paper reality, and only the new/necessary safety gates.",
        "integration_rule": {
            "new_panel_only": True,
            "old_panels_preserved": True,
            "old_code_paths_preserved": True,
            "does_not_replace_existing_fusion_panel": True,
        },
        "chart_decision_focus": {
            "latest_close": chart.get("latest_close"),
            "bar_count": chart.get("bar_count", 0),
            "candle_pattern": candle.get("pattern", "unknown"),
            "body_pct": candle.get("body_pct"),
            "upper_wick_pct": candle.get("upper_wick_pct"),
            "lower_wick_pct": candle.get("lower_wick_pct"),
            "vwap_position": indicators.get("vwap_position"),
            "rsi14": indicators.get("rsi14"),
            "ema_state": indicators.get("ema_state"),
            "volume_z": indicators.get("volume_z"),
        },
        "decision_guide": {
            "entry_zone": decision.get("best_entry_zone", []),
            "entry_condition": decision.get("entry_condition", "Wait for evidence agreement."),
            "target": decision.get("target"),
            "stop_loss": decision.get("stop_loss"),
            "invalidation_level": decision.get("invalidation_level"),
            "risk_reward": decision.get("risk_reward"),
            "wait_for": list(dict.fromkeys((decision.get("wait_for") or []) + _wait_for(gates))),
            "avoid_if": list(dict.fromkeys((decision.get("avoid_if") or []) + _avoid_if(gates))),
            "no_trade_reason": decision.get("no_trade_reason") or _first_failed_gate_reason(gates),
        },
        "evidence_stack": evidence_stack,
        "minimal_safety_gate_chain": gates,
        "engine_agreement": {
            "trade_vision": decision.get("final_trade_decision", "WAIT"),
            "fusion": fusion.get("final_view", "WAIT"),
            "arbiter": arbiter.get("final_action", "WAIT"),
            "gemini": _gemini_state(gemini_status, room),
            "kronos": kronos.get("status", "reserved"),
            "openalgo": openalgo.get("status", "reserved"),
            "conflicts": conflicts,
        },
        "gemini_fallback_policy": {
            "fallback_key_slots_supported": gemini_status.get("fallback_key_slots_supported", 5),
            "configured_key_slots": gemini_status.get("configured_key_slots", 0),
            "backend_only_keys": gemini_status.get("security", {}).get("backend_only_keys", True),
            "keys_exposed_to_frontend": gemini_status.get("security", {}).get("keys_exposed_to_frontend", False),
            "temperature": gemini_status.get("temperature", 0.0),
            "timeout_ms": gemini_status.get("timeout_ms", 2000),
            "on_failure": "Continue Trade Vision-only; never upgrade action because Gemini is unavailable.",
        },
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _evidence(source: str, state: Any, reasons: list[Any], primary: bool) -> dict[str, Any]:
    return {
        "source": source,
        "state": str(state or "unknown"),
        "primary_authority": primary,
        "read_only": True,
        "reasons": [str(reason) for reason in reasons[:5] if reason],
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _minimal_master_gates(room: dict[str, Any], fusion: dict[str, Any], gemini_status: dict[str, Any]) -> list[dict[str, Any]]:
    safety = room.get("safety_summary", {})
    packet = room.get("packet_metadata", {})
    return [
        _gate("MASTER-001", "Existing Trade Vision blocking gates are clear", not bool(safety.get("blocking_gates")), "block", "Reuse the existing safety system; master panel does not duplicate old gates."),
        _gate("MASTER-002", "Gemini has 4 or 5 backend-only fallback key slots", int(gemini_status.get("fallback_key_slots_supported", 0)) >= 4 and gemini_status.get("security", {}).get("backend_only_keys") is True, "downgrade", "Gemini must stay backend-only with multiple fallback slots."),
        _gate("MASTER-003", "External engines are read-only evidence", _external_read_only(room, fusion, gemini_status), "block", "Gemini, Kronos, OpenAlgo, and paper reports cannot execute or override safety."),
        _gate("MASTER-004", "Decision packet is present and bounded", bool(packet.get("packet_id")) and bool(packet.get("valid_until")), "downgrade", "Rebuild the evidence packet when packet metadata is missing or expired."),
        _gate("MASTER-005", "Trade Vision routing remains blocked", room.get("order_routing_enabled") is False and room.get("live_trading_blocked") is True, "block", "Trade Vision stays research/paper-evidence only; live execution belongs outside this app later."),
        _gate("MASTER-006", "Unified fusion did not block the idea", fusion.get("final_view") != "NO_TRADE", "downgrade", "Fusion panel conflict or blocker keeps the decision in WAIT/NO_TRADE."),
    ]


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _external_read_only(room: dict[str, Any], fusion: dict[str, Any], gemini_status: dict[str, Any]) -> bool:
    openalgo = room.get("openalgo_summary", {})
    kronos = room.get("kronos_summary", {})
    return all(
        [
            gemini_status.get("can_execute_orders") is False,
            gemini_status.get("can_override_no_trade") is False,
            gemini_status.get("can_override_risk") is False,
            kronos.get("can_execute_orders") is not True,
            kronos.get("can_override_no_trade") is not True,
            kronos.get("can_override_risk") is not True,
            openalgo.get("can_execute_orders") is not True,
            fusion.get("can_execute_orders") is False,
            fusion.get("can_override_no_trade") is False,
            fusion.get("can_override_risk") is False,
        ]
    )


def _chart_reasons(chart: dict[str, Any], candle: dict[str, Any]) -> list[str]:
    return [
        f"Latest close {chart.get('latest_close', 'unknown')}.",
        f"Candle pattern {candle.get('pattern', 'unknown')}.",
        f"Body {candle.get('body_pct', 'unknown')} / upper wick {candle.get('upper_wick_pct', 'unknown')} / lower wick {candle.get('lower_wick_pct', 'unknown')}.",
    ]


def _indicator_reasons(indicators: dict[str, Any]) -> list[str]:
    return [
        f"VWAP {indicators.get('vwap_position', 'unknown')}.",
        f"EMA state {indicators.get('ema_state', 'unknown')}.",
        f"RSI14 {indicators.get('rsi14', 'unknown')}.",
        f"Volume z {indicators.get('volume_z', 'unknown')}.",
    ]


def _similar_reasons(similar: dict[str, Any]) -> list[str]:
    return [
        f"Matches used {similar.get('matches_used', 0)} of {similar.get('total_matches_found', 0)}.",
        f"Similarity confidence {similar.get('memory_confidence_pct', 'unknown')}%.",
        f"Outcome mix {similar.get('outcome_mix', 'unknown')}.",
    ]


def _gemini_state(gemini_status: dict[str, Any], room: dict[str, Any]) -> str:
    review = room.get("gemini_review_summary", {})
    if review.get("display_allowed"):
        return str(review.get("safe_final_action", "review_available"))
    return str(gemini_status.get("status", "unavailable"))


def _gemini_reasons(gemini_status: dict[str, Any], room: dict[str, Any]) -> list[str]:
    review = room.get("gemini_review_summary", {})
    reasons = []
    if review.get("display_allowed"):
        candidate = review.get("candidate_response", {})
        reasons.extend([candidate.get("pattern_interpretation"), candidate.get("risk_warning")])
    reasons.append(f"{gemini_status.get('configured_key_slots', 0)}/{gemini_status.get('fallback_key_slots_supported', 5)} backend slots configured.")
    reasons.append("Gemini failure falls back to Trade Vision-only.")
    return [str(reason) for reason in reasons if reason]


def _openalgo_reasons(openalgo: dict[str, Any]) -> list[str]:
    return _as_list(openalgo.get("warnings")) + _as_list(openalgo.get("rejection_reasons")) or ["OpenAlgo is imported/report evidence only."]


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value:
        return [value]
    return []


def _wait_for(gates: list[dict[str, Any]]) -> list[str]:
    return [f"{gate['gate_id']} pass: {gate['name']}" for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]


def _avoid_if(gates: list[dict[str, Any]]) -> list[str]:
    return [f"{gate['gate_id']} fails: {gate['reason']}" for gate in gates if gate["effect"] == "block" and not gate["passed"]]


def _first_failed_gate_reason(gates: list[dict[str, Any]]) -> str | None:
    for gate in gates:
        if not gate["passed"]:
            return gate["reason"]
    return None
