from __future__ import annotations

import hashlib
import json
from math import sqrt
from uuid import NAMESPACE_URL, uuid5

from ..models import BehaviorExecutionRequest, ExecutionCostBreakdown, ExecutionSimulationResult


EXECUTION_SIM_VERSION = "behavior-execution-simulator.v0.22"


def simulate_behavior_execution(request: BehaviorExecutionRequest) -> ExecutionSimulationResult:
    """Deterministic execution realism model for mock/replay/simulation only."""

    validation_error = _validation_error(request)
    reference_price = _reference_price(request)
    if validation_error:
        return _result(
            request,
            filled_quantity=0,
            fill_status="REJECTED_SIMULATION",
            fill_probability_pct=0.0,
            fill_price=None,
            reference_price=reference_price,
            costs=_costs(0.0, 0.0, 0.0, 0.0),
            queue_position_estimate=0.0,
            no_fill_reason=validation_error,
            missed_trade_reason=validation_error,
        )

    touched = _order_touched(request)
    queue_position = _queue_position(request)
    max_fill_quantity = _max_fill_quantity(request, touched, queue_position)
    filled_quantity = min(request.requested_quantity, max_fill_quantity)
    if request.order_type in {"LIMIT", "STOP"} and not touched:
        filled_quantity = 0

    fill_status = _fill_status(request.requested_quantity, filled_quantity)
    costs = _execution_costs(request, filled_quantity)
    fill_price = None if filled_quantity == 0 else _fill_price(request, reference_price, costs.total_cost_pct)
    fill_probability = _fill_probability(request, touched, queue_position, filled_quantity)
    no_fill_reason = _no_fill_reason(request, touched, filled_quantity)
    missed_trade_reason = _missed_trade_reason(request, touched, filled_quantity)
    return _result(
        request,
        filled_quantity=filled_quantity,
        fill_status=fill_status,
        fill_probability_pct=fill_probability,
        fill_price=fill_price,
        reference_price=reference_price,
        costs=costs,
        queue_position_estimate=queue_position,
        no_fill_reason=no_fill_reason,
        missed_trade_reason=missed_trade_reason,
    )


def _validation_error(request: BehaviorExecutionRequest) -> str | None:
    if request.mode_confirmation != "MOCK_ONLY":
        return "Execution simulation requires MOCK_ONLY confirmation."
    if request.requested_quantity <= 0:
        return "Requested quantity is zero; no execution simulation can fill."
    if request.available_volume <= 0:
        return "Available volume is zero; no fill is possible."
    if request.order_type == "LIMIT" and request.limit_price is None:
        return "LIMIT execution simulation requires limit_price."
    if request.order_type == "STOP" and request.stop_price is None:
        return "STOP execution simulation requires stop_price."
    if not (request.bar_low <= request.bar_open <= request.bar_high and request.bar_low <= request.bar_close <= request.bar_high):
        return "Invalid OHLC bar; execution simulation rejected."
    return None


def _reference_price(request: BehaviorExecutionRequest) -> float:
    if request.order_type == "LIMIT" and request.limit_price is not None:
        return request.limit_price
    if request.order_type == "STOP" and request.stop_price is not None:
        return request.stop_price
    return request.entry_price


def _order_touched(request: BehaviorExecutionRequest) -> bool:
    if request.order_type == "MARKET":
        return True
    if request.order_type == "LIMIT" and request.limit_price is not None:
        if request.side == "BUY":
            return request.bar_low <= request.limit_price
        return request.bar_high >= request.limit_price
    if request.order_type == "STOP" and request.stop_price is not None:
        if request.side == "BUY":
            return request.bar_high >= request.stop_price
        return request.bar_low <= request.stop_price
    return False


def _queue_position(request: BehaviorExecutionRequest) -> float:
    queue_capacity = max(request.available_volume * request.max_participation_rate, 1.0)
    raw = 1.0 - min(request.queue_ahead_quantity / queue_capacity, 1.0)
    if request.order_type == "MARKET":
        raw = max(raw, 0.85)
    return round(max(0.0, min(raw, 1.0)), 4)


def _max_fill_quantity(request: BehaviorExecutionRequest, touched: bool, queue_position: float) -> int:
    if not touched:
        return 0
    volume_cap = request.available_volume * request.max_participation_rate
    if request.order_type == "MARKET":
        liquidity_factor = 1.0 - min(request.adverse_selection_score * 0.35, 0.35)
        return int(max(0, volume_cap * liquidity_factor))
    if request.order_type == "STOP":
        liquidity_factor = 0.55 - min(request.adverse_selection_score * 0.25, 0.25)
        return int(max(0, volume_cap * liquidity_factor))
    passive_factor = 0.45 * queue_position
    return int(max(0, volume_cap * passive_factor))


def _fill_status(requested_quantity: int, filled_quantity: int) -> str:
    if filled_quantity <= 0:
        return "NO_FILL"
    if filled_quantity < requested_quantity:
        return "PARTIAL_FILL"
    return "FULL_FILL"


def _execution_costs(request: BehaviorExecutionRequest, filled_quantity: int) -> ExecutionCostBreakdown:
    if filled_quantity <= 0:
        return _costs(0.0, 0.0, 0.0, 0.0)
    spread = request.bid_ask_spread_pct / 2.0 if request.order_type in {"MARKET", "STOP"} else request.bid_ask_spread_pct * 0.15
    bar_move_pct = abs(request.bar_close - request.bar_open) / request.bar_open * 100.0
    latency = min(request.latency_ms / 1000.0, 5.0) / 5.0 * bar_move_pct * (0.5 + request.adverse_selection_score)
    participation = min(filled_quantity / max(request.available_volume, 1), 1.0)
    impact = (request.impact_coefficient_bps / 100.0) * sqrt(participation)
    adverse = request.adverse_selection_score * max(bar_move_pct, request.bid_ask_spread_pct) * 0.35
    return _costs(spread, latency, impact, adverse)


