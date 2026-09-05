from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from .gemini_provider import REQUIRED_REVIEW_FIELDS, validate_gemini_review_response
from .jarvis_gemini_fallback_readiness import GEMINI_FALLBACK_READINESS_VERSION


GEMINI_LIVE_REVIEW_HARNESS_VERSION = "jarvis-gemini-live-review-harness.v1.19"
GEMINI_GENERATE_CONTENT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


GeminiTransport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def build_gemini_live_review_harness(
    *,
    evidence_packet: dict[str, Any],
    provider_status: dict[str, Any],
    outbound_bundle: dict[str, Any],
    fallback_readiness: dict[str, Any],
    execute: bool = False,
    transport: GeminiTransport | None = None,
) -> dict[str, Any]:
    model = str(provider_status.get("selected_model") or "gemini-3.5-flash")
    endpoint_url = f"{GEMINI_GENERATE_CONTENT_BASE_URL}/{model}:generateContent"
    selected_key = _select_key()
    request_body = _request_body(outbound_bundle)
    gates = _gates(
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        fallback_readiness=fallback_readiness,
        execute=execute,
        selected_key=selected_key,
    )
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    response_payload: dict[str, Any] | None = None
    parsed_review: dict[str, Any] | None = None
    validation = _empty_validation(evidence_packet)
    network_attempted = False
    latency_ms: float | None = None
    error: dict[str, Any] | None = None
    if not blockers:
        network_attempted = True
        started = datetime.now(timezone.utc)
        try:
            response_payload = (transport or _httpx_transport)(
                endpoint_url,
                {"x-goog-api-key": selected_key["value"], "Content-Type": "application/json"},
                request_body,
                float(provider_status.get("timeout_ms") or 2000) / 1000.0,
            )
            latency_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000.0, 3)
            parsed_review = _extract_json_review(response_payload)
            validation = validate_gemini_review_response(evidence_packet, parsed_review)
        except Exception as exc:  # noqa: BLE001 - external API errors must become safe evidence.
            latency_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000.0, 3)
            error = {"type": exc.__class__.__name__, "message": str(exc)[:240]}
    execution_state = _execution_state(execute, blockers, response_payload, validation, error)
    payload_hash = hashlib.sha256(json.dumps(request_body, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "harness_version": GEMINI_LIVE_REVIEW_HARNESS_VERSION,
        "provider": "gemini",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_state": execution_state,
        "execute_requested": bool(execute),
        "live_network_gate_enabled": _live_enabled(),
        "endpoint_url": endpoint_url,
        "endpoint_method": "POST",
        "api_version": "v1beta",
        "selected_model": model,
        "selected_key_slot": selected_key.get("slot"),
        "selected_key_env_name": selected_key.get("env_name"),
        "selected_key_material_exposed": False,
        "request_body_hash": payload_hash,
        "request_body_preview": _request_preview(request_body),
        "network_call_attempted": network_attempted,
        "live_call_performed": bool(response_payload is not None),
        "latency_ms": latency_ms,
        "response_payload_hash": _hash_response(response_payload),
        "parsed_review": parsed_review,
        "response_validation": validation,
        "error": error,
        "fallback_readiness_version": fallback_readiness.get("readiness_version"),
        "gates": gates,
        "operator_message": _operator_message(execution_state, blockers, error),
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _request_body(outbound_bundle: dict[str, Any]) -> dict[str, Any]:
    preview = outbound_bundle.get("outbound_request_preview", {})
    text_payload = json.dumps(
        {
            "system_prompt": preview.get("system_prompt"),
            "required_fields": preview.get("required_fields", sorted(REQUIRED_REVIEW_FIELDS)),
            "allowed_final_actions": preview.get("allowed_final_actions"),
            "evidence_packet": preview.get("evidence_packet", {}),
        },
        sort_keys=True,
        default=str,
    )
    return {
        "contents": [{"role": "user", "parts": [{"text": text_payload}]}],
        "generationConfig": {
            "temperature": 0.0,
            "response_mime_type": "application/json",
        },
    }


def _request_preview(request_body: dict[str, Any]) -> dict[str, Any]:
    text = request_body.get("contents", [{}])[0].get("parts", [{}])[0].get("text", "")
    return {
        "contents_count": len(request_body.get("contents", [])),
        "text_chars": len(text),
        "generationConfig": request_body.get("generationConfig", {}),
        "contains_api_key": False,
    }


def _gates(
    *,
    provider_status: dict[str, Any],
    outbound_bundle: dict[str, Any],
    fallback_readiness: dict[str, Any],
    execute: bool,
    selected_key: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _gate("GEM-LIVE-001", "Fallback readiness report exists", fallback_readiness.get("readiness_version") == GEMINI_FALLBACK_READINESS_VERSION, "block", "Run v1.18 fallback readiness before live review harness."),
        _gate("GEM-LIVE-002", "Fallback readiness has no blockers", fallback_readiness.get("readiness_state") in {"display_ready", "warning"}, "block", "Gemini fallback metadata must be safe before any call."),
        _gate("GEM-LIVE-003", "Execute flag is explicit", bool(execute), "block", "Dry-run endpoint must not call Gemini unless execute=true is explicitly requested."),
        _gate("GEM-LIVE-004", "Backend live network gate is enabled", _live_enabled(), "block", "Set TRADEVISION_GEMINI_ENABLE_LIVE=true only after manual approval."),
        _gate("GEM-LIVE-005", "A backend key slot is configured", bool(selected_key.get("value")), "block", "At least one GEMINI_API_KEY_N backend env var is required."),
        _gate("GEM-LIVE-006", "Provider status is ready", provider_status.get("status") == "ready", "block", "Provider must report ready before live execution."),
        _gate("GEM-LIVE-007", "Outbound bundle is sanitized and schema locked", outbound_bundle.get("dry_run_only") is True and outbound_bundle.get("review_schema_version") == provider_status.get("review_schema_version"), "block", "Use the already sanitized outbound review bundle as source."),
        _gate("GEM-LIVE-008", "No trade authority", _read_only(provider_status, outbound_bundle), "block", "Gemini live review cannot execute, export, or override safety."),
    ]


def _httpx_transport(url: str, headers: dict[str, str], body: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    response = httpx.post(url, headers=headers, json=body, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()


def _extract_json_review(response_payload: dict[str, Any]) -> dict[str, Any]:
    candidates = response_payload.get("candidates", []) if isinstance(response_payload, dict) else []
    if not candidates:
        return {}
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    if not text.strip():
        return {}
    return json.loads(text)


def _select_key() -> dict[str, Any]:
    for idx in range(1, 6):
        value = os.getenv(f"GEMINI_API_KEY_{idx}", "")
        if value:
            return {"slot": idx, "env_name": f"GEMINI_API_KEY_{idx}", "value": value}
    return {"slot": None, "env_name": None, "value": ""}


def _live_enabled() -> bool:
    return os.getenv("TRADEVISION_GEMINI_ENABLE_LIVE", "").strip().lower() == "true"


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


def _execution_state(execute: bool, blockers: list[dict[str, Any]], response_payload: dict[str, Any] | None, validation: dict[str, Any], error: dict[str, Any] | None) -> str:
    if not execute:
        return "dry_run_no_network"
    if blockers:
        return "blocked_before_network"
    if error:
        return "failed_safe_trade_vision_only"
    if response_payload is None:
        return "no_response_trade_vision_only"
    if validation.get("accepted_for_display"):
        return "validated_display_only"
    return "invalid_response_trade_vision_only"


def _hash_response(response_payload: dict[str, Any] | None) -> str | None:
    if response_payload is None:
        return None
    return hashlib.sha256(json.dumps(response_payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _empty_validation(evidence_packet: dict[str, Any]) -> dict[str, Any]:
    return validate_gemini_review_response(evidence_packet, None)


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(execution_state: str, blockers: list[dict[str, Any]], error: dict[str, Any] | None) -> str:
    if execution_state == "dry_run_no_network":
        return "Gemini live review harness is in dry-run mode; no network call was attempted."
    if blockers:
        return "Gemini live review is blocked before network; Trade Vision-only guidance remains active."
    if error:
        return "Gemini live review failed safely; discard response and continue Trade Vision-only."
    if execution_state == "validated_display_only":
        return "Gemini response validated for display only; it cannot approve trades or export orders."
    return "Gemini response is unavailable or invalid; continue Trade Vision-only."
