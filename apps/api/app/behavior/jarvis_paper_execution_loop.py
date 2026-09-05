from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


PAPER_EXECUTION_LOOP_VERSION = "jarvis-paper-execution-loop-gate.v1.21"


def build_paper_execution_loop_report(
    *,
    symbol: str,
    jarvis_room: dict[str, Any],
    paper_safety: Any,
    lifecycle: Any,
    lifecycle_comparison: Any,
    lifecycle_evidence: Any,
    tradeability: Any,
) -> dict[str, Any]:
    paper = _as_dict(paper_safety)
    life = _as_dict(lifecycle)
    comparison = _as_dict(lifecycle_comparison)
    evidence = _as_dict(lifecycle_evidence)
    guidance = _as_dict(tradeability)
    gates = _gates(jarvis_room, paper, life, comparison, evidence, guidance)
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    loop_allowed = not blockers and not warnings and _loop_inputs_safe(paper, life, comparison, evidence, guidance)
    payload = {
        "version": PAPER_EXECUTION_LOOP_VERSION,
        "symbol": symbol.upper(),
        "paper_safety": paper.get("paper_safety_version"),
        "lifecycle": life.get("lifecycle_version"),
        "comparison": comparison.get("comparison_version"),
        "evidence": evidence.get("evidence_version"),
        "guidance": guidance.get("guidance_version"),
        "gates": gates,
    }
    return {
        "paper_loop_version": PAPER_EXECUTION_LOOP_VERSION,
        "symbol": symbol.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "loop_state": "paper_loop_ready" if loop_allowed else "blocked_by_safety" if blockers else "manual_review_required",
        "loop_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "jarvis_decision_summary": {
            "final_action": jarvis_room.get("final_action"),
            "trade_vision_decision": jarvis_room.get("trade_vision_decision", {}).get("final_trade_decision"),
            "confidence_cap_pct": jarvis_room.get("trade_vision_decision", {}).get("confidence_cap_pct"),
            "safety_blocking_gates": jarvis_room.get("safety_summary", {}).get("blocking_gates", []),
            "timeframe": jarvis_room.get("timeframe"),
        },
        "paper_intent_lifecycle": {
            "version": paper.get("paper_safety_version"),
            "current_state": paper.get("intent_lifecycle", {}).get("current_state"),
            "manual_review_required": paper.get("intent_lifecycle", {}).get("manual_review_required"),
            "next_required_approval": paper.get("intent_lifecycle", {}).get("next_required_approval"),
            "valid_until": paper.get("intent_lifecycle", {}).get("valid_until"),
            "paper_estimate_count": len(paper.get("paper_estimates", []) or []),
            "simulation_estimates_labeled": paper.get("all_execution_outputs_labeled_simulation_estimate"),
            "manual_review_required_for_executor_handoff": paper.get("manual_review_required_for_executor_handoff"),
        },
        "shadow_lifecycle": {
            "version": life.get("lifecycle_version"),
            "run_id": life.get("run_id"),
            "lifecycle_status": life.get("lifecycle_status"),
            "readiness_action": life.get("readiness_action"),
            "entry_type": life.get("entry_type"),
            "entry_price": life.get("entry_price"),
            "stop_loss": life.get("stop_loss"),
            "target": life.get("target"),
            "risk_reward": life.get("risk_reward"),
            "trade_state_path": life.get("trade_state_path", []),
            "fill_status": life.get("execution", {}).get("fill_status"),
            "fill_quality": life.get("execution", {}).get("fill_quality"),
            "outcome_label": life.get("outcome", {}).get("outcome_label"),
            "expected_MFE": life.get("expected_MFE"),
            "expected_MAE": life.get("expected_MAE"),
            "bars_to_target": life.get("bars_to_target"),
            "bars_to_sl": life.get("bars_to_sl"),
        },
        "scenario_evidence_summary": {
            "comparison_version": comparison.get("comparison_version"),
            "scenario_count": comparison.get("scenario_count"),
            "blocked_count": comparison.get("blocked_count"),
            "no_fill_count": comparison.get("no_fill_count"),
            "average_MFE": comparison.get("average_MFE"),
            "average_MAE": comparison.get("average_MAE"),
            "deterministic": comparison.get("deterministic"),
            "all_simulation_only": comparison.get("all_simulation_only"),
            "evidence_version": evidence.get("evidence_version"),
            "evidence_scenario_count": evidence.get("scenario_count"),
        },
        "tradeability_summary": {
            "guidance_version": guidance.get("guidance_version"),
            "tradeability_status": guidance.get("tradeability_status"),
            "paper_review_allowed": guidance.get("paper_review_allowed", False),
            "promotion_allowed": guidance.get("promotion_allowed", False),
            "blocker_count": len(guidance.get("blockers", []) or []),
            "improvement_step_count": len(guidance.get("improvement_steps", []) or []),
        },
        "gates": gates,
        "operator_message": _operator_message(blockers, warnings, loop_allowed),
        "paper_loop_allowed": loop_allowed,
        "external_executor_handoff_allowed": False,
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "broker_order_created": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _gates(
    room: dict[str, Any],
    paper: dict[str, Any],
    life: dict[str, Any],
    comparison: dict[str, Any],
    evidence: dict[str, Any],
    guidance: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _gate("PAPER-LOOP-001", "Paper safety report exists", paper.get("paper_safety_version") == "execution-intent-paper-safety-memory.v0.83", "block", "Build v0.83 paper safety memory before loop review."),
        _gate("PAPER-LOOP-002", "Manual review is required before external handoff", paper.get("manual_review_required_for_executor_handoff") is True, "block", "Paper loop must stay manual-review-first."),
        _gate("PAPER-LOOP-003", "All paper estimates are simulation-labeled", paper.get("all_execution_outputs_labeled_simulation_estimate") is True, "block", "Paper estimates must be labeled SIMULATION_ESTIMATE."),
        _gate("PAPER-LOOP-004", "Shadow lifecycle simulation exists", life.get("lifecycle_version") == "behavior-trade-lifecycle-simulation.v0.36", "block", "Need replay-only lifecycle report."),
        _gate("PAPER-LOOP-005", "Lifecycle remains simulation-only", life.get("simulation_only") is True and life.get("trade_allowed") is False, "block", "Lifecycle cannot approve orders."),
        _gate("PAPER-LOOP-006", "Lifecycle is deterministic and point-in-time", life.get("deterministic") is True and life.get("no_future_leakage") is True, "block", "Paper loop must be replay deterministic and leak-free."),
        _gate("PAPER-LOOP-007", "Scenario comparison exists", comparison.get("comparison_version") == "behavior-lifecycle-scenario-comparison.v0.37", "downgrade", "Compare multiple lifecycle scenarios before paper loop trust."),
        _gate("PAPER-LOOP-008", "Lifecycle evidence drilldown exists", evidence.get("evidence_version") == "behavior-lifecycle-evidence-drilldown.v0.38", "downgrade", "Need row-level evidence to explain paper loop."),
        _gate("PAPER-LOOP-009", "Tradeability guidance blocks unsafe promotion", guidance.get("promotion_allowed") is False, "block", "Paper loop cannot promote to paper/live execution."),
        _gate("PAPER-LOOP-010", "Jarvis final action is not forced into execution", room.get("trade_allowed") is False and room.get("order_routing_enabled") is False, "block", "Jarvis room must remain research-only."),
        _gate("PAPER-LOOP-011", "No live broker route", _read_only(paper, life, comparison, guidance), "block", "No paper/live broker route may be enabled."),
    ]


