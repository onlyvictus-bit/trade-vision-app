from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from statistics import fmean
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorExecutionRequest,
    CandleBar,
    CandleSeries,
    LifecycleEvidenceDrilldownReport,
    LifecycleEvidenceDrilldownRequest,
    LifecycleEvidenceRowContribution,
    LifecycleEvidenceScenarioDrilldown,
    MarketEvent,
    MatrixDecisionGate,
    MatrixDecisionReadinessRequest,
    OutcomeLabelRequest,
    ReplayIndicatorMatrixRequest,
    ReplayIndicatorMatrixRow,
    ScenarioTradeabilityGuidance,
    TradeabilityGuidanceReport,
    TradeabilityGuidanceRequest,
    TradeabilityImprovementStep,
    TradeLifecycleScenarioComparisonItem,
    TradeLifecycleScenarioComparisonReport,
    TradeLifecycleScenarioComparisonRequest,
    TradeLifecycleScenarioConfig,
    TradeLifecycleSimulationReport,
    TradeLifecycleSimulationRequest,
)
from .execution_simulator import simulate_behavior_execution
from .matrix_decision_readiness import SAFETY_ROW_IDS, build_matrix_decision_readiness_report
from .outcome_learning import label_trade_outcome
from .replay_indicator_matrix import build_replay_indicator_matrix_report
from .replay_indicator_validation import build_replay_indicator_validation_report


LIFECYCLE_VERSION = "behavior-trade-lifecycle-simulation.v0.36"
COMPARISON_VERSION = "behavior-lifecycle-scenario-comparison.v0.37"
EVIDENCE_VERSION = "behavior-lifecycle-evidence-drilldown.v0.38"
GUIDANCE_VERSION = "behavior-lifecycle-tradeability-guidance.v0.39"
SAFETY_FIELD_BY_ROW = {
    "fakeout_risk_score": "fakeout_risk",
    "absorption_score": "absorption_score",
    "slippage_risk_proxy": "slippage_risk",
    "no_trade_safety_pressure": "no_trade_pressure",
}


def build_trade_lifecycle_simulation_report(
    request: TradeLifecycleSimulationRequest,
    events: list[MarketEvent],
) -> TradeLifecycleSimulationReport:
    """Compose readiness, execution realism, and outcome labeling into one replay-only lifecycle audit."""

    readiness_request = MatrixDecisionReadinessRequest(
        symbol=request.symbol,
        scenario_id=request.scenario_id,
        seed=request.seed,
        event_count=request.event_count,
        timeframe=request.timeframe,
        required_matrix_rows=request.required_matrix_rows,
        min_agreement_score=request.min_agreement_score,
        max_safety_pressure=request.max_safety_pressure,
    )
    readiness = build_matrix_decision_readiness_report(readiness_request, events)
    chart = build_replay_indicator_validation_report(readiness_request, events)
    bars = chart.candle_series.bars
    entry_index = min(max(request.entry_after_bars, 1), len(bars) - 1)
    entry_bar = bars[entry_index]
    direction = "short" if readiness.directional_bias == "SHORT" else "long"
    entry_price, stop_loss, target, atr_proxy = _trade_levels(bars, entry_index, direction)
    risk_reward = _risk_reward(entry_price, stop_loss, target)
    effective_quantity = request.shadow_quantity if _shadow_execution_allowed(request, readiness.readiness_action) else 0
    execution = simulate_behavior_execution(
        _execution_request(request, entry_bar, direction, entry_price, effective_quantity, readiness.risk_score)
    )
    run_id = _run_id(request)
    outcome = label_trade_outcome(
        OutcomeLabelRequest(
            series=_outcome_series(chart.candle_series, entry_index, request.max_holding_bars),
            direction=direction,  # type: ignore[arg-type]
            entry_price=execution.fill_price or entry_price,
            stop_loss=stop_loss,
            target=target,
            entry_timestamp_ns=entry_bar.timestamp_ns,
            max_holding_bars=request.max_holding_bars,
            pattern_id=f"{request.scenario_id}:{readiness.readiness_action}",
            run_id=run_id,
        )
    )
    lifecycle_status = _lifecycle_status(readiness.readiness_action, execution.fill_status, request.respect_readiness_block)
    gates = _gates(request, readiness, execution.simulation_only, execution.live_route_attempted, outcome.run_id)
    output_hash = _hash_output(
        {
            "lifecycle_version": LIFECYCLE_VERSION,
            "run_id": run_id,
            "readiness_output_hash": readiness.output_hash,
            "chart_output_hash": chart.output_hash,
            "execution": execution.model_dump(mode="json"),
            "outcome": outcome.model_dump(mode="json"),
            "entry": {
                "entry_sequence_number": entry_bar.sequence_number,
                "entry_timestamp_ns": entry_bar.timestamp_ns,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "atr_proxy": atr_proxy,
            },
            "lifecycle_status": lifecycle_status,
            "gates": [gate.model_dump(mode="json") for gate in gates],
        }
    )
    blocker_reasons = _blocker_reasons(readiness, execution.missed_trade_reason, request.respect_readiness_block)
    return TradeLifecycleSimulationReport(
        lifecycle_version=LIFECYCLE_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
        symbol=request.symbol.upper(),
        scenario_id=request.scenario_id,
        seed=request.seed,
        event_count=request.event_count,
        timeframe=request.timeframe,
        base_readiness_version=readiness.readiness_version,
        base_chart_version=chart.validation_version,
        readiness_action=readiness.readiness_action,
        lifecycle_status=lifecycle_status,  # type: ignore[arg-type]
        directional_bias=readiness.directional_bias,
        entry_type="NEXT_5M_OPEN_SHADOW",
        entry_sequence_number=entry_bar.sequence_number,
        entry_timestamp_ns=entry_bar.timestamp_ns,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target=target,
        risk_reward=risk_reward,
        atr_proxy=atr_proxy,
        trade_state_path=_state_path(lifecycle_status, outcome.outcome_label),
        readiness=readiness,
        execution=execution,
        outcome=outcome,
        expected_MFE=outcome.mfe,
        expected_MAE=outcome.mae,
        bars_to_target=outcome.bars_to_target,
        bars_to_sl=outcome.bars_to_sl,
        blocker_reasons=blocker_reasons,
        lifecycle_gate_summary=_gate_summary(gates),
        gates=gates,
        input_event_chain_hash=chart.input_event_chain_hash,
        readiness_output_hash=readiness.output_hash,
        outcome_run_id=outcome.run_id,
        execution_simulation_id=execution.simulation_id,
        output_hash=output_hash,
        deterministic=True,
        no_future_leakage=readiness.no_future_leakage and chart.no_future_leakage,
        simulation_only=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        narrative_read_only=True,
        reason=_reason(lifecycle_status, readiness.readiness_action, outcome.outcome_label, blocker_reasons),
        notes=[
            "v0.36 is a replay-only lifecycle audit: readiness -> simulated fill -> outcome label -> state path.",
            "The lifecycle report may compute shadow MFE/MAE for debugging, but it cannot approve an order.",
            "Live trading, paper trading, broker credentials, and outbound routing remain blocked.",
        ],
    )


