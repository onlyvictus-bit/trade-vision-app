from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


REVIEW_PREFLIGHT_VERSION = "jarvis-review-preflight-verdict.v1.09"


def build_jarvis_review_preflight_verdict(
    *,
    symbol: str,
    verified_evidence: dict[str, Any],
    external_ai_reliability: dict[str, Any],
    preflight_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Decide what kind of review is allowed before Gemini/Grok/OpenAlgo handoff."""
    gates = _gates(verified_evidence, external_ai_reliability, preflight_evidence)
    blocking = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    correction_review_allowed = bool(verified_evidence.get("evidence_sections")) and bool(verified_evidence.get("allowed_evidence_keys"))
    external_decision_review_allowed = not blocking and external_ai_reliability.get("reliability_state") == "watch_only"
    openalgo_dry_run_review_allowed = (
        external_decision_review_allowed
        and bool(preflight_evidence.get("operator_decision", {}).get("openalgo_dry_run_allowed"))
        and not bool(verified_evidence.get("external_ai_blocked_claims"))
    )
    return {
        "review_preflight_version": REVIEW_PREFLIGHT_VERSION,
        "symbol": symbol.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict_state": "blocked" if blocking else "needs_correction" if warnings else "review_ready_display_only",
        "review_targets": _review_targets(correction_review_allowed, external_decision_review_allowed, openalgo_dry_run_review_allowed),
        "gates": gates,
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "required_before_resubmission": _required_before_resubmission(verified_evidence, external_ai_reliability, blocking, warnings),
        "verified_evidence_summary": {
            "certificate_version": verified_evidence.get("certificate_version"),
            "certificate_state": verified_evidence.get("certificate_state"),
            "allowed_evidence_key_count": len(verified_evidence.get("allowed_evidence_keys", [])),
            "evidence_section_count": len(verified_evidence.get("evidence_sections", [])),
            "missed_item_count": len(verified_evidence.get("external_ai_missed_items", [])),
            "blocked_claim_count": len(verified_evidence.get("external_ai_blocked_claims", [])),
        },
        "external_ai_summary": {
            "reliability_version": external_ai_reliability.get("reliability_version"),
            "reliability_state": external_ai_reliability.get("reliability_state"),
            "disagreement_detected": external_ai_reliability.get("disagreement_detected", False),
            "low_evidence_detected": external_ai_reliability.get("low_evidence_detected", False),
            "stale_review_history": external_ai_reliability.get("stale_review_history", False),
        },
        "preflight_summary": {
            "preflight_version": preflight_evidence.get("preflight_version"),
            "overall_status": preflight_evidence.get("overall_status"),
            "paper_review_allowed": preflight_evidence.get("operator_decision", {}).get("paper_review_allowed", False),
            "openalgo_dry_run_allowed": preflight_evidence.get("operator_decision", {}).get("openalgo_dry_run_allowed", False),
            "live_trading_allowed": False,
        },
        "operator_message": _operator_message(blocking, warnings, correction_review_allowed, openalgo_dry_run_review_allowed),
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _gates(verified_evidence: dict[str, Any], external_ai_reliability: dict[str, Any], preflight_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _gate("REV-PRE-001", "Verified evidence certificate exists", verified_evidence.get("certificate_version") == "jarvis-verified-evidence-certificate.v1.08", "block", "Build v1.08 certificate before review handoff."),
        _gate("REV-PRE-002", "Evidence sections are available", bool(verified_evidence.get("evidence_sections")), "block", "External AI needs citable evidence sections."),
        _gate("REV-PRE-003", "No unsupported daily/HTF claim is present", not bool(verified_evidence.get("external_ai_blocked_claims")), "block", "Correct unsupported daily/weekly/HTF claims first."),
        _gate("REV-PRE-004", "External AI review history is reliable enough", external_ai_reliability.get("reliability_state") == "watch_only", "downgrade", "External AI remains correction-only until reliability warnings clear."),
        _gate("REV-PRE-005", "Preflight evidence pack exists", preflight_evidence.get("preflight_version") == "jarvis-preflight-evidence.v1.01", "block", "Run Jarvis preflight evidence before review handoff."),
        _gate("REV-PRE-006", "OpenAlgo dry-run review is preflight-allowed", bool(preflight_evidence.get("operator_decision", {}).get("openalgo_dry_run_allowed")), "downgrade", "OpenAlgo dry-run review remains blocked until preflight transport gates pass."),
        _gate("REV-PRE-007", "Live trading remains blocked", preflight_evidence.get("operator_decision", {}).get("live_trading_allowed") is False, "block", "Live trading must remain blocked in Trade Vision."),
    ]


def _review_targets(correction_review_allowed: bool, external_decision_review_allowed: bool, openalgo_dry_run_review_allowed: bool) -> list[dict[str, Any]]:
    return [
        _target("gemini_correction_review", correction_review_allowed, "Send verified certificate for corrected JSON review only; no confidence boost."),
        _target("grok_manual_placeholder", correction_review_allowed, "Use same certificate for future Grok/manual review; no hidden browser/session data."),
        _target("external_ai_decision_display", external_decision_review_allowed, "Display external review beside Trade Vision only when reliability gates clear."),
        _target("openalgo_dry_run_review", openalgo_dry_run_review_allowed, "Dry-run review only; no broker order and no export inside Trade Vision."),
        _target("live_trading", False, "Always blocked until a separate live execution production review exists."),
    ]


def _target(target_id: str, allowed: bool, rule: str) -> dict[str, Any]:
    return {
        "target_id": target_id,
        "allowed": bool(allowed),
        "rule": rule,
    }


def _required_before_resubmission(
    verified_evidence: dict[str, Any],
    external_ai_reliability: dict[str, Any],
    blocking: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> list[str]:
    actions: list[str] = []
    actions.extend(verified_evidence.get("required_external_ai_corrections", []))
    if external_ai_reliability.get("disagreement_detected"):
        actions.append("Ask the external reviewer to explain disagreement and return WAIT/NO_TRADE when sources conflict.")
    if external_ai_reliability.get("low_evidence_detected"):
        actions.append("State that similar-history evidence is below threshold and probabilities must stay capped.")
    if external_ai_reliability.get("stale_review_history"):
        actions.append("Refresh external review using the latest verified evidence certificate.")
    for gate in blocking + warnings:
        actions.append(f"{gate['gate_id']}: {gate['reason']}")
    deduped: list[str] = []
    for action in actions:
        if action and action not in deduped:
            deduped.append(action)
    return deduped


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blocking: list[dict[str, Any]], warnings: list[dict[str, Any]], correction_review_allowed: bool, openalgo_dry_run_review_allowed: bool) -> str:
    if blocking:
        return "Review preflight is blocked for decision/display handoff; send only a correction request using verified evidence."
    if warnings:
        return "Review preflight allows correction review only; reliability or OpenAlgo dry-run warnings remain."
    if openalgo_dry_run_review_allowed:
        return "Review preflight is ready for manual dry-run review, but Trade Vision still cannot export or route orders."
    if correction_review_allowed:
        return "Verified correction review is allowed; decision trust and trading remain blocked."
    return "No review handoff is allowed until verified evidence exists."
