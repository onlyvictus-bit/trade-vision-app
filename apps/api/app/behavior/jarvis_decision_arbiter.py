from __future__ import annotations

import hashlib
import json
from typing import Any


JARVIS_ARBITER_VERSION = "jarvis-decision-arbiter.v0.92"


def build_jarvis_arbiter_output(
    *,
    trade_vision_decision: dict[str, Any],
    gemini_review: dict[str, Any],
    kronos_summary: dict[str, Any],
    openalgo_summary: dict[str, Any],
    safety_summary: dict[str, Any],
    multi_timeframe_alignment: dict[str, Any],
    paper_reality_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tv_action = trade_vision_decision.get("final_trade_decision", "WAIT")
    gemini_action = gemini_review.get("safe_final_action", "TRADE_VISION_ONLY")
    gemini_valid = bool(gemini_review.get("display_allowed")) and bool(gemini_review.get("validation", {}).get("accepted_for_display"))
    reasons: list[str] = []
    gates = _hard_gates(trade_vision_decision, gemini_review, safety_summary, multi_timeframe_alignment, paper_reality_check)
    blocking = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    downgrade = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]

    if blocking:
        final_action = "NO_TRADE"
        arbiter_state = "SAFETY_BLOCK"
        reasons.extend(gate["reason"] for gate in blocking)
    elif tv_action == "NO_TRADE":
        final_action = "NO_TRADE"
        arbiter_state = "TV_NO_TRADE_AUTHORITY"
        reasons.append("Trade Vision says NO_TRADE; external reviewers cannot override it.")
    elif downgrade:
        final_action = "WATCH_ONLY" if tv_action == "WATCH_ONLY" else "WAIT"
        arbiter_state = "DOWNGRADED"
        reasons.extend(gate["reason"] for gate in downgrade)
    elif not gemini_valid:
        final_action = tv_action if tv_action in {"WAIT", "WATCH_ONLY", "NO_TRADE"} else "WAIT"
        arbiter_state = "GEMINI_UNTRUSTED"
        reasons.append("Gemini review is unavailable, invalid, or not accepted for display; use Trade Vision-only guidance.")
    elif _gemini_conflicts(tv_action, gemini_action):
        final_action = "WAIT"
        arbiter_state = "SOFT_CONFLICT"
        reasons.append(f"Gemini safe action {gemini_action} conflicts with Trade Vision action {tv_action}; reduced to WAIT.")
    else:
        final_action = tv_action
        arbiter_state = "ALIGNED_RESEARCH"
        reasons.append("Trade Vision and validated Gemini display are aligned, but result remains research-only.")

    if kronos_summary.get("status") not in {"ready", "mock_ready"}:
        reasons.append("Kronos is unavailable/reserved and cannot boost confidence.")
    else:
        reasons.append("Kronos is advisory only and cannot execute or override risk.")
    if openalgo_summary.get("status") != "ready":
        reasons.append("OpenAlgo execution reality report is not connected; no execution promotion is possible.")
    if paper_reality_check:
        paper_effect = paper_reality_check.get("jarvis_effect", {}).get("effect", "REVIEW_ONLY")
        reasons.append(f"Paper reality check effect is {paper_effect}; it cannot upgrade a trade.")

    payload = {
        "version": JARVIS_ARBITER_VERSION,
        "tv": tv_action,
        "gemini": gemini_action,
        "state": arbiter_state,
        "final": final_action,
        "gates": gates,
        "reasons": reasons,
    }
    arbiter_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "arbiter_version": JARVIS_ARBITER_VERSION,
        "arbiter_state": arbiter_state,
        "final_action": final_action,
        "trade_vision_action": tv_action,
        "gemini_safe_action": gemini_action,
        "gemini_review_accepted": gemini_valid,
        "kronos_status": kronos_summary.get("status", "reserved"),
        "openalgo_status": openalgo_summary.get("status", "reserved"),
        "hard_gates": gates,
        "conflict_reasons": list(dict.fromkeys(reasons)),
        "arbiter_hash": arbiter_hash,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_export_to_openalgo": False,
        "human_approval_required": True,
        "notes": [
            "v0.92 arbitrates Trade Vision, validated Gemini display, Kronos status, OpenAlgo status, and safety gates.",
            "Any conflict reduces action; no advisory engine can promote a blocked setup.",
            "This output cannot create broker orders.",
        ],
    }


def _hard_gates(
    trade_vision_decision: dict[str, Any],
    gemini_review: dict[str, Any],
    safety_summary: dict[str, Any],
    multi_timeframe_alignment: dict[str, Any],
    paper_reality_check: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    blocking_gates = safety_summary.get("blocking_gates", [])
    warning_gates = safety_summary.get("warning_gates", [])
    paper_effect = (paper_reality_check or {}).get("jarvis_effect", {}).get("effect", "REVIEW_ONLY")
    return [
        _gate("JARVIS-ARB-001", "Trade Vision safety has no blocking gate", not bool(blocking_gates), "block", f"blocking_gates={blocking_gates}"),
        _gate("JARVIS-ARB-002", "Order routing disabled", trade_vision_decision.get("order_routing_enabled") is False, "block", "Trade Vision decision must not enable routing."),
        _gate("JARVIS-ARB-003", "Live trading blocked", trade_vision_decision.get("live_trading_blocked") is True, "block", "Live trading must stay blocked."),
        _gate("JARVIS-ARB-004", "Gemini cannot override no-trade", gemini_review.get("can_override_no_trade") is False, "block", "Gemini override flag must be false."),
        _gate("JARVIS-ARB-005", "Gemini cannot override risk", gemini_review.get("can_override_risk") is False, "block", "Gemini risk override flag must be false."),
        _gate("JARVIS-ARB-006", "Gemini display validated", bool(gemini_review.get("validation", {}).get("accepted_for_display")), "downgrade", "Invalid Gemini output forces Trade Vision-only WAIT/WATCH."),
        _gate("JARVIS-ARB-007", "Minimum evidence passed", "MINIMUM_EVIDENCE" not in warning_gates, "downgrade", "Low evidence caps confidence and blocks promotion."),
        _gate("JARVIS-ARB-008", "Multi-timeframe alignment sufficient", float(multi_timeframe_alignment.get("alignment_score", 0.0)) >= 0.5, "downgrade", "Weak alignment reduces action."),
        _gate("JARVIS-ARB-009", "Paper reality check does not downgrade", paper_effect not in {"WAIT", "NO_TRADE"}, "downgrade", f"Paper reality check effect is {paper_effect}."),
    ]


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": passed,
        "effect": effect,
        "reason": reason,
    }


def _gemini_conflicts(tv_action: str, gemini_action: str) -> bool:
    if gemini_action in {"TRADE_VISION_ONLY", tv_action}:
        return False
    if tv_action in {"WAIT", "WATCH_ONLY"} and gemini_action in {"WAIT", "WATCH_ONLY"}:
        return False
    return True
