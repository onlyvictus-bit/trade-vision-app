from __future__ import annotations

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    ExecutorPreflightGateRecord,
    HumanApprovalGateRecord,
    KillSwitchRecheckRecord,
    ModePermissionMatrixRow,
    PaperExecutorPermissionReport,
    PaperExecutorPermissionRequest,
    SystemMode,
    SystemModeValue,
    KillSwitchState,
)


VERSION = "paper-executor-permission-matrix.v0.84"


def build_paper_executor_permission_report(
    payload: PaperExecutorPermissionRequest | None = None,
    *,
    system_mode: SystemMode | None = None,
    kill_switch: KillSwitchState | None = None,
) -> PaperExecutorPermissionReport:
    payload = payload or PaperExecutorPermissionRequest()
    mode = system_mode.mode if system_mode is not None else payload.requested_mode
    kill_state = kill_switch.state if kill_switch is not None else payload.kill_switch_state
    now = datetime.now(timezone.utc).isoformat()
    matrix = _permission_matrix(payload)
    kill_record = _kill_switch_recheck(kill_state, now)
    approval = _human_approval(payload)
    gates = _preflight_gates(payload, mode, kill_record, approval)
    rejections = [gate.evidence for gate in gates if gate.severity == "block" and not gate.passed]
    paper_review_ready = mode == SystemModeValue.PAPER and not rejections
    return PaperExecutorPermissionReport(
        permission_version=VERSION,
        generated_at=now,
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        target_executor=payload.target_executor,
        requested_mode=mode,
        permission_matrix=matrix,
        kill_switch_recheck=kill_record,
        human_approval=approval,
        preflight_gates=gates,
        accepted_for_external_paper_review=paper_review_ready,
        rejected=not paper_review_ready,
        rejection_reasons=rejections or ["External paper review is ready, but Trade Vision still creates no broker order."],
        mode_permission=_mode_permission(mode, paper_review_ready),
        broker_credentials_present=False,
        broker_order_created=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "v0.84 evaluates permission for external paper review; it does not execute orders.",
            "Kill switch and human veto are rechecked immediately before any future executor handoff.",
            "PAPER mode can only become external-review-ready when approval, risk, replay, paper validation, and reconciliation gates pass.",
            "LIVE mode remains blocked inside Trade Vision.",
        ],
    )


def _permission_matrix(payload: PaperExecutorPermissionRequest) -> list[ModePermissionMatrixRow]:
    return [
        ModePermissionMatrixRow(
            mode=SystemModeValue.MOCK,
            research_allowed=True,
            preview_intent_allowed=True,
            external_paper_review_allowed=False,
            live_handoff_allowed=False,
            required_gates=["mock_data", "capability_manifest"],
            reason="MOCK permits research and preview intent only.",
        ),
        ModePermissionMatrixRow(
            mode=SystemModeValue.SIMULATION,
            research_allowed=True,
            preview_intent_allowed=True,
            external_paper_review_allowed=False,
            live_handoff_allowed=False,
            required_gates=["deterministic_simulation", "simulation_integrity"],
            reason="SIMULATION permits research and preview intent only.",
        ),
        ModePermissionMatrixRow(
            mode=SystemModeValue.REPLAY,
            research_allowed=True,
            preview_intent_allowed=True,
            external_paper_review_allowed=False,
            live_handoff_allowed=False,
            required_gates=["deterministic_replay", "point_in_time_data"],
            reason="REPLAY permits replay-backed preview intent only.",
        ),
        ModePermissionMatrixRow(
            mode=SystemModeValue.PAPER,
            research_allowed=True,
            preview_intent_allowed=True,
            external_paper_review_allowed=_paper_review_gates_pass(payload),
            live_handoff_allowed=False,
            required_gates=[
                "dual_human_approval",
                "risk_gate",
                "replay_determinism",
                "paper_validation",
                "exchange_reconciliation",
                "kill_switch_armed",
            ],
            reason="PAPER may become external-review-ready only after all paper preflight gates pass.",
        ),
        ModePermissionMatrixRow(
            mode=SystemModeValue.LIVE,
            research_allowed=True,
            preview_intent_allowed=False,
            external_paper_review_allowed=False,
            live_handoff_allowed=False,
            required_gates=["separate_live_certification_not_implemented"],
            reason="LIVE is explicitly blocked inside Trade Vision.",
        ),
    ]


def _kill_switch_recheck(kill_state: str, checked_at: str) -> KillSwitchRecheckRecord:
    passed = kill_state == "armed"
    return KillSwitchRecheckRecord(
        checked_at=checked_at,
        kill_switch_state=kill_state,  # type: ignore[arg-type]
        kill_switch_rechecked=True,
        passes_executor_preflight=passed,
        blocks_reason=None if passed else f"Kill switch is {kill_state}; executor handoff is blocked.",
    )


