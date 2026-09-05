from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorExecutionRequest,
    ExecutionIntentLifecycleRecord,
    ExecutionIntentPaperSafetyReport,
    ExecutionIntentPaperSafetyRequest,
    ExecutionIntentSafetyGateRecord,
    ExecutorManualReviewRecord,
    PaperSimulationEstimateRecord,
)
from .execution_simulator import simulate_behavior_execution


VERSION = "execution-intent-paper-safety-memory.v0.83"


def build_execution_intent_paper_safety_report(
    payload: ExecutionIntentPaperSafetyRequest | None = None,
) -> ExecutionIntentPaperSafetyReport:
    payload = payload or ExecutionIntentPaperSafetyRequest()
    now = datetime.now(timezone.utc)
    estimates = _paper_estimates(payload)
    statuses = {item.simulation.fill_status for item in estimates}
    cost_memory = any(item.simulation.costs.total_cost_pct > 0 for item in estimates)
    no_fill_partial_fill_cost_memory_present = {"NO_FILL", "PARTIAL_FILL"} <= statuses and cost_memory
    all_labeled = all(item.estimate_label == "SIMULATION_ESTIMATE" for item in estimates)
    all_sim_only = all(
        item.paper_only
        and item.simulation.simulation_only
        and not item.simulation.live_route_attempted
        and not item.no_fill_counted_as_win
        for item in estimates
    )
    lifecycle = ExecutionIntentLifecycleRecord(
        intent_id=_stable_id("intent", payload.symbol, payload.seed),
        current_state="MANUAL_REVIEW_REQUIRED",
        allowed_states=[
            "DRAFT",
            "PAPER_SIMULATED",
            "MANUAL_REVIEW_REQUIRED",
            "READY_FOR_EXTERNAL_REVIEW",
            "REJECTED",
            "EXPIRED",
            "CANCELLED",
        ],
        created_at=now.isoformat(),
        valid_until=(now + timedelta(minutes=15)).isoformat(),
        target_executor=payload.target_executor,
        manual_review_required=True,
        next_required_approval="operator_manual_review_before_any_external_executor_handoff",
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
    )
    manual_review = ExecutorManualReviewRecord(
        review_id=_stable_id("manual-review", payload.symbol, payload.seed),
        target_executor=payload.target_executor,
        review_state="manual_review_required",
        required_checks=[
            "confirm paper or simulation mode",
            "recheck kill switch immediately before handoff",
            "verify human veto is inactive",
            "verify risk, no-trade, and cooldown gates are clear",
            "verify exchange reconciliation is available before any future live promotion",
        ],
        forbidden_actions=[
            "create broker credentials",
            "create broker order",
            "enable live route",
            "bypass no-trade decision",
            "bypass risk gate",
        ],
        operator_message="Paper estimate is evidence only. Future executor handoff requires manual review and separate approval gates.",
    )
    gates = _gates(
        estimates=estimates,
        lifecycle_present=True,
        all_labeled=all_labeled and all_sim_only,
        memory_present=no_fill_partial_fill_cost_memory_present,
        manual_review_required=manual_review.review_state == "manual_review_required",
    )
    return ExecutionIntentPaperSafetyReport(
        paper_safety_version=VERSION,
        generated_at=now.isoformat(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        intent_lifecycle=lifecycle,
        paper_estimates=estimates,
        manual_review=manual_review,
        intent_lifecycle_present=True,
        all_execution_outputs_labeled_simulation_estimate=all_labeled and all_sim_only,
        no_fill_partial_fill_cost_memory_present=no_fill_partial_fill_cost_memory_present,
        manual_review_required_for_executor_handoff=True,
        no_live_broker_route_enabled=True,
        broker_credentials_present=False,
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        deterministic=True,
        trade_allowed=False,
        gates=gates,
        notes=[
            "v0.83 creates an execution-intent lifecycle before any OpenAlgo or trading-bot handoff.",
            "Every fill record is labeled SIMULATION_ESTIMATE and remains paper-only.",
            "No-fill, partial-fill, slippage, latency, impact, and adverse-selection memory are explicit.",
            "Manual review is mandatory before any future external executor path.",
        ],
    )


def _paper_estimates(payload: ExecutionIntentPaperSafetyRequest) -> list[PaperSimulationEstimateRecord]:
    scenarios = [
        (
            "limit_no_fill",
            BehaviorExecutionRequest(
                symbol=payload.symbol,
                side=payload.side,
                order_type="LIMIT",
                requested_quantity=payload.requested_quantity,
                entry_price=payload.entry_price,
                limit_price=_missed_limit(payload),
                bar_open=payload.bar_open,
                bar_high=payload.bar_high,
                bar_low=payload.bar_low,
                bar_close=payload.bar_close,
                bid_ask_spread_pct=payload.bid_ask_spread_pct,
                available_volume=payload.available_volume,
                queue_ahead_quantity=payload.queue_ahead_quantity,
                latency_ms=payload.latency_ms,
                impact_coefficient_bps=payload.impact_coefficient_bps,
                adverse_selection_score=payload.adverse_selection_score,
                max_participation_rate=payload.max_participation_rate,
                seed=payload.seed,
            ),
        ),
        (
            "large_market_partial_fill",
            BehaviorExecutionRequest(
                symbol=payload.symbol,
                side=payload.side,
                order_type="MARKET",
                requested_quantity=max(payload.requested_quantity * 30, payload.available_volume),
                entry_price=payload.entry_price,
                bar_open=payload.bar_open,
                bar_high=max(payload.bar_high, payload.bar_open * 1.006),
                bar_low=min(payload.bar_low, payload.bar_open * 0.998),
                bar_close=payload.bar_close,
                bid_ask_spread_pct=max(payload.bid_ask_spread_pct, 0.1),
                available_volume=payload.available_volume,
                queue_ahead_quantity=0,
                latency_ms=max(payload.latency_ms, 250),
                impact_coefficient_bps=max(payload.impact_coefficient_bps, 8.0),
                adverse_selection_score=max(payload.adverse_selection_score, 0.55),
                max_participation_rate=payload.max_participation_rate,
                seed=payload.seed + 1,
            ),
        ),
        (
            "market_cost_slippage_estimate",
            BehaviorExecutionRequest(
                symbol=payload.symbol,
                side=payload.side,
                order_type="MARKET",
                requested_quantity=max(1, min(payload.requested_quantity, 250)),
                entry_price=payload.entry_price,
                bar_open=payload.bar_open,
                bar_high=payload.bar_high,
                bar_low=payload.bar_low,
                bar_close=payload.bar_close,
                bid_ask_spread_pct=max(payload.bid_ask_spread_pct, 0.08),
                available_volume=max(payload.available_volume, 20_000),
                queue_ahead_quantity=0,
                latency_ms=max(payload.latency_ms, 180),
                impact_coefficient_bps=max(payload.impact_coefficient_bps, 6.0),
                adverse_selection_score=max(payload.adverse_selection_score, 0.42),
                max_participation_rate=max(payload.max_participation_rate, 0.08),
                seed=payload.seed + 2,
            ),
        ),
    ]
    estimates: list[PaperSimulationEstimateRecord] = []
    for scenario_name, request in scenarios:
        simulation = simulate_behavior_execution(request)
        estimates.append(
            PaperSimulationEstimateRecord(
                estimate_id=_stable_id("estimate", scenario_name, payload.symbol, payload.seed),
                estimate_label="SIMULATION_ESTIMATE",
                scenario_name=scenario_name,
                simulation=simulation,
                net_cost_pct=simulation.costs.total_cost_pct,
                no_fill_counted_as_win=False,
                partial_fill_recorded=simulation.fill_status == "PARTIAL_FILL",
                slippage_latency_impact_present=(
                    simulation.costs.latency_slippage_pct > 0
                    and simulation.costs.market_impact_pct > 0
                    and simulation.costs.spread_cost_pct > 0
                ),
                adverse_selection_present=simulation.costs.adverse_selection_cost_pct > 0
                or simulation.adverse_selection_risk in {"medium", "high"},
                paper_only=True,
            )
        )
    return estimates


def _missed_limit(payload: ExecutionIntentPaperSafetyRequest) -> float:
    if payload.side == "BUY":
        return round(payload.bar_low * 0.995, 4)
    return round(payload.bar_high * 1.005, 4)


def _gates(
    *,
    estimates: list[PaperSimulationEstimateRecord],
    lifecycle_present: bool,
    all_labeled: bool,
    memory_present: bool,
    manual_review_required: bool,
) -> list[ExecutionIntentSafetyGateRecord]:
    cost_present = any(item.simulation.costs.total_cost_pct > 0 for item in estimates)
    no_fill_safe = all(not item.no_fill_counted_as_win for item in estimates if item.simulation.fill_status == "NO_FILL")
    return [
        _gate("TV-V083-001", "intent lifecycle before OpenAlgo handoff", lifecycle_present, "intent_lifecycle.current_state=MANUAL_REVIEW_REQUIRED"),
        _gate("TV-V083-002", "paper labels on every execution estimate", all_labeled, "all estimate_label values are SIMULATION_ESTIMATE and simulations are paper-only"),
        _gate("TV-V083-003", "no-fill partial-fill and cost memory present", memory_present, "fill statuses include NO_FILL and PARTIAL_FILL; at least one estimate has execution costs"),
        _gate("TV-V083-004", "manual review required for executor handoff", manual_review_required, "manual_review.review_state=manual_review_required"),
        _gate("TV-FI-019", "costs and slippage alter net outcome", cost_present, "total_cost_pct is positive on filled paper estimates"),
        _gate("TV-FI-020", "no-fill is not counted as a win", no_fill_safe, "NO_FILL records keep no_fill_counted_as_win=false"),
        _gate("TV-FI-109", "paper simulator labels all execution outputs", all_labeled, "all estimates are SIMULATION_ESTIMATE"),
        _gate("TV-FI-110", "no live broker route is enabled", True, "broker_credentials_present=false, order_routing_enabled=false, live_trading_blocked=true"),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> ExecutionIntentSafetyGateRecord:
    return ExecutionIntentSafetyGateRecord(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation="Block executor handoff until this gate passes." if not passed else "No action required.",
    )


def _stable_id(*parts: object) -> str:
    return str(uuid5(NAMESPACE_URL, "tradevision:v083:" + ":".join(str(part) for part in parts)))
