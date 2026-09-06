"""Jarvis decision quality gate (go/no-go evidence quality, display-only).

Evaluates the assembled evidence bundle for display safety: every flag and
gate below is derived from the sub-reports it receives. Nothing here approves
trading, probability, export, or routing — all of those stay hard False.

Reconstructed 2026-09-04 after the module was found emptied; the full gate
contract (QUAL-001..012, flag ids, version strings) is pinned by tests
(test_api.py v122 quality-gate cases) and by the evidence-assembly caller.
"""

from __future__ import annotations

from typing import Any


QUALITY_GATE_VERSION = "jarvis-decision-quality-gate.v1.22"


def _flag(flag_id: str, severity: str, name: str, repair: str) -> dict[str, Any]:
    return {"flag_id": flag_id, "severity": severity, "name": name, "repair": repair}


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def build_decision_quality_gate_report(
    *,
    symbol: str,
    jarvis_room: dict[str, Any],
    external_ai_reliability: dict[str, Any],
    verified_evidence: dict[str, Any],
    daily_authority: dict[str, Any],
    paper_execution_loop: dict[str, Any],
    openalgo_handoff_gate: dict[str, Any],
) -> dict[str, Any]:
    room = jarvis_room or {}
    reliability = external_ai_reliability or {}
    verified = verified_evidence or {}
    daily = daily_authority or {}
    paper_loop = paper_execution_loop or {}
    handoff = openalgo_handoff_gate or {}

    disagreement = bool(reliability.get("disagreement_detected"))
    low_evidence = bool(reliability.get("low_evidence_detected"))
    stale_history = bool(reliability.get("stale_review_history"))
    blocked_claims = list(verified.get("external_ai_blocked_claims") or [])
    missed_items = list(verified.get("external_ai_missed_items") or [])
    cert_state = str(verified.get("certificate_state", ""))
    claim_requires_citation = bool((verified.get("daily_data_authority") or {}).get("daily_claim_requires_citation"))
    authority_state = str(daily.get("authority_state", ""))
    daily_available = bool(daily.get("daily_available"))
    unexpected_paper_handoff = bool(paper_loop.get("external_executor_handoff_allowed"))
    unexpected_auto_delivery = bool(handoff.get("automatic_delivery_allowed"))

    flags: list[dict[str, Any]] = []
    if disagreement:
        flags.append(_flag("disagreement", "downgrade", "Provider disagreement", "Resolve Gemini/Grok conflict before trusting review"))
    if low_evidence:
        flags.append(_flag("low_evidence", "downgrade", "Low evidence", "More replay"))
    if stale_history:
        flags.append(_flag("stale_review_history", "downgrade", "Stale review history", "Refresh external AI reviews"))
    if blocked_claims or (claim_requires_citation and cert_state != "verified"):
        flags.append(_flag("unverified_daily_claim", "downgrade", "Unverified daily claim", "Cite daily data authority or drop the claim"))
    if unexpected_paper_handoff:
        flags.append(_flag("paper_loop_handoff_unexpected", "block", "Unexpected paper-loop handoff", "Disable external executor handoff"))
    if unexpected_auto_delivery:
        flags.append(_flag("openalgo_auto_delivery_unexpected", "block", "Unexpected OpenAlgo auto delivery", "Disable automatic delivery"))
    if authority_state == "blocked" or not daily_available:
        flags.append(_flag("daily_authority_not_verified", "downgrade", "Daily authority not verified", "Restore daily data authority"))

    gates = [
        _gate("QUAL-001", "All six evidence inputs present",
              all(isinstance(part, dict) for part in (room, reliability, verified, daily, paper_loop, handoff)),
              "block", "Missing evidence input."),
        _gate("QUAL-002", "No external-AI disagreement", not disagreement,
              "downgrade", "Provider disagreement forces manual review."),
        _gate("QUAL-003", "Verified-evidence certificate produced",
              bool(verified.get("certificate_version")), "block", "No certificate to evaluate."),
        _gate("QUAL-004", "Daily authority report produced",
              bool(daily.get("authority_version")), "block", "No daily authority to evaluate."),
        _gate("QUAL-005", "Paper loop report produced",
              bool(paper_loop.get("paper_loop_version")), "block", "No paper loop report to evaluate."),
        _gate("QUAL-006", "OpenAlgo handoff report produced",
              bool(handoff.get("handoff_gate_version")), "block", "No handoff report to evaluate."),
        _gate("QUAL-007", "Reliability report produced",
              bool(reliability.get("reliability_version")), "block", "No reliability report to evaluate."),
        _gate("QUAL-008", "Jarvis room carries the requested symbol",
              str(room.get("symbol", "")).upper() == symbol.upper(), "downgrade", "Room symbol mismatch."),
        _gate("QUAL-009", "No unexpected paper-loop executor handoff",
              not unexpected_paper_handoff, "block", "Unexpected paper-loop handoff."),
        _gate("QUAL-010", "Reliability version is supported",
              str(reliability.get("reliability_version", "")) != "", "block", "Unknown reliability version."),
        _gate("QUAL-011", "No unexpected OpenAlgo auto-delivery",
              not unexpected_auto_delivery, "block", "Unexpected OpenAlgo auto-delivery."),
        _gate("QUAL-012", "Daily authority not blocked",
              authority_state != "blocked", "downgrade", "Daily authority is blocked."),
    ]

    if cert_state == "blocked" or authority_state == "blocked" or blocked_claims or missed_items:
        quality_state = "display_blocked"
    elif disagreement or low_evidence or stale_history or unexpected_paper_handoff or unexpected_auto_delivery:
        quality_state = "manual_review_required"
    else:
        quality_state = "research_review_ready"

    review_display_allowed = quality_state != "display_blocked" and not (
        disagreement or low_evidence or stale_history
    )
    external_ai_display_allowed = review_display_allowed

    return {
        "quality_gate_version": QUALITY_GATE_VERSION,
        "symbol": symbol.upper(),
        "quality_state": quality_state,
        "quality_flags": flags,
        "gates": gates,
        "blocking_count": sum(1 for gate in gates if gate["effect"] == "block" and not gate["passed"]),
        "warning_count": sum(1 for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]),
        "external_ai_quality": {
            "reliability_version": reliability.get(
                "reliability_version", "jarvis-external-ai-consensus-reliability.v1.07"
            ),
            "disagreement_detected": disagreement,
            "low_evidence_detected": low_evidence,
            "stale_review_history": stale_history,
        },
        "verified_evidence_quality": {
            "certificate_version": verified.get(
                "certificate_version", "jarvis-verified-evidence-certificate.v1.08"
            ),
            "certificate_state": cert_state or "unknown",
        },
        "daily_data_quality": {
            "authority_version": daily.get(
                "authority_version", "jarvis-daily-verified-authority.v1.15"
            ),
            "authority_state": authority_state or "unknown",
            "daily_available": daily_available,
        },
        "paper_loop_quality": {
            "paper_loop_version": paper_loop.get(
                "paper_loop_version", "jarvis-paper-execution-loop-gate.v1.21"
            ),
        },
        "openalgo_handoff_quality": {
            "handoff_gate_version": handoff.get(
                "handoff_gate_version", "jarvis-openalgo-handoff-gate.v1.20"
            ),
        },
        "review_display_allowed": review_display_allowed,
        "external_ai_display_allowed": external_ai_display_allowed,
        "decision_trust_allowed": False,
        "confidence_boost_allowed": False,
        "operator_message": (
            "Display blocked: resolve the quality flags first."
            if quality_state == "display_blocked"
            else "Manual review required before trusting external AI content."
            if quality_state == "manual_review_required"
            else "Evidence quality is sufficient for research review."
        ),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "broker_order_created": False,
        "live_trading_blocked": True,
        "can_export_to_openalgo": False,
    }
