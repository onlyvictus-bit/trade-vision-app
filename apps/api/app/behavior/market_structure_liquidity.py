from __future__ import annotations

import math
from statistics import mean

from ..models import (
    CandleBar,
    MarketStructureLiquidityGate,
    MarketStructureLiquidityReport,
    MarketStructureLiquidityRequest,
    MarketStructureZone,
)


MARKET_STRUCTURE_LIQUIDITY_VERSION = "market-structure-liquidity.v1.72"
EPSILON = 1e-9


def build_market_structure_liquidity_report(request: MarketStructureLiquidityRequest) -> MarketStructureLiquidityReport:
    bars = sorted(request.series.bars, key=lambda bar: (bar.timestamp_ns, bar.sequence_number))
    latest = bars[-1] if bars else None
    atr = _atr(bars, request.atr_period)
    safe_atr = max(atr, _latest_close(bars) * 0.001, EPSILON)
    profile = _volume_profile(bars, request.bin_count, request.value_area_pct)
    tpo = _tpo_profile(bars, request.bin_count, request.value_area_pct)
    vsa = _vsa_state(bars)
    liquidity = _liquidity_geometry(bars, safe_atr, request.equal_level_tolerance_atr)
    order_block = _order_block_zone(bars, safe_atr)
    fvg = _fvg_zone(bars)
    bos_choch = _bos_choch_state(bars, safe_atr)
    wyckoff = _wyckoff_phase(liquidity["sweep_direction"], latest)
    trap_score = _trap_score(vsa, liquidity, latest)
    stop_hunt_score = _stop_hunt_score(liquidity, latest)
    confidence_cap = _confidence_cap(len(bars), request.minimum_bars, vsa, trap_score, stop_hunt_score)
    gates = _gates(
        bars=bars,
        request=request,
        profile=profile,
        tpo=tpo,
        vsa=vsa,
        liquidity=liquidity,
        trap_score=trap_score,
        stop_hunt_score=stop_hunt_score,
    )

    return MarketStructureLiquidityReport(
        structure_version=MARKET_STRUCTURE_LIQUIDITY_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        closed_candle_only=True,
        source_bar_count=len(bars),
        latest_timestamp_ns=latest.timestamp_ns if latest else None,
        latest_sequence_number=latest.sequence_number if latest else None,
        bin_count=request.bin_count,
        auction_state=_auction_state(profile, tpo, vsa),
        profile_shape=profile["shape"],
        poc=profile["poc"],
        vah=profile["vah"],
        val=profile["val"],
        poc_distance_atr=round(_safe_ratio(abs(_latest_close(bars) - (profile["poc"] or _latest_close(bars))), safe_atr), 6),
        value_area_position=_value_area_position(_latest_close(bars), profile["vah"], profile["val"]),
        hvn_levels=profile["hvn"],
        lvn_levels=profile["lvn"],
        hvn_lvn_context=_hvn_lvn_context(_latest_close(bars), profile["hvn"], profile["lvn"], safe_atr),
        tpo_poc=tpo["poc"],
        tpo_value_area_high=tpo["vah"],
        tpo_value_area_low=tpo["val"],
        tpo_single_print_count=tpo["single_print_count"],
        tpo_acceptance_state=_tpo_acceptance_state(tpo, _latest_close(bars)),
        vsa_effort_result_state=vsa["state"],
        vsa_downgrade_active=vsa["downgrade"],
        volume_percentile=round(vsa["volume_percentile"], 6),
        spread_percentile=round(vsa["spread_percentile"], 6),
        close_location_value=round(vsa["close_location_value"], 6),
        liquidity_pool_detected=liquidity["pool_detected"],
        liquidity_pool_side=liquidity["pool_side"],
        sweep_direction=liquidity["sweep_direction"],
        order_block_zone=order_block,
        fvg_zone=fvg,
        bos_choch_state=bos_choch,
        wyckoff_phase=wyckoff,
        trap_score=round(trap_score, 6),
        stop_hunt_score=round(stop_hunt_score, 6),
        confidence_cap=confidence_cap,
        no_future_leakage=True,
        used_for_probability=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        reasons=_reasons(profile, tpo, vsa, liquidity, wyckoff, trap_score, confidence_cap),
        failure_questions=_failure_questions(len(bars), profile, tpo, vsa, liquidity),
        gates=gates,
    )


