"""Single paper/research fill and exit engine.

Entries are at the first *whole execution bar open* strictly after approval.
No retrospective boundary fill and no favorable later-open shopping. Fixed
structural stop, fixed recipe RR target computed once from the actual fill.
OHLC ambiguity uses stop-first; target-gap improvement is conservatively not
credited. Modeled friction can put a fill outside the raw candle: it is an
explicit cost assumption, not an observed transaction.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN
from .contracts import (
    AccountLimits, Bar, Costs, MarketSnapshot, Policy, Position, Side, Template,
    TradePlan, MINUTE, NS, clock_ns, digest, evolve, next_grid_ns,
)


def D(value: float | int | str) -> Decimal:
    return Decimal(str(value))


def grid(price: float, tick: float, upward: bool) -> float:
    rounding = ROUND_CEILING if upward else ROUND_FLOOR
    ratio = D(price) / D(tick)
    nearest = ratio.to_integral_value(rounding=ROUND_HALF_EVEN)
    # Suppress sub-billionth-tick binary float arithmetic noise, not a genuine
    # off-grid price. All economic arithmetic below otherwise uses Decimal.
    if abs(ratio-nearest) < Decimal("1e-9"):
        ratio = nearest
    result = ratio.to_integral_value(rounding=rounding) * D(tick)
    return float(result)


def adverse_price(price: float, side: Side, tick: float, costs: Costs, *, entry: bool) -> float:
    bps = D(costs.spread_bps) / 2 + D(costs.slippage_bps) + D(costs.impact_bps)
    sign = side.sign if entry else -side.sign
    result = D(price) * (1 + sign * bps / 10_000)
    return grid(float(result), tick, upward=sign > 0)


def target_for(entry: float, stop: float, side: Side, rr: int, tick: float) -> float:
    risk = (D(entry) - D(stop)) * side.sign
    if risk <= 0:
        raise ValueError("STOP_ON_WRONG_SIDE_OF_ACTUAL_FILL")
    target = D(entry) + side.sign * rr * risk
    if target <= 0:
        raise ValueError("NON_POSITIVE_TARGET")
    return grid(float(target), tick, upward=side == Side.LONG)


def estimated_cost_r(entry: float, stop: float, side: Side, tick: float, costs: Costs) -> float:
    risk = abs(entry - stop)
    if risk <= 0:
        return float("inf")
    # Diagnostic total friction versus an ideal reference. NOT a second PnL debit.
    entry_friction = abs(adverse_price(entry, side, tick, costs, entry=True) - entry)
    exit_friction = abs(adverse_price(stop, side, tick, costs, entry=False) - stop)
    fee = (entry + stop) * costs.fee_bps_per_side / 10_000
    return (entry_friction + exit_friction + fee) / risk


def build_plan(snapshot: MarketSnapshot, policy: Policy, limits: AccountLimits,
               template: Template, side: Side, stop: float, invalidation: float,
               reason_codes: tuple[str, ...]) -> tuple[TradePlan | None, tuple[str, ...]]:
    tick = snapshot.prior.tick_size
    now = snapshot.as_of_ns
    last_entry = clock_ns(snapshot.session_date, policy.last_entry_minute)
    expiry = min(now + policy.proposal_ttl_seconds * NS, last_entry)
    if not snapshot.bars or now >= expiry:
        return None, ("ENTRY_WINDOW_EXPIRED",)
    earliest = next_grid_ns(now + policy.replay_approval_delay_seconds * NS + 1,
                            snapshot.session_date, policy.execution_minutes)
    if earliest > min(expiry, last_entry):
        return None, ("NO_OBSERVABLE_PERMITTED_FILL_BEFORE_EXPIRY",)
    reference = adverse_price(snapshot.bars[-1].close, side, tick, policy.costs, entry=True)
    low = grid(reference - tick * policy.entry_envelope_ticks, tick, False)
    high = grid(reference + tick * policy.entry_envelope_ticks, tick, True)
    stop = grid(stop, tick, upward=side == Side.SHORT)
    if low <= 0 or stop <= 0 or (side == Side.LONG and stop >= low) or (side == Side.SHORT and stop <= high):
        return None, ("WRONG_SIDE_STOP_IN_ENTRY_ENVELOPE",)
    min_risk = min(abs(low - stop), abs(high - stop))
    if min_risk + 1e-10 < policy.minimum_stop_ticks * tick:
        return None, ("STOP_BELOW_MINIMUM_PRICE_RESOLUTION",)
    if estimated_cost_r(reference, stop, side, tick, policy.costs) > policy.maximum_cost_r:
        return None, ("COST_TO_RISK_EXCEEDS_FROZEN_LIMIT",)
    try:
        targets = [target_for(e, stop, side, policy.reward_risk, tick) for e in (low, high, reference)]
    except ValueError as exc:
        return None, (str(exc),)
    fade = template == Template.GAP_FADE
    pdc = snapshot.prior.close
    if fade and (min(targets) < pdc + tick - 1e-9 if side == Side.SHORT else max(targets) > pdc - tick + 1e-9):
        return None, ("FIXED_FADE_TARGET_DOES_NOT_FIT_BEFORE_PDC",)
    exit_at_stop = adverse_price(stop, side, tick, policy.costs, entry=False)
    unit_risk = max(abs(e - exit_at_stop) + (e + exit_at_stop) * policy.costs.fee_bps_per_side / 10_000
                    for e in (low, high))
    quantity = min(limits.maximum_quantity, int(D(limits.risk_budget) / D(unit_risk)),
                   int(D(limits.maximum_notional) / D(high)))
    if quantity <= 0 or limits.risk_budget < policy.minimum_risk_budget:
        return None, ("INSUFFICIENT_RISK_OR_NOTIONAL_BUDGET",)
    identity = {"snapshot": snapshot.snapshot_hash, "policy": policy.policy_hash,
                "template": template.value, "side": side.value, "stop": stop,
                "entry": reference, "limits": limits.model_dump(mode="json")}
    plan = TradePlan(
        proposal_id=digest(identity), policy_hash=policy.policy_hash,
        snapshot_hash=snapshot.snapshot_hash, symbol=snapshot.prior.symbol,
        session_date=snapshot.session_date, template=template, side=side,
        created_ns=now, expires_ns=expiry, last_entry_ns=last_entry,
        flat_ns=clock_ns(snapshot.session_date, policy.flat_minute),
        execution_minutes=policy.execution_minutes, tick_size=tick,
        price_basis=snapshot.prior.price_basis, reference_entry=reference,
        minimum_entry=low, maximum_entry=high, stop=stop,
        reward_risk=policy.reward_risk, reference_target=targets[-1],
        maximum_quantity=quantity, risk_budget=limits.risk_budget,
        maximum_notional=limits.maximum_notional, cost_model=policy.costs,
        pdc=pdc, requires_gap_unfilled=fade, invalidation_level=invalidation,
        invalidate_on="GAP_DIRECTION_RECLAIM" if fade else "CLOSE_BACK_INSIDE",
        reason_codes=reason_codes,
    )
    return plan, ()


def start_position(plan: TradePlan, limits: AccountLimits, approved_ns: int,
                   quantity: int, approved_by: str, *, research: bool = False) -> Position:
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 0 < quantity <= plan.maximum_quantity:
        raise ValueError("QUANTITY_OUTSIDE_APPROVED_BOUND")
    if not plan.created_ns <= approved_ns < min(plan.expires_ns, plan.last_entry_ns):
        raise ValueError("APPROVAL_EXPIRED_OR_BEFORE_DECISION")
    expected = next_grid_ns(approved_ns + 1, plan.session_date, plan.execution_minutes)
    if expected > min(plan.last_entry_ns, plan.expires_ns):
        raise ValueError("NO_ELIGIBLE_EXECUTION_OPEN")
    return Position(position_id=digest([limits.account_id, plan.proposal_id]),
                    account_id=limits.account_id, plan=plan, approved_ns=approved_ns,
                    approved_by=approved_by, quantity=quantity, expected_open_ns=expected,
                    origin="RESEARCH_REPLAY" if research else "HUMAN_APPROVED_PAPER")


def mark_unknown(position: Position, reason: str) -> Position:
    if position.status in {"CLOSED", "NO_FILL", "UNKNOWN"}:
        return position
    return evolve(position, status="UNKNOWN", label="UNRESOLVED_DATA", unavailable_reason=reason,
                  gross_pnl=None, fees=None, net_pnl=None, net_r=None, net_budget_units=None)


def cancel_pending(position: Position, reason: str) -> Position:
    if position.status != "PENDING":
        return position
    return evolve(position, status="NO_FILL", label=reason, gross_pnl=0.0, fees=0.0,
                  net_pnl=0.0, net_r=0.0, net_budget_units=0.0)


def _excursions(position: Position, low: float, high: float, *, uncertain: bool = False,
                guaranteed_low: float | None = None, guaranteed_high: float | None = None) -> Position:
    assert position.fill_price is not None
    def pair(lo: float, hi: float) -> tuple[float, float]:
        if position.plan.side == Side.LONG:
            return max(0.0, hi - position.fill_price), max(0.0, position.fill_price - lo)
        return max(0.0, position.fill_price - lo), max(0.0, hi - position.fill_price)
    upper_mfe, upper_mae = pair(low, high)
    lower_mfe, lower_mae = pair(guaranteed_low if uncertain else low,
                              guaranteed_high if uncertain else high)  # type: ignore[arg-type]
    return evolve(position, mfe_lower=max(position.mfe_lower, lower_mfe),
                  mfe_upper=max(position.mfe_upper, upper_mfe),
                  mae_lower=max(position.mae_lower, lower_mae),
                  mae_upper=max(position.mae_upper, upper_mae))


def _close(position: Position, raw: float, when: int, label: str, ambiguous: bool = False) -> Position:
    plan = position.plan
    assert position.fill_price is not None and position.initial_risk_per_unit is not None
    exit_price = adverse_price(raw, plan.side, plan.tick_size, plan.cost_model, entry=False)
    if exit_price <= 0:
        return mark_unknown(position, "EXIT_FRICTION_PRODUCED_NON_POSITIVE_PRICE")
    entry = D(position.fill_price)
    exit_d = D(exit_price)
    gross = (exit_d - entry) * plan.side.sign * position.quantity
    fees = (entry + exit_d) * D(plan.cost_model.fee_bps_per_side) / 10_000 * position.quantity
    net = gross - fees
    return evolve(position, status="CLOSED", label=label, exit_price=exit_price, exit_ns=when,
                  exit_time_precision=("OPEN" if "GAP" in label else "SCHEDULED_CLOSE" if label == "TIME_EXIT" else "OBSERVATION_ENDPOINT"),
                  gross_pnl=float(gross), fees=float(fees), net_pnl=float(net),
                  net_r=float(net / (D(position.initial_risk_per_unit) * position.quantity)),
                  net_budget_units=float(net / D(plan.risk_budget)), same_bar_ambiguous=ambiguous)


def advance_position(position: Position, bar: Bar, *, as_of_ns: int) -> Position:
    """Advance exactly once from a fully available execution bar.

    Missing intervals become UNKNOWN; no synthetic stop/flat price is created.
    Terminal outcomes do not change when later bars are appended.
    """
    if position.status in {"CLOSED", "NO_FILL", "UNKNOWN"}:
        return position
    plan = position.plan
    if bar.symbol != plan.symbol or bar.minutes != plan.execution_minutes or bar.price_basis != plan.price_basis:
        return mark_unknown(position, "EXECUTION_IDENTITY_MISMATCH")
    if bar.available_ns > as_of_ns:
        raise ValueError("EXECUTION_BAR_NOT_YET_AVAILABLE")
    if bar.event_id == position.last_execution_event:
        return position
    if bar.open_ns < position.expected_open_ns:
        return position  # whole bar started before approval, or already consumed
    if bar.open_ns > position.expected_open_ns:
        return mark_unknown(position, "MISSING_EXECUTION_INTERVAL")
    if position.status == "PENDING":
        if bar.open_ns > min(plan.expires_ns, plan.last_entry_ns):
            return cancel_pending(position, "ENTRY_EXPIRED")
        # PDC on the OPEN is already known at this fill. High/low of the future
        # fill bar must not be used as a pre-entry veto.
        if plan.requires_gap_unfilled and (bar.open <= plan.pdc if plan.side == Side.SHORT else bar.open >= plan.pdc):
            return cancel_pending(position, "GAP_ALREADY_FILLED_AT_EXECUTION_OPEN")
        fill = adverse_price(bar.open, plan.side, plan.tick_size, plan.cost_model, entry=True)
        if (plan.side == Side.LONG and fill <= plan.stop) or (plan.side == Side.SHORT and fill >= plan.stop):
            return cancel_pending(position, "STOP_ON_WRONG_SIDE_OF_ACTUAL_FILL")
        if not plan.minimum_entry - 1e-9 <= fill <= plan.maximum_entry + 1e-9:
            return cancel_pending(position, "ACTUAL_FILL_OUTSIDE_APPROVED_ENVELOPE")
        target = target_for(fill, plan.stop, plan.side, plan.reward_risk, plan.tick_size)
        if plan.requires_gap_unfilled and (target < plan.pdc + plan.tick_size - 1e-9 if plan.side == Side.SHORT else target > plan.pdc - plan.tick_size + 1e-9):
            return cancel_pending(position, "FADE_ROOM_GONE_AT_ACTUAL_FILL")
        risk = abs(fill - plan.stop)
        worst_stop = adverse_price(plan.stop, plan.side, plan.tick_size, plan.cost_model, entry=False)
        nominal_loss = (abs(fill - worst_stop) + (fill + worst_stop) * plan.cost_model.fee_bps_per_side / 10_000) * position.quantity
        if nominal_loss > plan.risk_budget + 1e-8 or fill * position.quantity > plan.maximum_notional + 1e-8:
            return cancel_pending(position, "FILL_BREACHES_FROZEN_NOMINAL_BUDGET")
        position = evolve(position, status="OPEN", label="OPEN", fill_ns=bar.open_ns,
                          fill_price=fill, target=target, initial_risk_per_unit=risk)
    position = evolve(position, expected_open_ns=bar.close_ns, last_execution_event=bar.event_id,
                      observations=position.observations + 1)
    assert position.target is not None
    if bar.open_ns >= plan.flat_ns:
        position = _excursions(position, bar.open, bar.open)
        return _close(position, bar.open, bar.open_ns, "TIME_EXIT")
    if bar.open_ns < plan.flat_ns < bar.close_ns:
        return mark_unknown(position, "FLAT_TIME_INSIDE_UNOBSERVABLE_EXECUTION_BAR")
    long = plan.side == Side.LONG
    # Opening gap checks must precede intrabar extremes.
    if (bar.open <= plan.stop if long else bar.open >= plan.stop):
        position = _excursions(position, bar.open, bar.open)
        return _close(position, bar.open, bar.open_ns, "STOP_GAP")
    if (bar.open >= position.target if long else bar.open <= position.target):
        position = _excursions(position, position.target, position.target)
        return _close(position, position.target, bar.open_ns, "TARGET_GAP_CONSERVATIVE")
    stop_hit = bar.low <= plan.stop if long else bar.high >= plan.stop
    target_hit = bar.high >= position.target if long else bar.low <= position.target
    if stop_hit or target_hit:
        raw = plan.stop if stop_hit else position.target
        # Exit happened somewhere inside this interval. Its exact nanosecond is
        # unknown: close_ns is the observation endpoint, not a made-up hit time.
        position = _excursions(position, bar.low, bar.high, uncertain=True,
                               guaranteed_low=min(bar.open, raw), guaranteed_high=max(bar.open, raw))
        return _close(position, raw, bar.close_ns, "STOP_FIRST" if stop_hit else "TARGET_FIRST",
                      ambiguous=stop_hit and target_hit)
    position = _excursions(position, bar.low, bar.high)
    if bar.close_ns == plan.flat_ns:
        return _close(position, bar.close, bar.close_ns, "TIME_EXIT")
    return position
