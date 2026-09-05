from __future__ import annotations

from typing import Any


JARVIS_FINAL_PRODUCTION_AUDIT_VERSION = "jarvis-final-production-readiness-audit.v1.32"


def build_jarvis_final_production_audit(
    *,
    symbol: str,
    final_release_audit: Any,
    deployment_readiness: Any,
    realtime_freshness: dict[str, Any],
    gemini_decision_room: dict[str, Any],
    openalgo_paper_bridge: dict[str, Any],
    decision_quality: dict[str, Any],
    trading_decision_output: dict[str, Any],
    chart_overlay_qa: dict[str, Any],
) -> dict[str, Any]:
    final_release = _as_dict(final_release_audit)
    deployment = _as_dict(deployment_readiness)
    gates = [
        _gate("FINAL-001", "Research release audit has no blocking failures", int(final_release.get("fail_count", 999)) == 0, "research_release", "Existing v0.59 release audit must pass before any paper/sim claim."),
        _gate("FINAL-002", "Deployment is research-stack ready", deployment.get("ready") is True, "research_release", "Deployment readiness and recovery checks must pass."),
        _gate("FINAL-003", "Realtime evidence does not allow stale action", realtime_freshness.get("safe_display_action") in {"WAIT", "RESEARCH_ONLY"}, "paper_sim", "Freshness can show research evidence but stale/slow evidence must force WAIT."),
        _gate("FINAL-004", "Gemini is reviewer-only", _reviewer_only(gemini_decision_room), "paper_sim", "Gemini cannot execute, boost confidence, or override risk/no-trade."),
        _gate("FINAL-005", "OpenAlgo bridge is paper/sim only", _paper_bridge_only(openalgo_paper_bridge), "paper_sim", "OpenAlgo may inspect only paper/sim review packages and cannot execute."),
        _gate("FINAL-006", "Decision quality blocks unsafe promotion", decision_quality.get("order_routing_enabled") is False and decision_quality.get("live_trading_blocked") is True, "paper_sim", "Decision quality gate must keep routing disabled."),
        _gate("FINAL-007", "Trading output remains non-executable", trading_decision_output.get("trade_allowed") is False and trading_decision_output.get("order_routing_enabled") is False, "paper_sim", "Displayed entry/SL/target plans remain guidance only."),
        _gate("FINAL-008", "Chart overlay QA passes", chart_overlay_qa.get("qa_state") == "passed", "paper_sim", "Decision overlays must be nonblank and include entry/SL/target/invalidation evidence."),
        _gate("FINAL-009", "Live trading remains blocked", _live_blocked(final_release, deployment, realtime_freshness, gemini_decision_room, openalgo_paper_bridge, decision_quality, trading_decision_output, chart_overlay_qa), "live", "Every current artifact must explicitly block live trading."),
        _gate("FINAL-010", "Broker/order routing remains disabled", _routing_disabled(deployment, gemini_decision_room, openalgo_paper_bridge, decision_quality, trading_decision_output, chart_overlay_qa), "live", "No current artifact may enable broker routing or order creation."),
    ]
    failed = [gate for gate in gates if not gate["passed"]]
    live_blockers = [gate for gate in gates if gate["scope"] == "live" or not gate["passed"]]
    paper_ready = not failed and openalgo_paper_bridge.get("paper_intent_allowed") is True
    research_ready = not [gate for gate in failed if gate["scope"] == "research_release"]
    if failed:
        overall_state = "blocked"
    elif paper_ready:
        overall_state = "paper_sim_ready_live_blocked"
    elif research_ready:
        overall_state = "research_ready_live_blocked"
    else:
        overall_state = "blocked"
    return {
        "audit_version": JARVIS_FINAL_PRODUCTION_AUDIT_VERSION,
        "symbol": symbol.upper(),
        "overall_state": overall_state,
        "research_ready": research_ready,
        "paper_sim_ready": paper_ready,
        "live_ready": False,
        "openalgo_inspection_ready": bool(openalgo_paper_bridge.get("openalgo_may_inspect")) and not failed,
        "broker_connection_ready": False,
        "autonomous_execution_ready": False,
        "go_no_go": {
            "research_dashboard": "GO" if research_ready else "NO_GO",
            "paper_sim_openalgo_inspection": "GO" if paper_ready else "NO_GO",
            "live_broker_trading": "NO_GO",
            "autonomous_bot_execution": "NO_GO",
        },
        "gate_count": len(gates),
        "pass_count": len(gates) - len(failed),
        "fail_count": len(failed),
        "gates": gates,
        "live_blockers": [
            {
                "blocker_id": gate["gate_id"],
                "reason": gate["reason"],
                "required_before_live": _live_requirement(gate["gate_id"]),
            }
            for gate in live_blockers
        ],
        "current_safe_scope": "research_and_paper_sim_review_only",
        "operator_message": _operator_message(paper_ready=paper_ready, research_ready=research_ready),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _reviewer_only(report: dict[str, Any]) -> bool:
    return all(
        [
            report.get("network_call_allowed") is False,
            report.get("live_call_performed") is False,
            report.get("confidence_boost_allowed") is False,
            report.get("gemini_can_execute_orders") is False,
            report.get("gemini_can_override_no_trade") is False,
            report.get("gemini_can_override_risk") is False,
            report.get("order_routing_enabled") is False,
        ]
    )


def _paper_bridge_only(report: dict[str, Any]) -> bool:
    return all(
        [
            report.get("safe_external_scope") == "paper_or_sim_review_only",
            report.get("openalgo_may_execute") is False,
            report.get("trading_bot_may_execute") is False,
            report.get("live_intent_allowed") is False,
            report.get("order_routing_enabled") is False,
            report.get("live_trading_blocked") is True,
        ]
    )


def _live_blocked(*reports: dict[str, Any]) -> bool:
    for report in reports:
        if "live_trading_blocked" in report and report.get("live_trading_blocked") is not True:
            return False
        if "live_trading_ready" in report and report.get("live_trading_ready") is True:
            return False
        if "live_broker_deployment_allowed" in report and report.get("live_broker_deployment_allowed") is True:
            return False
    return True


def _routing_disabled(*reports: dict[str, Any]) -> bool:
    for report in reports:
        if "order_routing_enabled" in report and report.get("order_routing_enabled") is not False:
            return False
        if "broker_order_created" in report and report.get("broker_order_created") is not False:
            return False
        if "broker_credentials_present" in report and report.get("broker_credentials_present") is not False:
            return False
    return True


def _gate(gate_id: str, name: str, passed: bool, scope: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "scope": scope,
        "status": "pass" if passed else "fail",
        "reason": reason,
    }


def _live_requirement(gate_id: str) -> str:
    requirements = {
        "FINAL-009": "Live trading remains intentionally out of scope until replay, paper, risk, reconciliation, broker, and human approval gates are separately certified.",
        "FINAL-010": "A future live route requires a separate broker adapter review, kill-switch proof, reconciliation proof, and signed human authorization.",
    }
    return requirements.get(gate_id, "Resolve this gate and rerun the final production-readiness audit.")


def _operator_message(*, paper_ready: bool, research_ready: bool) -> str:
    if paper_ready:
        return "Trade Vision is ready for research and paper/simulation OpenAlgo inspection. Live broker trading remains blocked."
    if research_ready:
        return "Trade Vision is research-ready, but paper/simulation bridge inspection still has blockers."
    return "Trade Vision has blocking readiness failures. Keep the system in local research mode only."


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}
