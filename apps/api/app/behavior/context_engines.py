from __future__ import annotations

from statistics import mean

from ..models import (
    BehaviorContextRequest,
    BehaviorContextResult,
    CandleBar,
    CandleSeries,
    GapContextRequest,
    GapContextResult,
    HTFConfirmationRecord,
    HTFConfirmationRequest,
    HTFConfirmationResult,
    MarketContextRequest,
    MarketContextResult,
    TradeDirection,
    VwapOrbCprContextRequest,
    VwapOrbCprContextResult,
)
from .point_in_time_guard import timeframe_duration_ns


CONTEXT_VERSION = "behavior-context.v0.16"


def analyze_level_context(request: VwapOrbCprContextRequest) -> VwapOrbCprContextResult:
    bars = _closed_or_all_bars(request.series, request.decision_time_ns)
    latest = bars[-1] if bars else None
    previous = bars[-2] if len(bars) >= 2 else None
    latest_close = latest.close if latest else None
    calculated_vwap = request.vwap if request.vwap is not None else _calculate_vwap(bars)
    opening_high = request.opening_range_high if request.opening_range_high is not None else _opening_range_high(bars)
    opening_low = request.opening_range_low if request.opening_range_low is not None else _opening_range_low(bars)
    pivot, bc, tc = _calculate_cpr(request.previous_day_high, request.previous_day_low, request.previous_close)

    vwap_state = _state_against_level(latest, previous, calculated_vwap)
    orb_state = _opening_range_state(latest, opening_high, opening_low)
    cpr_state = _cpr_state(latest_close, bc, tc)
    pdh_state = _state_against_level(latest, previous, request.previous_day_high)
    pdl_state = _state_against_level(latest, previous, request.previous_day_low)
    vpd_state = _vpd_state(latest_close, request.volume_profile_hvn, request.volume_profile_lvn)
    flags = _support_resistance_flags(latest, request, calculated_vwap, opening_high, opening_low, pivot, bc, tc)
    score = _level_respect_score(vwap_state, orb_state, cpr_state, pdh_state, pdl_state, flags)
    reasons = _level_reasons(vwap_state, orb_state, cpr_state, pdh_state, pdl_state, vpd_state, flags)
    blocks_trade = any(flag in flags for flag in ["rejecting_pdh", "failed_orb_breakout", "below_vwap", "near_lvn_instability"])

    return VwapOrbCprContextResult(
        context_version=CONTEXT_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        latest_close=latest_close,
        calculated_vwap=calculated_vwap,
        price_vs_vwap_pct=_pct_diff(latest_close, calculated_vwap),
        vwap_state=vwap_state,
        opening_range_high=opening_high,
        opening_range_low=opening_low,
        opening_range_state=orb_state,
        cpr_pivot=pivot,
        cpr_bc=bc,
        cpr_tc=tc,
        cpr_state=cpr_state,
        pdh_state=pdh_state,
        pdl_state=pdl_state,
        vpd_state=vpd_state,
        support_resistance_flags=flags,
        level_respect_score=round(score, 4),
        blocks_trade=blocks_trade,
        reasons=reasons,
    )


