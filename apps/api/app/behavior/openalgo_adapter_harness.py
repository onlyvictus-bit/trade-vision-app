from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENALGO_ADAPTER_HARNESS_VERSION = "openalgo-local-adapter-harness.v1.02"
DEFAULT_LOCAL_ADAPTER_URL = "http://127.0.0.1:9010"


def build_openalgo_adapter_harness_status(*, project_root: Path, transport_status: Any) -> dict[str, Any]:
    adapter_root = project_root / "apps" / "openalgo-adapter"
    app_file = adapter_root / "adapter_app" / "main.py"
    tests_file = adapter_root / "tests" / "test_adapter.py"
    requirements_file = adapter_root / "requirements.txt"
    transport = _as_dict(transport_status)
    files = {
        "adapter_root": adapter_root.exists(),
        "adapter_app": app_file.is_file(),
        "adapter_tests": tests_file.is_file(),
        "requirements": requirements_file.is_file(),
    }
    env = _environment_status()
    readiness = _readiness(files, env, transport)
    payload = {
        "files": files,
        "env": env,
        "transport": {
            "configured": transport.get("configured"),
            "health_ok": transport.get("health_ok"),
            "service_auth_configured": transport.get("service_auth_configured"),
        },
        "readiness": readiness,
    }
    harness_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "harness_version": OPENALGO_ADAPTER_HARNESS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harness_hash": harness_hash,
        "adapter_path": str(adapter_root),
        "files": files,
        "environment": env,
        "transport_snapshot": {
            "status_version": transport.get("status_version"),
            "adapter_url": transport.get("adapter_url"),
            "configured": bool(transport.get("configured")),
            "health_checked": bool(transport.get("health_checked")),
            "health_ok": bool(transport.get("health_ok")),
            "service_auth_configured": bool(transport.get("service_auth_configured")),
            "circuit_state": transport.get("circuit_state"),
            "order_routing_enabled": bool(transport.get("order_routing_enabled")),
            "live_trading_blocked": transport.get("live_trading_blocked") is not False,
        },
        "readiness": readiness,
        "launch_plan": _launch_plan(project_root),
        "health_check_plan": _health_check_plan(),
        "intent_review_plan": _intent_review_plan(),
        "safety_contract": {
            "broker_credentials_allowed": False,
            "broker_order_creation_allowed": False,
            "order_routing_allowed": False,
            "live_trading_blocked": True,
            "dry_run_only": True,
            "unsafe_ack_must_be_rejected_by_trade_vision": True,
        },
        "next_actions": _next_actions(files, env, transport),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _environment_status() -> dict[str, Any]:
    configured_url = os.environ.get("TRADEVISION_OPENALGO_ADAPTER_URL")
    return {
        "adapter_url_configured": bool(configured_url),
        "adapter_url": configured_url or DEFAULT_LOCAL_ADAPTER_URL,
        "shared_secret_configured": bool(os.environ.get("TRADEVISION_ADAPTER_SHARED_SECRET")),
        "previous_secret_configured": bool(os.environ.get("TRADEVISION_ADAPTER_PREVIOUS_SECRET")),
        "allowed_hosts": os.environ.get("TRADEVISION_ADAPTER_ALLOWED_HOSTS", "127.0.0.1,localhost,.test"),
        "scenario": os.environ.get("TRADEVISION_ADAPTER_SCENARIO", "normal"),
        "delay_ms": int(os.environ.get("TRADEVISION_ADAPTER_DELAY_MS", "0") or "0"),
        "secrets_returned": False,
    }


def _readiness(files: dict[str, bool], env: dict[str, Any], transport: dict[str, Any]) -> dict[str, Any]:
    launch_ready = all(files.values())
    config_ready = bool(env["adapter_url_configured"] and env["shared_secret_configured"])
    health_ready = bool(transport.get("health_ok"))
    return {
        "adapter_files_ready": launch_ready,
        "configuration_ready": config_ready,
        "signed_health_ready": health_ready,
        "dry_run_handoff_ready": launch_ready and config_ready and health_ready,
        "manual_start_required": not health_ready,
        "live_trading_ready": False,
    }


def _launch_plan(project_root: Path) -> dict[str, Any]:
    adapter_cwd = project_root / "apps" / "openalgo-adapter"
    return {
        "plan_version": "openalgo-local-adapter-launch.v1.02",
        "manual_command": (
            "$env:TRADEVISION_ADAPTER_SHARED_SECRET='<operator-secret>'; "
            "$env:TRADEVISION_ADAPTER_ALLOWED_HOSTS='127.0.0.1,localhost'; "
            f"cd '{adapter_cwd}'; "
            "python -m uvicorn adapter_app.main:app --host 127.0.0.1 --port 9010"
        ),
        "trade_vision_backend_env": [
            f"TRADEVISION_OPENALGO_ADAPTER_URL={DEFAULT_LOCAL_ADAPTER_URL}",
            "TRADEVISION_ADAPTER_ALLOWED_HOSTS=127.0.0.1,localhost",
            "TRADEVISION_ADAPTER_SHARED_SECRET=<same-operator-secret>",
        ],
        "auto_start_supported": False,
        "reason_auto_start_disabled": "Starting external adapter processes and choosing secrets is an operator-controlled deployment action.",
    }


def _health_check_plan() -> dict[str, Any]:
    return {
        "endpoint": "/health",
        "method": "GET",
        "requires_hmac_headers": True,
        "expected_safe_fields": {
            "ok": True,
            "broker_credentials_present": False,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
    }


def _intent_review_plan() -> dict[str, Any]:
    return {
        "endpoint": "/intent-review",
        "method": "POST",
        "requires_hmac_headers": True,
        "expected_ack": "openalgo-adapter-ack.v0.54",
        "must_reject": [
            "missing package_hash",
            "tampered package_hash",
            "broker_credentials_present=true",
            "broker_order_created=true",
            "order_routing_enabled=true",
            "live_trading_blocked=false",
        ],
    }


def _next_actions(files: dict[str, bool], env: dict[str, Any], transport: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if not all(files.values()):
        actions.append("Restore missing apps/openalgo-adapter files before adapter harness testing.")
    if not env["shared_secret_configured"]:
        actions.append("Set TRADEVISION_ADAPTER_SHARED_SECRET in both API and adapter environments.")
    if not env["adapter_url_configured"]:
        actions.append(f"Set TRADEVISION_OPENALGO_ADAPTER_URL={DEFAULT_LOCAL_ADAPTER_URL} in the API environment.")
    if not transport.get("health_ok"):
        actions.append("Start the local adapter and rerun /api/v1/openalgo/transport/status with health check.")
    if not actions:
        actions.append("Run dry-run intent handoff; verify acknowledgement remains brokerless.")
    return actions


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}