def _volume_profile(bars: list[CandleBar], bin_count: int, value_area_pct: float) -> dict:
    if not bars:
        return _empty_profile()
    bins = _price_bins(bars, bin_count)
    volumes = [0.0 for _ in bins]
    for bar in bars:
        index = _bin_index(_typical_price(bar), bins)
        volumes[index] += float(bar.volume or 0.0)
    if sum(volumes) <= EPSILON:
        return _empty_profile(bins)
    poc_index = max(range(len(volumes)), key=lambda idx: volumes[idx])
    area_indices = _value_area_indices(volumes, poc_index, value_area_pct)
    hvn = _top_centers(bins, volumes, 3)
    lvn = _low_centers(bins, volumes, 3)
    return {
        "poc": round(bins[poc_index], 6),
        "vah": round(max(bins[index] for index in area_indices), 6),
        "val": round(min(bins[index] for index in area_indices), 6),
        "hvn": hvn,
        "lvn": lvn,
        "shape": _profile_shape(bars, volumes, poc_index),
        "total_volume": sum(volumes),
        "value_area_volume_ratio": sum(volumes[index] for index in area_indices) / max(sum(volumes), EPSILON),
        "bins": bins,
        "weights": volumes,
    }


def _tpo_profile(bars: list[CandleBar], bin_count: int, value_area_pct: float) -> dict:
    if not bars:
        return _empty_tpo()
    bins = _price_bins(bars, bin_count)
    counts = [0 for _ in bins]
    for bar in bars:
        low_index = _bin_index(bar.low, bins)
        high_index = _bin_index(bar.high, bins)
        for index in range(min(low_index, high_index), max(low_index, high_index) + 1):
            counts[index] += 1
    if sum(counts) == 0:
        return _empty_tpo(bins)
    poc_index = max(range(len(counts)), key=lambda idx: counts[idx])
    area_indices = _value_area_indices([float(item) for item in counts], poc_index, value_area_pct)
    return {
        "poc": round(bins[poc_index], 6),
        "vah": round(max(bins[index] for index in area_indices), 6),
        "val": round(min(bins[index] for index in area_indices), 6),
        "single_print_count": sum(1 for item in counts if item == 1),
        "bins": bins,
        "counts": counts,
    }


def _vsa_state(bars: list[CandleBar]) -> dict:
    if not bars:
        return _empty_vsa()
    latest = bars[-1]
    spreads = [max(bar.high - bar.low, 0.0) for bar in bars]
    volumes = [float(bar.volume or 0.0) for bar in bars]
    latest_spread = spreads[-1]
    latest_volume = volumes[-1]
    spread_percentile = _percentile_rank(latest_spread, spreads[:-1])
    volume_percentile = _percentile_rank(latest_volume, volumes[:-1])
    clv = _close_location_value(latest)
    no_demand = _no_demand(bars)
    no_supply = _no_supply(bars)
    if volume_percentile >= 80.0 and spread_percentile <= 35.0:
        state = "effort_without_result_absorption"
        downgrade = True
    elif volume_percentile <= 35.0 and spread_percentile >= 70.0:
        state = "low_opposition_easy_markup_or_markdown"
        downgrade = False
    elif volume_percentile >= 70.0 and spread_percentile >= 65.0 and clv >= 0.70:
        state = "true_demand_wide_spread_close_near_high"
        downgrade = False
    elif no_demand:
        state = "no_demand_up_candles"
        downgrade = True
    elif no_supply:
        state = "no_supply_down_candles"
        downgrade = False
    else:
        state = "neutral_effort_result"
        downgrade = False
    return {
        "state": state,
        "downgrade": downgrade,
        "volume_percentile": volume_percentile,
        "spread_percentile": spread_percentile,
        "close_location_value": clv,
    }


def _liquidity_geometry(bars: list[CandleBar], atr: float, tolerance_atr: float) -> dict:
    if len(bars) < 5:
        return {"pool_detected": False, "pool_side": "none", "sweep_direction": "none", "equal_high": None, "equal_low": None}
    latest = bars[-1]
    lookback = bars[-21:-1] if len(bars) > 21 else bars[:-1]
    tolerance = max(atr * tolerance_atr, EPSILON)
    equal_high = _equal_level([bar.high for bar in lookback], tolerance, mode="high")
    equal_low = _equal_level([bar.low for bar in lookback], tolerance, mode="low")
    up_sweep = equal_high is not None and latest.high > equal_high + tolerance and latest.close < equal_high
    down_sweep = equal_low is not None and latest.low < equal_low - tolerance and latest.close > equal_low
    if equal_high is not None and equal_low is not None:
        side = "both"
    elif equal_high is not None:
        side = "above_equal_highs"
    elif equal_low is not None:
        side = "below_equal_lows"
    else:
        side = "none"
    return {
        "pool_detected": side != "none",
        "pool_side": side,
        "sweep_direction": "up_sweep" if up_sweep else ("down_sweep" if down_sweep else "none"),
        "equal_high": equal_high,
        "equal_low": equal_low,
    }


