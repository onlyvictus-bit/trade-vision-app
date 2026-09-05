from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_PREFLIGHT_EVIDENCE_VERSION = "jarvis-preflight-evidence.v1.01"


def build_jarvis_preflight_evidence_pack(
    *,
    blocker_report: dict[str, Any],
    resolution_pack: dict[str, Any],
    deployment_readiness: Any,
    final_release_audit: Any,
    security_posture: Any,
    transport_status: Any,
) -> dict[str, Any]:
    deployment = _as_dict(deployment_readiness)
    final_audit = _as_dict(final_release_audit)
    security = _as_dict(security_posture)
    transport = _as_dict(transport_status)
    snapshots = _snapshots(blocker_report, resolution_pack, deployment, final_audit, security, transport)
    checklist = _checklist(snapshots)
    payload = {
        "blocker_hash": blocker_report.get("report_hash"),
        "resolution_hash": resolution_pack.get("pack_hash"),
        "snapshots": snapshots,
        "checklist": checklist,
    }
    preflight_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    blocking = [item for item in checklist if item["status"] == "fail"]
    warnings = [item for item in checklist if item["status"] == "warn"]
    return {
        "preflight_version": JARVIS_PREFLIGHT_EVIDENCE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": blocker_report.get("symbol"),
        "timeframe": blocker_report.get("timeframe"),
        "preflight_hash": preflight_hash,
        "overall_status": "blocked" if blocking else "review_required" if warnings else "ready_for_manual_paper_review",
        "check_count": len(checklist),
        "pass_count": sum(item["status"] == "pass" for item in checklist),
        "warn_count": len(warnings),
        "fail_count": len(blocking),
        "checklist": checklist,
        "evidence_snapshots": snapshots,
        "blocking_evidence": blocking,
        "warning_evidence": warnings,
        "minimum_evidence_bundle": _minimum_evidence_bundle(blocker_report, resolution_pack),
        "operator_decision": {
            "paper_review_allowed": not blocking,
            "openalgo_dry_run_allowed": not blocking and _transport_ready(transport),
            "live_trading_allowed": False,
            "manual_approval_required": True,
            "reason": "Preflight only prepares evidence. It does not self-approve paper mode or live execution.",
        },
        "artifact_names": [
            "production_blocker_report.json",
            "blocker_resolution_pack.json",
            "deployment_readiness.json",
            "final_release_audit.json",
            "transport_security_posture.json",
            "openalgo_transport_status.json",
        ],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _snapshots(
    blocker: dict[str, Any],
    resolution: dict[str, Any],
    deployment: dict[str, Any],
    final_audit: dict[str, Any],
    security: dict[str, Any],
    transport: dict[str, Any],
) -> dict[str, Any]:
    return {
        "production_blockers": {
            "version": blocker.get("blocker_report_version"),
            "overall_status": blocker.get("overall_status"),
            "blocker_count": blocker.get("blocker_count"),
            "warn_count": blocker.get("warn_count"),
            "report_hash": blocker.get("report_hash"),
        },
        "resolution_pack": {
            "version": resolution.get("resolution_version"),
            "overall_status": resolution.get("overall_status"),
            "remediation_count": resolution.get("remediation_count"),
            "must_fix_count": resolution.get("must_fix_count"),
            "manual_review_count": resolution.get("manual_review_count"),
            "pack_hash": resolution.get("pack_hash"),
        },
        "deployment_readiness": {
            "version": deployment.get("readiness_version"),
            "ready": deployment.get("ready"),
            "fail_count": deployment.get("fail_count"),
            "warn_count": deployment.get("warn_count"),
            "live_trading_blocked": deployment.get("live_trading_blocked"),
        },
        "final_release_audit": {
            "version": final_audit.get("audit_version"),
            "research_stack_ready": final_audit.get("research_stack_ready"),
            "release_candidate": final_audit.get("production_research_release_candidate"),
            "fail_count": final_audit.get("fail_count"),
            "warn_count": final_audit.get("warn_count"),
            "live_trading_ready": final_audit.get("live_trading_ready"),
        },
        "security_posture": {
            "version": security.get("security_version"),
            "overall_status": security.get("overall_status"),
            "active_key_configured": security.get("active_key_configured"),
            "allowlist": security.get("adapter_allowlist", []),
            "trace_integrity_valid": security.get("trace_integrity", {}).get("valid"),
        },
        "openalgo_transport": {
            "version": transport.get("status_version"),
            "configured": transport.get("configured"),
            "health_ok": transport.get("health_ok"),
            "service_auth_configured": transport.get("service_auth_configured"),
            "order_routing_enabled": transport.get("order_routing_enabled"),
            "live_trading_blocked": transport.get("live_trading_blocked"),
        },
    }


def _checklist(snapshots: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("PREFLIGHT-001", "Production blocker report generated", bool(snapshots["production_blockers"]["report_hash"]), "production_blockers.report_hash"),
        _check("PREFLIGHT-002", "Blocker resolution pack generated", bool(snapshots["resolution_pack"]["pack_hash"]), "resolution_pack.pack_hash"),
        _check("PREFLIGHT-003", "Jarvis has no unresolved must-fix remediation", int(snapshots["resolution_pack"].get("must_fix_count") or 0) == 0, f"must_fix_count={snapshots['resolution_pack'].get('must_fix_count')}"),
        _check("PREFLIGHT-004", "Deployment readiness has no failures", int(snapshots["deployment_readiness"].get("fail_count") or 0) == 0, f"fail_count={snapshots['deployment_readiness'].get('fail_count')}"),
        _check("PREFLIGHT-005", "Final release audit has no failures", int(snapshots["final_release_audit"].get("fail_count") or 0) == 0, f"fail_count={snapshots['final_release_audit'].get('fail_count')}"),
        _check("PREFLIGHT-006", "Transport security posture passes", snapshots["security_posture"].get("overall_status") == "pass", f"status={snapshots['security_posture'].get('overall_status')}"),
        _check("PREFLIGHT-007", "OpenAlgo dry-run transport is configured", bool(snapshots["openalgo_transport"].get("configured")), f"configured={snapshots['openalgo_transport'].get('configured')}", warn_only=True),
        _check("PREFLIGHT-008", "OpenAlgo dry-run health is OK", bool(snapshots["openalgo_transport"].get("health_ok")), f"health_ok={snapshots['openalgo_transport'].get('health_ok')}", warn_only=True),
        _check("PREFLIGHT-009", "Live trading remains blocked", snapshots["openalgo_transport"].get("live_trading_blocked") is not False and snapshots["final_release_audit"].get("live_trading_ready") is False, "live remains blocked"),
    ]


def _check(check_id: str, name: str, passed: bool, evidence: str, warn_only: bool = False) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "name": name,
        "status": "pass" if passed else "warn" if warn_only else "fail",
        "evidence": evidence,
        "blocks_preflight": not passed and not warn_only,
    }


def _minimum_evidence_bundle(blocker_report: dict[str, Any], resolution_pack: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"name": "Production Blocker Report", "version": blocker_report.get("blocker_report_version"), "hash": blocker_report.get("report_hash"), "required": True},
        {"name": "Blocker Resolution Pack", "version": resolution_pack.get("resolution_version"), "hash": resolution_pack.get("pack_hash"), "required": True},
        {"name": "Safe Configuration Template", "version": resolution_pack.get("safe_configuration_template", {}).get("template_version"), "hash": None, "required": True},
    ]


def _transport_ready(transport: dict[str, Any]) -> bool:
    return bool(transport.get("configured")) and bool(transport.get("health_ok")) and bool(transport.get("service_auth_configured"))


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}
