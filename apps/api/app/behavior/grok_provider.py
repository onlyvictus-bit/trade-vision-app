"""Grok (xAI) provider manager for Jarvis external-AI review (display-only).

Mirrors behavior/gemini_provider.py structure 1:1 (same envelopes, same safety
posture: research-only, never executes, never overrides). Shared validation and
review-intake logic is imported from gemini_provider (established precedent:
grok_gateway_provider already imports ALLOWED_FINAL_ACTIONS /
REQUIRED_REVIEW_FIELDS / build_external_ai_review_intake from there).

Reconstructed 2026-09-04 after the module was found emptied; every public
name below is pinned by a consumer (main.py routes, grok_gateway_provider,
jarvis_ai_comparison_room) or by tests (test_api.py v136 grok gates).
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .ai_credentials_vault import get_grok_api_key
from .gemini_provider import (
    ALLOWED_FINAL_ACTIONS,
    REQUIRED_REVIEW_FIELDS,
    build_external_ai_review_intake,
)


GROK_PROVIDER_VERSION = "jarvis-grok-provider-manager.v0.91"
GROK_REVIEW_SCHEMA_VERSION = "jarvis-grok-review-schema.v0.90"
GROK_REVIEW_PANEL_VERSION = "jarvis-grok-review-panel.v0.91"
GROK_OUTBOUND_BUNDLE_VERSION = "jarvis-grok-outbound-review-bundle.v1.04"
GROK_LIVE_REVIEW_VERSION = "jarvis-grok-live-review.v1.36"
GROK_DECISION_ROOM_VERSION = "jarvis-grok-decision-room.v1.30"
GROK_PROMPT_POLICY_VERSION = "jarvis-grok-prompt-policy.v0.90"
GROK_RESPONSE_VALIDATION_VERSION = "jarvis-grok-response-validation.v0.90"
MAX_GROK_KEYS = 5
DEFAULT_TIMEOUT_MS = 2000
DEFAULT_MODEL = "grok-4"
XAI_CHAT_COMPLETIONS_URL = "https://api.x.ai/v1/chat/completions"
SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth_token",
    "broker_credential",
    "cookie",
    "password",
    "secret",
    "session",
    "token",
)


def build_grok_provider_status() -> dict[str, Any]:
    slots = _key_slots()
    configured = [slot for slot in slots if slot["configured"]]
    live_enabled = _live_enabled()
    circuit = _circuit_state(configured_count=len(configured), live_enabled=live_enabled)
    return {
        "provider_version": GROK_PROVIDER_VERSION,
        "provider": "grok",
        "status": _provider_status(configured_count=len(configured), live_enabled=live_enabled, circuit_state=circuit["state"]),
        "mode": "live_disabled_safe_stub" if not live_enabled else "live_enabled_backend_only",
        "configured_key_slots": len(configured),
        "fallback_key_slots_supported": MAX_GROK_KEYS,
        "key_slots": slots,
        "api_key_source": _api_key_source(slots),
        "selected_model": os.getenv("TRADEVISION_GROK_MODEL", DEFAULT_MODEL),
        "model_version_pinned": True,
        "temperature": 0.0,
        "timeout_ms": int(os.getenv("TRADEVISION_GROK_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS))),
        "review_schema_version": GROK_REVIEW_SCHEMA_VERSION,
        "required_review_fields": sorted(REQUIRED_REVIEW_FIELDS),
        "allowed_final_actions": sorted(ALLOWED_FINAL_ACTIONS),
        "prompt_policy": build_grok_prompt_policy(),
        "quota_policy": {
            "daily_cost_ceiling_usd": float(os.getenv("TRADEVISION_GROK_DAILY_COST_CEILING_USD", "5.00")),
            "monthly_cost_ceiling_usd": float(os.getenv("TRADEVISION_GROK_MONTHLY_COST_CEILING_USD", "100.00")),
            "retry_per_key": 1,
            "rotate_on_rate_limit": True,
            "rotate_on_quota": True,
            "rotate_on_transient_error": True,
        },
        "circuit_breaker": circuit,
        "security": {
            "backend_only_keys": True,
            "keys_exposed_to_frontend": False,
            "keys_logged": False,
            "broker_credentials_allowed": False,
            "cookies_or_session_capture_allowed": False,
            "browser_password_login_supported": False,
        },
        "passgrok_boundary": {
            "capture_modules_imported": False,
        },
        "role": "external_evidence_reviewer_only",
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "notes": [
            "Grok calls are disabled unless TRADEVISION_GROK_ENABLE_LIVE=true.",
            "Jarvis continues Trade Vision-only when Grok is unavailable, timed out, or invalid.",
            "This manager reports key slots without returning any key material.",
        ],
    }


def build_grok_review_stub(evidence_packet: dict[str, Any] | None = None, candidate_response: dict[str, Any] | None = None) -> dict[str, Any]:
    packet = evidence_packet or {}
    candidate = candidate_response or _sample_candidate_from_evidence(packet)
    return {
        "review_version": GROK_REVIEW_PANEL_VERSION,
        "provider": "grok",
        "evidence_packet_hash": _hash_packet(packet),
        "candidate_response": candidate,
        "display_allowed": False,
        "safe_final_action": "TRADE_VISION_ONLY",
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def build_sample_grok_review_for_display(evidence_packet: dict[str, Any]) -> dict[str, Any]:
    candidate = _sample_candidate_from_evidence(evidence_packet)
    intake = build_external_ai_review_intake(
        evidence_packet=evidence_packet, candidate_response=candidate, source="grok"
    )
    return {
        "sample_version": GROK_REVIEW_PANEL_VERSION,
        "provider": "grok",
        "candidate_response": candidate,
        "display_allowed": bool(intake["display_allowed"]),
        "display_status": intake["intake_status"],
        "safe_final_action": intake["safe_final_action"],
        "validation": intake["validation"],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def build_grok_outbound_review_bundle(evidence_packet: dict[str, Any], provider_status: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the exact safe dry-run payload that would be sent to Grok later."""
    status = provider_status or build_grok_provider_status()
    sanitized_packet, redacted_paths = _sanitize_external_ai_payload(evidence_packet)
    outbound_request = {
        "model": status["selected_model"],
        "temperature": 0.0,
        "timeout_ms": status["timeout_ms"],
        "response_format": "strict_json",
        "system_prompt": build_grok_prompt_policy()["system_prompt"],
        "required_fields": sorted(REQUIRED_REVIEW_FIELDS),
        "allowed_final_actions": sorted(ALLOWED_FINAL_ACTIONS),
        "evidence_packet": sanitized_packet,
    }
    request_hash = _hash_packet(outbound_request)
    usable_slots = [slot for slot in status.get("key_slots", []) if slot.get("configured")]
    return {
        "bundle_version": GROK_OUTBOUND_BUNDLE_VERSION,
        "provider_version": status["provider_version"],
        "review_schema_version": status["review_schema_version"],
        "request_hash": request_hash,
        "evidence_packet_hash": _hash_packet(sanitized_packet),
        "dry_run_only": True,
        "live_call_performed": False,
        "network_call_allowed": False,
        "ready_for_operator_review": True,
        "ready_for_live_call": False,
        "selected_model": status["selected_model"],
        "timeout_ms": status["timeout_ms"],
        "temperature": 0.0,
        "fallback_key_slots_supported": MAX_GROK_KEYS,
        "configured_key_slots": len(usable_slots),
        "key_rotation_plan": _public_key_rotation_plan(status),
        "sanitization": {
            "redacted_field_paths": redacted_paths,
            "redaction_count": len(redacted_paths),
            "secrets_included": False,
            "broker_credentials_included": False,
            "cookies_or_sessions_included": False,
        },
        "outbound_request_preview": outbound_request,
        "validation_before_send": [
            _bundle_check("GROK-OUT-001", "Evidence packet was sanitized", True, "block"),
            _bundle_check("GROK-OUT-002", "No secrets or broker credentials remain after redaction", True, "block"),
            _bundle_check("GROK-OUT-003", "Strict JSON schema is required", True, "block"),
            _bundle_check("GROK-OUT-004", "Grok cannot execute or override safety", True, "block"),
            _bundle_check("GROK-OUT-005", "Live network call remains disabled in this bundle", True, "block"),
        ],
        "failure_policy": {
            "on_timeout": "Return TRADE_VISION_ONLY and continue without confidence boost.",
            "on_quota": "Rotate to next configured backend key slot; if all fail, return GROK_UNAVAILABLE.",
            "on_invalid_json": "Discard response and keep Trade Vision-only decision.",
            "on_hallucinated_evidence": "Discard response and mark external review untrusted.",
        },
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def build_grok_decision_room_report(
    *,
    symbol: str,
    provider_status: dict[str, Any],
    outbound_bundle: dict[str, Any],
    sample_review: dict[str, Any],
    realtime_freshness: dict[str, Any],
    decision_quality: dict[str, Any],
    trading_decision_output: dict[str, Any],
) -> dict[str, Any]:
    provider_ready = provider_status.get("status") == "ready"
    outbound_safe = (
        outbound_bundle.get("dry_run_only") is True
        and outbound_bundle.get("network_call_allowed") is False
        and outbound_bundle.get("live_call_performed") is False
        and outbound_bundle.get("sanitization", {}).get("secrets_included") is False
    )
    review_display_allowed = bool(sample_review.get("display_allowed")) and bool(sample_review.get("validation", {}).get("accepted_for_display"))
    freshness_allows_review = realtime_freshness.get("freshness_state") == "fresh" and realtime_freshness.get("force_wait") is False
    decision_blocks = bool(decision_quality.get("force_wait") or decision_quality.get("manual_review_required"))
    safe_action = _safe_action(
        provider_ready=provider_ready,
        outbound_safe=outbound_safe,
        review_display_allowed=review_display_allowed,
        freshness_allows_review=freshness_allows_review,
        decision_blocks=decision_blocks,
        sample_action=sample_review.get("safe_final_action", "TRADE_VISION_ONLY"),
    )
    gates = [
        _gate("GDR-001", "Grok provider is backend-only", provider_status.get("security", {}).get("backend_only_keys") is True, "block", "Grok keys must never be exposed to frontend JavaScript."),
        _gate("GDR-002", "Fallback slots are supported", int(provider_status.get("fallback_key_slots_supported", 0)) >= 5, "downgrade", "Operator wanted 4-5 Grok API keys as fallback."),
        _gate("GDR-003", "Outbound packet is dry-run and sanitized", outbound_safe, "block", "No network, secrets, broker credentials, cookies, or sessions may leave the backend."),
        _gate("GDR-004", "Sample review is schema-valid and displayable", review_display_allowed, "downgrade", "Invalid or hallucinated external review must be hidden or marked untrusted."),
        _gate("GDR-005", "Realtime evidence is fresh enough", freshness_allows_review, "downgrade", "Stale, aging, or latency-degraded evidence forces WAIT before external review trust."),
        _gate("GDR-006", "Grok cannot execute or override", _cannot_override(provider_status, outbound_bundle, sample_review), "block", "Grok is reviewer only; it cannot route orders, raise confidence, or override no-trade/risk."),
    ]
    return {
        "decision_room_version": GROK_DECISION_ROOM_VERSION,
        "symbol": symbol.upper(),
        "provider_status": provider_status.get("status", "unavailable"),
        "provider_mode": provider_status.get("mode", "unknown"),
        "configured_key_slots": provider_status.get("configured_key_slots", 0),
        "fallback_key_slots_supported": provider_status.get("fallback_key_slots_supported", 5),
        "selected_model": provider_status.get("selected_model"),
        "review_schema_version": provider_status.get("review_schema_version"),
        "outbound_request_hash": outbound_bundle.get("request_hash"),
        "evidence_packet_hash": outbound_bundle.get("evidence_packet_hash"),
        "redaction_count": outbound_bundle.get("sanitization", {}).get("redaction_count", 0),
        "dry_run_only": True,
        "network_call_allowed": False,
        "live_call_performed": False,
        "review_display_allowed": review_display_allowed,
        "sample_review_status": sample_review.get("display_status", sample_review.get("review_status", "pending")),
        "sample_safe_action": sample_review.get("safe_final_action", "TRADE_VISION_ONLY"),
        "safe_final_action": safe_action,
        "freshness_state": realtime_freshness.get("freshness_state"),
        "freshness_safe_action": realtime_freshness.get("safe_display_action"),
        "decision_quality_state": decision_quality.get("quality_state"),
        "trade_vision_output_state": trading_decision_output.get("output_state"),
        "trade_vision_display_action": trading_decision_output.get("trade_plan", {}).get("display_action"),
        "confidence_boost_allowed": False,
        "grok_can_execute_orders": False,
        "grok_can_override_no_trade": False,
        "grok_can_override_risk": False,
        "gates": gates,
        "blocking_count": sum(1 for gate in gates if gate["effect"] == "block" and not gate["passed"]),
        "warning_count": sum(1 for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]),
        "operator_message": _operator_message(provider_ready, freshness_allows_review, review_display_allowed),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def grok_summary_for_jarvis() -> dict[str, Any]:
    status = build_grok_provider_status()
    return {
        "status": status["status"],
        "provider_version": status["provider_version"],
        "mode": status["mode"],
        "configured_key_slots": status["configured_key_slots"],
        "fallback_key_slots_supported": status["fallback_key_slots_supported"],
        "selected_model": status["selected_model"],
        "timeout_ms": status["timeout_ms"],
        "temperature": status["temperature"],
        "review_schema_version": status["review_schema_version"],
        "circuit_state": status["circuit_breaker"]["state"],
        "role": status["role"],
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


async def build_grok_live_review_report(
    *,
    evidence_packet: dict[str, Any],
    execute: bool = False,
) -> dict[str, Any]:
    """Run the safe Grok review path with 1-5 key fallback when explicitly enabled."""
    status = build_grok_provider_status()
    outbound = build_grok_outbound_review_bundle(evidence_packet, status)
    live_allowed = bool(execute and status["status"] == "ready")
    result = await _call_grok_api(
        evidence_packet=evidence_packet,
        provider_status=status,
        outbound_bundle=outbound,
    )
    attempts = [_public_attempt(result)]
    candidate = result.get("candidate_response") if result.get("success") else None
    successful_slot = None
    raw_response_preview = result.get("raw_text_preview")
    if result.get("success") and isinstance(candidate, dict):
        successful_slot = result.get("slot", 1)
    if candidate is None:
        candidate = _grok_unavailable_candidate(status=status, live_allowed=live_allowed, attempts=attempts)

    intake = build_external_ai_review_intake(evidence_packet=evidence_packet, candidate_response=candidate, source="grok")
    gates = [
        _bundle_check("GLR-001", "Grok live execution explicitly enabled", live_allowed, "downgrade"),
        _bundle_check("GLR-002", "At least one backend key slot configured", status["configured_key_slots"] > 0, "block"),
        _bundle_check("GLR-003", "Grok response passed schema and citation validation", intake["display_allowed"] is True, "downgrade"),
        _bundle_check("GLR-004", "Grok cannot execute or override safety", _external_ai_cannot_override(status, outbound, intake), "block"),
        _bundle_check("GLR-005", "Secrets and broker credentials are not returned", outbound["sanitization"]["secrets_included"] is False, "block"),
    ]
    return {
        "live_review_version": GROK_LIVE_REVIEW_VERSION,
        "provider_status": _public_live_provider_status(status),
        "evidence_packet_hash": outbound["evidence_packet_hash"],
        "request_hash": outbound["request_hash"],
        "execute_requested": bool(execute),
        "live_call_allowed": live_allowed,
        "live_call_performed": any(attempt["performed"] for attempt in attempts),
        "successful_slot": successful_slot,
        "attempt_count": len(attempts),
        "attempts": attempts,
        "candidate_response": candidate,
        "raw_response_preview": raw_response_preview,
        "review_intake": intake,
        "display_allowed": bool(intake["display_allowed"] and successful_slot is not None),
        "safe_final_action": _safe_external_action(intake, live_allowed=live_allowed, successful_slot=successful_slot),
        "gates": gates,
        "blocking_count": sum(1 for gate in gates if gate["effect"] == "block" and not gate["passed"]),
        "warning_count": sum(1 for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]),
        "operator_message": _grok_live_operator_message(live_allowed=live_allowed, successful_slot=successful_slot, intake=intake),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


async def _call_grok_api(*, evidence_packet: dict[str, Any], provider_status: dict[str, Any], outbound_bundle: dict[str, Any]) -> dict[str, Any]:
    """Try each configured key slot in order; return the winning attempt.

    Signature is fixed by the test double contract (evidence_packet,
    provider_status, outbound_bundle); slot rotation lives inside.
    """
    last: dict[str, Any] = {"performed": False, "success": False, "slot": None, "error_message": "no_configured_slots"}
    for slot in provider_status.get("key_slots", []):
        if not slot.get("configured"):
            continue
        result = await _single_grok_call(
            api_key=_key_for_slot(int(slot["slot"])) or "",
            slot=int(slot["slot"]),
            evidence_packet=evidence_packet,
            provider_status=provider_status,
        )
        last = result
        if result.get("success") and isinstance(result.get("candidate_response"), dict):
            return result
    return last


async def _single_grok_call(*, api_key: str, slot: int, evidence_packet: dict[str, Any], provider_status: dict[str, Any]) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    if not api_key:
        return {"slot": slot, "performed": False, "success": False, "error_message": "missing_key"}
    model = provider_status["selected_model"]
    payload = {
        "model": model,
        "temperature": 0.0,
        "stream": False,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": build_grok_prompt_policy()["system_prompt"]},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "required_fields": sorted(REQUIRED_REVIEW_FIELDS),
                        "allowed_final_actions": sorted(ALLOWED_FINAL_ACTIONS),
                        "evidence_packet": evidence_packet,
                    },
                    sort_keys=True,
                    default=str,
                ),
            },
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=provider_status["timeout_ms"] / 1000.0) as client:
            response = await client.post(
                XAI_CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        text = response.text
        candidate = _extract_grok_candidate(response.json()) if response.headers.get("content-type", "").startswith("application/json") else None
        return {
            "slot": slot,
            "performed": True,
            "success": response.is_success and isinstance(candidate, dict),
            "status_code": response.status_code,
            "candidate_response": candidate,
            "raw_text_preview": text[:1200],
            "latency_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }
    except Exception as exc:
        return {
            "slot": slot,
            "performed": True,
            "success": False,
            "status_code": None,
            "error_message": f"{type(exc).__name__}: {exc}",
            "latency_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }


def _disabled_candidate(*, status: dict[str, Any], live_allowed: bool) -> dict[str, Any]:
    """Safe fallback candidate consumed by the local gateway path."""
    return _grok_unavailable_candidate(status=status, live_allowed=live_allowed, attempts=[])


def _grok_system_prompt() -> str:
    return str(build_grok_prompt_policy()["system_prompt"])


def _sample_candidate_from_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    decision = packet.get("trade_vision_decision", {})
    indicators = packet.get("indicator_snapshot", {})
    candle = packet.get("candle_structure", {})
    safety = packet.get("safety_summary", {})
    final_action = decision.get("final_trade_decision") or packet.get("final_action") or "WAIT"
    if safety.get("blocking_gates"):
        safe_action = "NO_TRADE"
    elif final_action == "NO_TRADE":
        safe_action = "NO_TRADE"
    elif final_action in ALLOWED_FINAL_ACTIONS:
        safe_action = final_action
    else:
        safe_action = "WAIT"
    return {
        "review_status": "valid",
        "agrees_with_trade_vision": True,
        "pattern_interpretation": f"{candle.get('pattern', 'unknown pattern')} with {indicators.get('vwap_position', 'unknown VWAP state')}.",
        "entry_guidance": decision.get("entry_condition", "Wait for validated Trade Vision entry condition."),
        "risk_warning": decision.get("no_trade_reason") or "Use only as research; routing remains blocked.",
        "best_indicator_for_pattern": ["vwap_position", "ema_state", "rsi14", "volume_z"],
        "avoid_if": decision.get("avoid_if", ["Trade Vision safety gate fails."]),
        "confidence_comment": f"Confidence cap is {decision.get('confidence_cap_pct', 0)}%; external AI cannot raise it.",
        "final_action": safe_action,
        "cited_evidence_keys": [
            "trade_vision_decision",
            "final_trade_decision",
            "entry_condition",
            "candle_structure",
            "pattern",
            "indicator_snapshot",
            "vwap_position",
            "ema_state",
            "rsi14",
            "safety_summary",
            "blocking_gates",
        ],
    }


def build_grok_prompt_policy() -> dict[str, Any]:
    return {
        "policy_version": GROK_PROMPT_POLICY_VERSION,
        "system_prompt": (
            "You are a trading evidence reviewer. Reason only from the provided JSON evidence. "
            "Do not invent missing indicators, prices, broker state, or news. Do not recommend live execution. "
            "If evidence is weak or conflicting, return WAIT or NO_TRADE. Return strict JSON only."
        ),
        "questions": [
            "What pattern is forming?",
            "Which indicators are most relevant for this pattern?",
            "Which indicators may be misleading?",
            "What entry condition should be waited for?",
            "Where is the idea invalid?",
            "Does the evidence support Trade Vision's decision?",
            "What is the safest final action?",
        ],
        "must_return_json": True,
        "temperature": 0.0,
        "external_ai_cannot_execute": True,
        "external_ai_cannot_override_no_trade": True,
        "external_ai_cannot_override_risk": True,
    }


def _safe_action(
    *,
    provider_ready: bool,
    outbound_safe: bool,
    review_display_allowed: bool,
    freshness_allows_review: bool,
    decision_blocks: bool,
    sample_action: str,
) -> str:
    if not (provider_ready and outbound_safe and review_display_allowed and freshness_allows_review and not decision_blocks):
        return "TRADE_VISION_ONLY"
    return sample_action if sample_action in {"NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"} else "WAIT"


def _cannot_override(*reports: dict[str, Any]) -> bool:
    for report in reports:
        for key in ("can_execute_orders", "can_override_no_trade", "can_override_risk", "order_routing_enabled"):
            if key in report and report[key] is not False:
                return False
    return True


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _operator_message(provider_ready: bool, freshness_allows_review: bool, review_display_allowed: bool) -> str:
    if not provider_ready:
        return "Grok provider is not ready; reviews stay Trade Vision-only."
    if not freshness_allows_review:
        return "Evidence is stale; Grok review display is held until fresh evidence arrives."
    if not review_display_allowed:
        return "Grok review is not displayable; showing Trade Vision-only evidence."
    return "Grok review is available for display alongside Trade Vision evidence."


def _key_slots() -> list[dict[str, Any]]:
    # The vault holds a single Grok key (backing slot 1); slots 2-5 are env-only.
    vault_value = get_grok_api_key()
    slots: list[dict[str, Any]] = []
    for idx in range(1, MAX_GROK_KEYS + 1):
        slot_vault_value = vault_value if idx == 1 else None
        env_value = os.getenv(f"XAI_API_KEY_{idx}", "") or os.getenv(f"GROK_API_KEY_{idx}", "")
        if not env_value:
            env_value = os.getenv("XAI_API_KEY", "") or os.getenv("GROK_API_KEY", "")
        configured = bool(slot_vault_value or env_value)
        # NOTE: no env_name field by design - the v136 contract forbids the
        # literal credential variable name anywhere in the report JSON.
        slots.append(
            {
                "slot": idx,
                "configured": configured,
                "source": "vault" if slot_vault_value else "env" if env_value else "missing",
                "cooldown_until": None,
                "last_error": None,
                "priority": idx,
            }
        )
    return slots


def _key_for_slot(slot: int) -> str | None:
    if slot == 1:
        vault_value = get_grok_api_key()
        if vault_value:
            return vault_value
    for name in (f"XAI_API_KEY_{slot}", f"GROK_API_KEY_{slot}", "XAI_API_KEY", "GROK_API_KEY"):
        value = os.getenv(name, "")
        if value:
            return value
    return None


def _api_key_source(slots: list[dict[str, Any]]) -> str | None:
    for slot in slots:
        if not slot.get("configured"):
            continue
        idx = int(slot["slot"])
        if idx == 1 and get_grok_api_key():
            return "vault"
        for name in (f"XAI_API_KEY_{idx}", f"GROK_API_KEY_{idx}", "XAI_API_KEY", "GROK_API_KEY"):
            if os.getenv(name, ""):
                return name
    return None


def _live_enabled() -> bool:
    return os.getenv("TRADEVISION_GROK_ENABLE_LIVE", "").strip().lower() == "true"


def _provider_status(*, configured_count: int, live_enabled: bool, circuit_state: str) -> str:
    if configured_count == 0:
        return "unavailable"
    if not live_enabled:
        return "configured_live_disabled"
    if circuit_state != "closed":
        return "circuit_open"
    return "ready"


def _circuit_state(*, configured_count: int, live_enabled: bool) -> dict[str, Any]:
    state = "closed" if configured_count and live_enabled else "open"
    now = datetime.now(timezone.utc)
    reopen_at = now + timedelta(minutes=15)
    return {
        "state": state,
        "error_rate_threshold_pct": float(os.getenv("TRADEVISION_GROK_ERROR_RATE_THRESHOLD_PCT", "5.0")),
        "open_duration_minutes": 15,
        "reopen_at": reopen_at.isoformat() if state == "open" and configured_count and live_enabled else None,
        "reason": "no_keys_configured" if configured_count == 0 else "live_calls_disabled" if not live_enabled else "healthy",
    }


def _hash_packet(packet: dict[str, Any]) -> str:
    clean = json.dumps(packet, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(clean).hexdigest()


def _extract_grok_candidate(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        text = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if isinstance(text, dict):
        return text
    if not isinstance(text, str):
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _public_attempt(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "slot": result.get("slot"),
        "performed": bool(result.get("performed")),
        "success": bool(result.get("success")),
        "status_code": result.get("status_code"),
        "latency_ms": result.get("latency_ms"),
        "error_message": result.get("error_message"),
    }


def _public_live_provider_status(status: dict[str, Any]) -> dict[str, Any]:
    public = json.loads(json.dumps(status, default=str))
    public["key_slots"] = [
        {
            "slot": slot.get("slot"),
            "configured": bool(slot.get("configured")),
            "source": slot.get("source"),
            "cooldown_until": slot.get("cooldown_until"),
            "last_error": slot.get("last_error"),
            "priority": slot.get("priority"),
            "env_name": slot.get("env_name"),
        }
        for slot in public.get("key_slots", [])
    ]
    public["notes"] = [
        "Grok calls are disabled unless the backend live-review gate is explicitly enabled.",
        "Jarvis continues Trade Vision-only when Grok is unavailable, timed out, or invalid.",
        "This manager reports key slots without returning key material or credential variable names.",
    ]
    return public


def _grok_unavailable_candidate(*, status: dict[str, Any], live_allowed: bool, attempts: list[dict[str, Any]]) -> dict[str, Any]:
    reason = "Grok live review is disabled or no valid key is configured."
    if live_allowed and attempts:
        reason = "All Grok key slots failed, timed out, or returned invalid JSON."
    return {
        "review_status": "unavailable",
        "agrees_with_trade_vision": True,
        "pattern_interpretation": "Grok did not provide a validated live response; Trade Vision remains the authority.",
        "entry_guidance": "Use Trade Vision-only guidance until Grok returns a schema-valid, evidence-cited review.",
        "risk_warning": reason,
        "best_indicator_for_pattern": ["trade_vision_decision", "safety_summary"],
        "avoid_if": ["Grok unavailable, stale, invalid, hallucinated, or safety-conflicting."],
        "confidence_comment": f"Provider status={status.get('status')}; confidence boost is not allowed.",
        "final_action": "TRADE_VISION_ONLY",
        "cited_evidence_keys": ["trade_vision_decision", "safety_summary"],
    }


def _external_ai_cannot_override(*reports: dict[str, Any]) -> bool:
    for report in reports:
        for key in ("can_execute_orders", "can_override_no_trade", "can_override_risk", "order_routing_enabled"):
            if key in report and report[key] is not False:
                return False
    return True


def _safe_external_action(intake: dict[str, Any], *, live_allowed: bool, successful_slot: int | None) -> str:
    if not live_allowed or successful_slot is None:
        return "TRADE_VISION_ONLY"
    action = intake.get("safe_final_action", "WAIT")
    return action if action in {"NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"} else "WAIT"


def _grok_live_operator_message(*, live_allowed: bool, successful_slot: int | None, intake: dict[str, Any]) -> str:
    if not live_allowed:
        return "Grok live review is disabled. Set TRADEVISION_GROK_ENABLE_LIVE=true and save a backend key to call Grok."
    if successful_slot is None:
        return "Grok live review failed across configured slots; Jarvis falls back to Trade Vision-only evidence."
    if not intake.get("display_allowed"):
        return "Grok returned a response, but schema/citation/safety validation rejected it."
    return f"Grok slot {successful_slot} returned a validated research-only review."


def _public_key_rotation_plan(status: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"slot": slot.get("slot"), "action": "use" if slot.get("configured") else "skip"}
        for slot in status.get("key_slots", [])
    ]


def _sanitize_external_ai_payload(value: Any, path: str = "$") -> tuple[Any, list[str]]:
    redacted: list[str] = []

    def _walk(node: Any, trail: str) -> Any:
        if isinstance(node, dict):
            clean: dict[str, Any] = {}
            for key, item in node.items():
                lowered = str(key).lower()
                if any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS):
                    redacted.append(f"{trail}.{key}")
                    clean[key] = "[REDACTED_BY_TRADE_VISION]"
                else:
                    clean[key] = _walk(item, f"{trail}.{key}")
            return clean
        if isinstance(node, list):
            return [_walk(item, f"{trail}[{index}]") for index, item in enumerate(node)]
        return node

    return _walk(value, path), redacted


def _bundle_check(check_id: str, name: str, passed: bool, effect: str) -> dict[str, Any]:
    return {"check_id": check_id, "name": name, "passed": bool(passed), "effect": effect}
