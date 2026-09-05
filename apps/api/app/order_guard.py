from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from .models import KillSwitchState, OrderPathStatus, SimulatedOrderRequest, SimulatedOrderResult, SystemMode, SystemModeValue


REQUIRED_ORDER_GATES = [
    "SystemMode must be MOCK for this MVP stub.",
    "KillSwitch must be armed.",
    "Broker credentials must be absent.",
    "Live order routing must be disabled.",
    "Request must explicitly confirm MOCK_ONLY.",
]


def order_path_status(kill_switch: KillSwitchState) -> OrderPathStatus:
    blocks_reason = None
    if kill_switch.blocks_order_paths:
        blocks_reason = kill_switch.reason or "Kill switch blocks all order-path stubs."
    return OrderPathStatus(
        live_order_routing_enabled=False,
        simulation_only=True,
        broker_credentials_configured=False,
        kill_switch_state=kill_switch.state,
        accepts_simulated_orders=not kill_switch.blocks_order_paths,
        blocks_reason=blocks_reason,
        required_gates=REQUIRED_ORDER_GATES,
    )


def simulate_order_request(request: SimulatedOrderRequest, mode: SystemMode, kill_switch: KillSwitchState) -> SimulatedOrderResult:
    if mode.mode != SystemModeValue.MOCK:
        return _result(request, False, "REJECTED_UNSAFE_MODE", "Only MOCK mode may use the v0.4 simulation stub.", None, mode.mode)

    if kill_switch.blocks_order_paths:
        return _result(request, False, "BLOCKED_BY_KILL_SWITCH", kill_switch.reason or "Kill switch is triggered.", None, mode.mode)

    if request.order_type == "LIMIT" and request.limit_price is None:
        return _result(request, False, "REJECTED_VALIDATION", "LIMIT orders require limit_price.", None, mode.mode)

    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    simulated_order_id = str(uuid5(NAMESPACE_URL, f"tradevision:simulated-order:{digest}"))
    return _result(
        request,
        True,
        "SIMULATED_ACCEPTED",
        "Simulation stub accepted request after mode and kill-switch gates.",
        simulated_order_id,
        mode.mode,
    )


def _result(
    request: SimulatedOrderRequest,
    accepted: bool,
    decision: str,
    reason: str,
    simulated_order_id: str | None,
    mode: SystemModeValue,
) -> SimulatedOrderResult:
    return SimulatedOrderResult(
        client_order_id=request.client_order_id,
        accepted=accepted,
        decision=decision,
        reason=reason,
        simulated_order_id=simulated_order_id,
        live_route_attempted=False,
        kill_switch_checked=True,
        mode=mode,
    )
