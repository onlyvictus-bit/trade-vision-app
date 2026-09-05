from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_PRODUCTION_BLOCKERS_VERSION = "jarvis-production-blockers.v0.99"


def build_jarvis_production_blocker_report(
    *,
    fusion: dict[str, Any],
    replay_determinism: dict[str, Any],
    final_release_audit: Any,
    deployment_readiness: Any,
    openalgo_transport_status: Any,
) -> dict[str, Any]:
    """Aggregate production blockers across Jarvis, replay, deployment, and OpenAlgo handoff evidence."""
    final_audit = _as_dict(final_release_audit)
    deployment = _as_dict(deployment_readiness)
    transport = _as_dict(openalgo_transport_status)
    gates = _gates(fusion, replay_determinism, final_audit, deployment, transport)
    blocker_items = [gate for gate in gates if gate["blocks_next_stage"]]
    warning_items = [gate for gate in gates if gate["status"] == "warn"]
    stage = _stage_statuses(gates, fusion, replay_determinism, final_audit, deployment, transport)
    payload = {
        "symbol": fusion.get("symbol"),
        "timeframe": fusion.get("timeframe"),
        "stage": stage,
        "gates": gates,
        "blockers": blocker_items,
    }
    report_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "blocker_report_version": JARVIS_PRODUCTION_BLOCKERS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": fusion.get("symbol"),
        "timeframe": fusion.get("timeframe"),
        "overall_status": _overall_status(stage),
        "report_hash": report_hash,
        "stage_statuses": stage,
        "gate_count": len(gates),
        "pass_count": sum(gate["status"] == "pass" for gate in gates),
        "warn_count": len(warning_items),
        "blocker_count": len(blocker_items),
        "gates": gates,
        "blockers": blocker_items,
        "warnings": warning_items,
        "next_actions": _next_actions(blocker_items, warning_items),
        "evidence_versions": {
            "fusion": fusion.get("fusion_version"),
            "replay_determinism": replay_determinism.get("determinism_version"),
            "final_release_audit": final_audit.get("audit_version"),
            "deployment_readiness": deployment.get("readiness_version"),
            "openalgo_transport": transport.get("status_version"),
        },
        "openalgo_handoff": {
            "transport_configured": bool(transport.get("configured")),
            "adapter_health_ok": bool(transport.get("health_ok")),
            "service_auth_configured": bool(transport.get("service_auth_configured")),
            "order_routing_enabled": bool(transport.get("order_routing_enabled")),
            "live_trading_blocked": transport.get("live_trading_blocked") is not False,
            "allowed_scope": "dry_run_or_research_handoff_only",
        },
        "production_scope": {
            "research_stack_candidate": bool(final_audit.get("production_research_release_candidate")),
            "paper_mode_candidate": stage["paper_mode"]["status"] == "ready",
            "live_mode_candidate": False,
            "brokerless_boundary_preserved": fusion.get("order_routing_enabled") is False and fusion.get("live_trading_blocked") is True,
        },
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _gates(
    fusion: dict[str, Any],
    replay: dict[str, Any],
    final_audit: dict[str, Any],
    deployment: dict[str, Any],
    transport: dict[str, Any],
) -> list[dict[str, Any]]:
    final_fail = int(final_audit.get("fail_count") or 0)
    deployment_fail = int(deployment.get("fail_count") or 0)
    return [
        _gate("PROD-001", "Jarvis fusion generated", bool(fusion.get("fusion_hash")), "Jarvis unified evidence panel exists.", "research"),
        _gate("PROD-002", "Jarvis replay deterministic", bool(replay.get("deterministic")) and bool(replay.get("hash_match")), "Same input hashes to same decision evidence.", "research"),
        _gate("PROD-003", "Research release audit has no failing gates", final_fail == 0, f"fail_count={final_fail}", "research"),
        _gate("PROD-004", "Deployment readiness has no failing gates", deployment_fail == 0, f"fail_count={deployment_fail}", "research"),
        _gate("PROD-005", "Brokerless boundary preserved", _brokerless(fusion, deployment, transport), "No live route, no broker order, no broker credentials.", "paper"),
        _gate("PROD-006", "OpenAlgo transport configured and healthy", _transport_ready(transport), _transport_evidence(transport), "openalgo", warn_only=True),
        _gate("PROD-007", "Manual paper approval still required", False, "Human paper-mode approval has not been granted inside this app.", "paper", warn_only=True),
        _gate("PROD-008", "Live trading explicitly blocked", True, "Live mode is intentionally out of scope until a separate production execution review.", "live"),
        _gate("PROD-009", "External AI cannot execute or override risk", _external_read_only(fusion), "Gemini/Kronos/OpenAlgo evidence remains advisory.", "paper"),
        _gate("PROD-010", "Paper execution reality does not downgrade", _paper_not_downgraded(fusion), str(fusion.get("evidence_quality", {}).get("paper_reality_effect")), "paper", warn_only=True),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, stage: str, warn_only: bool = False) -> dict[str, Any]:
    status = "pass" if passed else "warn" if warn_only else "fail"
    return {
        "gate_id": gate_id,
        "name": name,
        "status": status,
        "stage": stage,
        "evidence": evidence,
        "blocks_next_stage": status == "fail",
    }


