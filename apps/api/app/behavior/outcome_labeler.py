from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleBar,
    ConservativeCostModel,
    ConservativeOutcomeLabelRequest,
    ConservativeOutcomeLabelResult,
)


CONSERVATIVE_OUTCOME_VERSION = "behavior-conservative-outcome-labeler.v0.64"
FILL_MODEL_VERSION = "conservative-open-first-costed-fill.v0.64"


def label_conservative_outcome(request: ConservativeOutcomeLabelRequest) -> ConservativeOutcomeLabelResult:
    bars = _post_entry_bars(request)
    run_id = request.run_id or str(uuid5(NAMESPACE_URL, f"tradevision:v064:{request.series.symbol}:{request.pattern_id}:{request.entry_price}:{request.stop_price}:{request.target_price}"))
    if not bars:
        return _result(
            request=request,
            run_id=run_id,
            executable_entry_price=request.entry_price,
            first_target_index=None,
            first_stop_index=None,
            first_target_time=None,
            first_stop_time=None,
            mfe_price=0.0,
            mae_price=0.0,
            gross_return_pct=0.0,
            outcome_label="NO_FILL" if request.order_type == "limit_order" else "NEITHER_HIT_TIME_EXIT",
            horizon_end=None,
            same_bar_ambiguous=False,
            gap_through_stop=False,
            no_fill=request.order_type == "limit_order",
            conservative_ordering_used=True,
            lower_timeframe_required=False,
            reason="No post-entry bars were available; conservative labeler did not assume a favorable fill or outcome.",
        )

    fill_price, no_fill, fill_reason = _executable_entry(request, bars[0])
    bars = bars[: request.max_holding_bars]
    if no_fill:
        mfe_price, mae_price = _mfe_mae(request, request.entry_price, bars)
        return _result(
            request=request,
            run_id=run_id,
            executable_entry_price=fill_price,
            first_target_index=None,
            first_stop_index=None,
            first_target_time=None,
            first_stop_time=None,
            mfe_price=mfe_price,
            mae_price=mae_price,
            gross_return_pct=0.0,
            outcome_label="NO_FILL",
            horizon_end=bars[-1].timestamp_ns,
            same_bar_ambiguous=False,
            gap_through_stop=False,
            no_fill=True,
            conservative_ordering_used=True,
            lower_timeframe_required=False,
            reason=fill_reason,
        )

    first_target_index, first_target_time = _first_target_hit(request, bars)
    first_stop_index, first_stop_time = _first_stop_hit(request, bars)
    same_bar_ambiguous = (
        first_target_index is not None
        and first_stop_index is not None
        and first_target_index == first_stop_index
        and not request.has_lower_timeframe_sequence
    )
    gap_through_stop = _gap_through_stop(request, bars[0])
    mfe_price, mae_price = _mfe_mae(request, fill_price, bars)
    gross_return_pct, label, reason = _label_and_return(
        request=request,
        bars=bars,
        fill_price=fill_price,
        first_target_index=first_target_index,
        first_stop_index=first_stop_index,
        same_bar_ambiguous=same_bar_ambiguous,
        gap_through_stop=gap_through_stop,
    )
    if abs(gross_return_pct) <= 0.03 and label == "NEITHER_HIT_TIME_EXIT":
        label = "BREAKEVEN"
        reason = "Neither barrier was hit and the final close was near the executable entry after conservative fill handling."
    return _result(
        request=request,
        run_id=run_id,
        executable_entry_price=fill_price,
        first_target_index=first_target_index,
        first_stop_index=first_stop_index,
        first_target_time=first_target_time,
        first_stop_time=first_stop_time,
        mfe_price=mfe_price,
        mae_price=mae_price,
        gross_return_pct=gross_return_pct,
        outcome_label=label,
        horizon_end=bars[-1].timestamp_ns,
        same_bar_ambiguous=same_bar_ambiguous,
        gap_through_stop=gap_through_stop,
        no_fill=False,
        conservative_ordering_used=True,
        lower_timeframe_required=same_bar_ambiguous,
        reason=reason,
    )


def _post_entry_bars(request: ConservativeOutcomeLabelRequest) -> list[CandleBar]:
    bars = sorted(request.series.bars, key=lambda item: item.timestamp_ns)
    if request.entry_time_ns is None:
        return bars
    return [bar for bar in bars if bar.timestamp_ns >= request.entry_time_ns]