def _order_block_zone(bars: list[CandleBar], atr: float) -> MarketStructureZone | None:
    if len(bars) < 4:
        return None
    recent = bars[-12:]
    for index in range(len(recent) - 2, 0, -1):
        bar = recent[index]
        next_bar = recent[index + 1]
        impulse = abs(next_bar.close - next_bar.open)
        if impulse < max(atr * 0.60, EPSILON):
            continue
        if bar.close < bar.open and next_bar.close > next_bar.open:
            return MarketStructureZone(
                zone_type="order_block",
                direction="bullish",
                low=round(bar.low, 6),
                high=round(bar.high, 6),
                source_sequence_number=bar.sequence_number,
                confirmed_after_timestamp_ns=next_bar.timestamp_ns,
                point_in_time_safe=True,
                reason="Last down candle before bullish impulse.",
            )
        if bar.close > bar.open and next_bar.close < next_bar.open:
            return MarketStructureZone(
                zone_type="order_block",
                direction="bearish",
                low=round(bar.low, 6),
                high=round(bar.high, 6),
                source_sequence_number=bar.sequence_number,
                confirmed_after_timestamp_ns=next_bar.timestamp_ns,
                point_in_time_safe=True,
                reason="Last up candle before bearish impulse.",
            )
    return None


def _fvg_zone(bars: list[CandleBar]) -> MarketStructureZone | None:
    if len(bars) < 3:
        return None
    recent = bars[-20:]
    for index in range(len(recent) - 3, -1, -1):
        first, middle, third = recent[index], recent[index + 1], recent[index + 2]
        if first.high < third.low:
            return MarketStructureZone(
                zone_type="fair_value_gap",
                direction="bullish",
                low=round(first.high, 6),
                high=round(third.low, 6),
                source_sequence_number=middle.sequence_number,
                confirmed_after_timestamp_ns=third.timestamp_ns,
                point_in_time_safe=True,
                reason="Three-candle bullish imbalance: first high is below third low.",
            )
        if first.low > third.high:
            return MarketStructureZone(
                zone_type="fair_value_gap",
                direction="bearish",
                low=round(third.high, 6),
                high=round(first.low, 6),
                source_sequence_number=middle.sequence_number,
                confirmed_after_timestamp_ns=third.timestamp_ns,
                point_in_time_safe=True,
                reason="Three-candle bearish imbalance: first low is above third high.",
            )
    return None


def _bos_choch_state(bars: list[CandleBar], atr: float) -> str:
    if len(bars) < 8:
        return "insufficient_structure"
    previous = bars[-8:-1]
    latest = bars[-1]
    prior_high = max(bar.high for bar in previous)
    prior_low = min(bar.low for bar in previous)
    slope = bars[-2].close - bars[-6].close if len(bars) >= 6 else 0.0
    if latest.close > prior_high and slope >= -atr * 0.20:
        return "bullish_bos_continuation"
    if latest.close < prior_low and slope <= atr * 0.20:
        return "bearish_bos_continuation"
    if latest.close > prior_high and slope < -atr * 0.20:
        return "bullish_choch_reversal"
    if latest.close < prior_low and slope > atr * 0.20:
        return "bearish_choch_reversal"
    return "no_structure_break"


def _wyckoff_phase(sweep_direction: str, latest: CandleBar | None) -> str:
    if latest is None:
        return "none"
    clv = _close_location_value(latest)
    if sweep_direction == "down_sweep" and clv >= 0.60:
        return "spring"
    if sweep_direction == "up_sweep" and clv <= 0.40:
        return "utad"
    if sweep_direction == "none" and 0.42 <= clv <= 0.62:
        return "lps"
    return "none"