def _loop_inputs_safe(
    paper: dict[str, Any],
    life: dict[str, Any],
    comparison: dict[str, Any],
    evidence: dict[str, Any],
    guidance: dict[str, Any],
) -> bool:
    return all(
        [
            paper.get("paper_safety_version") == "execution-intent-paper-safety-memory.v0.83",
            life.get("lifecycle_version") == "behavior-trade-lifecycle-simulation.v0.36",
            comparison.get("comparison_version") == "behavior-lifecycle-scenario-comparison.v0.37",
            evidence.get("evidence_version") == "behavior-lifecycle-evidence-drilldown.v0.38",
            guidance.get("promotion_allowed") is False,
            _read_only(paper, life, comparison, guidance),
        ]
    )


def _read_only(paper: dict[str, Any], life: dict[str, Any], comparison: dict[str, Any], guidance: dict[str, Any]) -> bool:
    return all(
        [
            paper.get("broker_credentials_present") is False,
            paper.get("broker_order_created") is False,
            paper.get("order_routing_enabled") is False,
            paper.get("live_trading_blocked") is True,
            life.get("trade_allowed") is False,
            life.get("order_routing_enabled") is False,
            life.get("live_trading_blocked") is True,
            comparison.get("all_order_routing_disabled") is not False,
            comparison.get("all_live_trading_blocked") is not False,
            guidance.get("trade_allowed") is not True,
            guidance.get("order_routing_enabled") is not True,
            guidance.get("live_trading_blocked") is not False,
        ]
    )


def _operator_message(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], loop_allowed: bool) -> str:
    if blockers:
        return "Paper execution loop is blocked by safety gates; keep this setup in research/replay review."
    if warnings:
        return "Paper execution loop has warnings; use manual review only and do not hand off externally."
    if loop_allowed:
        return "Paper execution loop is ready for local simulation review only; it still cannot route orders."
    return "Paper execution loop is not approved for external executor handoff."


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}
