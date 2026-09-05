from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from .gemini_provider import (
    ALLOWED_FINAL_ACTIONS,
    REQUIRED_REVIEW_FIELDS,
    build_external_ai_review_intake,
)
from .grok_provider import _disabled_candidate, _grok_system_prompt


GROK_GATEWAY_PROVIDER_VERSION = "jarvis-grok-local-gateway.v1"
DEFAULT_GROK_GATEWAY_URL = "http://127.0.0.1:8899"
DEFAULT_GROK_GATEWAY_MODEL = "grok/grok-4-fast"
DEFAULT_HEALTH_TIMEOUT_MS = 1500
DEFAULT_ASK_TIMEOUT_MS = 45000
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_AI_VAULT_PATH = PROJECT_ROOT / "data" / "secrets" / "ai_credentials.enc"
DEFAULT_GATEWAY_CONFIG_PATH = PROJECT_ROOT / "data" / "secrets" / "grok_gateway.local.json"
SAFE_REDACTION = "[REDACTED_BY_TRADE_VISION]"
UNSUPPORTED_CONFIG_SECRET_KEYS = {"username", "password", "cookie", "cookies", "session", "token", "access_token", "refresh_token"}
ALLOWED_GATEWAY_CONFIG_KEYS = {"enabled", "gateway_url", "model", "health_timeout_ms", "ask_timeout_ms"}


def gateway_model() -> str:
    value = _config_value("TRADEVISION_GROK_GATEWAY_MODEL", "model", DEFAULT_GROK_GATEWAY_MODEL)
    return str(value).strip() or DEFAULT_GROK_GATEWAY_MODEL


async def build_grok_gateway_status(*, check_health: bool = False) -> dict[str, Any]:
    url = _gateway_url()
    validation = _validate_gateway_url(url)
    enabled = _gateway_enabled()
    health: dict[str, Any] = {
        "attempted": False,
        "success": False,
        "state": "not_checked",
        "latency_ms": None,
        "error_message": None,
    }
    models: dict[str, Any] = {"attempted": False, "success": False, "models": [], "error_message": None}
    if check_health and enabled and validation["valid"]:
        health = await _gateway_health(url)
        models = await _gateway_models(url) if health.get("success") else models
    state = _status_state(enabled=enabled, validation=validation, health=health)
    return {
        "provider_version": GROK_GATEWAY_PROVIDER_VERSION,
        "provider": "grok_gateway",
        "status": state,
        "gateway_state": state,
        "gateway_url_masked": _mask_gateway_url(url),
        "gateway_enabled": enabled,
        "localhost_only": validation["localhost_only"],
        "url_valid": validation["valid"],
        "url_error": validation["error"],
        "selected_model": gateway_model(),
        "health_check": health,
        "models_check": models,
        "health_timeout_ms": _health_timeout_ms(),
        "ask_timeout_ms": _ask_timeout_ms(),
        "single_box_paths": _single_box_paths(),
        "thinking_detection": {
            "states": ["idle", "checking", "waiting_for_reply", "validated", "timeout", "failed"],
            "backend_knows_thinking_only_while_request_in_flight": True,
            "timeout_policy": f"Ask call is marked timeout after {_ask_timeout_ms()} ms.",
            "passgrok_endpoint_used": "/v1/chat/completions",
        },
        "security": _security_block(),
        "role": "local_external_evidence_reviewer_only",
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "operator_message": _status_operator_message(state, validation, health),
    }


