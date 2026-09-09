from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import TYPE_CHECKING

from ..models import (
    CandleAnatomyFeature,
    CandleAnatomyRequest,
    CandleAnatomyResult,
    CandleBar,
    CandleDirection,
)

if TYPE_CHECKING:
    from .decision_spine.snapshot_feature_kernel import SnapshotFeatureKernel


CALCULATION_VERSION = "candle-anatomy.v0.15"


def analyze_candles(
    request: CandleAnatomyRequest,
    *,
    feature_kernel: SnapshotFeatureKernel | None = None,
) -> CandleAnatomyResult:
    """Build deterministic candle anatomy.

    Standalone callers retain the historical behavior. The canonical M3.1 path
    supplies the already-built D2 SnapshotFeatureKernel so ordering, average
    range and volume-window facts are reused instead of recalculated.
    """

    if feature_kernel is None:
        bars = sorted(request.series.bars, key=lambda bar: (bar.timestamp_ns, bar.sequence_number))
        average_ranges = None
        volume_zscores = None
        kernel_feature_hash = None
    else:
        _validate_feature_kernel(request, feature_kernel)
        bars = list(request.series.bars)
        average_ranges = feature_kernel.average_range(request.atr_period).values
        volume_zscores = feature_kernel.volume_stats(request.volume_z_window).zscores
        kernel_feature_hash = feature_kernel.feature_hash

    features: list[CandleAnatomyFeature] = []

    for index, bar in enumerate(bars):
        previous = bars[index - 1] if index > 0 else None
        if average_ranges is None:
            window = bars[max(0, index - request.atr_period + 1) : index + 1]
            average_range = _average_range(window)
        else:
            average_range = average_ranges[index]
        if volume_zscores is None:
            volume_window = bars[max(0, index - request.volume_z_window + 1) : index + 1]
            volume_z = _volume_z(bar, volume_window)
        else:
            volume_z = volume_zscores[index]
        candle_range = max(bar.high - bar.low, 0.0)
        body_size = abs(bar.close - bar.open)
        body_pct = _pct(body_size, candle_range)
        upper_wick = max(0.0, bar.high - max(bar.open, bar.close))
        lower_wick = max(0.0, min(bar.open, bar.close) - bar.low)
        upper_wick_pct = _pct(upper_wick, candle_range)
        lower_wick_pct = _pct(lower_wick, candle_range)
        close_location_value = _ratio(bar.close - bar.low, candle_range)
        body_to_volume_efficiency = _body_to_volume_efficiency(body_pct, volume_z)
        effort_vs_result = _effort_vs_result(body_pct, volume_z)
        wick_cluster_count = _wick_cluster_count(bars, index, request.wick_cluster_lookback)
        is_inside_bar = bool(previous and bar.high <= previous.high and bar.low >= previous.low)
        is_outside_bar = bool(previous and bar.high >= previous.high and bar.low <= previous.low)
        gap_pct = _gap_pct(bar, previous)
        follow_through_count = _follow_through_count(bars, index)
        failed_follow_through = _failed_follow_through(
            bars,
            index,
            request.breakout_reference_high,
            request.breakout_reference_low,
        )
        structure_types = _structure_types(
            bar=bar,
            previous=previous,
            body_pct=body_pct,
            upper_wick_pct=upper_wick_pct,
            lower_wick_pct=lower_wick_pct,
            range_atr=_ratio(candle_range, average_range),
            volume_z=volume_z,
            is_inside_bar=is_inside_bar,
            is_outside_bar=is_outside_bar,
            gap_pct=gap_pct,
            failed_follow_through=failed_follow_through,
        )

        features.append(
            CandleAnatomyFeature(
                symbol=bar.symbol.upper(),
                timeframe=bar.timeframe,
                timestamp_ns=bar.timestamp_ns,
                sequence_number=bar.sequence_number,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                direction=_direction(bar),
                candle_range=round(candle_range, 6),
                body_size=round(body_size, 6),
                body_pct=round(body_pct, 4),
                upper_wick_pct=round(upper_wick_pct, 4),
                lower_wick_pct=round(lower_wick_pct, 4),
                close_location_value=round(close_location_value, 4),
                range_atr=round(_ratio(candle_range, average_range), 4),
                volume_z=round(volume_z, 4) if volume_z is not None else None,
                body_to_volume_efficiency=body_to_volume_efficiency,
                effort_vs_result=effort_vs_result,
                wick_cluster_count=wick_cluster_count,
                is_inside_bar=is_inside_bar,
                is_outside_bar=is_outside_bar,
                gap_pct=round(gap_pct, 4),
                follow_through_count=follow_through_count,
                failed_follow_through=failed_follow_through,
                candle_structure_types=structure_types,
            )
        )

    latest = features[-1] if features else None
    summary = _summary(features)
    if feature_kernel is not None:
        summary["calculation_audit"] = {
            "candle_anatomy_compute_count": 1,
            "feature_kernel_reused": True,
            "feature_kernel_feature_hash": kernel_feature_hash,
        }
    return CandleAnatomyResult(
        calculation_version=CALCULATION_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        total_candles=len(features),
        features=features,
        latest=latest,
        summary=summary,
    )


