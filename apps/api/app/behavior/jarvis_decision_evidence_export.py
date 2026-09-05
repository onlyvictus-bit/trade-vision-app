from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_DECISION_EVIDENCE_EXPORT_VERSION = "jarvis-decision-evidence-export.v1.14"


def build_jarvis_decision_evidence_export(
    *,
    room: dict[str, Any],
    fusion: dict[str, Any],
    verified_evidence: dict[str, Any],
    review_preflight: dict[str, Any],
    daily_verified_authority: dict[str, Any],
    external_ai_reliability: dict[str, Any],
    external_ai_audit_integrity: dict[str, Any],
    correction_audit: dict[str, Any],
) -> dict[str, Any]:
    symbol = str(room.get("symbol") or "UNKNOWN").upper()
    timeframe = str(room.get("timeframe") or "unknown")
    generated_at = datetime.now(timezone.utc).isoformat()
    sections = _sections(
        room=room,
        fusion=fusion,
        verified_evidence=verified_evidence,
        review_preflight=review_preflight,
        daily_verified_authority=daily_verified_authority,
        external_ai_reliability=external_ai_reliability,
        external_ai_audit_integrity=external_ai_audit_integrity,
        correction_audit=correction_audit,
    )
    gates = _gates(room, verified_evidence, review_preflight, daily_verified_authority, external_ai_reliability, external_ai_audit_integrity)
    export_payload = {
        "version": JARVIS_DECISION_EVIDENCE_EXPORT_VERSION,
        "symbol": symbol,
        "timeframe": timeframe,
        "packet_id": room.get("packet_metadata", {}).get("packet_id"),
        "final_action": room.get("final_action"),
        "sections": sections,
        "gates": gates,
    }
    export_hash = hashlib.sha256(json.dumps(export_payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    return {
        "export_version": JARVIS_DECISION_EVIDENCE_EXPORT_VERSION,
        "symbol": symbol,
        "timeframe": timeframe,
        "generated_at": generated_at,
        "packet_id": room.get("packet_metadata", {}).get("packet_id"),
        "packet_schema_version": room.get("packet_metadata", {}).get("schema_version"),
        "export_hash": export_hash,
        "download_filename": f"trade_vision_{symbol}_{timeframe}_decision_evidence_{export_hash[:12]}.json",
        "decision_summary": {
            "final_action": room.get("final_action"),
            "trade_vision_decision": room.get("trade_vision_decision", {}).get("final_trade_decision"),
            "arbiter_action": room.get("decision_arbiter", {}).get("final_action"),
            "entry_condition": room.get("trade_vision_decision", {}).get("entry_condition"),
            "risk_warning": room.get("trade_vision_decision", {}).get("risk_warning"),
            "reason": room.get("trade_vision_decision", {}).get("reason"),
        },
        "evidence_sections": sections,
        "section_count": len(sections),
        "gate_count": len(gates),
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "gates": gates,
        "export_state": "blocked" if blockers else "review_packet_ready_with_warnings" if warnings else "review_packet_ready",
        "operator_message": _operator_message(blockers, warnings),
        "review_use_only": True,
        "network_call_performed": False,
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


def _sections(
    *,
    room: dict[str, Any],
    fusion: dict[str, Any],
    verified_evidence: dict[str, Any],
    review_preflight: dict[str, Any],
    daily_verified_authority: dict[str, Any],
    external_ai_reliability: dict[str, Any],
    external_ai_audit_integrity: dict[str, Any],
    correction_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _section("packet_metadata", "Packet Metadata", room.get("packet_metadata", {}), ("packet_id", "schema_version", "created_at", "valid_until")),
        _section("chart_context", "Chart Context", room.get("chart_context", {}), ("latest_price", "bar_count", "entry", "stop_loss", "target")),
        _section("candle_structure", "Current Candle Structure", room.get("candle_structure", {}), ("pattern", "body_pct", "upper_wick_pct", "lower_wick_pct")),
        _section("indicator_snapshot", "Indicator Snapshot", room.get("indicator_snapshot", {}), ("rsi14", "ema_state", "vwap_position", "macd_state", "volume_z")),
        _section("sequential_signals", "Sequential Indicator Signals", {"signals": room.get("sequential_signals", [])}, ("signals",)),
        _section("levels_and_zones", "Levels And Zones", room.get("levels_and_zones", {}), ("nearest_support", "nearest_resistance", "vwap", "level_warning")),
        _section("multi_timeframe_alignment", "Daily/Weekly/HTF Verified Context", room.get("multi_timeframe_alignment", {}), ("timeframes", "alignment_score", "htf_confirmation_available")),
        _section("similar_history", "Similar History And Minimum Evidence", room.get("similar_history", {}), ("matches_used", "minimum_sample_pass", "evidence_quality", "matches")),
        _section("trade_vision_decision", "Trade Vision Decision", room.get("trade_vision_decision", {}), ("final_trade_decision", "entry_condition", "stop_loss", "target", "reason")),
        _section("kronos_summary", "Kronos Forecast Prior", room.get("kronos_summary", {}), ("status", "trend_direction", "forecast_confidence", "can_execute_orders")),
        _section("gemini_external_review", "Gemini/External AI Review", room.get("gemini_review_summary", {}), ("display_status", "safe_final_action", "validation", "candidate_response")),
        _section("openalgo_paper_evidence", "OpenAlgo And Paper Reality Evidence", {"openalgo": room.get("openalgo_summary", {}), "paper_reality": room.get("paper_reality_check", {})}, ("openalgo", "paper_reality")),
        _section("safety_summary", "Safety Summary", room.get("safety_summary", {}), ("overall_status", "gates", "trade_allowed", "live_trading_blocked")),
        _section("decision_arbiter", "Decision Arbiter", room.get("decision_arbiter", {}), ("final_action", "conflict_state", "can_export_to_openalgo", "live_trading_blocked")),
        _section("fusion", "Unified Fusion", fusion, ("fusion_hash", "final_view", "gate_summary", "trade_allowed")),
        _section("verified_evidence", "Verified Evidence Certificate", verified_evidence, ("certificate_version", "certificate_state", "allowed_evidence_keys", "external_ai_blocked_claims")),
        _section("review_preflight", "Review Preflight Verdict", review_preflight, ("review_preflight_version", "verdict_state", "review_targets", "live_trading_blocked")),
        _section("daily_verified_authority", "Daily Verified Data Authority", daily_verified_authority, ("authority_version", "authority_state", "timeframe_records", "citable_evidence_keys")),
        _section("external_ai_reliability", "External AI Reliability Gate", external_ai_reliability, ("reliability_version", "reliability_state", "disagreement_detected", "low_evidence_detected", "stale_review_history")),
        _section("external_ai_audit_integrity", "External AI Audit Integrity", external_ai_audit_integrity, ("integrity_version", "integrity_state", "ledger_empty_warning", "authority_issues")),
        _section("correction_audit", "Correction Response Audit", correction_audit, ("summary_version", "record_count", "accepted_count", "rejected_count", "latest_packet_hash")),
    ]


def _section(section_id: str, name: str, payload: Any, citable_keys: tuple[str, ...]) -> dict[str, Any]:
    payload_dict = payload if isinstance(payload, dict) else {"value": payload}
    payload_hash = hashlib.sha256(json.dumps(payload_dict, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "section_id": section_id,
        "name": name,
        "payload_hash": payload_hash,
        "citable_keys": list(citable_keys),
        "payload": payload_dict,
    }


def _gates(
    room: dict[str, Any],
    verified_evidence: dict[str, Any],
    review_preflight: dict[str, Any],
    daily_verified_authority: dict[str, Any],
    external_ai_reliability: dict[str, Any],
    external_ai_audit_integrity: dict[str, Any],
) -> list[dict[str, Any]]:
    similar = room.get("similar_history", {})
    packet = room.get("packet_metadata", {})
    return [
        _gate("EVID-EXP-001", "Jarvis packet metadata exists", bool(packet.get("packet_id")) and bool(packet.get("valid_until")), "block", "Rebuild Jarvis room before evidence export."),
        _gate("EVID-EXP-002", "Chart and candle evidence included", bool(room.get("chart_context")) and bool(room.get("candle_structure")), "block", "Chart context and candle structure are required."),
        _gate("EVID-EXP-003", "Indicator snapshot included", bool(room.get("indicator_snapshot")), "block", "Indicator snapshot is required for review."),
        _gate("EVID-EXP-004", "Similar-history evidence included", bool(similar), "block", "Similar history is required even when minimum sample fails."),
        _gate("EVID-EXP-005", "Minimum evidence is not overclaimed", similar.get("minimum_sample_pass") is True, "downgrade", "Low evidence must remain visible and cannot become high-confidence guidance."),
        _gate("EVID-EXP-006", "Verified evidence certificate exists", verified_evidence.get("certificate_version") == "jarvis-verified-evidence-certificate.v1.08", "block", "Use v1.08 verified evidence certificate."),
        _gate("EVID-EXP-007", "Review preflight verdict exists", review_preflight.get("review_preflight_version") == "jarvis-review-preflight-verdict.v1.09", "block", "Use v1.09 review preflight."),
        _gate("EVID-EXP-008", "Daily verified authority is tracked", daily_verified_authority.get("authority_version") == "jarvis-daily-verified-authority.v1.15", "block", "Use v1.15 daily verified authority."),
        _gate("EVID-EXP-009", "External AI reliability is tracked", external_ai_reliability.get("reliability_version") == "jarvis-external-ai-consensus-reliability.v1.07", "block", "Use v1.07 external AI reliability gate."),
        _gate("EVID-EXP-010", "External AI audit integrity is tracked", external_ai_audit_integrity.get("integrity_version") == "jarvis-external-ai-audit-integrity.v1.13", "block", "Use v1.13 external AI audit integrity."),
        _gate("EVID-EXP-011", "Only verified daily data can be cited", external_ai_audit_integrity.get("verified_daily_data_policy", {}).get("only_trade_vision_verified_daily_data_allowed") is True and daily_verified_authority.get("closed_candle_only") is True, "block", "Daily/weekly/HTF claims must come from Trade Vision verified evidence."),
        _gate("EVID-EXP-012", "No trading or OpenAlgo export authority", True, "block", "Evidence export is review-only and cannot become an order."),
    ]


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
    if blockers:
        return "Decision evidence export is blocked until required verified evidence sections exist."
    if warnings:
        return "Decision evidence export is ready for review, but low evidence or stale/external-review warnings must stay visible."
    return "Decision evidence export is ready for operator/external-AI review only; no execution or confidence boost is allowed."