def _human_approval(payload: PaperExecutorPermissionRequest) -> HumanApprovalGateRecord:
    if payload.human_veto_active:
        state = "veto_active"
        reason = "Human veto is active."
    elif payload.external_human_approval_present and payload.secondary_approval_present:
        state = "dual_approval_recorded"
        reason = None
    elif payload.external_human_approval_present:
        state = "single_approval_only"
        reason = "Secondary approval is missing."
    else:
        state = "missing"
        reason = "External human approval is missing."
    return HumanApprovalGateRecord(
        approval_id=_stable_id("approval", payload.symbol, payload.requested_by, payload.secondary_approver or "none", payload.seed),
        requested_by=payload.requested_by,
        primary_approval_present=payload.external_human_approval_present,
        secondary_approval_present=payload.secondary_approval_present,
        dual_approval_required=True,
        human_veto_active=payload.human_veto_active,
        approval_state=state,  # type: ignore[arg-type]
        blocks_reason=reason,
    )


def _preflight_gates(
    payload: PaperExecutorPermissionRequest,
    mode: SystemModeValue,
    kill_record: KillSwitchRecheckRecord,
    approval: HumanApprovalGateRecord,
) -> list[ExecutorPreflightGateRecord]:
    return [
        _gate("TV-V084-001", "mode permission matrix present", True, f"requested_mode={mode}", "Add mode matrix before executor preflight."),
        _gate("TV-V084-002", "kill switch armed and rechecked", kill_record.passes_executor_preflight, kill_record.blocks_reason or "kill_switch=armed", "Arm or reset kill switch before handoff."),
        _gate("TV-V084-003", "human veto inactive", not payload.human_veto_active, approval.blocks_reason or "human_veto=false", "Clear human veto before handoff."),
        _gate("TV-V084-004", "dual manual approval present", approval.approval_state == "dual_approval_recorded", approval.blocks_reason or "dual approval recorded", "Record primary and secondary approval."),
        _gate("TV-V084-005", "risk gate passed", payload.risk_gate_passed, f"risk_gate_passed={payload.risk_gate_passed}", "Pass portfolio, cooldown, and no-trade risk gates."),
        _gate("TV-V084-006", "replay determinism passed", payload.replay_determinism_passed, f"replay_determinism_passed={payload.replay_determinism_passed}", "Attach deterministic replay evidence."),
        _gate("TV-V084-007", "paper validation passed", payload.paper_validation_passed, f"paper_validation_passed={payload.paper_validation_passed}", "Complete paper validation before executor review."),
        _gate("TV-V084-008", "exchange reconciliation ready", payload.exchange_reconciliation_ready, f"exchange_reconciliation_ready={payload.exchange_reconciliation_ready}", "Prepare reconciliation before executor review."),
        _gate("TV-V084-009", "live mode blocked", mode != SystemModeValue.LIVE, f"mode={mode}", "Do not use Trade Vision for live handoff."),
        _gate("TV-FI-110", "no live broker route enabled", True, "broker_credentials_present=false, order_routing_enabled=false", "Remove live route from Trade Vision."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str) -> ExecutorPreflightGateRecord:
    return ExecutorPreflightGateRecord(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity="info" if passed else "block",
        evidence=evidence,
        remediation=remediation if not passed else "No action required.",
    )


def _paper_review_gates_pass(payload: PaperExecutorPermissionRequest) -> bool:
    return (
        payload.external_human_approval_present
        and payload.secondary_approval_present
        and not payload.human_veto_active
        and payload.kill_switch_state == "armed"
        and payload.risk_gate_passed
        and payload.replay_determinism_passed
        and payload.paper_validation_passed
        and payload.exchange_reconciliation_ready
        and payload.slippage_simulator_ready
        and payload.point_in_time_data_ready
    )


def _mode_permission(mode: SystemModeValue, paper_ready: bool) -> str:
    if mode == SystemModeValue.MOCK:
        return "mock_preview_only"
    if mode == SystemModeValue.SIMULATION:
        return "simulation_preview_only"
    if mode == SystemModeValue.REPLAY:
        return "replay_preview_only"
    if mode == SystemModeValue.PAPER:
        return "paper_review_ready" if paper_ready else "paper_review_blocked"
    return "live_blocked"


def _stable_id(*parts: object) -> str:
    return str(uuid5(NAMESPACE_URL, "tradevision:v084:" + ":".join(str(part) for part in parts)))