def _validate_feature_kernel(request: CandleAnatomyRequest, feature_kernel: SnapshotFeatureKernel) -> None:
    if feature_kernel.identity.symbol != request.series.symbol.upper():
        raise ValueError("Candle Anatomy feature-kernel symbol mismatch")
    if feature_kernel.identity.timeframe != str(request.series.timeframe):
        raise ValueError("Candle Anatomy feature-kernel timeframe mismatch")
    if feature_kernel.closed_bar_count != len(request.series.bars):
        raise ValueError("Candle Anatomy feature-kernel bar-count mismatch")
    if tuple(feature_kernel.vectors.timestamps_ns) != tuple(bar.timestamp_ns for bar in request.series.bars):
        raise ValueError("Candle Anatomy feature-kernel timestamp identity mismatch")
    if tuple(feature_kernel.vectors.sequence_numbers) != tuple(bar.sequence_number for bar in request.series.bars):
        raise ValueError("Candle Anatomy feature-kernel sequence identity mismatch")


def _direction(bar: CandleBar) -> CandleDirection:
    body = abs(bar.close - bar.open)
    candle_range = max(bar.high - bar.low, 0.0)
    if candle_range == 0 or body / candle_range <= 0.08:
        return "doji"
    return "bullish" if bar.close > bar.open else "bearish"


def _average_range(bars: list[CandleBar]) -> float:
    ranges = [max(bar.high - bar.low, 0.0) for bar in bars]
    return max(mean(ranges), 1e-9) if ranges else 1e-9


def _pct(numerator: float, denominator: float) -> float:
    return _ratio(numerator, denominator) * 100.0


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, numerator / denominator)


def _volume_z(bar: CandleBar, window: list[CandleBar]) -> float | None:
    if bar.volume is None or any(item.volume is None for item in window):
        return None
    volumes = [float(item.volume or 0.0) for item in window]
    if len(volumes) < 2:
        return 0.0
    deviation = pstdev(volumes)
    if deviation == 0:
        return 0.0
    return (float(bar.volume or 0.0) - mean(volumes)) / deviation


def _body_to_volume_efficiency(body_pct: float, volume_z: float | None) -> float | None:
    if volume_z is None:
        return None
    return round(body_pct / (abs(volume_z) + 1.0), 4)


def _effort_vs_result(body_pct: float, volume_z: float | None) -> float | None:
    if volume_z is None:
        return None
    return round(volume_z / max(body_pct, 1.0), 4)


