from __future__ import annotations

"""M3.1.1-C shadow Canonical Chart State / Reasoning v2.

Separates signed trend direction from directionless trend quality. This module
consumes already-calculated MarketPrimitiveKernelV2 facts and the exact matching
SnapshotFeatureKernel for observed close/volume identity only. It has zero
execution/final-band authority and produces no calibrated probabilities.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from statistics import mean, pstdev

from .market_primitive_kernel_v2 import MarketPrimitiveKernelV2
from .snapshot_feature_kernel import SnapshotFeatureKernel


CANONICAL_CHART_STATE_V2_VERSION = "canonical-chart-state.v2"
DEFAULT_ATR_PERIOD = 14
DEFAULT_VOL_WINDOW = 20
DEFAULT_SHORT_SLOPE_WINDOW = 5
DEFAULT_MEDIUM_SLOPE_WINDOW = 9
DEFAULT_LONG_SLOPE_WINDOW = 20
DEFAULT_EFFICIENCY_WINDOW = 20
NSE_REGULAR_SESSION_MINUTES = 375.0
MIN_PERCENTILE_HISTORY = 5
MIN_HURST_RETURNS = 32


class CanonicalChartStateV2Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ChartStateIdentity:
    symbol: str
    timeframe: str
    decision_time_ns: int
    snapshot_hash: str
    snapshot_id: str
    source_feature_kernel_hash: str
    source_primitive_hash: str


@dataclass(frozen=True, slots=True)
class MetricAvailability:
    value: float | None
    availability: str


@dataclass(frozen=True, slots=True)
class CanonicalChartStateV2:
    calculation_version: str
    identity: ChartStateIdentity
    trend_direction: str
    trend_direction_availability: str
    trend_strength: float | None
    trend_persistence: float | None
    trend_efficiency: float | None
    trend_acceleration: float | None
    trend_change_risk_score: float | None
    signed_trend_evidence: float | None
    volatility_state: str
    realized_vol_per_bar: float | None
    realized_vol_per_session: float | None
    annualized_realized_vol: float | None
    realized_vol_percentile: float | None
    realized_vol_percentile_availability: str
    chop_balance_state: str
    chop_balance_score: float | None
    compression_expansion_state: str
    mean_reversion_pressure_score: float | None
    mean_reversion_direction: str
    momentum_cleanliness_score: float | None
    hurst_diagnostic: float | None
    hurst_availability: str
    volume_state: str
    session_normalized_volume_confirmation: str
    source_snapshot_hash: str
    source_feature_kernel_hash: str
    source_primitive_hash: str
    chart_state_hash: str
    legacy_d6_compatibility_debt: bool = True
    hurst_is_secondary_only: bool = True
    scores_are_uncalibrated: bool = True
    epistemic_level: str = "INFERRED"
    research_only: bool = True
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    human_approval_required: bool = True

    def receipt_summary(self) -> dict[str, object]:
        return {
            "calculation_version": self.calculation_version,
            "identity": {
                "symbol": self.identity.symbol,
                "timeframe": self.identity.timeframe,
                "decision_time_ns": self.identity.decision_time_ns,
                "snapshot_hash": self.identity.snapshot_hash,
            },
            "trend": {
                "direction": self.trend_direction,
                "direction_availability": self.trend_direction_availability,
                "strength": self.trend_strength,
                "persistence": self.trend_persistence,
                "efficiency": self.trend_efficiency,
                "acceleration": self.trend_acceleration,
                "change_risk_score_uncalibrated": self.trend_change_risk_score,
                "signed_evidence_uncalibrated": self.signed_trend_evidence,
            },
            "state": {
                "volatility": self.volatility_state,
                "realized_vol_per_bar": self.realized_vol_per_bar,
                "realized_vol_per_session": self.realized_vol_per_session,
                "annualized_realized_vol": self.annualized_realized_vol,
                "realized_vol_percentile": self.realized_vol_percentile,
                "realized_vol_percentile_availability": self.realized_vol_percentile_availability,
                "chop_balance": self.chop_balance_state,
                "compression_expansion": self.compression_expansion_state,
                "mean_reversion_pressure_score_uncalibrated": self.mean_reversion_pressure_score,
                "mean_reversion_direction": self.mean_reversion_direction,
                "momentum_cleanliness_score_uncalibrated": self.momentum_cleanliness_score,
            },
            "diagnostics": {
                "hurst": self.hurst_diagnostic,
                "hurst_availability": self.hurst_availability,
                "hurst_secondary_only": True,
                "volume_state": self.volume_state,
                "session_normalized_volume_confirmation": self.session_normalized_volume_confirmation,
                "legacy_d6_compatibility_debt": True,
            },
            "quality": {
                "missing_volume_neutralized": False,
                "fake_neutral_percentiles_used": False,
                "fake_neutral_hurst_used": False,
                "annualized_volatility_claimed": False,
                "scores_are_uncalibrated": True,
            },
            "provenance": {
                "source_snapshot_hash": self.source_snapshot_hash,
                "source_feature_kernel_hash": self.source_feature_kernel_hash,
                "source_primitive_hash": self.source_primitive_hash,
                "chart_state_hash": self.chart_state_hash,
            },
            "authority": {
                "research_only": True,
                "used_for_probability": False,
                "may_set_final_band": False,
                "may_execute": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
                "human_approval_required": True,
            },
        }


def build_canonical_chart_state_v2(
    primitive: MarketPrimitiveKernelV2,
    observed: SnapshotFeatureKernel,
    *,
    atr_period: int = DEFAULT_ATR_PERIOD,
    vol_window: int = DEFAULT_VOL_WINDOW,
) -> CanonicalChartStateV2:
    _validate_sources(primitive, observed, atr_period, vol_window)

    short_slope = primitive.log_slope(DEFAULT_SHORT_SLOPE_WINDOW).latest
    medium_slope = primitive.log_slope(DEFAULT_MEDIUM_SLOPE_WINDOW).latest
    long_slope = primitive.log_slope(DEFAULT_LONG_SLOPE_WINDOW).latest
    signed_eff = primitive.signed_path_efficiency(DEFAULT_EFFICIENCY_WINDOW).latest
    atr = primitive.wilder_atr(atr_period).latest
    latest_close = float(observed.vectors.closes[-1])

    direction, direction_availability = _trend_direction(long_slope, medium_slope, signed_eff)
    strength = _trend_strength(long_slope, latest_close, atr)
    efficiency = None if signed_eff is None else _clamp(abs(signed_eff))
    persistence = _trend_persistence(
        primitive.signed_path_efficiency(DEFAULT_EFFICIENCY_WINDOW).values,
        direction,
        efficiency,
    )
    acceleration = None if short_slope is None or long_slope is None else short_slope - long_slope

    ema9 = primitive.ema(9)
    ema20 = primitive.ema(20)
    ema50 = primitive.ema(50)
    ema_ready = ema9.latest_ready and ema20.latest_ready and ema50.latest_ready and atr is not None and atr > 0.0
    ema_tangle_score = None
    ema_alignment_conflict = False
    ema20_distance_atr = None
    if ema_ready:
        ema9_20 = abs(ema9.latest - ema20.latest) / atr
        ema20_50 = abs(ema20.latest - ema50.latest) / atr
        ema_tangle_score = 1.0 - _clamp(mean([ema9_20 / 0.35, ema20_50 / 0.60]))
        ema20_distance_atr = (latest_close - ema20.latest) / atr
        if direction == "bullish":
            ema_alignment_conflict = not (ema9.latest >= ema20.latest >= ema50.latest)
        elif direction == "bearish":
            ema_alignment_conflict = not (ema9.latest <= ema20.latest <= ema50.latest)

    overlap_score = _recent_mean(primitive.vectors.overlap_to_smaller_range, 9)
    latest_bar_eff = primitive.vectors.signed_bar_efficiency[-1]
    change_risk = _change_risk(
        direction=direction,
        short_slope=short_slope,
        long_slope=long_slope,
        latest_bar_eff=latest_bar_eff,
        overlap_score=overlap_score,
        ema_tangle_score=ema_tangle_score,
        ema_alignment_conflict=ema_alignment_conflict,
    )
    signed_trend = _signed_trend_evidence(direction, strength, persistence, efficiency)

    vol_series = primitive.realized_volatility(vol_window)
    realized_per_bar = vol_series.latest
    vol_pct = _percentile_with_availability(vol_series.values_per_bar)
    realized_per_session = _realized_vol_per_session(realized_per_bar, primitive.identity.timeframe)
    volatility_state = _volatility_state(realized_per_bar, vol_pct)

    chop_score = _chop_score(overlap_score, efficiency, ema_tangle_score)
    chop_state = _chop_state(chop_score)
    compression_expansion = _compression_expansion_state(
        primitive.wilder_atr(atr_period).range_ratios[-1], vol_pct
    )
    mean_reversion_score, mean_reversion_direction = _mean_reversion_pressure(
        ema20_distance_atr, efficiency
    )
    momentum_cleanliness = _momentum_cleanliness(
        efficiency, overlap_score, short_slope, long_slope, ema_alignment_conflict
    )
    hurst = _hurst_from_log_returns(primitive.vectors.log_returns)
    volume_state = _volume_state(primitive.vectors.missing_volume_mask)

    payload = {
        "calculation_version": CANONICAL_CHART_STATE_V2_VERSION,
        "snapshot_hash": primitive.source_snapshot_hash,
        "source_feature_kernel_hash": primitive.source_feature_kernel_hash,
        "source_primitive_hash": primitive.primitive_hash,
        "trend_direction": direction,
        "trend_direction_availability": direction_availability,
        "trend_strength": strength,
        "trend_persistence": persistence,
        "trend_efficiency": efficiency,
        "trend_acceleration": acceleration,
        "trend_change_risk_score": change_risk,
        "signed_trend_evidence": signed_trend,
        "volatility_state": volatility_state,
        "realized_vol_per_bar": realized_per_bar,
        "realized_vol_per_session": realized_per_session,
        "realized_vol_percentile": vol_pct.value,
        "realized_vol_percentile_availability": vol_pct.availability,
        "chop_balance_state": chop_state,
        "chop_balance_score": chop_score,
        "compression_expansion_state": compression_expansion,
        "mean_reversion_pressure_score": mean_reversion_score,
        "mean_reversion_direction": mean_reversion_direction,
        "momentum_cleanliness_score": momentum_cleanliness,
        "hurst_diagnostic": hurst.value,
        "hurst_availability": hurst.availability,
        "volume_state": volume_state,
    }
    state_hash = _stable_hash(payload)

    return CanonicalChartStateV2(
        calculation_version=CANONICAL_CHART_STATE_V2_VERSION,
        identity=ChartStateIdentity(
            symbol=primitive.identity.symbol,
            timeframe=primitive.identity.timeframe,
            decision_time_ns=primitive.identity.decision_time_ns,
            snapshot_hash=primitive.identity.snapshot_hash,
            snapshot_id=primitive.identity.snapshot_id,
            source_feature_kernel_hash=primitive.source_feature_kernel_hash,
            source_primitive_hash=primitive.primitive_hash,
        ),
        trend_direction=direction,
        trend_direction_availability=direction_availability,
        trend_strength=strength,
        trend_persistence=persistence,
        trend_efficiency=efficiency,
        trend_acceleration=acceleration,
        trend_change_risk_score=change_risk,
        signed_trend_evidence=signed_trend,
        volatility_state=volatility_state,
        realized_vol_per_bar=realized_per_bar,
        realized_vol_per_session=realized_per_session,
        annualized_realized_vol=None,
        realized_vol_percentile=vol_pct.value,
        realized_vol_percentile_availability=vol_pct.availability,
        chop_balance_state=chop_state,
        chop_balance_score=chop_score,
        compression_expansion_state=compression_expansion,
        mean_reversion_pressure_score=mean_reversion_score,
        mean_reversion_direction=mean_reversion_direction,
        momentum_cleanliness_score=momentum_cleanliness,
        hurst_diagnostic=hurst.value,
        hurst_availability=hurst.availability,
        volume_state=volume_state,
        session_normalized_volume_confirmation="UNAVAILABLE_REQUIRES_SESSION_HISTORY",
        source_snapshot_hash=primitive.source_snapshot_hash,
        source_feature_kernel_hash=primitive.source_feature_kernel_hash,
        source_primitive_hash=primitive.primitive_hash,
        chart_state_hash=state_hash,
    )


def _validate_sources(primitive: MarketPrimitiveKernelV2, observed: SnapshotFeatureKernel, atr_period: int, vol_window: int) -> None:
    if primitive.closed_bar_count != observed.closed_bar_count:
        raise CanonicalChartStateV2Error("primitive/observed bar-count mismatch")
    if primitive.identity.symbol != observed.identity.symbol:
        raise CanonicalChartStateV2Error("primitive/observed symbol mismatch")
    if primitive.identity.timeframe != observed.identity.timeframe:
        raise CanonicalChartStateV2Error("primitive/observed timeframe mismatch")
    if primitive.identity.decision_time_ns != observed.identity.decision_time_ns:
        raise CanonicalChartStateV2Error("primitive/observed decision-time mismatch")
    if primitive.source_snapshot_hash != observed.source_snapshot_hash:
        raise CanonicalChartStateV2Error("primitive/observed snapshot hash mismatch")
    if primitive.source_feature_kernel_hash != observed.feature_hash:
        raise CanonicalChartStateV2Error("primitive/observed feature hash mismatch")
    if primitive.identity.snapshot_id != observed.identity.snapshot_id:
        raise CanonicalChartStateV2Error("primitive/observed snapshot-id mismatch")
    required = (
        ("Wilder ATR", lambda: primitive.wilder_atr(atr_period)),
        ("realized volatility", lambda: primitive.realized_volatility(vol_window)),
        ("EMA 9", lambda: primitive.ema(9)),
        ("EMA 20", lambda: primitive.ema(20)),
        ("EMA 50", lambda: primitive.ema(50)),
        ("slope 5", lambda: primitive.log_slope(DEFAULT_SHORT_SLOPE_WINDOW)),
        ("slope 9", lambda: primitive.log_slope(DEFAULT_MEDIUM_SLOPE_WINDOW)),
        ("slope 20", lambda: primitive.log_slope(DEFAULT_LONG_SLOPE_WINDOW)),
        ("efficiency 20", lambda: primitive.signed_path_efficiency(DEFAULT_EFFICIENCY_WINDOW)),
    )
    for name, getter in required:
        try:
            getter()
        except ValueError as exc:
            raise CanonicalChartStateV2Error(f"required primitive {name} was not materialized") from exc


def _trend_direction(long_slope: float | None, medium_slope: float | None, signed_eff: float | None) -> tuple[str, str]:
    values = [item for item in (long_slope, medium_slope, signed_eff) if item is not None]
    if len(values) < 2:
        return "unavailable", "INSUFFICIENT_HISTORY"
    signs = [_sign(item) for item in values if abs(item) > 1e-12]
    if not signs:
        return "neutral", "AVAILABLE"
    positive = sum(item > 0 for item in signs)
    negative = sum(item < 0 for item in signs)
    if positive >= 2 and negative == 0:
        return "bullish", "AVAILABLE"
    if negative >= 2 and positive == 0:
        return "bearish", "AVAILABLE"
    if positive >= 2:
        return "bullish", "CONFLICTED"
    if negative >= 2:
        return "bearish", "CONFLICTED"
    return "neutral", "CONFLICTED"


def _trend_strength(slope: float | None, close: float, atr: float | None) -> float | None:
    if slope is None or atr is None or atr <= 0.0:
        return None
    atr_normalized = abs(slope) * close / atr
    return _clamp(atr_normalized / 0.35)


def _trend_persistence(values: tuple[float | None, ...], direction: str, efficiency: float | None) -> float | None:
    if direction not in {"bullish", "bearish"} or efficiency is None:
        return None
    expected = 1 if direction == "bullish" else -1
    clean = [item for item in values[-9:] if item is not None]
    if len(clean) < 5:
        return None
    consistency = sum(_sign(item) == expected for item in clean) / len(clean)
    return _clamp(mean([consistency, efficiency]))


def _change_risk(*, direction: str, short_slope: float | None, long_slope: float | None, latest_bar_eff: float | None, overlap_score: float | None, ema_tangle_score: float | None, ema_alignment_conflict: bool) -> float | None:
    if direction not in {"bullish", "bearish"}:
        return None
    expected = 1 if direction == "bullish" else -1
    components: list[float] = []
    if short_slope is not None and long_slope is not None:
        components.append(1.0 if _sign(short_slope) != _sign(long_slope) else 0.0)
    if latest_bar_eff is not None:
        components.append(_clamp(max(0.0, -expected * latest_bar_eff)))
    if overlap_score is not None:
        components.append(_clamp(overlap_score))
    if ema_tangle_score is not None:
        components.append(_clamp(ema_tangle_score))
    components.append(1.0 if ema_alignment_conflict else 0.0)
    return _clamp(mean(components)) if components else None


def _signed_trend_evidence(direction: str, strength: float | None, persistence: float | None, efficiency: float | None) -> float | None:
    values = [item for item in (strength, persistence, efficiency) if item is not None]
    if direction not in {"bullish", "bearish"} or len(values) < 2:
        return None
    magnitude = _clamp(mean(values))
    return magnitude if direction == "bullish" else -magnitude


def _percentile_with_availability(values: tuple[float | None, ...]) -> MetricAvailability:
    if not values or values[-1] is None:
        return MetricAvailability(None, "INSUFFICIENT_HISTORY")
    current = float(values[-1])
    history = [float(item) for item in values[:-1] if item is not None and math.isfinite(item)]
    if len(history) < MIN_PERCENTILE_HISTORY:
        return MetricAvailability(None, "INSUFFICIENT_HISTORY")
    rank = sum(item <= current for item in history) / len(history)
    return MetricAvailability(rank * 100.0, "AVAILABLE")


def _realized_vol_per_session(per_bar: float | None, timeframe: str) -> float | None:
    if per_bar is None:
        return None
    minute_map = {"1m": 1.0, "3m": 3.0, "5m": 5.0, "15m": 15.0, "30m": 30.0, "1H": 60.0, "4H": 240.0}
    if timeframe == "daily":
        return per_bar
    minutes = minute_map.get(timeframe)
    if minutes is None:
        return None
    return per_bar * math.sqrt(NSE_REGULAR_SESSION_MINUTES / minutes)


def _volatility_state(current: float | None, percentile: MetricAvailability) -> str:
    if current is None:
        return "INSUFFICIENT_HISTORY"
    if percentile.value is None:
        return "AVAILABLE_UNRANKED"
    if percentile.value >= 90.0:
        return "HIGH_EXPANSION"
    if percentile.value <= 20.0:
        return "LOW_COMPRESSION"
    return "NORMAL"


def _chop_score(overlap: float | None, efficiency: float | None, ema_tangle: float | None) -> float | None:
    components: list[float] = []
    if overlap is not None:
        components.append(_clamp(overlap))
    if efficiency is not None:
        components.append(1.0 - _clamp(efficiency))
    if ema_tangle is not None:
        components.append(_clamp(ema_tangle))
    return _clamp(mean(components)) if components else None


def _chop_state(score: float | None) -> str:
    if score is None:
        return "INSUFFICIENT_HISTORY"
    if score >= 0.67:
        return "BALANCED_CHOPPY"
    if score <= 0.33:
        return "DIRECTIONALLY_CLEAN"
    return "MIXED"


def _compression_expansion_state(range_ratio: float | None, vol_pct: MetricAvailability) -> str:
    if range_ratio is None:
        return "INSUFFICIENT_HISTORY"
    if range_ratio >= 1.5 or (vol_pct.value is not None and vol_pct.value >= 80.0):
        return "EXPANSION"
    if range_ratio <= 0.65 or (vol_pct.value is not None and vol_pct.value <= 20.0):
        return "COMPRESSION"
    return "NORMAL"


def _mean_reversion_pressure(distance_atr: float | None, efficiency: float | None) -> tuple[float | None, str]:
    if distance_atr is None:
        return None, "UNAVAILABLE"
    stretch = _clamp(abs(distance_atr) / 2.0)
    persistence_discount = 1.0 if efficiency is None else 1.0 - 0.5 * _clamp(efficiency)
    score = _clamp(stretch * persistence_discount)
    if abs(distance_atr) < 0.15:
        direction = "none"
    else:
        direction = "toward_lower_prices" if distance_atr > 0 else "toward_higher_prices"
    return score, direction


def _momentum_cleanliness(efficiency: float | None, overlap: float | None, short_slope: float | None, long_slope: float | None, ema_conflict: bool) -> float | None:
    components: list[float] = []
    if efficiency is not None:
        components.append(_clamp(efficiency))
    if overlap is not None:
        components.append(1.0 - _clamp(overlap))
    if short_slope is not None and long_slope is not None:
        components.append(1.0 if _sign(short_slope) == _sign(long_slope) else 0.0)
    components.append(0.0 if ema_conflict else 1.0)
    return _clamp(mean(components)) if components else None


def _hurst_from_log_returns(log_returns: tuple[float | None, ...]) -> MetricAvailability:
    clean = [float(item) for item in log_returns if item is not None and math.isfinite(item)]
    if len(clean) < MIN_HURST_RETURNS:
        return MetricAvailability(None, "INSUFFICIENT_HISTORY")
    path: list[float] = [0.0]
    for item in clean[-64:]:
        path.append(path[-1] + item)
    lags = [2, 4, 8, 16]
    xs: list[float] = []
    ys: list[float] = []
    for lag in lags:
        if lag >= len(path):
            continue
        diffs = [path[index] - path[index - lag] for index in range(lag, len(path))]
        if len(diffs) < 2:
            continue
        dev = pstdev(diffs)
        if dev > 1e-12:
            xs.append(math.log(lag))
            ys.append(math.log(dev))
    if len(xs) < 2:
        return MetricAvailability(None, "INSUFFICIENT_HISTORY")
    slope = _linear_slope(xs, ys)
    if slope is None:
        return MetricAvailability(None, "INSUFFICIENT_HISTORY")
    return MetricAvailability(_clamp(slope), "AVAILABLE")


def _volume_state(mask: tuple[bool, ...]) -> str:
    missing = sum(mask)
    if missing == 0:
        return "AVAILABLE"
    if missing == len(mask):
        return "UNAVAILABLE"
    return "PARTIAL"


def _recent_mean(values: tuple[float | None, ...], window: int) -> float | None:
    clean = [float(item) for item in values[-window:] if item is not None]
    return mean(clean) if clean else None


def _linear_slope(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    xm = mean(xs)
    ym = mean(ys)
    denominator = sum((x - xm) ** 2 for x in xs)
    if denominator <= 1e-15:
        return None
    return sum((x - xm) * (y - ym) for x, y in zip(xs, ys, strict=True)) / denominator


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if not math.isfinite(value):
        return minimum
    return max(minimum, min(maximum, value))


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