def _stage_statuses(
    gates: list[dict[str, Any]],
    fusion: dict[str, Any],
    replay: dict[str, Any],
    final_audit: dict[str, Any],
    deployment: dict[str, Any],
    transport: dict[str, Any],
) -> dict[str, Any]:
    research_blockers = [gate for gate in gates if gate["stage"] == "research" and gate["blocks_next_stage"]]
    paper_blockers = [gate for gate in gates if gate["stage"] in {"research", "paper"} and gate["blocks_next_stage"]]
    openalgo_warnings = [gate for gate in gates if gate["stage"] == "openalgo" and gate["status"] == "warn"]
    return {
        "research_stack": {
            "status": "ready" if not research_blockers else "blocked",
            "blocker_count": len(research_blockers),
            "release_candidate": bool(final_audit.get("production_research_release_candidate")),
            "deployment_ready": bool(deployment.get("ready")),
        },
        "paper_mode": {
            "status": "ready" if not paper_blockers and _paper_not_downgraded(fusion) else "blocked",
            "blocker_count": len(paper_blockers),
            "manual_approval_required": True,
            "replay_deterministic": bool(replay.get("deterministic")),
        },
        "openalgo_handoff": {
            "status": "ready" if not openalgo_warnings and _transport_ready(transport) else "not_configured",
            "warning_count": len(openalgo_warnings),
            "transport_configured": bool(transport.get("configured")),
            "dry_run_only": True,
        },
        "live_trading": {
            "status": "blocked",
            "reason": "Live broker routing remains intentionally out of scope.",
            "requires_separate_review": True,
        },
    }


def _overall_status(stage: dict[str, Any]) -> str:
    if stage["research_stack"]["status"] != "ready":
        return "research_blocked"
    if stage["paper_mode"]["status"] != "ready":
        return "paper_blocked"
    if stage["openalgo_handoff"]["status"] != "ready":
        return "openalgo_not_configured"
    return "research_ready_paper_review_required"


def _next_actions(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> list[str]:
    actions = [f"Fix {gate['gate_id']}: {gate['name']} ({gate['evidence']})" for gate in blockers]
    actions.extend(f"Review {gate['gate_id']}: {gate['name']} ({gate['evidence']})" for gate in warnings[:5])
    if not actions:
        actions.append("Proceed to manual paper-mode review; live trading remains blocked.")
    return actions[:10]


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}


def _brokerless(fusion: dict[str, Any], deployment: dict[str, Any], transport: dict[str, Any]) -> bool:
    return (
        fusion.get("order_routing_enabled") is False
        and fusion.get("live_trading_blocked") is True
        and deployment.get("order_routing_enabled") is False
        and deployment.get("broker_credentials_present") is False
        and deployment.get("broker_order_created") is False
        and transport.get("order_routing_enabled") is not True
    )


def _transport_ready(transport: dict[str, Any]) -> bool:
    return (
        bool(transport.get("configured"))
        and bool(transport.get("health_ok"))
        and bool(transport.get("service_auth_configured"))
        and transport.get("order_routing_enabled") is False
    )


def _transport_evidence(transport: dict[str, Any]) -> str:
    return (
        f"configured={transport.get('configured')}; health_ok={transport.get('health_ok')}; "
        f"service_auth={transport.get('service_auth_configured')}"
    )


def _external_read_only(fusion: dict[str, Any]) -> bool:
    return (
        fusion.get("can_execute_orders") is False
        and fusion.get("can_override_no_trade") is False
        and fusion.get("can_override_risk") is False
    )


def _paper_not_downgraded(fusion: dict[str, Any]) -> bool:
    return fusion.get("evidence_quality", {}).get("paper_reality_effect") not in {"WAIT", "NO_TRADE"}
