from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .ai_credentials_vault import get_gemini_api_key


GEMINI_PROVIDER_VERSION = "jarvis-gemini-provider-manager.v0.91"
GEMINI_REVIEW_SCHEMA_VERSION = "jarvis-gemini-review-schema.v0.90"
GEMINI_REVIEW_PANEL_VERSION = "jarvis-gemini-review-panel.v0.91"
GEMINI_OUTBOUND_BUNDLE_VERSION = "jarvis-gemini-outbound-review-bundle.v1.04"
EXTERNAL_AI_REVIEW_INTAKE_VERSION = "jarvis-external-ai-review-intake.v1.05"
GEMINI_LIVE_REVIEW_VERSION = "jarvis-gemini-live-review.v1.35"
MAX_GEMINI_KEYS = 5
DEFAULT_TIMEOUT_MS = 2000
DEFAULT_MODEL = "gemini-1.5-pro"
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
REQUIRED_REVIEW_FIELDS = {
    "review_status",
    "agrees_with_trade_vision",
    "pattern_interpretation",
    "entry_guidance",
    "risk_warning",
    "best_indicator_for_pattern",
    "avoid_if",
    "confidence_comment",
    "final_action",
    "cited_evidence_keys",
}
ALLOWED_FINAL_ACTIONS = {"NO_TRADE", "WAIT", "WATCH_ONLY", "PAPER_CANDIDATE", "APPROVAL_REQUIRED", "TRADE_VISION_ONLY"}


