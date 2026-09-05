from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


GEMINI_FALLBACK_READINESS_VERSION = "jarvis-gemini-fallback-readiness.v1.18"
FORBIDDEN_KEY_SLOT_FIELDS = {"api_key", "apikey", "key", "value", "secret", "token", "fingerprint", "suffix", "prefix"}


def build_gemini_fallback_readiness_report(
    *,
    provider_status: dict[str, Any],
    outbound_bundle: dict[str, Any],
) -> dict[str, Any]:
    key_slots = provider_status.get("key_slots", []) if isinstance(provider_status.get("key_slots"), list) else []
    forbidden_paths = _forbidden_key_paths(key_slots)
    configured_count = int(provider_status.get("configured_key_slots") or 0)
    supported_slots = int(provider_status.get("fallback_key_slots_supported") or 0)
    gates = _gates(provider_status, outbound_bundle, forbidden_paths, configured_count, supported_slots)
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    redacted_slots = [_public_slot(slot) for slot in key_slots]
    payload = {
        "version": GEMINI_FALLBACK_READINESS_VERSION,
        "provider_version": provider_status.get("provider_version"),
        "bundle_version": outbound_bundle.get("bundle_version"),
        "configured_count": configured_count,
        "supported_slots": supported_slots,
        "gates": gates,
    }
    return {
        "readiness_version": GEMINI_FALLBACK_READINESS_VERSION,
        "provider": "gemini",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "readiness_state": "blocked" if blockers else "warning" if warnings else "display_ready",
        "readiness_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "configured_key_slots": configured_count,
        "fallback_key_slots_supported": supported_slots,
        "configured_slot_count_ok": configured_count <= supported_slots and supported_slots >= 5,
        "backend_only_keys": provider_status.get("security", {}).get("backend_only_keys") is True,
        "keys_exposed_to_frontend": provider_status.get("security", {}).get("keys_exposed_to_frontend") is True,
        "forbidden_key_material_paths": forbidden_paths,
        "public_key_slots": redacted_slots,
        "selected_model": provider_status.get("selected_model"),
        "timeout_ms": provider_status.get("timeout_ms"),
        "temperature": provider_status.get("temperature"),
        "review_schema_version": provider_status.get("review_schema_version"),
        "circuit_state": provider_status.get("circuit_breaker", {}).get("state"),
        "live_call_performed": outbound_bundle.get("live_call_performed") is True,
        "network_call_allowed": outbound_bundle.get("network_call_allowed") is True,
        "dry_run_only": outbound_bundle.get("dry_run_only") is True,
        "rotation_policy": {
            "rotate_on_rate_limit": provider_status.get("quota_policy", {}).get("rotate_on_rate_limit") is True,
            "rotate_on_quota": provider_status.get("quota_policy", {}).get("rotate_on_quota") is True,
            "rotate_on_transient_error": provider_status.get("quota_policy", {}).get("rotate_on_transient_error") is True,
            "retry_per_key": provider_status.get("quota_policy", {}).get("retry_per_key"),
        },
        "failure_policy": outbound_bundle.get("failure_policy", {}),
        "gates": gates,
        "operator_message": _operator_message(blockers, warnings, configured_count),
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _public_slot(slot: dict[str, Any]) -> dict[str, Any]:
    return {
        "slot": slot.get("slot"),
        "env_name": slot.get("env_name"),
        "configured": bool(slot.get("configured")),
        "priority": slot.get("priority"),
        "cooldown_until": slot.get("cooldown_until"),
        "last_error": slot.get("last_error"),
    }


def _forbidden_key_paths(key_slots: list[Any]) -> list[str]:
    paths: list[str] = []
    for idx, slot in enumerate(key_slots):
        if not isinstance(slot, dict):
            continue
        for key in slot.keys():
            if str(key).lower() in FORBIDDEN_KEY_SLOT_FIELDS:
                paths.append(f"key_slots[{idx}].{key}")
    return paths


def _gates(
    provider_status: dict[str, Any],
    outbound_bundle: dict[str, Any],
    forbidden_paths: list[str],
    configured_count: int,
    supported_slots: int,
) -> list[dict[str, Any]]:
    return [
        _gate("GEM-FALLBACK-001", "Five backend fallback slots are supported", supported_slots >= 5, "block", "Gemini fallback must support five backend-only slots."),
        _gate("GEM-FALLBACK-002", "Configured slot count is within supported range", 0 <= configured_count <= supported_slots, "block", "Configured slots cannot exceed fallback capacity."),
        _gate("GEM-FALLBACK-003", "Keys are backend-only", provider_status.get("security", {}).get("backend_only_keys") is True, "block", "Gemini API keys must stay only on the backend."),
        _gate("GEM-FALLBACK-004", "No secret-derived slot metadata is exposed", not forbidden_paths, "block", "Frontend-visible slot metadata must not include derived key identifiers."),
        _gate("GEM-FALLBACK-005", "Live Gemini network call is disabled", outbound_bundle.get("live_call_performed") is False and outbound_bundle.get("network_call_allowed") is False, "block", "Readiness check is dry-run only."),
        _gate("GEM-FALLBACK-006", "Strict JSON schema is locked", bool(provider_status.get("review_schema_version")) and outbound_bundle.get("review_schema_version") == provider_status.get("review_schema_version"), "block", "External AI response schema must be pinned before use."),
        _gate("GEM-FALLBACK-007", "Rotation handles rate limit, quota, and transient failures", _rotation_ok(provider_status), "downgrade", "Fallback should rotate across configured keys on operational failures."),
        _gate("GEM-FALLBACK-008", "No trade authority", _read_only(provider_status, outbound_bundle), "block", "Gemini fallback cannot execute, export, or override risk/no-trade."),
    ]


def _rotation_ok(provider_status: dict[str, Any]) -> bool:
    quota = provider_status.get("quota_policy", {})
    return (
        quota.get("rotate_on_rate_limit") is True
        and quota.get("rotate_on_quota") is True
        and quota.get("rotate_on_transient_error") is True
        and int(quota.get("retry_per_key") or 0) >= 1
    )


def _read_only(provider_status: dict[str, Any], outbound_bundle: dict[str, Any]) -> bool:
    return all(
        [
            provider_status.get("can_execute_orders") is False,
            provider_status.get("can_override_no_trade") is False,
            provider_status.get("can_override_risk") is False,
            outbound_bundle.get("can_execute_orders") is False,
            outbound_bundle.get("can_export_to_openalgo") is False,
            outbound_bundle.get("can_override_no_trade") is False,
            outbound_bundle.get("can_override_risk") is False,
            outbound_bundle.get("trade_allowed") is False,
            outbound_bundle.get("order_routing_enabled") is False,
            outbound_bundle.get("live_trading_blocked") is True,
        ]
    )


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], configured_count: int) -> str:
    if blockers:
        return "Gemini fallback readiness is blocked; keep external AI as dry-run correction review only."
    if warnings:
        return "Gemini fallback is display-safe but operational rotation warnings remain; no network call or trade authority exists."
    if configured_count == 0:
        return "Gemini fallback is structurally safe, but no backend API key slots are configured yet."
    return "Gemini fallback is structurally safe for future dry-run review; it still cannot trade, export, or override safety."
