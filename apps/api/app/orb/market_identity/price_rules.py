"""Exact Decimal price/lot validation against versioned BUILD-2 rules.

No binary floats anywhere: ticks, bounds, multipliers, and candidate
prices are Decimals. A price is valid only against the rule causally
effective for its instrument at its timestamp; the caller selects the
rule version (registry/resolver), this module checks the grid.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .contracts import LotRuleV1, PriceRuleV1


def to_decimal(value: Any, *, field_name: str = "price") -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an exact decimal, not boolean")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field_name} must be an exact decimal amount") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


def tick_for_price(rule: PriceRuleV1, price: Decimal) -> Decimal:
    """Tick for a price under a (possibly banded) rule. Static rules return
    their single tick; banded rules return the first band whose inclusive
    upper bound covers the price; above all bands the last band applies."""
    price = to_decimal(price)
    if price <= 0:
        raise ValueError("price must be positive")
    if not rule.bands:
        return rule.tick
    for band in rule.bands:
        if price <= band.upper_bound_inclusive:
            return band.tick
    return rule.bands[-1].tick


def is_on_tick_grid(rule: PriceRuleV1, price: Any) -> bool:
    """Exact grid check: (price / tick) must be integral. No float epsilon."""
    amount = to_decimal(price)
    if amount <= 0:
        return False
    tick = tick_for_price(rule, amount)
    return (amount % tick) == 0


def quantize_to_precision(rule: PriceRuleV1, price: Any) -> Decimal:
    amount = to_decimal(price)
    quantum = Decimal(1).scaleb(-rule.price_precision)
    return amount.quantize(quantum)


def check_precision_consistency(rule: PriceRuleV1) -> None:
    """The declared precision must be able to represent the tick exactly."""
    tick = rule.tick
    quantum = Decimal(1).scaleb(-rule.price_precision)
    if tick % quantum != 0:
        raise ValueError(
            f"price_precision {rule.price_precision} cannot represent tick {tick} "
            f"for rule {rule.rule_id} version {rule.rule_version}"
        )
    for band in rule.bands:
        if band.tick % quantum != 0:
            raise ValueError(f"price_precision {rule.price_precision} cannot represent band tick {band.tick}")


def notional_value(lot_rule: LotRuleV1, price: Any) -> Decimal:
    """Contract notional = price x multiplier x lot_size, exact."""
    amount = to_decimal(price)
    if amount <= 0:
        raise ValueError("price must be positive")
    return amount * lot_rule.multiplier * lot_rule.lot_size


def check_lot_quantity(lot_rule: LotRuleV1, quantity: int) -> bool:
    """A valid order quantity is a positive whole number of lots."""
    return isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0 and quantity % lot_rule.lot_size == 0


def rule_effective_at(rule: PriceRuleV1 | LotRuleV1, moment: datetime) -> bool:
    """Market-time effectiveness window check (knowledge cutoff is enforced
    by the registry/resolver, not here)."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("moment must be timezone-aware")
    if rule.effective_from is not None and moment < rule.effective_from:
        return False
    if rule.effective_to is not None and moment >= rule.effective_to:
        return False
    return True
