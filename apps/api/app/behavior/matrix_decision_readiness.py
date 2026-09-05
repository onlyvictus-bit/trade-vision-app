from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    MarketEvent,
    MatrixDecisionGate,
    MatrixDecisionReadinessReport,
    MatrixDecisionReadinessRequest,
    ReplayIndicatorMatrixRequest,
    ReplayIndicatorMatrixReport,
    ReplayIndicatorMatrixRow,
)
from .replay_indicator_matrix import build_replay_indicator_matrix_report


READINESS_VERSION = "behavior-matrix-decision-readiness.v0.35"
SAFETY_ROW_IDS = {
    "fakeout_risk_score",
    "absorption_score",
    "liquidity_score",
    "slippage_risk_proxy",
    "no_trade_safety_pressure",
}


def build_matrix_decision_readiness_report(
    request: MatrixDecisionReadinessRequest,
    events: list[MarketEvent],
) -> MatrixDecisionReadinessReport:
    """Convert the replay indicator matrix into deterministic decision-readiness gates."""

    matrix_request = ReplayIndicatorMatrixRequest(
        symbol=request.symbol,
        scenario_id=request.scenario_id,
        seed=request.seed,
        event_count=request.event_count,
        timeframe=request.timeframe,
        required_matrix_rows=request.required_matrix_rows,
    )
    matrix = build_replay_indicator_matrix_report(matrix_request, events)
    signal_counts = _signal_counts(matrix.rows)
    directional_bias, agreement_score = _directional_bias(matrix.rows)
    risk_score, safety_score, safety_pressure = _risk_and_safety(matrix.rows)
    gates = _gates(request, matrix, agreement_score, safety_pressure, safety_score)
    blocker_reasons = [gate.evidence for gate in gates if gate.blocks_decision and gate.status == "fail"]
    readiness_action = _readiness_action(directional_bias, blocker_reasons, agreement_score, safety_pressure, request)
    simulated_decision_allowed = readiness_action in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE"}
    output_hash = _hash_output(
        {
            "readiness_version": READINESS_VERSION,
            "matrix_output_hash": matrix.output_hash,
            "symbol": request.symbol,
            "scenario_id": request.scenario_id,
            "seed": request.seed,
            "event_count": request.event_count,
            "timeframe": request.timeframe,
            "directional_bias": directional_bias,
            "readiness_action": readiness_action,
            "agreement_score": round(agreement_score, 6),
            "safety_score": round(safety_score, 6),
            "risk_score": round(risk_score, 6),
            "blocker_reasons": blocker_reasons,
            "gates": [gate.model_dump(mode="json") for gate in gates],
        }
    )
    return MatrixDecisionReadinessReport(
        readiness_version=READINESS_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:{READINESS_VERSION}:{request.scenario_id}:{request.seed}:{request.event_count}:{request.timeframe}:{request.required_matrix_rows}")),
        base_matrix_version=matrix.matrix_version,
        symbol=request.symbol,
        scenario_id=request.scenario_id,
        seed=request.seed,
        event_count=request.event_count,
        timeframe=request.timeframe,
        matrix_indicator_count=matrix.matrix_indicator_count,
        ready_rows=matrix.ready_rows,
        proxy_rows=matrix.proxy_rows,
        blocked_rows=matrix.blocked_rows,
        bullish_rows=signal_counts["bullish"],
        bearish_rows=signal_counts["bearish"],
        watch_rows=signal_counts["watch"],
        neutral_rows=signal_counts["neutral"],
        directional_bias=directional_bias,
        readiness_action=readiness_action,
        simulated_decision_allowed=simulated_decision_allowed,
        trade_allowed=False,
        order_routing_enabled=False,
        confidence_score=round(min(agreement_score, safety_score), 4),
        agreement_score=round(agreement_score, 4),
        safety_score=round(safety_score, 4),
        risk_score=round(risk_score, 4),
        blocker_reasons=blocker_reasons,
        gate_summary=_gate_summary(gates),
        used_row_ids=[row.row_id for row in matrix.rows],
        matrix_output_hash=matrix.output_hash,
        input_event_chain_hash=matrix.input_event_chain_hash,
        output_hash=output_hash,
        deterministic=True,
        no_future_leakage=matrix.no_future_leakage,
        narrative_read_only=True,
        live_trading_blocked=True,
        gates=gates,
        reason=_reason(readiness_action, directional_bias, agreement_score, safety_pressure, blocker_reasons),
        notes=[
            "v0.35 turns the replay indicator matrix into decision-readiness gates only.",
            "A replay candidate is not a trade order, not paper mode, and not a broker route.",
            "Live trading remains blocked even if a simulated replay candidate appears.",
        ],
    )


def _signal_counts(rows: list[ReplayIndicatorMatrixRow]) -> dict[str, int]:
    counts = {"bullish": 0, "bearish": 0, "watch": 0, "neutral": 0}
    for row in rows:
        counts[row.signal] = counts.get(row.signal, 0) + 1
    return counts


def _directional_bias(rows: list[ReplayIndicatorMatrixRow]) -> tuple[str, float]:
    directional_rows = [row for row in rows if row.row_id not in SAFETY_ROW_IDS and row.readiness_status != "blocked"]
    positive = sum(max(row.normalized_score, 0.0) for row in directional_rows)
    negative = sum(max(-row.normalized_score, 0.0) for row in directional_rows)
    total = positive + negative
    if total == 0:
        return "NEUTRAL", 0.0
    agreement = max(positive, negative) / total
    if positive > negative:
        return "LONG", agreement
    if negative > positive:
        return "SHORT", agreement
    return "NEUTRAL", agreement


