from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Literal

# Sources verified 2026-09-07:
# NSE equity derivatives contract specification updated 2026-08-11 and
# NSE/FAOP/68589: contracts expiring on/after 2025-09-01 use Tuesday expiry.
TUESDAY_EXPIRY_EFFECTIVE = date(2025, 9, 1)
TUESDAY = 1  # datetime.weekday(), Monday=0
THURSDAY = 3


@dataclass(frozen=True, slots=True)
class NseContractRule:
    instrument: Literal["INDEX_FUTURE", "INDEX_OPTION", "STOCK_FUTURE", "STOCK_OPTION"]
    expiry_weekday: int
    holiday_adjustment: Literal["PREVIOUS_TRADING_DAY"] = "PREVIOUS_TRADING_DAY"


def equity_derivative_expiry_weekday(expiry: date) -> int:
    """Historical transition helper only.

    Current contracts should ALWAYS be discovered from OpenAlgo/NSE master data.
    This function validates obvious stale/incorrect expiry assumptions; it does
    not invent an expiry when the exchange contract master is available.
    """
    return TUESDAY if expiry >= TUESDAY_EXPIRY_EFFECTIVE else THURSDAY


def previous_trading_day(day: date, holidays: Iterable[date] = ()) -> date:
    holiday_set = set(holidays)
    d = day
    while d.weekday() >= 5 or d in holiday_set:
        d -= timedelta(days=1)
    return d


def expected_expiry_date(period_anchor: date, *, weekly: bool, holidays: Iterable[date] = ()) -> date:
    """Compute a validation expectation for NSE equity derivatives.

    For current rules the expiry weekday is Tuesday. For a weekly contract the
    Tuesday in the anchor's Monday-Sunday week is used. For monthly contracts,
    the last expiry weekday of the month is used. Holidays shift to the previous
    trading day. Do not use this instead of exchange-provided expiry lists.
    """
    weekday = equity_derivative_expiry_weekday(period_anchor)
    if weekly:
        monday = period_anchor - timedelta(days=period_anchor.weekday())
        raw = monday + timedelta(days=weekday)
    else:
        if period_anchor.month == 12:
            next_month = date(period_anchor.year + 1, 1, 1)
        else:
            next_month = date(period_anchor.year, period_anchor.month + 1, 1)
        raw = next_month - timedelta(days=1)
        while raw.weekday() != weekday:
            raw -= timedelta(days=1)
    return previous_trading_day(raw, holidays)


def current_index_future_tick(monthly_reference_index_level: float) -> float:
    """NSE index-futures tick schedule effective 2025-04-15.

    IMPORTANT: NSE reviews this monthly using the prescribed prior month-end
    reference index close. Pass that reference value, not the live intraday
    index level. Provider/master-contract tick_size remains authoritative.
    """
    index_level = monthly_reference_index_level
    if index_level <= 0:
        raise ValueError("monthly reference index level must be positive")
    if index_level <= 15000:
        return 0.05
    if index_level <= 30000:
        return 0.10
    return 0.20


def current_index_option_tick() -> float:
    return 0.05


def current_stock_option_tick(monthly_reference_underlying_price: float) -> float:
    """Stock-option tick schedule effective 2025-11-03.

    NSE determines the applicable tier during its monthly review. Use the
    monthly reference close; do not switch tick sizes intraday at Rs 250.
    """
    price = monthly_reference_underlying_price
    if price <= 0:
        raise ValueError("monthly reference underlying price must be positive")
    return 0.01 if price < 250.0 else 0.05


def current_stock_future_tick(monthly_reference_underlying_price: float) -> float:
    """Stock-futures tick schedule effective 2025-04-15 (FAOP/67134)."""
    price = monthly_reference_underlying_price
    if price <= 0:
        raise ValueError("monthly reference underlying price must be positive")
    if price < 250:
        return 0.01
    if price <= 1000:
        return 0.05
    if price <= 5000:
        return 0.10
    if price <= 10000:
        return 0.50
    if price <= 20000:
        return 1.00
    return 5.00


def validate_master_tick(*, instrument: str, underlying_price: float, observed_tick: float) -> tuple[bool, str]:
    """Sanity-check OpenAlgo master metadata against current published rules.

    Fail soft: exchange master data is authoritative and can change. A mismatch
    returns a reason code rather than silently replacing provider metadata.
    """
    if observed_tick <= 0:
        return False, "NON_POSITIVE_TICK"
    if instrument == "INDEX_OPTION":
        expected = current_index_option_tick()
    elif instrument == "STOCK_OPTION":
        expected = current_stock_option_tick(underlying_price)
    elif instrument == "INDEX_FUTURE":
        expected = current_index_future_tick(underlying_price)
    elif instrument == "STOCK_FUTURE":
        expected = current_stock_future_tick(underlying_price)
    else:
        return True, "MASTER_DATA_AUTHORITATIVE"
    if abs(observed_tick - expected) > 1e-9:
        return False, f"TICK_RULE_MISMATCH:observed={observed_tick}:published={expected}"
    return True, "OK"
