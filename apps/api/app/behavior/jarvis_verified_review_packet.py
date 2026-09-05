from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_VERIFIED_REVIEW_PACKET_VERSION = "jarvis-verified-review-packet.v1.45"
SECRET_MARKERS = ("api_key", "apikey", "authorization", "password", "secret", "session", "token", "cookie")


def build_jarvis_verified_review_packet(
    *,
    symbol: str,
    evidence_packet: dict[str, Any],
    gemini_status: dict[str, Any],
    grok_status: dict[str, Any],
    gemini_bundle: dict[str, Any],
    grok_bundle: dict[str, Any],
    review_records: list[dict[str, Any]],
    refresh_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = symbol.upper()
    providers = {
        "gemini": _provider_packet("gemini", gemini_status, gemini_bundle, review_records),
        "grok": _provider_packet("grok", grok_status, grok_bundle, review_records),
    }
    export_packet = {
        "packet_version": JARVIS_VERIFIED_REVIEW_PACKET_VERSION,
        "symbol": normalized,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_packet_hash": _hash_packet(evidence_packet),
        "refresh_packet_hash": refresh_action.get("packet_hash") if isinstance(refresh_action, dict) else None,
        "providers": {
            name: {
                "provider": packet["provider"],
                "provider_status": packet["provider_status"],
                "request_hash": packet["request_hash"],
                "evidence_packet_hash": packet["evidence_packet_hash"],
                "latest_review_id": packet["latest_review_id"],
                "latest_review_status": packet["latest_review_status"],
                "latest_response_packet_hash_matches": packet["latest_response_packet_hash_matches"],
            }
            for name, packet in providers.items()
        },
    }
    secret_scan = _secret_scan({"providers": providers, "export_packet": export_packet})
    gates = [
        _gate("VRP-001", "Gemini packet exists", bool(providers["gemini"]["request_hash"]), "downgrade", "Gemini outbound packet is missing."),
        _gate("VRP-002", "Grok packet exists", bool(providers["grok"]["request_hash"]), "downgrade", "Grok outbound packet is missing."),
        _gate("VRP-003", "No plaintext secrets in verified packet", not secret_scan["secret_like_value_detected"], "block", "Verified packet must not expose secrets."),
        _gate("VRP-004", "No provider can execute or override", _all_read_only(providers), "block", "Provider packet must remain review-only."),
        _gate("VRP-005", "Copy-safe export is hash-bound", bool(export_packet["evidence_packet_hash"]), "block", "Operator export must be bound to evidence hash."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    packet_state = "unsafe_blocked" if blockers else "operator_review_ready" if not warnings else "needs_provider_setup"
    return {
        "verified_packet_version": JARVIS_VERIFIED_REVIEW_PACKET_VERSION,
        "symbol": normalized,
        "generated_at": export_packet["created_at"],
        "packet_state": packet_state,
        "evidence_packet_hash": export_packet["evidence_packet_hash"],
        "refresh_packet_hash": export_packet["refresh_packet_hash"],
        "providers": providers,
        "copy_safe_export_packet": export_packet,
        "copy_safe_export_hash": _hash_packet(export_packet),
        "secret_scan": secret_scan,
        "gates": gates,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "operator_message": _operator_message(packet_state),
        "network_call_allowed": False,
        "network_call_performed": False,
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _provider_packet(provider: str, status: dict[str, Any], bundle: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    provider_records = [record for record in records if str(record.get("source") or "").lower() == provider]
    latest = provider_records[0] if provider_records else None
    latest_accepted = next((record for record in provider_records if record.get("display_allowed")), None)
    latest_rejected = next((record for record in provider_records if not record.get("display_allowed")), None)
    request_preview = bundle.get("outbound_request_preview", {}) if isinstance(bundle.get("outbound_request_preview"), dict) else {}
    return {
        "provider": provider,
        "provider_status": _public_status(provider, status),
        "bundle_version": bundle.get("bundle_version") or bundle.get("provider_version"),
        "request_hash": bundle.get("request_hash"),
        "evidence_packet_hash": bundle.get("evidence_packet_hash"),
        "selected_model": bundle.get("selected_model") or status.get("selected_model"),
        "timeout_ms": bundle.get("timeout_ms") or status.get("timeout_ms"),
        "request_preview": request_preview,
        "request_preview_hash": _hash_packet(request_preview),
        "latest_review_id": latest.get("review_id") if latest else None,
        "latest_review_status": latest.get("intake_status") if latest else "none",
        "latest_accepted_review_id": latest_accepted.get("review_id") if latest_accepted else None,
        "latest_rejected_review_id": latest_rejected.get("review_id") if latest_rejected else None,
        "latest_response_hash": latest.get("candidate_response_hash") if latest else None,
        "latest_response_packet_hash_matches": bool(latest.get("response_packet_hash_matches")) if latest else False,
        "latest_display_allowed": bool(latest.get("display_allowed")) if latest else False,
        "secret_returned_to_frontend": False,
        "network_call_allowed": bool(bundle.get("network_call_allowed")) and False,
        "network_call_performed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _public_status(provider: str, status: dict[str, Any]) -> dict[str, Any]:
    if provider == "gemini":
        return {
            "provider": "gemini",
            "status": status.get("status"),
            "mode": status.get("mode"),
            "selected_model": status.get("selected_model"),
            "configured_key_slots": status.get("configured_key_slots", 0),
            "fallback_key_slots_supported": status.get("fallback_key_slots_supported", 5),
            "active_slot": _active_gemini_slot(status),
            "keys_exposed_to_frontend": False,
        }
    return {
        "provider": "grok",
        "status": status.get("status"),
        "mode": status.get("mode"),
        "selected_model": status.get("selected_model"),
        "api_key_configured": bool(status.get("api_key_configured")),
        "api_url_preview": status.get("api_url_preview"),
        "api_key_exposed_to_frontend": False,
        "passgrok_capture_allowed": False,
    }


def _active_gemini_slot(status: dict[str, Any]) -> int | None:
    for slot in status.get("key_slots", []):
        if slot.get("configured"):
            return int(slot.get("slot"))
    return None


def _all_read_only(providers: dict[str, dict[str, Any]]) -> bool:
    unsafe_fields = ("trade_allowed", "order_routing_enabled", "can_execute_orders", "can_export_to_openalgo", "can_override_no_trade", "can_override_risk")
    return all(not bool(packet.get(field)) for packet in providers.values() for field in unsafe_fields)


def _secret_scan(value: Any) -> dict[str, Any]:
    paths: list[str] = []
    _scan(value, "$", paths)
    return {
        "secret_like_value_detected": bool(paths),
        "secret_like_paths": paths[:20],
        "secret_path_count": len(paths),
    }


def _scan(value: Any, path: str, paths: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower().replace("-", "_")
            child = f"{path}.{key}"
            if any(marker in lowered for marker in SECRET_MARKERS) and isinstance(item, str) and item:
                paths.append(child)
            _scan(item, child, paths)
    elif isinstance(value, list):
        for idx, item in enumerate(value[:50]):
            _scan(item, f"{path}[{idx}]", paths)


def _hash_packet(packet: Any) -> str:
    canonical = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(state: str) -> str:
    if state == "operator_review_ready":
        return "Verified review packet is ready for operator review only; no network call or trade was performed."
    if state == "unsafe_blocked":
        return "Verified review packet is blocked because a safety invariant failed."
    return "Verified review packet is available, but provider setup or response history is incomplete."