def analyze_htf_confirmation(request: HTFConfirmationRequest) -> HTFConfirmationResult:
    records = [_htf_record(series, request.decision_time_ns, request.direction) for series in request.higher_timeframe_series]
    reasons: list[str] = []
    if not records:
        reasons.append("No higher-timeframe series supplied; HTF confirmation unavailable.")
    else:
        reasons.extend(record.reason for record in records)

    available = [record for record in records if record.bias != "unavailable"]
    confirmations = [record for record in available if record.confirmed]
    conflicts = [record for record in available if not record.confirmed and record.bias != "neutral"]
    confirmed = bool(available) and len(confirmations) >= max(1, len(available) // 2 + len(available) % 2)
    blocks_trade = request.direction != "neutral" and bool(conflicts) and not confirmed
    confidence_adjustment = 0.12 if confirmed else (-0.18 if blocks_trade else -0.05)

    return HTFConfirmationResult(
        context_version=CONTEXT_VERSION,
        symbol=request.symbol.upper(),
        decision_time_ns=request.decision_time_ns,
        direction=request.direction,
        records=records,
        confirmed=confirmed,
        blocks_trade=blocks_trade,
        confidence_adjustment=round(confidence_adjustment, 4),
        reasons=reasons,
    )


def analyze_gap_context(request: GapContextRequest) -> GapContextResult:
    bars = request.series.bars
    first = bars[0] if bars else None
    latest = bars[-1] if bars else None
    gap_pct = _pct_diff(first.open if first else None, request.previous_close)
    gap_type = _gap_type(gap_pct, request.atr, request.previous_close)
    fill_probability = _gap_fill_probability(first, latest, request.previous_close, gap_pct)
    trap_risk = _gap_trap_risk(first, latest, gap_pct)
    blocks_trade = trap_risk >= 0.68 or gap_type in {"large_gap_up", "large_gap_down"}
    reasons = [
        f"Gap type is {gap_type}.",
        f"Gap fill probability is {round(fill_probability, 2)}%.",
        f"Gap trap risk is {round(trap_risk, 2)}.",
    ]
    if blocks_trade:
        reasons.append("Gap context blocks trade-like promotion until retest or follow-through confirms.")

    return GapContextResult(
        context_version=CONTEXT_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        opening_price=first.open if first else None,
        latest_close=latest.close if latest else None,
        previous_close=request.previous_close,
        gap_pct=gap_pct,
        gap_type=gap_type,
        gap_fill_probability_pct=round(fill_probability, 4),
        gap_trap_risk=round(trap_risk, 4),
        blocks_trade=blocks_trade,
        reasons=reasons,
    )


def analyze_market_context(request: MarketContextRequest) -> MarketContextResult:
    index_direction = _direction_label(request.index_return_pct)
    sector_strength = _sector_strength(request.sector_return_pct)
    relative_strength_score = _relative_strength_score(
        request.stock_return_pct,
        request.index_return_pct,
        request.sector_return_pct,
        request.global_risk_score,
    )
    alignment = _market_alignment(request.direction, request.index_return_pct, request.sector_return_pct, request.global_risk_score)
    blocks_trade = alignment == "avoid" or (
        request.direction == "long" and request.index_return_pct < -0.35 and request.sector_return_pct < -0.35
    ) or (
        request.direction == "short" and request.index_return_pct > 0.35 and request.sector_return_pct > 0.35
    )
    reasons = [
        f"Index direction is {index_direction} at {request.index_return_pct}%.",
        f"Sector strength is {sector_strength} at {request.sector_return_pct}%.",
        f"Relative strength score is {round(relative_strength_score, 2)}.",
        f"Market alignment is {alignment}.",
    ]
    if blocks_trade:
        reasons.append("Index/sector context conflicts with the requested trade direction.")

    return MarketContextResult(
        context_version=CONTEXT_VERSION,
        symbol=request.symbol.upper(),
        direction=request.direction,
        index_direction=index_direction,
        sector_strength=sector_strength,
        relative_strength_score=round(relative_strength_score, 4),
        market_alignment=alignment,
        blocks_trade=blocks_trade,
        reasons=reasons,
    )


def analyze_behavior_context(request: BehaviorContextRequest) -> BehaviorContextResult:
    decision_time = request.decision_time_ns or _latest_close_time(request.series)
    levels = analyze_level_context(
        VwapOrbCprContextRequest(
            series=request.series,
            decision_time_ns=decision_time,
            previous_day_high=request.previous_day_high,
            previous_day_low=request.previous_day_low,
            previous_close=request.previous_close,
            vwap=request.vwap,
            opening_range_high=request.opening_range_high,
            opening_range_low=request.opening_range_low,
            volume_profile_hvn=request.volume_profile_hvn,
            volume_profile_lvn=request.volume_profile_lvn,
        )
    )
    htf = None
    if request.higher_timeframe_series:
        htf = analyze_htf_confirmation(
            HTFConfirmationRequest(
                symbol=request.series.symbol,
                decision_time_ns=decision_time,
                direction=request.direction,
                higher_timeframe_series=request.higher_timeframe_series,
            )
        )
    gap = None
    if request.previous_close is not None:
        gap = analyze_gap_context(GapContextRequest(series=request.series, previous_close=request.previous_close))
    market = analyze_market_context(
        MarketContextRequest(
            symbol=request.series.symbol,
            direction=request.direction,
            stock_return_pct=request.stock_return_pct,
            index_return_pct=request.index_return_pct,
            sector_return_pct=request.sector_return_pct,
            banknifty_return_pct=request.banknifty_return_pct,
            global_risk_score=request.global_risk_score,
        )
    )
    blockers = [
        levels.blocks_trade,
        bool(htf and htf.blocks_trade),
        bool(gap and gap.blocks_trade),
        market.blocks_trade,
    ]
    quality = _context_quality(levels, htf, gap, market)
    final_bias = _final_context_bias(request.direction, levels, htf, gap, market, blockers)
    reason_tree = {
        "levels": "; ".join(levels.reasons),
        "htf": "; ".join(htf.reasons) if htf else "No higher-timeframe context supplied.",
        "gap": "; ".join(gap.reasons) if gap else "No previous close supplied; gap context unavailable.",
        "market": "; ".join(market.reasons),
        "final": "Context blocks trade-like promotion." if any(blockers) else "Context does not block trade-like promotion.",
    }

    return BehaviorContextResult(
        context_version=CONTEXT_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        direction=request.direction,
        levels=levels,
        htf=htf,
        gap=gap,
        market=market,
        final_context_bias=final_bias,
        context_quality_score=round(quality, 4),
        blocks_trade=any(blockers),
        reason_tree=reason_tree,
    )


def _closed_or_all_bars(series: CandleSeries, decision_time_ns: int | None) -> list[CandleBar]:
    ordered = sorted(series.bars, key=lambda item: item.timestamp_ns)
    if decision_time_ns is None:
        return ordered
    duration = timeframe_duration_ns(series.timeframe)
    return [bar for bar in ordered if bar.timestamp_ns + duration <= decision_time_ns]


def _latest_close_time(series: CandleSeries) -> int:
    if not series.bars:
        return 0
    duration = timeframe_duration_ns(series.timeframe)
    return max(bar.timestamp_ns + duration for bar in series.bars)


def _calculate_vwap(bars: list[CandleBar]) -> float | None:
    weighted = 0.0
    total_volume = 0.0
    for bar in bars:
        if bar.volume is None:
            continue
        typical = (bar.high + bar.low + bar.close) / 3.0
        weighted += typical * bar.volume
        total_volume += bar.volume
    if total_volume <= 0:
        return None
    return round(weighted / total_volume, 4)


def _opening_range_high(bars: list[CandleBar], count: int = 3) -> float | None:
    if not bars:
        return None
    return max(bar.high for bar in bars[:count])


def _opening_range_low(bars: list[CandleBar], count: int = 3) -> float | None:
    if not bars:
        return None
    return min(bar.low for bar in bars[:count])


def _calculate_cpr(pdh: float | None, pdl: float | None, previous_close: float | None) -> tuple[float | None, float | None, float | None]:
    if pdh is None or pdl is None or previous_close is None:
        return None, None, None
    pivot = (pdh + pdl + previous_close) / 3.0
    bc = (pdh + pdl) / 2.0
    tc = pivot + (pivot - bc)
    return round(pivot, 4), round(min(bc, tc), 4), round(max(bc, tc), 4)


def _state_against_level(latest: CandleBar | None, previous: CandleBar | None, level: float | None):
    if latest is None or level is None:
        return "unknown"
    tolerance = max(level * 0.001, 0.01)
    if latest.high >= level and latest.close < level and _has_upper_wick_rejection(latest):
        return "rejecting"
    if previous and previous.close < level <= latest.close:
        return "reclaiming"
    if latest.close > level + tolerance:
        return "above"
    if latest.close < level - tolerance:
        return "below"
    return "inside"


def _opening_range_state(latest: CandleBar | None, high: float | None, low: float | None):
    if latest is None or high is None or low is None:
        return "unknown"
    if latest.high > high and latest.close <= high:
        return "rejecting"
    if latest.low < low and latest.close >= low:
        return "reclaiming"
    if latest.close > high:
        return "breaking_up"
    if latest.close < low:
        return "breaking_down"
    return "inside"


def _cpr_state(close: float | None, bc: float | None, tc: float | None):
    if close is None or bc is None or tc is None:
        return "unknown"
    if close > tc:
        return "above"
    if close < bc:
        return "below"
    return "inside"


def _vpd_state(close: float | None, hvn: float | None, lvn: float | None):
    if close is None or (hvn is None and lvn is None):
        return "unknown"
    if hvn is not None and abs(_pct_diff(close, hvn) or 0.0) <= 0.12:
        return "at_hvn"
    if lvn is not None and abs(_pct_diff(close, lvn) or 0.0) <= 0.12:
        return "at_lvn"
    if hvn is not None and close > hvn:
        return "above_hvn"
    if lvn is not None and close < lvn:
        return "below_lvn"
    return "between_nodes"


def _support_resistance_flags(
    latest: CandleBar | None,
    request: VwapOrbCprContextRequest,
    vwap: float | None,
    orb_high: float | None,
    orb_low: float | None,
    pivot: float | None,
    bc: float | None,
    tc: float | None,
) -> list[str]:
    if latest is None:
        return ["no_candles"]
    flags: list[str] = []
    if vwap is not None and latest.close < vwap:
        flags.append("below_vwap")
    if vwap is not None and latest.low <= vwap <= latest.close:
        flags.append("vwap_held")
    if request.previous_day_high is not None and latest.high >= request.previous_day_high and latest.close < request.previous_day_high:
        flags.append("rejecting_pdh")
    if request.previous_day_high is not None and latest.close > request.previous_day_high:
        flags.append("breaking_pdh")
    if request.previous_day_low is not None and latest.low <= request.previous_day_low and latest.close > request.previous_day_low:
        flags.append("reclaiming_pdl")
    if orb_high is not None and latest.high > orb_high and latest.close <= orb_high:
        flags.append("failed_orb_breakout")
    if orb_high is not None and latest.close > orb_high:
        flags.append("orb_breakout")
    if pivot is not None and latest.close >= pivot:
        flags.append("above_pivot")
    if bc is not None and tc is not None and bc <= latest.close <= tc:
        flags.append("inside_cpr")
    if request.volume_profile_lvn is not None and abs(_pct_diff(latest.close, request.volume_profile_lvn) or 0.0) <= 0.12:
        flags.append("near_lvn_instability")
    return flags or ["no_key_level_interaction"]


def _level_respect_score(*states_and_flags) -> float:
    score = 0.5
    flat: list[str] = []
    for item in states_and_flags:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    for item in flat:
        if item in {"above", "breaking_up", "reclaiming", "vwap_held", "orb_breakout", "above_pivot", "breaking_pdh"}:
            score += 0.06
        if item in {"rejecting", "below", "breaking_down", "failed_orb_breakout", "below_vwap", "near_lvn_instability"}:
            score -= 0.08
    return min(max(score, 0.0), 1.0)


def _level_reasons(vwap_state, orb_state, cpr_state, pdh_state, pdl_state, vpd_state, flags: list[str]) -> list[str]:
    return [
        f"VWAP state is {vwap_state}.",
        f"Opening range state is {orb_state}.",
        f"CPR state is {cpr_state}.",
        f"PDH state is {pdh_state}; PDL state is {pdl_state}.",
        f"Volume profile state is {vpd_state}.",
        f"Level flags: {', '.join(flags)}.",
    ]


def _htf_record(series: CandleSeries, decision_time_ns: int, direction: TradeDirection) -> HTFConfirmationRecord:
    bars = _closed_or_all_bars(series, decision_time_ns)
    if not bars:
        return HTFConfirmationRecord(
            timeframe=series.timeframe,
            usable_bars=0,
            latest_close=None,
            first_close=None,
            slope_pct=None,
            bias="unavailable",
            confirmed=False,
            reason=f"{series.timeframe}: no closed higher-timeframe candle available.",
        )
    first = bars[0]
    latest = bars[-1]
    slope_pct = _pct_diff(latest.close, first.close) or 0.0
    if slope_pct > 0.1:
        bias = "bullish"
    elif slope_pct < -0.1:
        bias = "bearish"
    else:
        bias = "neutral"
    confirmed = direction == "neutral" or (direction == "long" and bias in {"bullish", "neutral"}) or (direction == "short" and bias in {"bearish", "neutral"})
    return HTFConfirmationRecord(
        timeframe=series.timeframe,
        usable_bars=len(bars),
        latest_close=latest.close,
        first_close=first.close,
        slope_pct=round(slope_pct, 4),
        bias=bias,
        confirmed=confirmed,
        reason=f"{series.timeframe}: {bias} slope {round(slope_pct, 4)}% with {len(bars)} closed candles.",
    )


def _gap_type(gap_pct: float | None, atr: float | None, previous_close: float):
    if gap_pct is None:
        return "unknown"
    atr_pct = (atr / previous_close * 100.0) if atr else 0.75
    large_threshold = max(1.0, atr_pct * 1.4)
    if abs(gap_pct) <= 0.1:
        return "flat_gap"
    if gap_pct >= large_threshold:
        return "large_gap_up"
    if gap_pct <= -large_threshold:
        return "large_gap_down"
    return "gap_up" if gap_pct > 0 else "gap_down"


def _gap_fill_probability(first: CandleBar | None, latest: CandleBar | None, previous_close: float, gap_pct: float | None) -> float:
    if first is None or latest is None or gap_pct is None:
        return 0.0
    if abs(gap_pct) <= 0.1:
        return 35.0
    if gap_pct > 0:
        progress = max(0.0, (first.open - latest.close) / max(first.open - previous_close, 0.0001))
    else:
        progress = max(0.0, (latest.close - first.open) / max(previous_close - first.open, 0.0001))
    return min(90.0, 25.0 + progress * 65.0)


def _gap_trap_risk(first: CandleBar | None, latest: CandleBar | None, gap_pct: float | None) -> float:
    if first is None or latest is None or gap_pct is None:
        return 0.0
    score = 0.15
    if gap_pct > 0 and latest.close < first.open:
        score += 0.45
    if gap_pct < 0 and latest.close > first.open:
        score += 0.45
    if latest.high > first.high and latest.close < first.high:
        score += 0.2
    if latest.low < first.low and latest.close > first.low:
        score += 0.2
    if abs(gap_pct) >= 1.0:
        score += 0.1
    return min(score, 1.0)


def _direction_label(value: float):
    if value > 0.12:
        return "up"
    if value < -0.12:
        return "down"
    return "flat"


def _sector_strength(value: float):
    if value >= 0.35:
        return "strong"
    if value <= -0.25:
        return "weak"
    return "neutral"


def _relative_strength_score(stock_return: float, index_return: float, sector_return: float, global_risk_score: float) -> float:
    benchmark = (index_return + sector_return) / 2.0
    raw = 0.5 + ((stock_return - benchmark) / 4.0) - (global_risk_score * 0.08)
    return min(max(raw, 0.0), 1.0)


def _market_alignment(direction: TradeDirection, index_return: float, sector_return: float, global_risk_score: float):
    if global_risk_score >= 0.8:
        return "avoid"
    if direction == "long":
        if index_return >= 0 and sector_return >= 0:
            return "supports_long"
        if index_return < -0.35 and sector_return < -0.35:
            return "avoid"
    if direction == "short":
        if index_return <= 0 and sector_return <= 0:
            return "supports_short"
        if index_return > 0.35 and sector_return > 0.35:
            return "avoid"
    return "mixed"


def _context_quality(levels: VwapOrbCprContextResult, htf: HTFConfirmationResult | None, gap: GapContextResult | None, market: MarketContextResult) -> float:
    parts = [levels.level_respect_score, market.relative_strength_score]
    if htf is not None:
        parts.append(0.7 if htf.confirmed else 0.35)
    if gap is not None:
        parts.append(1.0 - gap.gap_trap_risk)
    return min(max(mean(parts), 0.0), 1.0)


def _final_context_bias(
    direction: TradeDirection,
    levels: VwapOrbCprContextResult,
    htf: HTFConfirmationResult | None,
    gap: GapContextResult | None,
    market: MarketContextResult,
    blockers: list[bool],
):
    if any(blockers):
        return "avoid"
    if direction == "long" and market.market_alignment in {"supports_long", "mixed"} and levels.level_respect_score >= 0.48:
        if htf is None or htf.confirmed:
            return "supports_long"
    if direction == "short" and market.market_alignment in {"supports_short", "mixed"} and levels.level_respect_score >= 0.48:
        if htf is None or htf.confirmed:
            return "supports_short"
    if gap is not None and gap.gap_trap_risk > 0.55:
        return "avoid"
    return "mixed"


def _pct_diff(value: float | None, base: float | None) -> float | None:
    if value is None or base is None or base == 0:
        return None
    return round(((value - base) / base) * 100.0, 4)


def _has_upper_wick_rejection(bar: CandleBar) -> bool:
    body_high = max(bar.open, bar.close)
    body_low = min(bar.open, bar.close)
    candle_range = max(bar.high - bar.low, 0.0001)
    upper = max(bar.high - body_high, 0.0) / candle_range
    lower = max(body_low - bar.low, 0.0) / candle_range
    return upper > lower and upper >= 0.25