def _wick_cluster_count(bars: list[CandleBar], index: int, lookback: int) -> int:
    start = max(0, index - lookback + 1)
    count = 0
    for bar in bars[start : index + 1]:
        candle_range = max(bar.high - bar.low, 0.0)
        if candle_range <= 0:
            continue
        upper = max(0.0, bar.high - max(bar.open, bar.close))
        lower = max(0.0, min(bar.open, bar.close) - bar.low)
        if upper / candle_range >= 0.35 or lower / candle_range >= 0.35:
            count += 1
    return count


def _gap_pct(bar: CandleBar, previous: CandleBar | None) -> float:
    if previous is None or previous.close <= 0:
        return 0.0
    return ((bar.open - previous.close) / previous.close) * 100.0


def _follow_through_count(bars: list[CandleBar], index: int) -> int:
    if index == 0:
        return 0
    current = bars[index]
    direction = _direction(current)
    if direction == "doji":
        return 0
    count = 0
    for prior in reversed(bars[:index]):
        prior_direction = _direction(prior)
        if prior_direction == direction and (
            (direction == "bullish" and prior.close <= current.close)
            or (direction == "bearish" and prior.close >= current.close)
        ):
            count += 1
        else:
            break
    return count


def _failed_follow_through(
    bars: list[CandleBar],
    index: int,
    breakout_reference_high: float | None,
    breakout_reference_low: float | None,
) -> bool:
    if index == 0:
        return False
    current = bars[index]
    previous = bars[index - 1]
    failed_long_breakout = bool(
        breakout_reference_high is not None
        and previous.close > breakout_reference_high
        and current.close < breakout_reference_high
    )
    failed_short_breakdown = bool(
        breakout_reference_low is not None
        and previous.close < breakout_reference_low
        and current.close > breakout_reference_low
    )
    return failed_long_breakout or failed_short_breakdown


def _structure_types(
    *,
    bar: CandleBar,
    previous: CandleBar | None,
    body_pct: float,
    upper_wick_pct: float,
    lower_wick_pct: float,
    range_atr: float,
    volume_z: float | None,
    is_inside_bar: bool,
    is_outside_bar: bool,
    gap_pct: float,
    failed_follow_through: bool,
) -> list[str]:
    types: list[str] = []
    if body_pct >= 65 and range_atr >= 1.1:
        types.append("trend_candle")
    if upper_wick_pct >= 45 or lower_wick_pct >= 45:
        types.append("rejection_candle")
    if previous and ((bar.close > previous.high and bar.open < previous.low) or (bar.close < previous.low and bar.open > previous.high)):
        types.append("engulfing_behavior")
    if is_inside_bar:
        types.append("inside_bar")
    if is_outside_bar:
        types.append("outside_bar")
    if body_pct <= 25 and range_atr <= 0.75:
        types.append("compression_candle")
    if body_pct >= 55 and range_atr >= 1.25:
        types.append("expansion_candle")
    if abs(gap_pct) >= 0.4:
        types.append("gap_candle")
    if failed_follow_through:
        types.append("fake_breakout_candle")
    if volume_z is not None and volume_z >= 1.0 and body_pct <= 30:
        types.append("absorption_looking_candle")
    if volume_z is not None and volume_z >= 1.0 and upper_wick_pct >= 35 and bar.close <= bar.open:
        types.append("distribution_looking_candle")
    if not types:
        types.append("neutral_candle")
    return types


def _summary(features: list[CandleAnatomyFeature]) -> dict[str, object]:
    type_counts: dict[str, int] = {}
    for feature in features:
        for structure_type in feature.candle_structure_types:
            type_counts[structure_type] = type_counts.get(structure_type, 0) + 1
    latest = features[-1] if features else None
    avg_body_pct = round(mean([feature.body_pct for feature in features]), 4) if features else 0.0
    avg_range_atr = round(mean([feature.range_atr for feature in features]), 4) if features else 0.0
    return {
        "type_counts": type_counts,
        "avg_body_pct": avg_body_pct,
        "avg_range_atr": avg_range_atr,
        "latest_structure_types": latest.candle_structure_types if latest else [],
    }