def _costs(spread: float, latency: float, impact: float, adverse: float) -> ExecutionCostBreakdown:
    total = spread + latency + impact + adverse
    return ExecutionCostBreakdown(
        spread_cost_pct=round(spread, 6),
        latency_slippage_pct=round(latency, 6),
        market_impact_pct=round(impact, 6),
        adverse_selection_cost_pct=round(adverse, 6),
        total_cost_pct=round(total, 6),
    )


def _fill_price(request: BehaviorExecutionRequest, reference_price: float, total_cost_pct: float) -> float:
    direction = 1.0 if request.side == "BUY" else -1.0
    return round(reference_price * (1.0 + direction * total_cost_pct / 100.0), 4)


def _fill_probability(
    request: BehaviorExecutionRequest,
    touched: bool,
    queue_position: float,
    filled_quantity: int,
) -> float:
    if not touched or request.requested_quantity <= 0:
        return 0.0
    fill_ratio = filled_quantity / max(request.requested_quantity, 1)
    if request.order_type == "MARKET":
        base = 98.0
    elif request.order_type == "STOP":
        base = 76.0
    else:
        base = 62.0 * queue_position
    penalty = request.adverse_selection_score * 18.0 + min(request.latency_ms / 1000.0, 5.0) * 2.0
    return round(max(0.0, min(base * fill_ratio - penalty, 100.0)), 4)


def _no_fill_reason(request: BehaviorExecutionRequest, touched: bool, filled_quantity: int) -> str | None:
    if filled_quantity > 0:
        return None
    if request.order_type in {"LIMIT", "STOP"} and not touched:
        return f"{request.order_type} price was not touched by the replay bar."
    if request.queue_ahead_quantity > request.available_volume * request.max_participation_rate:
        return "Queue ahead quantity exceeded simulated participation capacity."
    if request.available_volume <= 0:
        return "No available volume."
    return "Requested quantity could not be filled under participation and liquidity caps."


def _missed_trade_reason(request: BehaviorExecutionRequest, touched: bool, filled_quantity: int) -> str | None:
    if filled_quantity == request.requested_quantity:
        return None
    if filled_quantity == 0:
        return _no_fill_reason(request, touched, filled_quantity)
    return "Partial fill: requested size exceeded simulated liquidity after queue, latency, and impact caps."


def _adverse_selection_risk(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def _fill_quality(fill_status: str, total_cost_pct: float, adverse_selection_score: float) -> str:
    if fill_status == "REJECTED_SIMULATION":
        return "rejected"
    if fill_status == "NO_FILL":
        return "no_fill"
    if total_cost_pct <= 0.12 and adverse_selection_score < 0.35:
        return "excellent"
    if total_cost_pct <= 0.35 and adverse_selection_score < 0.7:
        return "acceptable"
    return "poor"


def _simulation_id(request: BehaviorExecutionRequest) -> str:
    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return str(uuid5(NAMESPACE_URL, f"tradevision:execution-sim:{digest}"))


def _result(
    request: BehaviorExecutionRequest,
    *,
    filled_quantity: int,
    fill_status: str,
    fill_probability_pct: float,
    fill_price: float | None,
    reference_price: float,
    costs: ExecutionCostBreakdown,
    queue_position_estimate: float,
    no_fill_reason: str | None,
    missed_trade_reason: str | None,
) -> ExecutionSimulationResult:
    unfilled = max(request.requested_quantity - filled_quantity, 0)
    return ExecutionSimulationResult(
        execution_version=EXECUTION_SIM_VERSION,
        simulation_id=_simulation_id(request),
        symbol=request.symbol.upper(),
        side=request.side,
        order_type=request.order_type,
        requested_quantity=request.requested_quantity,
        filled_quantity=filled_quantity,
        unfilled_quantity=unfilled,
        fill_status=fill_status,  # type: ignore[arg-type]
        fill_probability_pct=round(fill_probability_pct, 4),
        fill_price=fill_price,
        reference_price=round(reference_price, 4),
        fill_quality=_fill_quality(fill_status, costs.total_cost_pct, request.adverse_selection_score),  # type: ignore[arg-type]
        queue_position_estimate=queue_position_estimate,
        partial_fill_probability_pct=round(100.0 if fill_status == "PARTIAL_FILL" else 0.0, 4),
        no_fill_reason=no_fill_reason,
        missed_trade_reason=missed_trade_reason,
        adverse_selection_risk=_adverse_selection_risk(request.adverse_selection_score),  # type: ignore[arg-type]
        costs=costs,
        market_impact_model="sqrt(participation_rate) scaled by impact_coefficient_bps",
        latency_model="bar move percentage scaled by latency window and adverse selection score",
        deterministic=True,
        simulation_only=True,
        live_route_attempted=False,
        safety_notes=[
            "Execution simulation is deterministic and MOCK_ONLY.",
            "No broker route, exchange API, or live credential path exists.",
            "Limit and stop orders can miss if replay bar does not touch the trigger price.",
            "Market orders can still partial-fill when requested size exceeds participation cap.",
        ],
    )