def build_gemini_provider_status() -> dict[str, Any]:
    slots = _key_slots()
    configured = [slot for slot in slots if slot["configured"]]
    live_enabled = _live_enabled()
    circuit = _circuit_state(configured_count=len(configured), live_enabled=live_enabled)
    return {
        "provider_version": GEMINI_PROVIDER_VERSION,
        "provider": "gemini",
        "status": _provider_status(configured_count=len(configured), live_enabled=live_enabled, circuit_state=circuit["state"]),
        "mode": "live_disabled_safe_stub" if not live_enabled else "live_enabled_backend_only",
        "configured_key_slots": len(configured),
        "fallback_key_slots_supported": MAX_GEMINI_KEYS,
        "key_slots": slots,
        "selected_model": os.getenv("TRADEVISION_GEMINI_MODEL", DEFAULT_MODEL),
        "model_version_pinned": True,
        "temperature": 0.0,
        "timeout_ms": int(os.getenv("TRADEVISION_GEMINI_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS))),
        "review_schema_version": GEMINI_REVIEW_SCHEMA_VERSION,
        "required_review_fields": sorted(REQUIRED_REVIEW_FIELDS),
        "allowed_final_actions": sorted(ALLOWED_FINAL_ACTIONS),
        "prompt_policy": build_gemini_prompt_policy(),
        "quota_policy": {
            "daily_cost_ceiling_usd": float(os.getenv("TRADEVISION_GEMINI_DAILY_COST_CEILING_USD", "5.00")),
            "monthly_cost_ceiling_usd": float(os.getenv("TRADEVISION_GEMINI_MONTHLY_COST_CEILING_USD", "100.00")),
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
        },
        "role": "external_evidence_reviewer_only",
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "notes": [
            "Gemini calls are disabled unless TRADEVISION_GEMINI_ENABLE_LIVE=true.",
            "Jarvis continues Trade Vision-only when Gemini is unavailable, timed out, or invalid.",
            "This manager reports key slots without returning any key material.",
        ],
    }


def build_gemini_review_stub(evidence_packet: dict[str, Any] | None = None, candidate_response: dict[str, Any] | None = None) -> dict[str, Any]:
    status = build_gemini_provider_status()
    packet_hash = _hash_packet(evidence_packet or {})
    validation = validate_gemini_review_response(evidence_packet or {}, candidate_response) if candidate_response is not None else _empty_validation()
    if status["status"] != "ready":
        return {
            "review_version": f"{GEMINI_PROVIDER_VERSION}.review",
            "review_status": "unavailable",
            "provider_status": status,
            "evidence_packet_hash": packet_hash,
            "agreement_with_trade_vision": "not_evaluated",
            "safe_final_action": "TRADE_VISION_ONLY",
            "validation": validation,
            "hallucination_detected": validation["hallucination_detected"],
            "schema_validation_passed": validation["schema_validation_passed"],
            "can_execute_orders": False,
            "can_override_no_trade": False,
            "can_override_risk": False,
            "reason": "Gemini live calls are disabled or no backend API key slots are configured.",
        }
    return {
        "review_version": f"{GEMINI_PROVIDER_VERSION}.review",
        "review_status": "queued_stub",
        "provider_status": status,
        "evidence_packet_hash": packet_hash,
        "agreement_with_trade_vision": "pending",
        "safe_final_action": "WAIT_FOR_VALIDATED_REVIEW",
        "validation": validation,
        "hallucination_detected": validation["hallucination_detected"],
        "schema_validation_passed": validation["schema_validation_passed"],
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "reason": "Provider is configured, but live Gemini execution remains disabled until request signing, quota control, and production response validation are promoted.",
    }


def build_sample_gemini_review_for_display(evidence_packet: dict[str, Any]) -> dict[str, Any]:
    candidate = _sample_candidate_from_evidence(evidence_packet)
    validation = validate_gemini_review_response(evidence_packet, candidate)
    return {
        "review_panel_version": GEMINI_REVIEW_PANEL_VERSION,
        "review_source": "deterministic_sample_not_live_gemini",
        "candidate_response": candidate,
        "validation": validation,
        "display_allowed": validation["accepted_for_display"],
        "display_status": "validated_sample" if validation["accepted_for_display"] else "rejected_sample",
        "safe_final_action": validation["safe_final_action"],
        "live_gemini_called": False,
        "api_cost_usd": 0.0,
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "notes": [
            "v0.91 renders the Gemini review panel using deterministic sample output.",
            "Live Gemini review remains disabled until API keys, quota, request signing, and response validation are explicitly promoted.",
            "The sample response must pass the same schema and hallucination checks as future live responses.",
        ],
    }


def build_gemini_outbound_review_bundle(evidence_packet: dict[str, Any], provider_status: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the exact safe dry-run payload that would be sent to Gemini later."""
    status = provider_status or build_gemini_provider_status()
    sanitized_packet, redacted_paths = _sanitize_external_ai_payload(evidence_packet)
    outbound_request = {
        "model": status["selected_model"],
        "temperature": 0.0,
        "timeout_ms": status["timeout_ms"],
        "response_format": "strict_json",
        "system_prompt": build_gemini_prompt_policy()["system_prompt"],
        "required_fields": sorted(REQUIRED_REVIEW_FIELDS),
        "allowed_final_actions": sorted(ALLOWED_FINAL_ACTIONS),
        "evidence_packet": sanitized_packet,
    }
    request_hash = _hash_packet(outbound_request)
    usable_slots = [slot for slot in status.get("key_slots", []) if slot.get("configured")]
    return {
        "bundle_version": GEMINI_OUTBOUND_BUNDLE_VERSION,
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
        "fallback_key_slots_supported": MAX_GEMINI_KEYS,
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
            _bundle_check("GEMINI-OUT-001", "Evidence packet was sanitized", True, "block"),
            _bundle_check("GEMINI-OUT-002", "No secrets or broker credentials remain after redaction", True, "block"),
            _bundle_check("GEMINI-OUT-003", "Strict JSON schema is required", True, "block"),
            _bundle_check("GEMINI-OUT-004", "Gemini cannot execute or override safety", True, "block"),
            _bundle_check("GEMINI-OUT-005", "Live network call remains disabled in this bundle", True, "block"),
        ],
        "failure_policy": {
            "on_timeout": "Return TRADE_VISION_ONLY and continue without confidence boost.",
            "on_quota": "Rotate to next configured backend key slot; if all fail, return GEMINI_UNAVAILABLE.",
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


def build_external_ai_review_intake(
    evidence_packet: dict[str, Any],
    candidate_response: dict[str, Any],
    source: str = "gemini",
) -> dict[str, Any]:
    """Validate external AI output before it can be displayed as Jarvis evidence."""
    normalized_source = source.strip().lower() if source else "manual"
    if normalized_source not in {"gemini", "grok", "manual"}:
        normalized_source = "manual"
    sanitized_response, redacted_paths = _sanitize_external_ai_payload(candidate_response)
    validation = validate_gemini_review_response(evidence_packet, sanitized_response if isinstance(sanitized_response, dict) else {})
    accepted = bool(validation["accepted_for_display"])
    final_action = sanitized_response.get("final_action") if isinstance(sanitized_response, dict) else "TRADE_VISION_ONLY"
    if not accepted:
        safe_action = "TRADE_VISION_ONLY"
        intake_status = "rejected"
    elif final_action in {"NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"}:
        safe_action = final_action
        intake_status = "accepted_for_display"
    else:
        safe_action = "WAIT"
        intake_status = "downgraded_to_wait"
    return {
        "intake_version": EXTERNAL_AI_REVIEW_INTAKE_VERSION,
        "source": normalized_source,
        "review_schema_version": GEMINI_REVIEW_SCHEMA_VERSION,
        "evidence_packet_hash": _hash_packet(evidence_packet),
        "candidate_response_hash": _hash_packet(sanitized_response if isinstance(sanitized_response, dict) else {"response": sanitized_response}),
        "intake_status": intake_status,
        "display_allowed": accepted,
        "safe_final_action": safe_action,
        "sanitized_candidate_response": sanitized_response,
        "validation": validation,
        "sanitization": {
            "redacted_field_paths": redacted_paths,
            "redaction_count": len(redacted_paths),
            "secrets_included": False,
            "broker_credentials_included": False,
            "cookies_or_sessions_included": False,
        },
        "jarvis_effect": _external_ai_jarvis_effect(accepted=accepted, safe_action=safe_action, validation=validation),
        "binding": {
            "must_match_evidence_packet": True,
            "schema_locked": True,
            "hallucinated_evidence_rejected": True,
            "unsafe_override_rejected": True,
        },
        "allowed_sources": ["gemini", "grok", "manual"],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def build_external_ai_review_sample(evidence_packet: dict[str, Any], source: str = "gemini") -> dict[str, Any]:
    candidate = _sample_candidate_from_evidence(evidence_packet)
    return build_external_ai_review_intake(evidence_packet=evidence_packet, candidate_response=candidate, source=source)


def gemini_summary_for_jarvis() -> dict[str, Any]:
    status = build_gemini_provider_status()
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


async def build_gemini_live_review_report(
    *,
    evidence_packet: dict[str, Any],
    execute: bool = False,
) -> dict[str, Any]:
    """Run the safe Gemini review path with 1-5 key fallback when explicitly enabled."""
    status = build_gemini_provider_status()
    outbound = build_gemini_outbound_review_bundle(evidence_packet, status)
    live_allowed = bool(execute and status["status"] == "ready")
    attempts: list[dict[str, Any]] = []
    candidate: dict[str, Any] | None = None
    successful_slot: int | None = None
    raw_response_preview: str | None = None

    if live_allowed:
        for slot in status["key_slots"]:
            if not slot.get("configured"):
                continue
            result = await _call_gemini_api(
                api_key=_key_for_slot(int(slot["slot"])) or "",
                slot=int(slot["slot"]),
                evidence_packet=evidence_packet,
                provider_status=status,
            )
            attempts.append(_public_attempt(result))
            if result.get("success") and isinstance(result.get("candidate_response"), dict):
                candidate = result["candidate_response"]
                successful_slot = int(slot["slot"])
                raw_response_preview = result.get("raw_text_preview")
                break
    if candidate is None:
        candidate = _gemini_unavailable_candidate(status=status, live_allowed=live_allowed, attempts=attempts)

    intake = build_external_ai_review_intake(evidence_packet=evidence_packet, candidate_response=candidate, source="gemini")
    gates = [
        _bundle_check("GLR-001", "Gemini live execution explicitly enabled", live_allowed, "downgrade"),
        _bundle_check("GLR-002", "At least one backend key slot configured", status["configured_key_slots"] > 0, "block"),
        _bundle_check("GLR-003", "Gemini response passed schema and citation validation", intake["display_allowed"] is True, "downgrade"),
        _bundle_check("GLR-004", "Gemini cannot execute or override safety", _external_ai_cannot_override(status, outbound, intake), "block"),
        _bundle_check("GLR-005", "Secrets and broker credentials are not returned", outbound["sanitization"]["secrets_included"] is False, "block"),
    ]
    return {
        "live_review_version": GEMINI_LIVE_REVIEW_VERSION,
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
        "operator_message": _gemini_live_operator_message(live_allowed=live_allowed, successful_slot=successful_slot, intake=intake),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


async def _call_gemini_api(*, api_key: str, slot: int, evidence_packet: dict[str, Any], provider_status: dict[str, Any]) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    if not api_key:
        return {"slot": slot, "performed": False, "success": False, "error_message": "missing_key"}
    model = provider_status["selected_model"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": build_gemini_prompt_policy()["system_prompt"]}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": json.dumps(
                            {
                                "required_fields": sorted(REQUIRED_REVIEW_FIELDS),
                                "allowed_final_actions": sorted(ALLOWED_FINAL_ACTIONS),
                                "evidence_packet": evidence_packet,
                            },
                            sort_keys=True,
                            default=str,
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "response_mime_type": "application/json",
        },
    }
    try:
        async with httpx.AsyncClient(timeout=provider_status["timeout_ms"] / 1000.0) as client:
            response = await client.post(url, params={"key": api_key}, json=payload)
        text = response.text
        candidate = _extract_gemini_candidate(response.json()) if response.headers.get("content-type", "").startswith("application/json") else None
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


def build_gemini_prompt_policy() -> dict[str, Any]:
    return {
        "policy_version": "jarvis-gemini-prompt-policy.v0.90",
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


def validate_gemini_review_response(evidence_packet: dict[str, Any], candidate_response: dict[str, Any] | None) -> dict[str, Any]:
    if candidate_response is None:
        return _empty_validation()
    missing_fields = sorted(REQUIRED_REVIEW_FIELDS.difference(candidate_response.keys()))
    wrong_types: list[str] = []
    if not isinstance(candidate_response.get("best_indicator_for_pattern"), list):
        wrong_types.append("best_indicator_for_pattern must be a list")
    if not isinstance(candidate_response.get("avoid_if"), list):
        wrong_types.append("avoid_if must be a list")
    if not isinstance(candidate_response.get("cited_evidence_keys"), list):
        wrong_types.append("cited_evidence_keys must be a list")
    if candidate_response.get("final_action") not in ALLOWED_FINAL_ACTIONS:
        wrong_types.append("final_action is not an allowed safe action")
    cited = candidate_response.get("cited_evidence_keys", [])
    available = _available_evidence_keys(evidence_packet)
    hallucinated_keys = sorted(str(key) for key in cited if str(key) not in available) if isinstance(cited, list) else []
    unsafe_override = _unsafe_override_attempt(evidence_packet, candidate_response)
    schema_passed = not missing_fields and not wrong_types and not unsafe_override
    hallucination = bool(hallucinated_keys)
    return {
        "validation_version": "jarvis-gemini-response-validation.v0.90",
        "schema_validation_passed": schema_passed,
        "hallucination_detected": hallucination,
        "missing_fields": missing_fields,
        "wrong_types": wrong_types,
        "available_evidence_keys": sorted(available),
        "hallucinated_evidence_keys": hallucinated_keys,
        "unsafe_override_attempted": unsafe_override,
        "accepted_for_display": schema_passed and not hallucination,
        "safe_final_action": "WAIT" if schema_passed and not hallucination else "TRADE_VISION_ONLY",
    }


def _empty_validation() -> dict[str, Any]:
    return {
        "validation_version": "jarvis-gemini-response-validation.v0.90",
        "schema_validation_passed": False,
        "hallucination_detected": False,
        "missing_fields": sorted(REQUIRED_REVIEW_FIELDS),
        "wrong_types": [],
        "available_evidence_keys": [],
        "hallucinated_evidence_keys": [],
        "unsafe_override_attempted": False,
        "accepted_for_display": False,
        "safe_final_action": "TRADE_VISION_ONLY",
    }


def _sanitize_external_ai_payload(value: Any, path: str = "$") -> tuple[Any, list[str]]:
    redacted: list[str] = []
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if _is_secret_key(str(key)):
                clean[key] = "[REDACTED]"
                redacted.append(child_path)
                continue
            child_value, child_redacted = _sanitize_external_ai_payload(item, child_path)
            clean[key] = child_value
            redacted.extend(child_redacted)
        return clean, redacted
    if isinstance(value, list):
        items: list[Any] = []
        for index, item in enumerate(value):
            child_value, child_redacted = _sanitize_external_ai_payload(item, f"{path}[{index}]")
            items.append(child_value)
            redacted.extend(child_redacted)
        return items, redacted
    return value, redacted


def _is_secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS)


def _public_key_rotation_plan(status: dict[str, Any]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for slot in status.get("key_slots", []):
        plan.append(
            {
                "slot": slot["slot"],
                "env_name": slot["env_name"],
                "configured": bool(slot["configured"]),
                "priority": slot["priority"],
                "cooldown_until": slot.get("cooldown_until"),
                "last_error": slot.get("last_error"),
            }
        )
    return plan


def _bundle_check(check_id: str, name: str, passed: bool, effect: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
    }


def _external_ai_jarvis_effect(*, accepted: bool, safe_action: str, validation: dict[str, Any]) -> dict[str, Any]:
    if not accepted:
        effect = "discard_external_review"
    elif safe_action in {"NO_TRADE", "WAIT"}:
        effect = "confirm_wait_or_no_trade"
    else:
        effect = "display_only_no_confidence_boost"
    return {
        "effect": effect,
        "confidence_boost_allowed": False,
        "can_upgrade_trade": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "reasons": [
            "External AI output is evidence-only.",
            "Invalid schema, hallucinated citations, or unsafe overrides are discarded.",
            f"Schema pass={validation.get('schema_validation_passed')}; hallucination={validation.get('hallucination_detected')}.",
        ],
    }


def _available_evidence_keys(packet: dict[str, Any]) -> set[str]:
    keys: set[str] = set()

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                joined = f"{prefix}.{key}" if prefix else str(key)
                keys.add(joined)
                keys.add(str(key))
                walk(joined, child)
        elif isinstance(value, list):
            for idx, child in enumerate(value[:5]):
                walk(f"{prefix}[{idx}]", child)

    walk("", packet)
    return keys


def _unsafe_override_attempt(evidence_packet: dict[str, Any], response: dict[str, Any]) -> bool:
    tv_decision = (
        evidence_packet.get("trade_vision_decision", {}).get("final_trade_decision")
        or evidence_packet.get("trade_vision_decision", {}).get("decision")
        or evidence_packet.get("final_action")
    )
    final_action = response.get("final_action")
    if tv_decision == "NO_TRADE" and final_action not in {"NO_TRADE", "TRADE_VISION_ONLY"}:
        return True
    if evidence_packet.get("safety_summary", {}).get("blocking_gates") and final_action not in {"NO_TRADE", "TRADE_VISION_ONLY"}:
        return True
    return False


def _key_slots() -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for idx in range(1, MAX_GEMINI_KEYS + 1):
        vault_value = get_gemini_api_key(idx)
        env_value = os.getenv(f"GEMINI_API_KEY_{idx}", "")
        configured = bool(vault_value or env_value)
        slots.append(
            {
                "slot": idx,
                "env_name": f"GEMINI_API_KEY_{idx}",
                "configured": configured,
                "source": "vault" if vault_value else "env" if env_value else "missing",
                "cooldown_until": None,
                "last_error": None,
                "priority": idx,
            }
        )
    return slots


def _key_for_slot(slot: int) -> str | None:
    return get_gemini_api_key(slot) or os.getenv(f"GEMINI_API_KEY_{slot}", "") or None


def _live_enabled() -> bool:
    return os.getenv("TRADEVISION_GEMINI_ENABLE_LIVE", "").strip().lower() == "true"


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
        "error_rate_threshold_pct": float(os.getenv("TRADEVISION_GEMINI_ERROR_RATE_THRESHOLD_PCT", "5.0")),
        "open_duration_minutes": 15,
        "reopen_at": reopen_at.isoformat() if state == "open" and configured_count and live_enabled else None,
        "reason": "no_keys_configured" if configured_count == 0 else "live_calls_disabled" if not live_enabled else "healthy",
    }


def _hash_packet(packet: dict[str, Any]) -> str:
    clean = json.dumps(packet, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(clean).hexdigest()


def _extract_gemini_candidate(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
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
        }
        for slot in public.get("key_slots", [])
    ]
    public["notes"] = [
        "Gemini calls are disabled unless the backend live-review gate is explicitly enabled.",
        "Jarvis continues Trade Vision-only when Gemini is unavailable, timed out, or invalid.",
        "This manager reports key slots without returning key material or credential variable names.",
    ]
    return public


def _gemini_unavailable_candidate(*, status: dict[str, Any], live_allowed: bool, attempts: list[dict[str, Any]]) -> dict[str, Any]:
    reason = "Gemini live review is disabled or no valid key is configured."
    if live_allowed and attempts:
        reason = "All Gemini key slots failed, timed out, or returned invalid JSON."
    return {
        "review_status": "unavailable",
        "agrees_with_trade_vision": True,
        "pattern_interpretation": "Gemini did not provide a validated live response; Trade Vision remains the authority.",
        "entry_guidance": "Use Trade Vision-only guidance until Gemini returns a schema-valid, evidence-cited review.",
        "risk_warning": reason,
        "best_indicator_for_pattern": ["trade_vision_decision", "safety_summary"],
        "avoid_if": ["Gemini unavailable, stale, invalid, hallucinated, or safety-conflicting."],
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


def _gemini_live_operator_message(*, live_allowed: bool, successful_slot: int | None, intake: dict[str, Any]) -> str:
    if not live_allowed:
        return "Gemini live review is disabled. Set TRADEVISION_GEMINI_ENABLE_LIVE=true and save a backend key to call Gemini."
    if successful_slot is None:
        return "Gemini live review failed across configured slots; Jarvis falls back to Trade Vision-only evidence."
    if not intake.get("display_allowed"):
        return "Gemini returned a response, but schema/citation/safety validation rejected it."
    return f"Gemini slot {successful_slot} returned a validated research-only review."