def build_trade_lifecycle_scenario_comparison_report(
    request: TradeLifecycleScenarioComparisonRequest,
    event_factory: Callable[[int, str, int], list[MarketEvent]],
) -> TradeLifecycleScenarioComparisonReport:
    """Run several lifecycle simulations and compare them without granting trade permission."""

    lifecycle_reports: list[TradeLifecycleSimulationReport] = []
    for scenario in request.scenarios:
        scenario_request = TradeLifecycleSimulationRequest(
            symbol=request.symbol,
            scenario_id=scenario.scenario_id,
            seed=scenario.seed,
            event_count=request.event_count,
            timeframe=request.timeframe,
            required_matrix_rows=request.required_matrix_rows,
            min_agreement_score=scenario.min_agreement_score if scenario.min_agreement_score is not None else request.min_agreement_score,
            max_safety_pressure=scenario.max_safety_pressure if scenario.max_safety_pressure is not None else request.max_safety_pressure,
            entry_after_bars=scenario.entry_after_bars if scenario.entry_after_bars is not None else request.entry_after_bars,
            shadow_quantity=scenario.shadow_quantity if scenario.shadow_quantity is not None else request.shadow_quantity,
            max_holding_bars=request.max_holding_bars,
            respect_readiness_block=scenario.respect_readiness_block if scenario.respect_readiness_block is not None else request.respect_readiness_block,
        )
        events = event_factory(scenario_request.seed, scenario_request.scenario_id, scenario_request.event_count)
        lifecycle_reports.append(build_trade_lifecycle_simulation_report(scenario_request, events))

    items = [_comparison_item(scenario.label, report) for scenario, report in zip(request.scenarios, lifecycle_reports)]
    candidate_count = sum(1 for item in items if item.readiness_action in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE"})
    blocked_count = sum(1 for item in items if item.lifecycle_status == "BLOCKED_BY_READINESS")
    no_fill_count = sum(1 for item in items if item.lifecycle_status == "SHADOW_NO_FILL")
    rejected_count = sum(1 for item in items if item.fill_status == "REJECTED_SIMULATION")
    target_hit_count = sum(1 for item in items if item.outcome_label == "TARGET_HIT")
    stop_hit_count = sum(1 for item in items if item.outcome_label == "SL_HIT")
    average_mfe = round(fmean([item.expected_MFE for item in items]), 4) if items else 0.0
    average_mae = round(fmean([item.expected_MAE for item in items]), 4) if items else 0.0
    best = max(items, key=lambda item: item.expected_MFE - item.expected_MAE, default=None)
    worst = min(items, key=lambda item: item.expected_MFE - item.expected_MAE, default=None)
    all_trade_allowed_false = all(not report.trade_allowed for report in lifecycle_reports)
    all_order_routing_disabled = all(not report.order_routing_enabled for report in lifecycle_reports)
    all_live_trading_blocked = all(report.live_trading_blocked for report in lifecycle_reports)
    all_simulation_only = all(report.simulation_only and report.execution.simulation_only for report in lifecycle_reports)
    deterministic = all(report.deterministic for report in lifecycle_reports)
    no_future_leakage = all(report.no_future_leakage for report in lifecycle_reports)
    gates = _comparison_gates(
        scenario_count=len(items),
        deterministic=deterministic,
        no_future_leakage=no_future_leakage,
        all_trade_allowed_false=all_trade_allowed_false,
        all_order_routing_disabled=all_order_routing_disabled,
        all_live_trading_blocked=all_live_trading_blocked,
        all_simulation_only=all_simulation_only,
        candidate_count=candidate_count,
    )
    output_hash = _hash_output(
        {
            "comparison_version": COMPARISON_VERSION,
            "symbol": request.symbol.upper(),
            "timeframe": request.timeframe,
            "event_count": request.event_count,
            "items": [item.model_dump(mode="json") for item in items],
            "gates": [gate.model_dump(mode="json") for gate in gates],
        }
    )
    return TradeLifecycleScenarioComparisonReport(
        comparison_version=COMPARISON_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=_comparison_run_id(request),
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        event_count=request.event_count,
        scenario_count=len(items),
        candidate_count=candidate_count,
        blocked_count=blocked_count,
        no_fill_count=no_fill_count,
        rejected_count=rejected_count,
        target_hit_count=target_hit_count,
        stop_hit_count=stop_hit_count,
        average_MFE=average_mfe,
        average_MAE=average_mae,
        best_scenario_label=best.label if best else None,
        worst_scenario_label=worst.label if worst else None,
        items=items,
        all_trade_allowed_false=all_trade_allowed_false,
        all_order_routing_disabled=all_order_routing_disabled,
        all_live_trading_blocked=all_live_trading_blocked,
        all_simulation_only=all_simulation_only,
        deterministic=deterministic,
        no_future_leakage=no_future_leakage,
        output_hash=output_hash,
        gates=gates,
        notes=[
            "v0.37 compares multiple replay lifecycle scenarios side by side.",
            "Candidate scenarios are shadow candidates only; the comparison cannot approve paper or live orders.",
            "Use this report to understand why similar replay conditions are blocked, simulated, rejected, or no-filled.",
        ],
    )


def build_lifecycle_evidence_drilldown_report(
    request: LifecycleEvidenceDrilldownRequest,
    event_factory: Callable[[int, str, int], list[MarketEvent]],
) -> LifecycleEvidenceDrilldownReport:
    """Explain which replay matrix rows drive each lifecycle scenario without granting trading authority."""

    comparison_request = TradeLifecycleScenarioComparisonRequest(
        symbol=request.symbol,
        timeframe=request.timeframe,
        event_count=request.event_count,
        required_matrix_rows=request.required_matrix_rows,
        min_agreement_score=request.min_agreement_score,
        max_safety_pressure=request.max_safety_pressure,
        entry_after_bars=request.entry_after_bars,
        shadow_quantity=request.shadow_quantity,
        max_holding_bars=request.max_holding_bars,
        respect_readiness_block=request.respect_readiness_block,
        scenarios=request.scenarios,
    )
    comparison = build_trade_lifecycle_scenario_comparison_report(comparison_request, event_factory)
    items: list[LifecycleEvidenceScenarioDrilldown] = []
    for scenario in request.scenarios:
        lifecycle_request = _lifecycle_request_from_scenario(request, scenario)
        events = event_factory(lifecycle_request.seed, lifecycle_request.scenario_id, lifecycle_request.event_count)
        lifecycle = build_trade_lifecycle_simulation_report(lifecycle_request, events)
        matrix = build_replay_indicator_matrix_report(
            ReplayIndicatorMatrixRequest(
                symbol=lifecycle_request.symbol,
                scenario_id=lifecycle_request.scenario_id,
                seed=lifecycle_request.seed,
                event_count=lifecycle_request.event_count,
                timeframe=lifecycle_request.timeframe,
                required_matrix_rows=lifecycle_request.required_matrix_rows,
            ),
            events,
        )
        items.append(_evidence_item(scenario.label, lifecycle, matrix.rows, request.top_n_rows))

    all_trade_allowed_false = all(not item.trade_allowed for item in items)
    all_order_routing_disabled = all(not item.order_routing_enabled for item in items)
    all_live_trading_blocked = all(item.live_trading_blocked for item in items)
    no_future_leakage = comparison.no_future_leakage and all(item.no_future_leakage for item in items)
    deterministic = comparison.deterministic and len(items) == len(request.scenarios)
    gates = _evidence_gates(
        scenario_count=len(items),
        expected_count=len(request.scenarios),
        deterministic=deterministic,
        no_future_leakage=no_future_leakage,
        all_trade_allowed_false=all_trade_allowed_false,
        all_order_routing_disabled=all_order_routing_disabled,
        all_live_trading_blocked=all_live_trading_blocked,
        row_evidence_present=all(
            item.top_directional_drivers or item.top_counter_drivers or item.top_safety_pressures for item in items
        ),
        safety_evidence_present=all(item.top_safety_pressures for item in items),
    )
    output_hash = _hash_output(
        {
            "evidence_version": EVIDENCE_VERSION,
            "comparison_output_hash": comparison.output_hash,
            "symbol": request.symbol.upper(),
            "timeframe": request.timeframe,
            "event_count": request.event_count,
            "items": [item.model_dump(mode="json") for item in items],
            "gates": [gate.model_dump(mode="json") for gate in gates],
        }
    )
    return LifecycleEvidenceDrilldownReport(
        evidence_version=EVIDENCE_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=_evidence_run_id(request),
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        event_count=request.event_count,
        scenario_count=len(items),
        candidate_count=comparison.candidate_count,
        blocked_count=comparison.blocked_count,
        base_comparison_version=comparison.comparison_version,
        comparison_output_hash=comparison.output_hash,
        dominant_directional_driver=_dominant_row_id(
            [row for item in items for row in item.top_directional_drivers]
        ),
        dominant_safety_pressure=_dominant_row_id(
            [row for item in items for row in item.top_safety_pressures]
        ),
        items=items,
        all_trade_allowed_false=all_trade_allowed_false,
        all_order_routing_disabled=all_order_routing_disabled,
        all_live_trading_blocked=all_live_trading_blocked,
        deterministic=deterministic,
        no_future_leakage=no_future_leakage,
        narrative_read_only=True,
        output_hash=output_hash,
        gates=gates,
        notes=[
            "v0.38 explains lifecycle scenarios by row-level matrix evidence.",
            "Directional drivers and safety pressures are replay evidence only; they cannot approve paper or live orders.",
            "Use this drilldown to debug why a scenario is a candidate, blocked, rejected, or no-filled before adding new intelligence.",
        ],
    )


def build_tradeability_guidance_report(
    request: TradeabilityGuidanceRequest,
    event_factory: Callable[[int, str, int], list[MarketEvent]],
) -> TradeabilityGuidanceReport:
    """Convert lifecycle evidence into replay-only tradeability guidance and improvement targets."""

    evidence_request = LifecycleEvidenceDrilldownRequest(
        symbol=request.symbol,
        timeframe=request.timeframe,
        event_count=request.event_count,
        required_matrix_rows=request.required_matrix_rows,
        min_agreement_score=request.min_agreement_score,
        max_safety_pressure=request.max_safety_pressure,
        entry_after_bars=request.entry_after_bars,
        shadow_quantity=request.shadow_quantity,
        max_holding_bars=request.max_holding_bars,
        respect_readiness_block=request.respect_readiness_block,
        top_n_rows=request.top_n_rows,
        scenarios=request.scenarios,
    )
    evidence = build_lifecycle_evidence_drilldown_report(evidence_request, event_factory)
    items = [_guidance_item(item, request.guidance_threshold) for item in evidence.items]
    blocked_count = sum(1 for item in items if item.tradeability_status == "BLOCKED")
    avoid_count = sum(1 for item in items if item.tradeability_status == "AVOID")
    research_watch_count = sum(1 for item in items if item.tradeability_status == "RESEARCH_WATCH")
    replay_candidate_count = sum(1 for item in items if item.tradeability_status == "REPLAY_CANDIDATE_RESEARCH_ONLY")
    safest = max(items, key=lambda item: item.tradeability_score, default=None)
    riskiest = min(items, key=lambda item: item.tradeability_score, default=None)
    all_trade_allowed_false = all(not item.trade_allowed for item in items)
    all_order_routing_disabled = all(not item.order_routing_enabled for item in items)
    all_live_trading_blocked = all(item.live_trading_blocked for item in items)
    no_future_leakage = evidence.no_future_leakage and all(item.no_future_leakage for item in items)
    deterministic = evidence.deterministic and len(items) == len(evidence.items)
    top_global_blocker = _top_global_blocker(items)
    gates = _guidance_gates(
        evidence_version=evidence.evidence_version,
        scenario_count=len(items),
        expected_count=evidence.scenario_count,
        improvement_steps_present=all(item.improvement_steps for item in items),
        promotion_allowed=False,
        deterministic=deterministic,
        no_future_leakage=no_future_leakage,
        all_trade_allowed_false=all_trade_allowed_false,
        all_order_routing_disabled=all_order_routing_disabled,
        all_live_trading_blocked=all_live_trading_blocked,
    )
    output_hash = _hash_output(
        {
            "guidance_version": GUIDANCE_VERSION,
            "evidence_output_hash": evidence.output_hash,
            "symbol": request.symbol.upper(),
            "timeframe": request.timeframe,
            "event_count": request.event_count,
            "items": [item.model_dump(mode="json") for item in items],
            "gates": [gate.model_dump(mode="json") for gate in gates],
        }
    )
    return TradeabilityGuidanceReport(
        guidance_version=GUIDANCE_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=_guidance_run_id(request),
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        event_count=request.event_count,
        scenario_count=len(items),
        blocked_count=blocked_count,
        avoid_count=avoid_count,
        research_watch_count=research_watch_count,
        replay_candidate_research_only_count=replay_candidate_count,
        base_evidence_version=evidence.evidence_version,
        evidence_output_hash=evidence.output_hash,
        safest_scenario_label=safest.label if safest else None,
        riskiest_scenario_label=riskiest.label if riskiest else None,
        top_global_blocker=top_global_blocker,
        items=items,
        all_trade_allowed_false=all_trade_allowed_false,
        all_order_routing_disabled=all_order_routing_disabled,
        all_live_trading_blocked=all_live_trading_blocked,
        deterministic=deterministic,
        no_future_leakage=no_future_leakage,
        narrative_read_only=True,
        promotion_allowed=False,
        output_hash=output_hash,
        gates=gates,
        notes=[
            "v0.39 translates row-level lifecycle evidence into research-only tradeability guidance.",
            "Guidance identifies blockers and improvement targets; it cannot approve paper or live orders.",
            "Every scenario must remain simulation-only until replay, data, execution, risk, and human approval gates are promoted separately.",
        ],
    )


def _guidance_item(
    evidence: LifecycleEvidenceScenarioDrilldown,
    guidance_threshold: float,
) -> ScenarioTradeabilityGuidance:
    worst_safety = evidence.top_safety_pressures[0] if evidence.top_safety_pressures else None
    best_driver = evidence.top_directional_drivers[0] if evidence.top_directional_drivers else None
    worst_pressure = worst_safety.contribution_score if worst_safety else 0.0
    raw_score = evidence.agreement_score * evidence.safety_score * (1 - min(evidence.risk_score * 0.25, 0.25))
    if evidence.lifecycle_status == "BLOCKED_BY_READINESS":
        raw_score = min(raw_score, 0.35)
    if evidence.fill_status in {"REJECTED_SIMULATION", "NO_FILL"}:
        raw_score = min(raw_score, 0.45)
    if worst_pressure >= 0.65:
        raw_score = min(raw_score, 0.5)
    tradeability_score = round(max(0.0, min(raw_score, 1.0)), 4)
    status = _tradeability_status(evidence, tradeability_score, worst_pressure, guidance_threshold)
    next_action = _next_safe_action(evidence, status, worst_safety)
    steps = _improvement_steps(evidence, status, worst_safety)
    blockers = [step.rationale for step in steps if step.blocks_promotion]
    output_hash = _hash_output(
        {
            "scenario": evidence.scenario_id,
            "seed": evidence.seed,
            "evidence_output_hash": evidence.output_hash,
            "tradeability_status": status,
            "next_safe_action": next_action,
            "score": tradeability_score,
            "steps": [step.model_dump(mode="json") for step in steps],
        }
    )
    return ScenarioTradeabilityGuidance(
        label=evidence.label,
        scenario_id=evidence.scenario_id,
        seed=evidence.seed,
        readiness_action=evidence.readiness_action,
        lifecycle_status=evidence.lifecycle_status,
        directional_bias=evidence.directional_bias,
        tradeability_status=status,  # type: ignore[arg-type]
        next_safe_action=next_action,  # type: ignore[arg-type]
        tradeability_score=tradeability_score,
        best_driver_row_id=best_driver.row_id if best_driver else None,
        worst_safety_row_id=worst_safety.row_id if worst_safety else None,
        agreement_score=evidence.agreement_score,
        safety_score=evidence.safety_score,
        risk_score=evidence.risk_score,
        promotion_blockers=blockers,
        improvement_steps=steps,
        reason=_guidance_reason(status, next_action, tradeability_score, best_driver, worst_safety),
        must_remain_simulation_only=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        no_future_leakage=evidence.no_future_leakage,
        output_hash=output_hash,
    )


def _tradeability_status(
    evidence: LifecycleEvidenceScenarioDrilldown,
    tradeability_score: float,
    worst_pressure: float,
    guidance_threshold: float,
) -> str:
    if evidence.lifecycle_status == "BLOCKED_BY_READINESS" or evidence.readiness_action in {"NO_TRADE", "BLOCK"}:
        return "BLOCKED"
    if worst_pressure >= 0.7 or evidence.fill_status == "NO_FILL":
        return "AVOID"
    if evidence.readiness_action in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE"} and tradeability_score >= guidance_threshold:
        return "REPLAY_CANDIDATE_RESEARCH_ONLY"
    return "RESEARCH_WATCH"


def _next_safe_action(
    evidence: LifecycleEvidenceScenarioDrilldown,
    status: str,
    worst_safety: LifecycleEvidenceRowContribution | None,
) -> str:
    if status == "BLOCKED":
        return "NO_TRADE"
    if worst_safety and worst_safety.row_id == "slippage_risk_proxy":
        return "IMPROVE_LIQUIDITY"
    if worst_safety and worst_safety.row_id == "fakeout_risk_score":
        return "AVOID_FAKEOUT"
    if status == "REPLAY_CANDIDATE_RESEARCH_ONLY":
        return "REPLAY_REVIEW_ONLY"
    if evidence.top_counter_drivers:
        return "WAIT_FOR_RETEST"
    return "COLLECT_MORE_EVIDENCE"


def _improvement_steps(
    evidence: LifecycleEvidenceScenarioDrilldown,
    status: str,
    worst_safety: LifecycleEvidenceRowContribution | None,
) -> list[TradeabilityImprovementStep]:
    steps: list[TradeabilityImprovementStep] = [
        TradeabilityImprovementStep(
            step_id=f"{evidence.scenario_id}:{evidence.seed}:permission-lock",
            category="permission_lock",
            source_row_id=None,
            priority="critical",
            current_value=None,
            target_value=None,
            action="Keep this setup in MOCK/REPLAY review only; do not route paper or live orders from this report.",
            rationale="Tradeability guidance is research evidence, not execution authority.",
            blocks_promotion=True,
        )
    ]
    if evidence.lifecycle_status == "BLOCKED_BY_READINESS":
        steps.append(
            TradeabilityImprovementStep(
                step_id=f"{evidence.scenario_id}:{evidence.seed}:readiness-block",
                category="evidence_quality",
                source_row_id=None,
                priority="critical",
                current_value=evidence.agreement_score,
                target_value=0.65,
                action="Resolve readiness blockers before reviewing any entry timing.",
                rationale=f"Lifecycle is blocked by readiness action {evidence.readiness_action}.",
                blocks_promotion=True,
            )
        )
    if evidence.agreement_score < 0.65:
        directional_source = evidence.top_directional_drivers[0].row_id if evidence.top_directional_drivers else None
        steps.append(
            TradeabilityImprovementStep(
                step_id=f"{evidence.scenario_id}:{evidence.seed}:directional-agreement",
                category="directional_confirmation",
                source_row_id=directional_source,
                priority="high",
                current_value=evidence.agreement_score,
                target_value=0.65,
                action="Wait for stronger directional alignment across matrix rows before treating this as a candidate.",
                rationale="Directional agreement is not strong enough for reliable replay review.",
                blocks_promotion=True,
            )
        )
    if worst_safety is not None:
        steps.append(_safety_improvement_step(evidence, worst_safety))
    if evidence.fill_status in {"REJECTED_SIMULATION", "NO_FILL"}:
        steps.append(
            TradeabilityImprovementStep(
                step_id=f"{evidence.scenario_id}:{evidence.seed}:execution-fill",
                category="execution_quality",
                source_row_id=None,
                priority="high",
                current_value=None,
                target_value=None,
                action="Improve fill realism inputs and require a non-rejected simulation before promotion.",
                rationale=f"Execution simulator returned {evidence.fill_status}.",
                blocks_promotion=True,
            )
        )
    if status == "REPLAY_CANDIDATE_RESEARCH_ONLY":
        steps.append(
            TradeabilityImprovementStep(
                step_id=f"{evidence.scenario_id}:{evidence.seed}:research-review",
                category="risk_control",
                source_row_id=None,
                priority="medium",
                current_value=evidence.safety_score,
                target_value=0.7,
                action="Review this only as a replay candidate and compare against walk-forward, OOS, drift, OOD, and risk gates.",
                rationale="Replay candidate visibility is useful for research, but cannot bypass production safety gates.",
                blocks_promotion=True,
            )
        )
    return steps


def _safety_improvement_step(
    evidence: LifecycleEvidenceScenarioDrilldown,
    safety: LifecycleEvidenceRowContribution,
) -> TradeabilityImprovementStep:
    action_by_row = {
        "slippage_risk_proxy": "Improve liquidity, spread, latency, and impact assumptions before trusting the fill path.",
        "fakeout_risk_score": "Wait for follow-through, retest confirmation, or VWAP reclaim before treating breakout evidence as usable.",
        "absorption_score": "Wait for candle body expansion or lower effort-vs-result pressure before considering continuation.",
        "liquidity_score": "Require stronger recent volume and lower participation pressure before any promotion review.",
        "no_trade_safety_pressure": "Reduce combined no-trade pressure before treating the setup as research-tradable.",
    }
    target_by_row = {
        "slippage_risk_proxy": 0.45,
        "fakeout_risk_score": 0.45,
        "absorption_score": 0.50,
        "liquidity_score": 0.40,
        "no_trade_safety_pressure": 0.45,
    }
    priority = "critical" if safety.contribution_score >= 0.65 else "high"
    return TradeabilityImprovementStep(
        step_id=f"{evidence.scenario_id}:{evidence.seed}:{safety.row_id}",
        category="safety_pressure",
        source_row_id=safety.row_id,
        priority=priority,  # type: ignore[arg-type]
        current_value=safety.contribution_score,
        target_value=target_by_row.get(safety.row_id, 0.5),
        action=action_by_row.get(safety.row_id, "Reduce this safety pressure before promotion review."),
        rationale=f"{safety.row_id} is the dominant safety pressure at {safety.contribution_score:.0%}.",
        blocks_promotion=safety.contribution_score >= 0.45,
    )


def _guidance_reason(
    status: str,
    next_action: str,
    score: float,
    best_driver: LifecycleEvidenceRowContribution | None,
    worst_safety: LifecycleEvidenceRowContribution | None,
) -> str:
    driver = best_driver.row_id if best_driver else "no_directional_driver"
    safety = worst_safety.row_id if worst_safety else "no_safety_pressure"
    return (
        f"{status}. Tradeability score {score:.0%}. Best driver {driver}; worst safety pressure {safety}. "
        f"Next safe action: {next_action}. This remains research-only and cannot route orders."
    )


def _top_global_blocker(items: list[ScenarioTradeabilityGuidance]) -> str | None:
    blocker_ids: list[str] = []
    for item in items:
        for step in item.improvement_steps:
            if step.blocks_promotion:
                blocker_ids.append(step.source_row_id or step.category)
    if not blocker_ids:
        return None
    return Counter(blocker_ids).most_common(1)[0][0]


def _guidance_gates(
    *,
    evidence_version: str,
    scenario_count: int,
    expected_count: int,
    improvement_steps_present: bool,
    promotion_allowed: bool,
    deterministic: bool,
    no_future_leakage: bool,
    all_trade_allowed_false: bool,
    all_order_routing_disabled: bool,
    all_live_trading_blocked: bool,
) -> list[MatrixDecisionGate]:
    return [
        _gate("TV-V039-001", "Evidence drilldown linked", evidence_version == EVIDENCE_VERSION, 1.0 if evidence_version == EVIDENCE_VERSION else 0.0, 1.0, f"Base evidence version is {evidence_version}.", True),
        _gate("TV-V039-002", "Guidance scenario coverage", scenario_count == expected_count, 1.0 if scenario_count == expected_count else 0.0, 1.0, f"{scenario_count}/{expected_count} scenarios have tradeability guidance.", True),
        _gate("TV-V039-003", "Improvement steps present", improvement_steps_present, 1.0 if improvement_steps_present else 0.0, 1.0, "Every scenario contains concrete improvement steps.", True),
        _gate("TV-V039-004", "Promotion remains disabled", not promotion_allowed, 1.0 if not promotion_allowed else 0.0, 1.0, "Tradeability guidance cannot promote paper or live trading.", True),
        _gate("TV-V039-005", "Trade permission remains false", all_trade_allowed_false, 1.0 if all_trade_allowed_false else 0.0, 1.0, "No guidance scenario may enable trade permission.", True),
        _gate("TV-V039-006", "Order routing disabled", all_order_routing_disabled, 1.0 if all_order_routing_disabled else 0.0, 1.0, "No guidance scenario may enable order routing.", True),
        _gate("TV-V039-007", "Live trading blocked", all_live_trading_blocked, 1.0 if all_live_trading_blocked else 0.0, 1.0, "Every guidance scenario keeps live trading blocked.", True),
        _gate("TV-V039-008", "Deterministic guidance", deterministic, 1.0 if deterministic else 0.0, 1.0, "Guidance is derived from deterministic evidence hashes.", True),
        _gate("TV-V039-009", "Point-in-time guidance", no_future_leakage, 1.0 if no_future_leakage else 0.0, 1.0, "Guidance inherits point-in-time evidence only.", True),
        _gate("TV-V039-010", "Narrative remains explanation-only", True, 1.0, 1.0, "Guidance explains blockers and cannot execute or override calibrated probabilities.", False),
    ]


def _lifecycle_request_from_scenario(
    request: LifecycleEvidenceDrilldownRequest,
    scenario: TradeLifecycleScenarioConfig,
) -> TradeLifecycleSimulationRequest:
    return TradeLifecycleSimulationRequest(
        symbol=request.symbol,
        scenario_id=scenario.scenario_id,
        seed=scenario.seed,
        event_count=request.event_count,
        timeframe=request.timeframe,
        required_matrix_rows=request.required_matrix_rows,
        min_agreement_score=scenario.min_agreement_score if scenario.min_agreement_score is not None else request.min_agreement_score,
        max_safety_pressure=scenario.max_safety_pressure if scenario.max_safety_pressure is not None else request.max_safety_pressure,
        entry_after_bars=scenario.entry_after_bars if scenario.entry_after_bars is not None else request.entry_after_bars,
        shadow_quantity=scenario.shadow_quantity if scenario.shadow_quantity is not None else request.shadow_quantity,
        max_holding_bars=request.max_holding_bars,
        respect_readiness_block=scenario.respect_readiness_block if scenario.respect_readiness_block is not None else request.respect_readiness_block,
    )


def _evidence_item(
    label: str,
    lifecycle: TradeLifecycleSimulationReport,
    rows: list[ReplayIndicatorMatrixRow],
    top_n_rows: int,
) -> LifecycleEvidenceScenarioDrilldown:
    top_directional, top_counter = _directional_contributions(rows, lifecycle.directional_bias, top_n_rows)
    top_safety = _safety_contributions(rows, top_n_rows)
    output_hash = _hash_output(
        {
            "label": label,
            "scenario_id": lifecycle.scenario_id,
            "seed": lifecycle.seed,
            "lifecycle_output_hash": lifecycle.output_hash,
            "top_directional": [row.model_dump(mode="json") for row in top_directional],
            "top_counter": [row.model_dump(mode="json") for row in top_counter],
            "top_safety": [row.model_dump(mode="json") for row in top_safety],
        }
    )
    return LifecycleEvidenceScenarioDrilldown(
        label=label,
        scenario_id=lifecycle.scenario_id,
        seed=lifecycle.seed,
        readiness_action=lifecycle.readiness_action,
        lifecycle_status=lifecycle.lifecycle_status,
        directional_bias=lifecycle.directional_bias,
        outcome_label=lifecycle.outcome.outcome_label,
        fill_status=lifecycle.execution.fill_status,
        fill_quality=lifecycle.execution.fill_quality,
        agreement_score=lifecycle.readiness.agreement_score,
        safety_score=lifecycle.readiness.safety_score,
        risk_score=lifecycle.readiness.risk_score,
        top_directional_drivers=top_directional,
        top_counter_drivers=top_counter,
        top_safety_pressures=top_safety,
        blocker_reasons=lifecycle.blocker_reasons,
        reason=_evidence_reason(lifecycle, top_directional, top_safety),
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        no_future_leakage=lifecycle.no_future_leakage and all(row.point_in_time_safe for row in rows),
        output_hash=output_hash,
    )


def _directional_contributions(
    rows: list[ReplayIndicatorMatrixRow],
    directional_bias: str,
    top_n_rows: int,
) -> tuple[list[LifecycleEvidenceRowContribution], list[LifecycleEvidenceRowContribution]]:
    direction = 1.0
    if directional_bias == "SHORT":
        direction = -1.0
    directional_rows = [
        row for row in rows if row.row_id not in SAFETY_ROW_IDS and row.readiness_status != "blocked"
    ]
    scored: list[tuple[ReplayIndicatorMatrixRow, float]] = []
    for row in directional_rows:
        aligned = abs(row.normalized_score) if directional_bias == "NEUTRAL" else row.normalized_score * direction
        scored.append((row, aligned))
    positives = [
        _row_contribution(row, "directional_positive", min(abs(score), 1.0))
        for row, score in sorted(scored, key=lambda item: item[1], reverse=True)
        if score > 0
    ][:top_n_rows]
    counters = [
        _row_contribution(row, "directional_negative", min(abs(score), 1.0))
        for row, score in sorted(scored, key=lambda item: item[1])
        if score < 0
    ][:top_n_rows]
    return positives, counters


def _safety_contributions(
    rows: list[ReplayIndicatorMatrixRow],
    top_n_rows: int,
) -> list[LifecycleEvidenceRowContribution]:
    safety_rows = [row for row in rows if row.row_id in SAFETY_ROW_IDS]
    ranked = sorted(
        ((row, _safety_pressure(row)) for row in safety_rows),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        _row_contribution(row, "safety_pressure", score)
        for row, score in ranked
        if score > 0
    ][:top_n_rows]


def _row_contribution(
    row: ReplayIndicatorMatrixRow,
    contribution_kind: str,
    contribution_score: float,
) -> LifecycleEvidenceRowContribution:
    return LifecycleEvidenceRowContribution(
        row_id=row.row_id,
        family=row.family,
        layer_index=row.layer_index,
        contract_name=row.contract_name,
        source=row.source,
        signal=row.signal,
        readiness_status=row.readiness_status,
        normalized_score=row.normalized_score,
        contribution_kind=contribution_kind,  # type: ignore[arg-type]
        contribution_score=round(max(0.0, min(contribution_score, 1.0)), 4),
        latest_value=row.latest_value,
        output_fields=row.output_fields,
        explanation=row.explanation,
    )


def _safety_pressure(row: ReplayIndicatorMatrixRow) -> float:
    if row.row_id == "liquidity_score":
        return round(max(0.0, min(1.0, 1 - float(row.output_fields.get("liquidity_score", 1.0) or 0.0))), 4)
    field_name = SAFETY_FIELD_BY_ROW.get(row.row_id)
    if field_name:
        return round(max(0.0, min(1.0, float(row.output_fields.get(field_name, 0.0) or 0.0))), 4)
    return round(max(0.0, min(1.0, abs(min(row.normalized_score, 0.0)))), 4)


def _evidence_reason(
    lifecycle: TradeLifecycleSimulationReport,
    top_directional: list[LifecycleEvidenceRowContribution],
    top_safety: list[LifecycleEvidenceRowContribution],
) -> str:
    driver = top_directional[0].row_id if top_directional else "no_directional_driver"
    safety = top_safety[0].row_id if top_safety else "no_safety_pressure"
    return (
        f"{lifecycle.readiness_action} / {lifecycle.lifecycle_status}. Dominant driver {driver}; "
        f"dominant safety pressure {safety}. Trade permission remains false and live routing remains blocked."
    )


def _dominant_row_id(rows: list[LifecycleEvidenceRowContribution]) -> str | None:
    if not rows:
        return None
    return max(rows, key=lambda row: row.contribution_score).row_id


def _evidence_gates(
    *,
    scenario_count: int,
    expected_count: int,
    deterministic: bool,
    no_future_leakage: bool,
    all_trade_allowed_false: bool,
    all_order_routing_disabled: bool,
    all_live_trading_blocked: bool,
    row_evidence_present: bool,
    safety_evidence_present: bool,
) -> list[MatrixDecisionGate]:
    return [
        _gate("TV-V038-001", "Scenario drilldown coverage", scenario_count == expected_count, 1.0 if scenario_count == expected_count else 0.0, 1.0, f"{scenario_count}/{expected_count} scenarios have drilldown evidence.", True),
        _gate("TV-V038-002", "Row-level evidence present", row_evidence_present, 1.0 if row_evidence_present else 0.0, 1.0, "Every scenario exposes directional, counter, or safety row contributions.", True),
        _gate("TV-V038-003", "Safety pressure evidence present", safety_evidence_present, 1.0 if safety_evidence_present else 0.0, 1.0, "Every scenario exposes safety pressure rows from the matrix.", True),
        _gate("TV-V038-004", "Deterministic drilldown", deterministic, 1.0 if deterministic else 0.0, 1.0, "Drilldown is derived from deterministic replay, matrix, and lifecycle hashes.", True),
        _gate("TV-V038-005", "Point-in-time drilldown", no_future_leakage, 1.0 if no_future_leakage else 0.0, 1.0, "All contributing rows declare point-in-time safety.", True),
        _gate("TV-V038-006", "Trade permission remains false", all_trade_allowed_false, 1.0 if all_trade_allowed_false else 0.0, 1.0, "No drilldown scenario may enable trade permission.", True),
        _gate("TV-V038-007", "Order routing disabled", all_order_routing_disabled, 1.0 if all_order_routing_disabled else 0.0, 1.0, "No drilldown scenario may enable order routing.", True),
        _gate("TV-V038-008", "Live trading blocked", all_live_trading_blocked, 1.0 if all_live_trading_blocked else 0.0, 1.0, "Every drilldown scenario keeps live trading blocked.", True),
        _gate("TV-V038-009", "Narrative remains explanation-only", True, 1.0, 1.0, "Evidence reasons explain the replay state and cannot execute or override probabilities.", False),
    ]


def _comparison_item(label: str, report: TradeLifecycleSimulationReport) -> TradeLifecycleScenarioComparisonItem:
    return TradeLifecycleScenarioComparisonItem(
        label=label,
        scenario_id=report.scenario_id,
        seed=report.seed,
        readiness_action=report.readiness_action,
        lifecycle_status=report.lifecycle_status,
        directional_bias=report.directional_bias,
        outcome_label=report.outcome.outcome_label,
        fill_status=report.execution.fill_status,
        fill_quality=report.execution.fill_quality,
        entry_price=report.entry_price,
        stop_loss=report.stop_loss,
        target=report.target,
        risk_reward=report.risk_reward,
        expected_MFE=report.expected_MFE,
        expected_MAE=report.expected_MAE,
        bars_to_target=report.bars_to_target,
        bars_to_sl=report.bars_to_sl,
        blocker_count=len(report.blocker_reasons),
        trade_state_path=report.trade_state_path,
        output_hash=report.output_hash,
        trade_allowed=report.trade_allowed,
        live_trading_blocked=report.live_trading_blocked,
        no_future_leakage=report.no_future_leakage,
    )


def _comparison_gates(
    *,
    scenario_count: int,
    deterministic: bool,
    no_future_leakage: bool,
    all_trade_allowed_false: bool,
    all_order_routing_disabled: bool,
    all_live_trading_blocked: bool,
    all_simulation_only: bool,
    candidate_count: int,
) -> list[MatrixDecisionGate]:
    return [
        _gate("TV-V037-001", "Scenario coverage", scenario_count >= 2, min(scenario_count / 4, 1.0), 0.5, f"{scenario_count} lifecycle scenarios compared.", False),
        _gate("TV-V037-002", "Deterministic comparison", deterministic, 1.0 if deterministic else 0.0, 1.0, "Every lifecycle report declares deterministic output.", True),
        _gate("TV-V037-003", "Point-in-time comparison", no_future_leakage, 1.0 if no_future_leakage else 0.0, 1.0, "Every scenario preserves no-future-leakage flags.", True),
        _gate("TV-V037-004", "Trade permission remains false", all_trade_allowed_false, 1.0 if all_trade_allowed_false else 0.0, 1.0, "No compared scenario may set trade_allowed=true.", True),
        _gate("TV-V037-005", "Order routing disabled", all_order_routing_disabled, 1.0 if all_order_routing_disabled else 0.0, 1.0, "No compared scenario may enable order routing.", True),
        _gate("TV-V037-006", "Live trading blocked", all_live_trading_blocked, 1.0 if all_live_trading_blocked else 0.0, 1.0, "Every compared scenario keeps live trading blocked.", True),
        _gate("TV-V037-007", "Simulation-only lifecycle", all_simulation_only, 1.0 if all_simulation_only else 0.0, 1.0, "Every compared scenario uses MOCK_ONLY execution simulation.", True),
        _gate("TV-V037-008", "Candidate visibility", True, 1.0 if candidate_count else 0.5, 0.0, f"{candidate_count} replay candidate scenarios visible as shadow-only candidates.", False),
    ]


def _shadow_execution_allowed(request: TradeLifecycleSimulationRequest, readiness_action: str) -> bool:
    if not request.respect_readiness_block:
        return True
    return readiness_action in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE"}


def _trade_levels(bars: list[CandleBar], entry_index: int, direction: str) -> tuple[float, float, float, float]:
    entry_bar = bars[entry_index]
    entry_price = round(entry_bar.open, 4)
    prior = bars[:entry_index] or [entry_bar]
    atr_proxy = round(max(fmean([bar.high - bar.low for bar in prior[-5:]]), 0.01), 4)
    if direction == "short":
        breakdown_level = min(bar.low for bar in prior)
        stop_loss = round(max(entry_price + atr_proxy * 2.0, breakdown_level + atr_proxy * 2.0), 4)
        risk = max(stop_loss - entry_price, 0.01)
        target = round(max(0.01, entry_price - risk * 3.0), 4)
    else:
        breakout_level = max(bar.high for bar in prior)
        stop_loss = round(min(entry_price - atr_proxy * 2.0, breakout_level - atr_proxy * 2.0), 4)
        stop_loss = max(0.01, stop_loss)
        risk = max(entry_price - stop_loss, 0.01)
        target = round(entry_price + risk * 3.0, 4)
    return entry_price, stop_loss, target, atr_proxy


def _risk_reward(entry_price: float, stop_loss: float, target: float) -> float:
    risk = abs(entry_price - stop_loss)
    reward = abs(target - entry_price)
    return round(reward / risk, 4) if risk > 0 else 0.0


def _execution_request(
    request: TradeLifecycleSimulationRequest,
    entry_bar: CandleBar,
    direction: str,
    entry_price: float,
    effective_quantity: int,
    readiness_risk_score: float,
) -> BehaviorExecutionRequest:
    volume = int(entry_bar.volume or 0)
    return BehaviorExecutionRequest(
        symbol=request.symbol.upper(),
        side="SELL" if direction == "short" else "BUY",
        order_type="MARKET",
        requested_quantity=effective_quantity,
        entry_price=entry_price,
        bar_open=entry_bar.open,
        bar_high=entry_bar.high,
        bar_low=entry_bar.low,
        bar_close=entry_bar.close,
        bid_ask_spread_pct=0.08,
        available_volume=volume,
        queue_ahead_quantity=max(0, int(volume * 0.03)),
        latency_ms=120,
        impact_coefficient_bps=4.0,
        adverse_selection_score=min(max(readiness_risk_score, 0.0), 1.0),
        max_participation_rate=0.08,
        mode_confirmation="MOCK_ONLY",
        seed=request.seed,
    )


def _outcome_series(series: CandleSeries, entry_index: int, max_holding_bars: int) -> CandleSeries:
    bars = series.bars[entry_index : entry_index + max_holding_bars]
    return CandleSeries(
        symbol=series.symbol,
        timeframe=series.timeframe,
        bars=bars,
        snapshot_id=series.snapshot_id,
        schema_version=f"{series.schema_version}.lifecycle",
    )


def _lifecycle_status(readiness_action: str, fill_status: str, respect_readiness_block: bool) -> str:
    if respect_readiness_block and readiness_action not in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE"}:
        return "BLOCKED_BY_READINESS"
    if fill_status == "REJECTED_SIMULATION":
        return "SHADOW_REJECTED"
    if fill_status == "NO_FILL":
        return "SHADOW_NO_FILL"
    return "SHADOW_SIMULATED"


def _state_path(lifecycle_status: str, outcome_label: str) -> list[str]:
    if lifecycle_status == "BLOCKED_BY_READINESS":
        return ["WAITING", "SIGNAL_FORMING", "INVALIDATED"]
    path = ["WAITING", "SIGNAL_FORMING", "ENTRY_READY"]
    if lifecycle_status == "SHADOW_NO_FILL":
        return path + ["INVALIDATED"]
    if lifecycle_status == "SHADOW_REJECTED":
        return path + ["INVALIDATED"]
    if outcome_label in {"TARGET_HIT", "PARTIAL_WIN", "BREAKEVEN"}:
        return path + ["ENTERED", "PARTIAL_EXIT", "TRAILING", "EXITED"]
    if outcome_label in {"SL_HIT", "FAKE_BREAKOUT", "RETEST_FAIL", "CHOP_NO_FOLLOWTHROUGH"}:
        return path + ["ENTERED", "INVALIDATED", "EXITED"]
    return path + ["ENTERED", "EXITED"]


def _gates(
    request: TradeLifecycleSimulationRequest,
    readiness,
    simulation_only: bool,
    live_route_attempted: bool,
    outcome_run_id: str,
) -> list[MatrixDecisionGate]:
    readiness_block_honored = (
        readiness.readiness_action in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE"}
        or request.respect_readiness_block
    )
    return [
        _gate("TV-V036-001", "Readiness report linked", True, 1.0, 1.0, f"Readiness version {readiness.readiness_version} consumed.", False),
        _gate("TV-V036-002", "Readiness block honored", readiness_block_honored, 1.0 if readiness_block_honored else 0.0, 1.0, f"Readiness action {readiness.readiness_action}; respect_readiness_block={request.respect_readiness_block}.", True),
        _gate("TV-V036-003", "Execution simulation only", simulation_only, 1.0 if simulation_only else 0.0, 1.0, "Execution uses MOCK_ONLY simulator and never leaves process memory.", True),
        _gate("TV-V036-004", "No live route attempted", not live_route_attempted, 1.0 if not live_route_attempted else 0.0, 1.0, "ExecutionSimulationResult.live_route_attempted is false.", True),
        _gate("TV-V036-005", "Outcome label produced", bool(outcome_run_id), 1.0 if outcome_run_id else 0.0, 1.0, f"Outcome run id {outcome_run_id}.", False),
        _gate("TV-V036-006", "Point-in-time lifecycle", readiness.no_future_leakage, 1.0 if readiness.no_future_leakage else 0.0, 1.0, "Lifecycle consumes replay candles generated from current/prior bars only.", True),
        _gate("TV-V036-007", "Trade permission remains false", True, 1.0, 1.0, "Lifecycle report cannot set trade_allowed=true.", True),
        _gate("TV-V036-008", "Narrative remains read-only", True, 1.0, 1.0, "Lifecycle reason is an explanation, not an execution instruction.", False),
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
        score=round(max(0.0, min(score, 1.0)), 4),
        threshold=round(max(0.0, min(threshold, 1.0)), 4),
        evidence=evidence,
        blocks_decision=blocks_decision,
        remediation=None if passed else "Keep lifecycle in blocked simulation state until this gate passes.",
    )


def _gate_summary(gates: list[MatrixDecisionGate]) -> dict[str, int]:
    return {
        "pass": sum(1 for gate in gates if gate.status == "pass"),
        "warn": sum(1 for gate in gates if gate.status == "warn"),
        "fail": sum(1 for gate in gates if gate.status == "fail"),
    }


def _blocker_reasons(readiness, missed_trade_reason: str | None, respect_readiness_block: bool) -> list[str]:
    reasons = list(readiness.blocker_reasons)
    if respect_readiness_block and readiness.readiness_action not in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE"}:
        reasons.append(f"Lifecycle blocked because readiness action is {readiness.readiness_action}.")
    if missed_trade_reason:
        reasons.append(missed_trade_reason)
    return reasons


def _reason(lifecycle_status: str, readiness_action: str, outcome_label: str, blocker_reasons: list[str]) -> str:
    if lifecycle_status == "BLOCKED_BY_READINESS":
        return f"Lifecycle blocked before entry because readiness action is {readiness_action}. {'; '.join(blocker_reasons)}"
    return (
        f"{lifecycle_status}. Replay-only lifecycle produced outcome {outcome_label}. "
        "This is a shadow simulation and cannot approve, route, or size a live trade."
    )


def _run_id(request: TradeLifecycleSimulationRequest) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            (
                f"tradevision:{LIFECYCLE_VERSION}:{request.symbol}:{request.scenario_id}:"
                f"{request.seed}:{request.event_count}:{request.timeframe}:{request.entry_after_bars}:"
                f"{request.max_holding_bars}:{request.required_matrix_rows}:{request.min_agreement_score}:"
                f"{request.max_safety_pressure}:{request.respect_readiness_block}"
            ),
        )
    )


def _comparison_run_id(request: TradeLifecycleScenarioComparisonRequest) -> str:
    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return str(uuid5(NAMESPACE_URL, f"tradevision:{COMPARISON_VERSION}:{digest}"))


def _evidence_run_id(request: LifecycleEvidenceDrilldownRequest) -> str:
    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return str(uuid5(NAMESPACE_URL, f"tradevision:{EVIDENCE_VERSION}:{digest}"))


def _guidance_run_id(request: TradeabilityGuidanceRequest) -> str:
    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return str(uuid5(NAMESPACE_URL, f"tradevision:{GUIDANCE_VERSION}:{digest}"))


def _hash_output(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
