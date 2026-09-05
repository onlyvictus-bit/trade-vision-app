from __future__ import annotations

from typing import Any


JARVIS_READINESS_REMEDIATION_VERSION = "jarvis-readiness-remediation.v1.33"


def build_readiness_remediation_report(
    *,
    deployment_readiness: Any,
    final_release_audit: Any,
    jarvis_final_audit: dict[str, Any],
) -> dict[str, Any]:
    deployment = _as_dict(deployment_readiness)
    release = _as_dict(final_release_audit)
    failed_deployment = [
        _normalize_item(item, item.get("check_id", "unknown"))
        for item in deployment.get("checks", [])
        if item.get("status") == "fail"
    ]
    failed_release = [
        _normalize_item(item, item.get("gate_id", "unknown"))
        for item in release.get("gates", [])
        if item.get("status") == "fail"
    ]
    remediation = [_remediation_for(item["id"], item["name"]) for item in failed_deployment + failed_release]
    unique_remediation = list({item["remediation_id"]: item for item in remediation}.values())
    ready_after_operator_config = bool(unique_remediation) and all(not item["requires_code_change"] for item in unique_remediation)
    return {
        "remediation_version": JARVIS_READINESS_REMEDIATION_VERSION,
        "current_overall_state": jarvis_final_audit.get("overall_state", "unknown"),
        "deployment_ready": deployment.get("ready") is True,
        "release_candidate": release.get("production_research_release_candidate") is True,
        "jarvis_research_ready": jarvis_final_audit.get("research_ready") is True,
        "jarvis_paper_sim_ready": jarvis_final_audit.get("paper_sim_ready") is True,
        "failed_deployment_checks": failed_deployment,
        "failed_release_gates": failed_release,
        "remediation_steps": unique_remediation,
        "ready_after_operator_config": ready_after_operator_config,
        "safe_to_apply_without_live_trading": True,
        "operator_message": _operator_message(unique_remediation, ready_after_operator_config),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _normalize_item(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    return {
        "id": fallback_id,
        "name": item.get("name", fallback_id),
        "status": item.get("status", "fail"),
        "evidence": item.get("evidence") or item.get("reason") or "No evidence text available.",
    }


def _remediation_for(item_id: str, name: str) -> dict[str, Any]:
    mapping = {
        "adapter_config": {
            "title": "Configure the local OpenAlgo adapter URL",
            "actions": [
                "Start the brokerless OpenAlgo adapter in review-only mode.",
                "Set TRADEVISION_OPENALGO_ADAPTER_URL to the adapter health/review service URL.",
                "Keep the adapter pointed at paper/simulation review endpoints only.",
            ],
        },
        "adapter_auth": {
            "title": "Configure service identity signing secret",
            "actions": [
                "Set TRADEVISION_ADAPTER_SHARED_SECRET to a local service secret.",
                "Optionally set TRADEVISION_ADAPTER_PREVIOUS_SECRET for rotation rehearsal.",
                "Do not put broker API keys or account credentials in these variables.",
            ],
        },
        "adapter_health": {
            "title": "Pass authenticated adapter health check",
            "actions": [
                "Confirm the adapter exposes signed health and intent-review endpoints.",
                "Rerun /api/v1/openalgo/transport/status after URL and shared secret are configured.",
                "Health must prove brokerless review mode, not live order routing.",
            ],
        },
        "security": {
            "title": "Pass transport security posture",
            "actions": [
                "Configure active service secret and allowed adapter host.",
                "Keep nonce, timestamp skew, request size, and rate limits enabled.",
                "Rerun /api/v1/openalgo/security/posture and threat report.",
            ],
        },
        "deployment": {
            "title": "Clear deployment readiness failures",
            "actions": [
                "Complete all failed deployment checks first.",
                "Rerun deployment readiness and smoke endpoints.",
            ],
        },
        "smoke": {
            "title": "Rerun deployment smoke after readiness passes",
            "actions": [
                "Smoke depends on deployment readiness.",
                "Rerun /api/v1/deployment/smoke after adapter/security config is fixed.",
            ],
        },
    }
    base = mapping.get(item_id, {"title": f"Resolve {name}", "actions": ["Inspect the failed gate evidence.", "Fix the underlying condition and rerun v1.32 audit."]})
    return {
        "remediation_id": item_id,
        "title": base["title"],
        "actions": base["actions"],
        "requires_code_change": False,
        "requires_operator_config": True,
        "live_trading_must_remain_blocked": True,
    }


def _operator_message(steps: list[dict[str, Any]], ready_after_operator_config: bool) -> str:
    if not steps:
        return "No readiness remediation is currently required by the audited gates."
    if ready_after_operator_config:
        return "Readiness blockers are configuration/operator setup items. Apply them in paper/sim review mode, then rerun v1.32."
    return "Some readiness blockers may require code changes. Keep the system in local research mode until they are resolved."


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}