def _trap_score(vsa: dict, liquidity: dict, latest: CandleBar | None) -> float:
    score = 0.0
    if vsa["downgrade"]:
        score += 0.32
    if liquidity["sweep_direction"] != "none":
        score += 0.34
    if latest is not None:
        rejection_ratio = _wick_rejection_ratio(latest)
        if rejection_ratio >= 0.60:
            score += 0.26
        if vsa["volume_percentile"] < 50.0 and _body_pct(latest) >= 0.55:
            score += 0.10
    return _clamp(score, 0.0, 1.0)


def _stop_hunt_score(liquidity: dict, latest: CandleBar | None) -> float:
    if latest is None or liquidity["sweep_direction"] == "none":
        return 0.0
    clv = _close_location_value(latest)
    wick = _wick_rejection_ratio(latest)
    return _clamp(0.40 + wick * 0.35 + (0.20 if clv <= 0.35 or clv >= 0.65 else 0.0), 0.0, 1.0)


def _gates(
    *,
    bars: list[CandleBar],
    request: MarketStructureLiquidityRequest,
    profile: dict,
    tpo: dict,
    vsa: dict,
    liquidity: dict,
    trap_score: float,
    stop_hunt_score: float,
) -> list[MarketStructureLiquidityGate]:
    return [
        _gate("AUC-001", "Volume POC calculated", profile["poc"] is not None, "info", f"poc={profile['poc']}"),
        _gate("AUC-002", "Value area covers configured volume", profile.get("value_area_volume_ratio", 0.0) >= request.value_area_pct, "info", f"ratio={profile.get('value_area_volume_ratio', 0.0):.2f}"),
        _gate("AUC-006", "TPO profile calculated", tpo["poc"] is not None, "info", f"single_prints={tpo['single_print_count']}"),
        _gate("VSA-004", "VSA downgrade visible", not vsa["downgrade"], "warn", vsa["state"], "Do not trust raw breakout strength while effort/result downgrades."),
        _gate("SMC-001", "Liquidity pool scan completed", True, "info", f"pool={liquidity['pool_side']}"),
        _gate("TRAP-003", "Trap score below hard warning", trap_score < 0.70 and stop_hunt_score < 0.70, "warn", f"trap={trap_score:.2f}, stop_hunt={stop_hunt_score:.2f}", "Keep decision capped at WAIT/WATCH until sweep is resolved."),
        _gate("V172-SAFE-001", "Research only", True, "info", "No probability authority, order routing, or live trading enabled."),
        _gate("V172-SAFE-002", "Minimum closed candles", len(bars) >= request.minimum_bars, "warn", f"bars={len(bars)}, minimum={request.minimum_bars}", "Collect more closed candles before trusting structure context."),
    ]


def _gate(gate_id: str, name: str, passed: bool, severity: str, evidence: str, remediation: str | None = None) -> MarketStructureLiquidityGate:
    return MarketStructureLiquidityGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity=severity,  # type: ignore[arg-type]
        evidence=evidence,
        remediation=remediation,
    )


def _price_bins(bars: list[CandleBar], bin_count: int) -> list[float]:
    low = min(bar.low for bar in bars)
    high = max(bar.high for bar in bars)
    if high - low <= EPSILON:
        return [round(low, 6) for _ in range(bin_count)]
    step = (high - low) / max(bin_count - 1, 1)
    return [low + step * index for index in range(bin_count)]


def _bin_index(price: float, bins: list[float]) -> int:
    if not bins:
        return 0
    return min(range(len(bins)), key=lambda index: abs(bins[index] - price))


def _typical_price(bar: CandleBar) -> float:
    return (bar.high + bar.low + bar.close) / 3.0


def _value_area_indices(weights: list[float], poc_index: int, target_ratio: float) -> set[int]:
    total = sum(weights)
    if total <= EPSILON:
        return {poc_index}
    selected = {poc_index}
    selected_weight = weights[poc_index]
    left = poc_index - 1
    right = poc_index + 1
    while selected_weight / total < target_ratio and (left >= 0 or right < len(weights)):
        left_weight = weights[left] if left >= 0 else -1.0
        right_weight = weights[right] if right < len(weights) else -1.0
        if right_weight >= left_weight:
            selected.add(right)
            selected_weight += max(right_weight, 0.0)
            right += 1
        else:
            selected.add(left)
            selected_weight += max(left_weight, 0.0)
            left -= 1
    return selected


