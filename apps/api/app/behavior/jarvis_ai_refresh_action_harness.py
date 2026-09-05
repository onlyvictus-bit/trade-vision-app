from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_AI_REFRESH_ACTION_HARNESS_VERSION = "jarvis-ai-refresh-action-harness.v1.40"


def build_jarvis_ai_refresh_action_harness(
    *,
    symbol: str,
    current_evidence_packet: dict[str, Any],
    refresh_guard: dict[str, Any],
    gemini_bundle: dict[str, Any],
    grok_bundle: dict[str, Any],
    execute_requested: bool = False,
) -> dict[str, Any]:
    evidence_hash = _hash_packet(current_evidence_packet)
    refresh_needed = bool(refresh_guard.get("needs_external_ai_refresh"))
    targets = [target.get("target_id") for target in refresh_guard.get("refresh_targets", [])]
    bundle_hashes_match = (
        gemini_bundle.get("evidence_packet_hash") == evidence_hash
        and grok_bundle.get("evidence_packet_hash") == evidence_hash
    )
    gates = [
        _gate("AIRH-001", "Refresh guard is available", refresh_guard.get("refresh_guard_version") == "jarvis-ai-review-refresh-guard.v1.39", "block", "Run v1.39 refresh guard first."),
        _gate("AIRH-002", "Refresh is needed or explicitly reviewable", refresh_needed or "none" in targets, "downgrade", "No refresh target is active; packet remains operator-review only."),
        _gate("AIRH-003", "Gemini request bundle matches current evidence", gemini_bundle.get("evidence_packet_hash") == evidence_hash, "block", "Gemini refresh bundle must use current Trade Vision evidence."),
        _gate("AIRH-004", "Grok request bundle matches current evidence", grok_bundle.get("evidence_packet_hash") == evidence_hash, "block", "Grok refresh bundle must use current Trade Vision evidence."),
        _gate("AIRH-005", "Both bundles are sanitized", _sanitized(gemini_bundle) and _sanitized(grok_bundle), "block", "No secrets, broker credentials, cookies, or sessions may leave Trade Vision."),
        _gate("AIRH-006", "Network execution remains disabled unless explicitly requested", not execute_requested, "downgrade", "This harness prepares refresh requests; live calls require separate provider gates."),
        _gate("AIRH-007", "No refresh path grants trading authority", _read_only(refresh_guard, gemini_bundle, grok_bundle), "block", "External AI refresh cannot execute, export, or override risk/no-trade."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    harness_state = "blocked" if blockers else "operator_review_ready" if warnings else "refresh_packet_ready"
    packet = {
        "symbol": symbol.upper(),
        "evidence_packet_hash": evidence_hash,
        "refresh_guard_state": refresh_guard.get("refresh_state"),
        "refresh_targets": refresh_guard.get("refresh_targets", []),
        "gemini_request": _provider_request("gemini", gemini_bundle),
        "grok_request": _provider_request("grok", grok_bundle),
        "instructions": [
            "Use only the attached Trade Vision evidence packet.",
            "Return strict JSON only.",
            "If evidence is stale, conflicting, weak, or incomplete, return WAIT or NO_TRADE.",
            "Do not recommend broker routing, OpenAlgo export, live trading, or confidence boost.",
            "Do not invent evidence keys or daily/weekly/HTF context not present in the packet.",
        ],
    }
    packet_hash = _hash_packet(packet)
    return {
        "harness_version": JARVIS_AI_REFRESH_ACTION_HARNESS_VERSION,
        "symbol": symbol.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execute_requested": bool(execute_requested),
        "harness_state": harness_state,
        "current_evidence_packet_hash": evidence_hash,
        "packet_hash": packet_hash,
        "bundle_hashes_match_current": bundle_hashes_match,
        "refresh_needed": refresh_needed,
        "refresh_target_ids": targets,
        "network_call_allowed": False,
        "network_call_performed": False,
        "ready_for_operator_review": not blockers,
        "ready_for_provider_refresh": not blockers and not execute_requested,
        "provider_requests": {
            "gemini": _provider_summary(gemini_bundle),
            "grok": _provider_summary(grok_bundle),
        },
        "refresh_packet_preview": packet,
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message(harness_state, refresh_needed, execute_requested),
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


def _provider_request(provider: str, bundle: dict[str, Any]) -> dict[str, Any]:
    preview = bundle.get("outbound_request_preview", {})
    return {
        "provider": provider,
        "selected_model": bundle.get("selected_model") or preview.get("model"),
        "request_hash": bundle.get("request_hash"),
        "evidence_packet_hash": bundle.get("evidence_packet_hash"),
        "strict_json": preview.get("response_format") == "strict_json",
        "required_fields": preview.get("required_fields", []),
        "allowed_final_actions": preview.get("allowed_final_actions", []),
        "outbound_request_preview": preview,
    }


def _provider_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_version": bundle.get("provider_version"),
        "selected_model": bundle.get("selected_model"),
        "request_hash": bundle.get("request_hash"),
        "evidence_packet_hash": bundle.get("evidence_packet_hash"),
        "dry_run_only": bool(bundle.get("dry_run_only")),
        "network_call_allowed": False,
        "live_call_performed": False,
        "sanitization": bundle.get("sanitization", {}),
    }


def _sanitized(bundle: dict[str, Any]) -> bool:
    sanitization = bundle.get("sanitization", {})
    return (
        sanitization.get("secrets_included") is False
        and sanitization.get("broker_credentials_included") is False
        and sanitization.get("cookies_or_sessions_included") is False
    )


def _read_only(*reports: dict[str, Any]) -> bool:
    fields = (
        "trade_allowed",
        "order_routing_enabled",
        "can_execute_orders",
        "can_export_to_openalgo",
        "can_override_no_trade",
        "can_override_risk",
    )
    for report in reports:
        for field in fields:
            if bool(report.get(field)):
                return False
        if report.get("live_trading_blocked") is False:
            return False
    return True


def _hash_packet(packet: dict[str, Any]) -> str:
    canonical = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(harness_state: str, refresh_needed: bool, execute_requested: bool) -> str:
    if harness_state == "blocked":
        return "External AI refresh packet is blocked; rebuild current evidence and refresh guard first."
    if execute_requested:
        return "Execute was requested, but v1.40 remains a dry-run preparation harness; no network or trade was performed."
    if refresh_needed:
        return "External AI refresh packet is ready for operator review only. It cannot trade, export, or boost confidence."
    return "No refresh is required, but the packet can be reviewed for audit; Trade Vision remains the authority."