def _executable_entry(request: ConservativeOutcomeLabelRequest, first_bar: CandleBar) -> tuple[float, bool, str]:
    slippage = _entry_slippage_price(request)
    if request.order_type == "market_order":
        if request.direction == "long":
            return round(first_bar.open + slippage, 4), False, "Market order filled at next eligible open plus conservative slippage."
        return round(first_bar.open - slippage, 4), False, "Market order filled at next eligible open minus conservative slippage for short."
    if request.order_type == "limit_order":
        touched = first_bar.low <= request.entry_price <= first_bar.high
        ambiguous = first_bar.low <= request.stop_price <= first_bar.high and first_bar.low <= request.target_price <= first_bar.high
        if touched and not ambiguous:
            return request.entry_price, False, "Limit order touched without same-bar stop/target ambiguity."
        return request.entry_price, True, "Limit order was not safely fillable; touched-only ambiguous OHLC is labeled NO_FILL."
    return request.entry_price, False, "Stop order activation is treated as filled at stop/entry or worse by later barrier rules."


def _first_target_hit(request: ConservativeOutcomeLabelRequest, bars: list[CandleBar]) -> tuple[int | None, int | None]:
    for index, bar in enumerate(bars):
        if request.direction == "long" and bar.high >= request.target_price:
            return index, bar.timestamp_ns
        if request.direction == "short" and bar.low <= request.target_price:
            return index, bar.timestamp_ns
    return None, None


def _first_stop_hit(request: ConservativeOutcomeLabelRequest, bars: list[CandleBar]) -> tuple[int | None, int | None]:
    for index, bar in enumerate(bars):
        if request.direction == "long" and bar.low <= request.stop_price:
            return index, bar.timestamp_ns
        if request.direction == "short" and bar.high >= request.stop_price:
            return index, bar.timestamp_ns
    return None, None


def _gap_through_stop(request: ConservativeOutcomeLabelRequest, first_bar: CandleBar) -> bool:
    if request.direction == "long":
        return first_bar.open < request.stop_price
    return first_bar.open > request.stop_price


def _mfe_mae(request: ConservativeOutcomeLabelRequest, entry_price: float, bars: list[CandleBar]) -> tuple[float, float]:
    if not bars:
        return 0.0, 0.0
    if request.direction == "long":
        mfe = max(bar.high - entry_price for bar in bars)
        mae = max(entry_price - bar.low for bar in bars)
    else:
        mfe = max(entry_price - bar.low for bar in bars)
        mae = max(bar.high - entry_price for bar in bars)
    return round(max(mfe, 0.0), 4), round(max(mae, 0.0), 4)


def _label_and_return(
    *,
    request: ConservativeOutcomeLabelRequest,
    bars: list[CandleBar],
    fill_price: float,
    first_target_index: int | None,
    first_stop_index: int | None,
    same_bar_ambiguous: bool,
    gap_through_stop: bool,
) -> tuple[float, str, str]:
    if gap_through_stop:
        stop_fill = bars[0].open
        return _gross_pct(request, fill_price, stop_fill), "GAP_THROUGH_STOP", "Next open crossed beyond stop; executable open price is used before any optimistic barrier assumption."
    if same_bar_ambiguous:
        return 0.0, "AMBIGUOUS_BOTH_HIT_SAME_BAR", "Target and stop touched in the same OHLC bar without lower-timeframe path; profitable ordering is not assumed."
    if first_target_index is not None and first_stop_index is not None:
        if first_target_index < first_stop_index:
            return _gross_pct(request, fill_price, request.target_price), "TARGET_HIT_FIRST", "Target was reached before stop using open-price-first conservative ordering."
        if first_stop_index < first_target_index:
            return _gross_pct(request, fill_price, request.stop_price), "SL_HIT_FIRST", "Stop was reached before target using open-price-first conservative ordering."
        return 0.0, "AMBIGUOUS_BOTH_HIT_SAME_BAR", "Target and stop have equal ordering; conservative ambiguity label used."
    if first_target_index is not None:
        if first_target_index == 0 and _open_gap_target(request, bars[0]):
            return _gross_pct(request, fill_price, bars[0].open), "OVERNIGHT_GAP_TARGET", "First executable open was already beyond target; open price is used."
        return _gross_pct(request, fill_price, request.target_price), "TARGET_HIT_FIRST", "Target was reached before stop."
    if first_stop_index is not None:
        if first_stop_index == 0 and _open_gap_stop(request, bars[0]):
            return _gross_pct(request, fill_price, bars[0].open), "OVERNIGHT_GAP_SL", "First executable open was already beyond stop; open price is used."
        return _gross_pct(request, fill_price, request.stop_price), "SL_HIT_FIRST", "Stop was reached before target."
    final_close = bars[-1].close
    return _gross_pct(request, fill_price, final_close), "NEITHER_HIT_TIME_EXIT", "Maximum holding window ended before target or stop."


