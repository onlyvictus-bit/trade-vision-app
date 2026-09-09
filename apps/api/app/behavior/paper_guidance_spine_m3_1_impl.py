from __future__ import annotations

"""M3.1 canonical price-intelligence orchestration contract.

This module intentionally contains no alternate Paper Guidance runner and no
arbiter logic. The public ``paper_guidance_spine`` facade remains the only
runtime entrypoint during migration. M3.1 orchestration is limited to asserting
that the composed price world-state has zero decision/execution authority.
"""

from typing import Any, Mapping


PAPER_GUIDANCE_M3_1_ORCHESTRATION_VERSION = "paper-guidance-m3.1-price-orchestration.v1"


class M31PriceOrchestrationError(ValueError):
    pass


def validate_zero_authority_price_evidence(payload: Mapping[str, Any]) -> None:
    """Fail closed if the M3.1 composer ever claims specialist authority."""

    forbidden_truthy = (
        "may_propose",
        "may_veto",
        "may_downgrade",
        "may_set_final_band",
        "may_execute",
        "trade_allowed",
        "order_routing_enabled",
    )
    claimed = [name for name in forbidden_truthy if bool(payload.get(name, False))]
    if claimed:
        raise M31PriceOrchestrationError(
            "M3.1 price evidence claimed forbidden authority: " + ", ".join(claimed)
        )
    if payload.get("live_trading_blocked") is not True:
        raise M31PriceOrchestrationError(
            "M3.1 price evidence must preserve live_trading_blocked=true"
        )