def _top_centers(bins: list[float], weights: list[float], limit: int) -> list[float]:
    ranked = sorted(range(len(weights)), key=lambda index: (-weights[index], bins[index]))
    return [round(bins[index], 6) for index in ranked[:limit] if weights[index] > EPSILON]


def _low_centers(bins: list[float], weights: list[float], limit: int) -> list[float]:
    nonzero = [index for index, weight in enumerate(weights) if weight > EPSILON]
    ranked = sorted(nonzero, key=lambda index: (weights[index], bins[index]))
    return [round(bins[index], 6) for index in ranked[:limit]]


def _profile_shape(bars: list[CandleBar], weights: list[float], poc_index: int) -> str:
    nonzero = [weight for weight in weights if weight > EPSILON]
    if len(nonzero) <= max(2, len(weights) // 8):
        return "thin"
    poc_position = poc_index / max(len(weights) - 1, 1)
    latest = bars[-1]
    first = bars[0]
    direction = latest.close - first.open
    if 0.35 <= poc_position <= 0.65:
        return "D"
    if direction > 0 and poc_position >= 0.55:
        return "P"
    if direction < 0 and poc_position <= 0.45:
        return "b"
    return "thin"


def _empty_profile(bins: list[float] | None = None) -> dict:
    return {"poc": None, "vah": None, "val": None, "hvn": [], "lvn": [], "shape": "unknown", "total_volume": 0.0, "value_area_volume_ratio": 0.0, "bins": bins or [], "weights": []}


def _empty_tpo(bins: list[float] | None = None) -> dict:
    return {"poc": None, "vah": None, "val": None, "single_print_count": 0, "bins": bins or [], "counts": []}


def _empty_vsa() -> dict:
    return {"state": "unavailable", "downgrade": True, "volume_percentile": 0.0, "spread_percentile": 0.0, "close_location_value": 0.5}


def _value_area_position(close: float, vah: float | None, val: float | None) -> str:
    if vah is None or val is None:
        return "unknown"
    if close > vah:
        return "above_value"
    if close < val:
        return "below_value"
    return "inside_value"


def _hvn_lvn_context(close: float, hvn: list[float], lvn: list[float], atr: float) -> str:
    nearest_hvn = min([abs(close - level) / max(atr, EPSILON) for level in hvn], default=999.0)
    nearest_lvn = min([abs(close - level) / max(atr, EPSILON) for level in lvn], default=999.0)
    if nearest_hvn <= 0.50:
        return "near_hvn_acceptance_magnet"
    if nearest_lvn <= 0.50:
        return "near_lvn_rejection_or_vacuum"
    return "between_profile_nodes"


def _tpo_acceptance_state(tpo: dict, close: float) -> str:
    vah = tpo["vah"]
    val = tpo["val"]
    if vah is None or val is None:
        return "unknown"
    if close > vah:
        return "above_time_value_acceptance"
    if close < val:
        return "below_time_value_acceptance"
    if tpo["single_print_count"] >= max(3, len(tpo["counts"]) // 5):
        return "single_print_fast_movement_present"
    return "inside_time_value_acceptance"


def _auction_state(profile: dict, tpo: dict, vsa: dict) -> str:
    if profile["shape"] == "D" and tpo["single_print_count"] <= 2:
        return "balanced_auction"
    if profile["shape"] in {"P", "b"} or tpo["single_print_count"] >= 3:
        return "initiative_or_trend_auction"
    if vsa["downgrade"]:
        return "acceptance_rejection_conflict"
    return "thin_or_uncertain_auction"


def _confidence_cap(bar_count: int, minimum_bars: int, vsa: dict, trap_score: float, stop_hunt_score: float) -> str:
    if bar_count < minimum_bars or trap_score >= 0.70 or stop_hunt_score >= 0.70:
        return "WAIT"
    if vsa["downgrade"] or trap_score >= 0.45:
        return "WATCH"
    return "RESEARCH_CONTEXT_ONLY"


def _reasons(profile: dict, tpo: dict, vsa: dict, liquidity: dict, wyckoff: str, trap_score: float, confidence_cap: str) -> list[str]:
    return [
        f"Volume Profile POC={profile['poc']} VAH={profile['vah']} VAL={profile['val']} shape={profile['shape']}.",
        f"TPO POC={tpo['poc']} with {tpo['single_print_count']} single-print bins.",
        f"VSA state is {vsa['state']}; downgrade={vsa['downgrade']}.",
        f"Liquidity pool side={liquidity['pool_side']}; sweep={liquidity['sweep_direction']}; Wyckoff={wyckoff}.",
        f"Trap score={trap_score:.2f}; confidence cap={confidence_cap}. This layer is context-only.",
    ]


def _failure_questions(bar_count: int, profile: dict, tpo: dict, vsa: dict, liquidity: dict) -> list[str]:
    questions = [
        "Is the profile computed from enough closed bars for this session?",
        "Is volume reliable enough for VP/VSA, or should it be masked?",
        "Did a sweep close back inside the prior liquidity pool?",
        "Are SMC zones confirmed by closed candles rather than developing pivots?",
    ]
    if bar_count < 30:
        questions.append("Low bar count: avoid treating the structure layer as stable.")
    if profile["poc"] is None:
        questions.append("Volume Profile unavailable: missing or zero volume blocks auction confidence.")
    if tpo["poc"] is None:
        questions.append("TPO unavailable: cannot distinguish time acceptance from fast movement.")
    if vsa["downgrade"]:
        questions.append("Effort/result conflict is active; raw breakout strength may be false.")
    if liquidity["sweep_direction"] != "none":
        questions.append("Sweep detected: wait for reclaim/retest confirmation before trusting continuation.")
    return questions


def _atr(bars: list[CandleBar], period: int) -> float:
    if not bars:
        return 0.0
    ranges: list[float] = []
    previous_close: float | None = None
    for bar in bars[-period:]:
        if previous_close is None:
            ranges.append(max(bar.high - bar.low, 0.0))
        else:
            ranges.append(max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close), 0.0))
        previous_close = bar.close
    return mean(ranges) if ranges else 0.0