async def build_grok_gateway_review_report(
    *,
    symbol: str,
    evidence_packet: dict[str, Any],
    execute: bool = False,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    status = await build_grok_gateway_status(check_health=False)
    redacted_packet = _redact_sensitive(evidence_packet)
    request = _build_openai_compatible_request(redacted_packet, status)
    call = {
        "attempted": False,
        "performed": False,
        "success": False,
        "state": "idle",
        "status_code": None,
        "latency_ms": None,
        "error_message": None,
    }
    raw_response: dict[str, Any] | None = None
    if execute and status["gateway_enabled"] and status["url_valid"]:
        call["attempted"] = True
        call["state"] = "waiting_for_reply"
        try:
            raw_response = await _post_gateway_chat(_gateway_url(), request)
            candidate = _extract_candidate(raw_response)
            call = {
                "attempted": True,
                "performed": True,
                "success": isinstance(candidate, dict) and candidate.get("review_status") != "invalid",
                "state": "validated" if isinstance(candidate, dict) and candidate.get("review_status") != "invalid" else "failed",
                "status_code": raw_response.get("status_code"),
                "latency_ms": raw_response.get("latency_ms"),
                "error_message": raw_response.get("error_message"),
            }
        except httpx.TimeoutException as exc:
            candidate = _invalid_candidate(f"Grok gateway timed out after {_ask_timeout_ms()} ms: {exc}")
            call = _failed_call("timeout", f"{type(exc).__name__}: {exc}", started)
        except Exception as exc:
            candidate = _invalid_candidate(f"Grok gateway failed safely: {type(exc).__name__}: {exc}")
            call = _failed_call("failed", f"{type(exc).__name__}: {exc}", started)
    else:
        candidate = _disabled_candidate(status={"status": status["gateway_state"]}, live_allowed=False)
        call["error_message"] = _disabled_reason(execute=execute, status=status)

    intake = build_external_ai_review_intake(
        evidence_packet=redacted_packet,
        candidate_response=candidate,
        source="grok",
    )
    gates = _review_gates(status=status, call=call, intake=intake)
    return {
        "gateway_review_version": GROK_GATEWAY_PROVIDER_VERSION,
        "symbol": symbol.upper(),
        "provider_status": status,
        "gateway_call": call,
        "thinking_state": call["state"],
        "evidence_packet_hash": _hash(redacted_packet),
        "request_hash": _hash(request),
        "execute_requested": bool(execute),
        "gateway_call_allowed": bool(execute and status["gateway_enabled"] and status["url_valid"]),
        "candidate_response": candidate,
        "raw_response_text": _raw_response_text(raw_response),
        "raw_response_preview": _raw_response_text(raw_response)[:4000],
        "sent_packet_preview": redacted_packet,
        "review_intake": intake,
        "display_allowed": bool(intake["display_allowed"] and call["success"]),
        "safe_final_action": _safe_action(intake=intake, call=call),
        "gates": gates,
        "blocking_count": sum(1 for gate in gates if gate["effect"] == "block" and not gate["passed"]),
        "warning_count": sum(1 for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]),
        "operator_message": _review_operator_message(call=call, status=status, intake=intake),
        "security": _security_block(),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _gateway_url() -> str:
    value = _config_value("TRADEVISION_GROK_GATEWAY_URL", "gateway_url", DEFAULT_GROK_GATEWAY_URL)
    return str(value).strip() or DEFAULT_GROK_GATEWAY_URL


def _gateway_enabled() -> bool:
    value = str(_config_value("TRADEVISION_GROK_GATEWAY_ENABLED", "enabled", "true")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _health_timeout_ms() -> int:
    return max(250, int(_config_value("TRADEVISION_GROK_GATEWAY_HEALTH_TIMEOUT_MS", "health_timeout_ms", DEFAULT_HEALTH_TIMEOUT_MS)))


def _ask_timeout_ms() -> int:
    return max(1000, int(_config_value("TRADEVISION_GROK_GATEWAY_ASK_TIMEOUT_MS", "ask_timeout_ms", DEFAULT_ASK_TIMEOUT_MS)))


def _gateway_config_path() -> Path:
    return Path(os.getenv("TRADEVISION_GROK_GATEWAY_CONFIG_PATH", str(DEFAULT_GATEWAY_CONFIG_PATH)))


def _api_vault_path() -> Path:
    return Path(os.getenv("TRADEVISION_AI_CREDENTIAL_VAULT_PATH", str(DEFAULT_AI_VAULT_PATH)))


def _gateway_config() -> dict[str, Any]:
    path = _gateway_config_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_config_error": "invalid_json_or_unreadable"}
    return payload if isinstance(payload, dict) else {"_config_error": "config_root_must_be_object"}


def _config_value(env_name: str, config_key: str, default: Any) -> Any:
    env_value = os.getenv(env_name)
    if env_value is not None and str(env_value).strip() != "":
        return env_value
    config = _gateway_config()
    if config_key in config:
        return config[config_key]
    return default


def _single_box_paths() -> dict[str, Any]:
    config = _gateway_config()
    unsupported = sorted(key for key in config.keys() if key.lower() in UNSUPPORTED_CONFIG_SECRET_KEYS)
    unknown = sorted(key for key in config.keys() if not key.startswith("_") and key not in ALLOWED_GATEWAY_CONFIG_KEYS and key.lower() not in UNSUPPORTED_CONFIG_SECRET_KEYS)
    return {
        "mode": "single_box_trade_vision_local_config",
        "gateway_config_path": str(_gateway_config_path()),
        "gateway_config_file_exists": _gateway_config_path().exists(),
        "official_api_key_vault_path": str(_api_vault_path()),
        "official_api_key_vault_file_exists": _api_vault_path().exists(),
        "manual_edit_allowed_for_gateway_config": True,
        "manual_edit_allowed_for_api_key_vault": False,
        "allowed_gateway_config_keys": sorted(ALLOWED_GATEWAY_CONFIG_KEYS),
        "example_gateway_config": {
            "enabled": True,
            "gateway_url": DEFAULT_GROK_GATEWAY_URL,
            "model": DEFAULT_GROK_GATEWAY_MODEL,
            "health_timeout_ms": DEFAULT_HEALTH_TIMEOUT_MS,
            "ask_timeout_ms": DEFAULT_ASK_TIMEOUT_MS,
        },
        "browser_username_password_supported": False,
        "browser_session_cookie_supported": False,
        "unsupported_secret_keys_detected": unsupported,
        "unknown_keys_detected": unknown,
        "config_error": config.get("_config_error"),
        "operator_note": "Use this file for local gateway settings only. Do not place Grok username/password, cookies, or browser sessions in Trade Vision.",
    }


def _validate_gateway_url(url: str) -> dict[str, Any]:
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return {"valid": False, "localhost_only": False, "error": f"invalid_url:{type(exc).__name__}"}
    host = (parsed.hostname or "").lower()
    valid = parsed.scheme == "http" and host in LOCAL_HOSTS and not parsed.username and not parsed.password
    error = None
    if parsed.scheme != "http":
        error = "only_http_localhost_gateway_allowed"
    elif host not in LOCAL_HOSTS:
        error = "gateway_must_be_localhost_or_127_0_0_1"
    elif parsed.username or parsed.password:
        error = "gateway_url_must_not_contain_credentials"
    return {"valid": valid, "localhost_only": host in LOCAL_HOSTS, "error": error}


def _mask_gateway_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or "invalid"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme or 'http'}://{host}{port}"


async def _gateway_health(url: str) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=_health_timeout_ms() / 1000.0) as client:
            response = await client.get(f"{url.rstrip('/')}/health")
        return {
            "attempted": True,
            "success": response.is_success,
            "state": "connected" if response.is_success else "failed",
            "status_code": response.status_code,
            "latency_ms": _elapsed_ms(started),
            "error_message": None if response.is_success else response.text[:500],
        }
    except httpx.TimeoutException as exc:
        return {"attempted": True, "success": False, "state": "timeout", "status_code": None, "latency_ms": _elapsed_ms(started), "error_message": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:
        return {"attempted": True, "success": False, "state": "failed", "status_code": None, "latency_ms": _elapsed_ms(started), "error_message": f"{type(exc).__name__}: {exc}"}


async def _gateway_models(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=_health_timeout_ms() / 1000.0) as client:
            response = await client.get(f"{url.rstrip('/')}/v1/models")
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        return {"attempted": True, "success": response.is_success, "models": payload.get("data", []), "error_message": None if response.is_success else response.text[:500]}
    except Exception as exc:
        return {"attempted": True, "success": False, "models": [], "error_message": f"{type(exc).__name__}: {exc}"}


def _build_openai_compatible_request(evidence_packet: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": status["selected_model"],
        "temperature": 0.0,
        "stream": False,
        "messages": [
            {"role": "system", "content": _grok_system_prompt()},
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


async def _post_gateway_chat(url: str, request: dict[str, Any]) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    async with httpx.AsyncClient(timeout=_ask_timeout_ms() / 1000.0) as client:
        response = await client.post(f"{url.rstrip('/')}/v1/chat/completions", json=request)
    text = response.text
    parsed: Any = None
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            parsed = response.json()
        except json.JSONDecodeError:
            parsed = None
    return {
        "performed": True,
        "success": response.is_success,
        "status_code": response.status_code,
        "payload": parsed,
        "raw_text": text,
        "latency_ms": _elapsed_ms(started),
        "error_message": None if response.is_success else text[:500],
    }


def _extract_candidate(raw_response: dict[str, Any] | None) -> dict[str, Any]:
    if not raw_response or not raw_response.get("success"):
        return _invalid_candidate(raw_response.get("error_message") if raw_response else "empty_gateway_response")
    payload = raw_response.get("payload")
    content: Any = None
    if isinstance(payload, dict):
        content = payload.get("candidate_response") or payload.get("review") or payload.get("data")
        if content is None:
            try:
                content = payload["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                content = payload
    if isinstance(content, dict) and REQUIRED_REVIEW_FIELDS.issubset(set(content.keys())):
        return content
    if isinstance(content, str):
        parsed = _json_from_text(content)
        if isinstance(parsed, dict) and REQUIRED_REVIEW_FIELDS.issubset(set(parsed.keys())):
            return parsed
    parsed_raw = _json_from_text(_raw_response_text(raw_response))
    if isinstance(parsed_raw, dict) and REQUIRED_REVIEW_FIELDS.issubset(set(parsed_raw.keys())):
        return parsed_raw
    return _invalid_candidate("Grok gateway returned non-schema response. Raw reply is visible but cannot influence decision.")


def _json_from_text(text: str) -> dict[str, Any] | None:
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


def _raw_response_text(raw_response: dict[str, Any] | None) -> str:
    if not raw_response:
        return ""
    if isinstance(raw_response.get("raw_text"), str):
        return raw_response["raw_text"]
    return json.dumps(raw_response.get("payload") or {}, sort_keys=True, default=str)


def _invalid_candidate(reason: str | None) -> dict[str, Any]:
    return {
        "review_status": "invalid",
        "agrees_with_trade_vision": False,
        "pattern_interpretation": "Grok gateway response is not accepted for decision support.",
        "entry_guidance": "Use Trade Vision-only evidence until Grok returns a validated schema response.",
        "risk_warning": reason or "invalid_gateway_response",
        "best_indicator_for_pattern": ["trade_vision_decision", "safety_summary"],
        "avoid_if": ["gateway timeout, invalid schema, missing citations, stale evidence, or safety conflict"],
        "confidence_comment": "No confidence boost is allowed from this Grok response.",
        "final_action": "TRADE_VISION_ONLY",
        "cited_evidence_keys": ["trade_vision_decision", "safety_summary"],
    }


def _failed_call(state: str, error: str, started: datetime) -> dict[str, Any]:
    return {"attempted": True, "performed": True, "success": False, "state": state, "status_code": None, "latency_ms": _elapsed_ms(started), "error_message": error}


def _status_state(*, enabled: bool, validation: dict[str, Any], health: dict[str, Any]) -> str:
    if not enabled:
        return "disabled"
    if not validation["valid"]:
        return "blocked_invalid_gateway_url"
    if health["attempted"]:
        return health["state"]
    return "ready_unchecked"


def _status_operator_message(state: str, validation: dict[str, Any], health: dict[str, Any]) -> str:
    if validation["error"]:
        return f"Grok gateway is blocked: {validation['error']}."
    if state == "connected":
        return "Local passGROK gateway is reachable. It remains reviewer-only."
    if state == "timeout":
        return "Local passGROK gateway did not answer health check before timeout."
    if state == "failed":
        return f"Local passGROK gateway health check failed: {health.get('error_message') or 'unknown'}."
    if state == "disabled":
        return "Local Grok gateway is disabled by environment."
    return "Local passGROK gateway is configured but not yet checked."


def _review_operator_message(*, call: dict[str, Any], status: dict[str, Any], intake: dict[str, Any]) -> str:
    if not status["url_valid"]:
        return "Grok gateway URL is unsafe. Only localhost/127.0.0.1 HTTP gateway is allowed."
    if call["state"] == "waiting_for_reply":
        return "Grok request is still waiting. Frontend should show in-progress state until completion or timeout."
    if call["state"] == "timeout":
        return "Grok took too long. Jarvis marks it timeout and keeps Trade Vision-only decision."
    if call["state"] == "failed":
        return "Grok failed or returned invalid schema. Raw reply can be inspected, but decision is not affected."
    if call["success"] and intake["display_allowed"]:
        return "Grok gateway reply is validated for display only. It cannot approve or execute trades."
    return "Grok gateway is idle or disabled. Trade Vision remains the authority."


def _disabled_reason(*, execute: bool, status: dict[str, Any]) -> str:
    if not execute:
        return "Gateway call not requested. Safe preview only."
    if not status["gateway_enabled"]:
        return "Gateway disabled by TRADEVISION_GROK_GATEWAY_ENABLED."
    if not status["url_valid"]:
        return status["url_error"] or "invalid gateway url"
    return "Gateway unavailable."


def _safe_action(*, intake: dict[str, Any], call: dict[str, Any]) -> str:
    if not call["success"] or not intake.get("display_allowed"):
        return "TRADE_VISION_ONLY"
    action = intake.get("safe_final_action", "WAIT")
    return action if action in {"NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"} else "WAIT"


def _review_gates(*, status: dict[str, Any], call: dict[str, Any], intake: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _gate("GROK-GW-001", "Gateway URL is localhost-only", status["url_valid"] and status["localhost_only"], "block", "Remote Grok gateways are not allowed."),
        _gate("GROK-GW-002", "No credentials/cookies/sessions sent", True, "block", "Trade Vision must not forward login material."),
        _gate("GROK-GW-003", "Gateway reply completed before timeout", call["state"] != "timeout", "downgrade", "Timeout keeps Trade Vision-only decision."),
        _gate("GROK-GW-004", "Gateway response passed display validation", intake.get("display_allowed") is True and call["success"] is True, "downgrade", "Invalid responses are visible as raw text only."),
        _gate("GROK-GW-005", "Grok cannot execute or override safety", True, "block", "Gateway is reviewer-only."),
    ]


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": bool(passed), "effect": effect, "reason": reason}


def _security_block() -> dict[str, Any]:
    return {
        "frontend_username_password_form_allowed": False,
        "trade_vision_stores_grok_password": False,
        "trade_vision_reads_passgrok_credentials_file": False,
        "browser_session_capture_allowed": False,
        "cookie_capture_allowed": False,
        "hidden_token_capture_allowed": False,
        "gateway_must_own_any_login_state": True,
        "passgrok_capture_code_vendored_into_core": False,
    }


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            output[key] = SAFE_REDACTION if _is_sensitive_key(str(key)) else _redact_sensitive(item)
        return output
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    safe_state_keys = {"broker_credentials_present"}
    if lowered in safe_state_keys:
        return False
    return any(token in lowered for token in ("api_key", "secret", "token", "password", "cookie", "session", "authorization", "credential"))


def _elapsed_ms(started: datetime) -> int:
    return int((datetime.now(timezone.utc) - started).total_seconds() * 1000)


def _hash(packet: dict[str, Any]) -> str:
    payload = json.dumps(packet, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