def _open_gap_target(request: ConservativeOutcomeLabelRequest, bar: CandleBar) -> bool:
    return bar.open >= request.target_price if request.direction == "long" else bar.open <= request.target_price


def _open_gap_stop(request: ConservativeOutcomeLabelRequest, bar: CandleBar) -> bool:
    return bar.open <= request.stop_price if request.direction == "long" else bar.open >= request.stop_price


def _gross_pct(request: ConservativeOutcomeLabelRequest, entry: float, exit_price: float) -> float:
    if entry <= 0:
        return 0.0
    pnl = exit_price - entry if request.direction == "long" else entry - exit_price
    return round((pnl / entry) * 100.0, 6)


def _entry_slippage_price(request: ConservativeOutcomeLabelRequest) -> float:
    return request.entry_price * ((request.cost_model.latency_slippage_pct + request.cost_model.impact_cost_pct) / 100.0)


def _total_cost_pct(cost_model: ConservativeCostModel) -> float:
    brokerage = min(cost_model.brokerage_pct_per_side * 2, cost_model.brokerage_cap_rs / 100_000.0)
    taxable_charges = brokerage + cost_model.exchange_transaction_pct + cost_model.sebi_pct
    gst = taxable_charges * (cost_model.gst_pct_on_charges / 100.0)
    return round(
        brokerage
        + cost_model.stt_sell_side_pct
        + cost_model.sebi_pct
        + cost_model.exchange_transaction_pct
        + cost_model.stamp_duty_buy_side_pct
        + cost_model.impact_cost_pct
        + cost_model.latency_slippage_pct
        + cost_model.adverse_selection_penalty_pct
        + gst,
        6,
    )


def _result(
    *,
    request: ConservativeOutcomeLabelRequest,
    run_id: str,
    executable_entry_price: float,
    first_target_index: int | None,
    first_stop_index: int | None,
    first_target_time: int | None,
    first_stop_time: int | None,
    mfe_price: float,
    mae_price: float,
    gross_return_pct: float,
    outcome_label: str,
    horizon_end: int | None,
    same_bar_ambiguous: bool,
    gap_through_stop: bool,
    no_fill: bool,
    conservative_ordering_used: bool,
    lower_timeframe_required: bool,
    reason: str,
) -> ConservativeOutcomeLabelResult:
    total_cost = _total_cost_pct(request.cost_model)
    net = 0.0 if no_fill else round(gross_return_pct - total_cost, 6)
    return ConservativeOutcomeLabelResult(
        outcome_version=CONSERVATIVE_OUTCOME_VERSION,
        run_id=run_id,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        direction=request.direction,
        pattern_id=request.pattern_id,
        entry_time_ns=request.entry_time_ns,
        entry_price=request.entry_price,
        executable_entry_price=round(executable_entry_price, 4),
        fill_model_version=FILL_MODEL_VERSION,
        target_price=request.target_price,
        stop_price=request.stop_price,
        first_target_time_ns=first_target_time,
        first_stop_time_ns=first_stop_time,
        bars_to_target=first_target_index + 1 if first_target_index is not None else None,
        bars_to_stop=first_stop_index + 1 if first_stop_index is not None else None,
        mfe_price=round(mfe_price, 4),
        mae_price=round(mae_price, 4),
        mfe_atr=round(mfe_price / request.atr, 4),
        mae_atr=round(mae_price / request.atr, 4),
        gross_return_pct=round(gross_return_pct, 6),
        total_cost_pct=total_cost,
        net_return_after_costs=net,
        outcome_label=outcome_label,  # type: ignore[arg-type]
        outcome_horizon_end_ns=horizon_end,
        same_bar_ambiguous=same_bar_ambiguous,
        gap_through_stop=gap_through_stop,
        no_fill=no_fill,
        conservative_ordering_used=conservative_ordering_used,
        lower_timeframe_required=lower_timeframe_required,
        reason=reason,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        audit_fields={
            "open_price_first": True,
            "ambiguous_same_bar_not_target_hit": True,
            "has_lower_timeframe_sequence": request.has_lower_timeframe_sequence,
            "max_holding_bars": request.max_holding_bars,
            "order_type": request.order_type,
            "quantity": request.quantity,
        },
    )