def _latest_close(bars: list[CandleBar]) -> float:
    return bars[-1].close if bars else 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= EPSILON:
        return 0.0
    return numerator / denominator


def _percentile_rank(value: float, history: list[float]) -> float:
    clean = [item for item in history if not math.isnan(item) and not math.isinf(item)]
    if not clean:
        return 50.0
    below = sum(1 for item in clean if item <= value)
    return _clamp((below / len(clean)) * 100.0, 0.0, 100.0)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return minimum
    return max(minimum, min(maximum, value))


def _close_location_value(bar: CandleBar) -> float:
    return _clamp(_safe_ratio(bar.close - bar.low, bar.high - bar.low), 0.0, 1.0)


def _body_pct(bar: CandleBar) -> float:
    return _clamp(_safe_ratio(abs(bar.close - bar.open), bar.high - bar.low), 0.0, 1.0)


def _wick_rejection_ratio(bar: CandleBar) -> float:
    candle_range = max(bar.high - bar.low, EPSILON)
    upper = bar.high - max(bar.open, bar.close)
    lower = min(bar.open, bar.close) - bar.low
    return _clamp(max(upper, lower) / candle_range, 0.0, 1.0)


def _no_demand(bars: list[CandleBar]) -> bool:
    recent = bars[-3:]
    if len(recent) < 3:
        return False
    return all(bar.close >= bar.open for bar in recent) and all(float(recent[index].volume or 0.0) < float(recent[index - 1].volume or 0.0) for index in range(1, 3))


def _no_supply(bars: list[CandleBar]) -> bool:
    recent = bars[-3:]
    if len(recent) < 3:
        return False
    return all(bar.close <= bar.open for bar in recent) and all(float(recent[index].volume or 0.0) < float(recent[index - 1].volume or 0.0) for index in range(1, 3))


def _equal_level(values: list[float], tolerance: float, mode: str = "largest") -> float | None:
    if len(values) < 3:
        return None
    sorted_values = sorted(values)
    clusters: list[list[float]] = []
    for value in sorted_values:
        cluster = [candidate for candidate in sorted_values if abs(candidate - value) <= tolerance]
        if len(cluster) >= 2:
            center = mean(cluster)
            if not any(abs(mean(existing) - center) <= tolerance for existing in clusters):
                clusters.append(cluster)
    if not clusters:
        return None
    if mode == "high":
        selected = max(clusters, key=lambda cluster: mean(cluster))
    elif mode == "low":
        selected = min(clusters, key=lambda cluster: mean(cluster))
    else:
        selected = max(clusters, key=lambda cluster: (len(cluster), -abs(mean(cluster))))
    if len(selected) >= 2:
        return round(mean(selected), 6)
    return None
