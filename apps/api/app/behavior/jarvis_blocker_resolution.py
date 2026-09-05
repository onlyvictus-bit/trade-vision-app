from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_BLOCKER_RESOLUTION_VERSION = "jarvis-blocker-resolution.v1.00"


def build_jarvis_blocker_resolution_pack(
    *,
    blocker_report: dict[str, Any],
    deployment_readiness: Any,
    final_release_audit: Any,
    security_posture: Any,
    transport_status: Any,
) -> dict[str, Any]:
    deployment = _as_dict(deployment_readiness)
    final_audit = _as_dict(final_release_audit)
    security = _as_dict(security_posture)
    transport = _as_dict(transport_status)
    deployment_checks = deployment.get("checks", [])
    release_gates = final_audit.get("gates", [])
    security_checks = security.get("checks", [])
    remediation_items = _remediation_items(deployment_checks, release_gates, security_checks, transport)
    runbook = _runbook_steps()
    payload = {
        "blocker_report_hash": blocker_report.get("report_hash"),
        "remediation_items": remediation_items,
        "runbook": runbook,
    }
    pack_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "resolution_version": JARVIS_BLOCKER_RESOLUTION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": blocker_report.get("symbol"),
        "timeframe": blocker_report.get("timeframe"),
        "source_blocker_report_version": blocker_report.get("blocker_report_version"),
        "source_blocker_report_hash": blocker_report.get("report_hash"),
        "overall_status": _overall_status(remediation_items),
        "pack_hash": pack_hash,
        "remediation_count": len(remediation_items),
        "must_fix_count": sum(item["severity"] == "must_fix" for item in remediation_items),
        "manual_review_count": sum(item["severity"] == "manual_review" for item in remediation_items),
        "remediation_items": remediation_items,
        "safe_configuration_template": _safe_configuration_template(),
        "operator_runbook": runbook,
        "verification_commands": _verification_commands(),
        "evidence_to_collect": _evidence_to_collect(),
        "cannot_auto_fix": [
            "OpenAlgo adapter URL, shared secret, allowlist, and health endpoint are external operator-controlled configuration.",
            "Manual paper approval must be granted by the operator after reviewing evidence; code must not self-approve.",
            "Live trading requires a separate production execution review and remains blocked in Trade Vision.",
        ],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _remediation_items(
    deployment_checks: list[dict[str, Any]],
    release_gates: list[dict[str, Any]],
    security_checks: list[dict[str, Any]],
    transport: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for check in deployment_checks:
        if check.get("status") == "fail":
            check_id = str(check.get("check_id", "deployment"))
            items.append(_deployment_item(check_id, check))
    for gate in release_gates:
        if gate.get("status") == "fail":
            gate_id = str(gate.get("gate_id", "release"))
            items.append(_release_item(gate_id, gate))
    for check in security_checks:
        if not check.get("passed"):
            check_id = str(check.get("check_id", "security"))
            items.append(_security_item(check_id, check))
    if not transport.get("configured"):
        items.append(
            _item(
                "OPENALGO-CONFIG-001",
                "Configure OpenAlgo adapter URL",
                "manual_review",
                "openalgo_handoff",
                "Set TRADEVISION_OPENALGO_ADAPTER_URL to an HTTPS or loopback adapter endpoint in the allowlist.",
                "GET /api/v1/openalgo/transport/status reports configured=true.",
                ["TRADEVISION_OPENALGO_ADAPTER_URL=http://127.0.0.1:<adapter-port>"],
            )
        )
    if not transport.get("service_auth_configured"):
        items.append(
            _item(
                "OPENALGO-AUTH-001",
                "Configure adapter shared secret",
                "must_fix",
                "openalgo_handoff",
                "Set TRADEVISION_ADAPTER_SHARED_SECRET in backend environment; never store it in frontend code.",
                "Security posture active_key passes and transport service_auth_configured=true.",
                ["TRADEVISION_ADAPTER_SHARED_SECRET=<operator-generated-secret>"],
            )
        )
    return _dedupe(items)


def _deployment_item(check_id: str, check: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "adapter_config": ("OPENALGO-CONFIG-001", "Configure OpenAlgo adapter URL", "manual_review", "Set adapter URL for dry-run/research handoff."),
        "adapter_auth": ("OPENALGO-AUTH-001", "Configure adapter shared secret", "must_fix", "Set backend-only shared secret for signed transport."),
        "adapter_health": ("OPENALGO-HEALTH-001", "Start and verify OpenAlgo adapter health", "manual_review", "Run adapter service and confirm authenticated health succeeds."),
        "security": ("OPENALGO-SECURITY-001", "Pass transport security posture", "must_fix", "Resolve active key, allowlist, and trace-integrity security checks."),
        "trace": ("OPENALGO-TRACE-001", "Repair transport trace integrity baseline", "must_fix", "Clear or rebuild invalid transport traces, then rerun trace integrity."),
    }
    code, title, severity, action = mapping.get(check_id, (f"DEPLOY-{check_id.upper()}", str(check.get("name", check_id)), "must_fix", str(check.get("evidence", ""))))
    return _item(code, title, severity, "deployment", action, str(check.get("evidence", "")), [])


def _release_item(gate_id: str, gate: dict[str, Any]) -> dict[str, Any]:
    return _item(
        f"RELEASE-{gate_id.upper()}",
        str(gate.get("name", gate_id)),
        "must_fix",
        "release_audit",
        "Resolve the underlying deployment/security blocker, then rerun final release audit.",
        str(gate.get("evidence", "")),
        [],
    )


def _security_item(check_id: str, check: dict[str, Any]) -> dict[str, Any]:
    env_hints = {
        "active_key": ["TRADEVISION_ADAPTER_SHARED_SECRET=<operator-generated-secret>"],
        "rotation_key": ["TRADEVISION_ADAPTER_PREVIOUS_SECRET=<previous-secret-during-rotation>"],
        "allowlist": ["TRADEVISION_ADAPTER_ALLOWLIST=127.0.0.1,localhost,<adapter-host>"],
    }.get(check_id, [])
    severity = "manual_review" if check.get("severity") == "warning" else "must_fix"
    return _item(
        f"SECURITY-{check_id.upper()}",
        str(check.get("name", check_id)),
        severity,
        "security",
        "Fix the security control and rerun /api/v1/openalgo/security/posture.",
        str(check.get("evidence", "")),
        env_hints,
    )


def _item(
    item_id: str,
    title: str,
    severity: str,
    category: str,
    action: str,
    acceptance: str,
    env_hints: list[str],
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "title": title,
        "severity": severity,
        "category": category,
        "action": action,
        "acceptance": acceptance,
        "env_hints": env_hints,
        "safe_scope": "research_or_dry_run_only",
        "requires_operator_input": bool(env_hints) or severity == "manual_review",
    }


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        deduped.setdefault(item["item_id"], item)
    return list(deduped.values())


def _safe_configuration_template() -> dict[str, Any]:
    return {
        "template_version": "jarvis-safe-openalgo-config.v1.00",
        "backend_environment_only": True,
        "frontend_must_not_receive_secrets": True,
        "variables": [
            {"name": "TRADEVISION_OPENALGO_ADAPTER_URL", "required_for": "dry_run_handoff", "example": "http://127.0.0.1:9010"},
            {"name": "TRADEVISION_ADAPTER_ALLOWLIST", "required_for": "egress_guard", "example": "127.0.0.1,localhost"},
            {"name": "TRADEVISION_ADAPTER_SHARED_SECRET", "required_for": "signed_transport", "example": "<do-not-commit>"},
            {"name": "TRADEVISION_ADAPTER_PREVIOUS_SECRET", "required_for": "key_rotation", "example": "<optional-rotation-secret>"},
        ],
    }


def _runbook_steps() -> list[dict[str, Any]]:
    return [
        {"step": 1, "title": "Configure adapter environment", "command": "Set backend-only adapter URL, allowlist, and shared secret.", "expected": "No secrets appear in frontend bundles or API responses."},
        {"step": 2, "title": "Start OpenAlgo adapter in dry-run mode", "command": "Run the external adapter with order creation disabled.", "expected": "Adapter health endpoint authenticates successfully."},
        {"step": 3, "title": "Run transport status", "command": "GET /api/v1/openalgo/transport/status", "expected": "configured=true, service_auth_configured=true, health_ok=true."},
        {"step": 4, "title": "Run security posture", "command": "GET /api/v1/openalgo/security/posture", "expected": "overall_status is pass or operator-accepted warning."},
        {"step": 5, "title": "Run production blockers", "command": "GET /api/v1/jarvis/production-blockers/RELIANCE", "expected": "research stack no longer blocked; live trading still blocked."},
    ]


def _verification_commands() -> list[str]:
    return [
        "python -m pytest trade-vision-app/apps/api/tests/test_api.py -q",
        "npm run typecheck --workspace apps/web",
        "npm run build --workspace apps/web",
        "GET /api/v1/jarvis/production-blockers/RELIANCE?timeframe=1m&rows=390&position=tail",
        "GET /api/v1/jarvis/blocker-resolution/RELIANCE?timeframe=1m&rows=390&position=tail",
    ]


def _evidence_to_collect() -> list[str]:
    return [
        "Transport status JSON with configured=true and health_ok=true.",
        "Security posture JSON with active_key and allowlist passing.",
        "Final release audit JSON with fail_count=0 for research stack.",
        "Production blocker report JSON showing live_trading.status=blocked.",
        "Frontend screenshot of Production Readiness Blockers and Blocker Resolution Pack panels.",
    ]


def _overall_status(items: list[dict[str, Any]]) -> str:
    if any(item["severity"] == "must_fix" for item in items):
        return "must_fix_before_paper_or_openalgo"
    if any(item["severity"] == "manual_review" for item in items):
        return "operator_configuration_required"
    return "ready_for_manual_paper_review"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}