def _risk_and_safety(rows: list[ReplayIndicatorMatrixRow]) -> tuple[float, float, float]:
    fields = {row.row_id: row.output_fields for row in rows}
    fakeout = float(fields.get("fakeout_risk_score", {}).get("fakeout_risk", 0.0) or 0.0)
    absorption = float(fields.get("absorption_score", {}).get("absorption_score", 0.0) or 0.0)
    slippage = float(fields.get("slippage_risk_proxy", {}).get("slippage_risk", 0.0) or 0.0)
    no_trade = float(fields.get("no_trade_safety_pressure", {}).get("no_trade_pressure", 0.0) or 0.0)
    liquidity = float(fields.get("liquidity_score", {}).get("liquidity_score", 1.0) or 0.0)
    safety_pressure = max(fakeout, absorption, slippage, no_trade, 1 - liquidity)
    safety_score = _clamp01(1 - safety_pressure)
    risk_score = _clamp01((slippage * 0.35) + (fakeout * 0.25) + (absorption * 0.2) + (no_trade * 0.2))
    return risk_score, safety_score, safety_pressure


def _gates(
    request: MatrixDecisionReadinessRequest,
    matrix: ReplayIndicatorMatrixReport,
    agreement_score: float,
    safety_pressure: float,
    safety_score: float,
) -> list[MatrixDecisionGate]:
    matrix_coverage = matrix.matrix_indicator_count >= request.required_matrix_rows
    no_blocked_rows = matrix.blocked_rows == 0
    agreement_pass = agreement_score >= request.min_agreement_score
    safety_pass = safety_pressure <= request.max_safety_pressure
    return [
        _gate("TV-V035-001", "Matrix coverage", matrix_coverage, matrix.matrix_indicator_count / max(request.required_matrix_rows, 1), 1.0, f"{matrix.matrix_indicator_count} rows available; required {request.required_matrix_rows}.", True),
        _gate("TV-V035-002", "No blocked matrix rows", no_blocked_rows, 1.0 if no_blocked_rows else 0.0, 1.0, f"{matrix.blocked_rows} blocked rows in matrix.", True),
        _gate("TV-V035-003", "Point-in-time evidence", matrix.no_future_leakage, 1.0 if matrix.no_future_leakage else 0.0, 1.0, "Matrix declares no future leakage and uses replay current/prior bars.", True),
        _gate("TV-V035-004", "Directional agreement", agreement_pass, agreement_score, request.min_agreement_score, f"Directional agreement score {agreement_score:.2f}; threshold {request.min_agreement_score:.2f}.", True),
        _gate("TV-V035-005", "Safety pressure", safety_pass, safety_score, 1 - request.max_safety_pressure, f"Safety pressure {safety_pressure:.2f}; max allowed {request.max_safety_pressure:.2f}.", True),
        _gate("TV-V035-006", "Narrative read-only", True, 1.0, 1.0, "Decision readiness reason is read-only and cannot execute orders.", False),
        _gate("TV-V035-007", "Live trading blocked", True, 1.0, 1.0, "Live trading remains blocked regardless of replay candidate status.", False),
        _gate("TV-V035-008", "Order routing disabled", True, 1.0, 1.0, "No broker route, credentials, or outbound order path is enabled.", False),
        _gate("TV-V035-009", "Deterministic reproducibility", matrix.deterministic, 1.0 if matrix.deterministic else 0.0, 1.0, "Decision readiness is derived from deterministic matrix hash.", True),
    ]


def _gate(
    gate_id: str,
    name: str,
    passed: bool,
    score: float,
    threshold: float,
    evidence: str,
    blocks_decision: bool,
) -> MatrixDecisionGate:
    return MatrixDecisionGate(
        gate_id=gate_id,
        name=name,
        status="pass" if passed else "fail",
        score=round(_clamp01(score), 4),
        threshold=round(_clamp01(threshold), 4),
        evidence=evidence,
        blocks_decision=blocks_decision,
        remediation=None if passed else "Keep action at WAIT/NO_TRADE until this gate passes.",
    )


def _readiness_action(
    directional_bias: str,
    blocker_reasons: list[str],
    agreement_score: float,
    safety_pressure: float,
    request: MatrixDecisionReadinessRequest,
) -> str:
    if blocker_reasons:
        return "NO_TRADE"
    if directional_bias == "LONG" and agreement_score >= request.min_agreement_score and safety_pressure <= request.max_safety_pressure:
        return "REPLAY_BUY_CANDIDATE"
    if directional_bias == "SHORT" and agreement_score >= request.min_agreement_score and safety_pressure <= request.max_safety_pressure:
        return "REPLAY_SELL_CANDIDATE"
    return "WAIT"


def _gate_summary(gates: list[MatrixDecisionGate]) -> dict[str, int]:
    return {
        "pass": sum(1 for gate in gates if gate.status == "pass"),
        "warn": sum(1 for gate in gates if gate.status == "warn"),
        "fail": sum(1 for gate in gates if gate.status == "fail"),
    }


def _reason(
    readiness_action: str,
    directional_bias: str,
    agreement_score: float,
    safety_pressure: float,
    blocker_reasons: list[str],
) -> str:
    if blocker_reasons:
        return (
            f"{readiness_action}. Matrix bias is {directional_bias} with agreement {agreement_score:.0%}, "
            f"but safety pressure is {safety_pressure:.0%}. Blocking reasons: {'; '.join(blocker_reasons)}"
        )
    return (
        f"{readiness_action}. Matrix bias is {directional_bias}, agreement is {agreement_score:.0%}, "
        f"and safety pressure is {safety_pressure:.0%}. This is replay-only readiness, not order permission."
    )


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _hash_output(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
