from __future__ import annotations

"""M3.1.1 shadow Market Primitive Kernel v2.

This module extends the locked M3.1 SnapshotFeatureKernel without changing its
verified compatibility mathematics. It is an internal, zero-authority physical
fact substrate: deterministic calculations from one already-approved D2-derived
SnapshotFeatureKernel only.

Important semantic rules:
- legacy ``average_range`` remains untouched and is not renamed to ATR;
- true range and Wilder ATR are new, separately versioned primitives;
- undefined ratios remain ``None`` instead of being fabricated as neutral zero;
- no market label, probability, trade recommendation or final-band authority is
  produced here;
- signed direction primitives are kept separate from persistence/efficiency so
  downstream reasoning cannot confuse trend magnitude with direction.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from statistics import mean, pstdev
from typing import Iterable

from .snapshot_feature_kernel import SnapshotFeatureKernel


MARKET_PRIMITIVE_KERNEL_VERSION = "market-primitive-kernel.v2"
WILDER_ATR_VERSION = "wilder-atr.v1"
REALIZED_VOLATILITY_VERSION = "realized-vol-per-bar.v1"
LOG_SLOPE_VERSION = "log-price-slope.v1"
PATH_EFFICIENCY_VERSION = "signed-path-efficiency.v1"

DEFAULT_ATR_PERIODS: tuple[int, ...] = (14,)
DEFAULT_REALIZED_VOL_WINDOWS: tuple[int, ...] = (20,)
DEFAULT_EMA_PERIODS: tuple[int, ...] = (9, 20, 50)
DEFAULT_LOG_SLOPE_WINDOWS: tuple[int, ...] = (5, 9, 20)
DEFAULT_PATH_EFFICIENCY_WINDOWS: tuple[int, ...] = (9, 20)
MAX_WINDOW = 10_000


class MarketPrimitiveKernelV2Error(ValueError):
    """Raised when a locked M3.1 feature kernel cannot form safe v2 primitives."""


@dataclass(frozen=True, slots=True)
class PrimitiveIdentity:
    symbol: str
    timeframe: str
    decision_time_ns: int
    snapshot_hash: str
    snapshot_id: str
    source_feature_kernel_hash: str
    source_feature_kernel_version: str


@dataclass(frozen=True, slots=True)
class PrimitiveVectors:
    true_ranges: tuple[float, ...]
    log_returns: tuple[float | None, ...]
    body_ratios: tuple[float | None, ...]
    upper_wick_ratios: tuple[float | None, ...]
    lower_wick_ratios: tuple[float | None, ...]
    close_locations: tuple[float | None, ...]
    overlap_to_smaller_range: tuple[float | None, ...]
    signed_bar_efficiency: tuple[float | None, ...]
    missing_volume_mask: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class WilderAtrSeries:
    period: int
    values: tuple[float | None, ...]
    range_ratios: tuple[float | None, ...]
    calculation_version: str = WILDER_ATR_VERSION

    @property
    def latest(self) -> float | None:
        return self.values[-1] if self.values else None

    @property
    def warmup_complete(self) -> bool:
        return self.latest is not None


@dataclass(frozen=True, slots=True)
class RealizedVolatilitySeries:
    window: int
    values_per_bar: tuple[float | None, ...]
    calculation_version: str = REALIZED_VOLATILITY_VERSION

    @property
    def latest(self) -> float | None:
        return self.values_per_bar[-1] if self.values_per_bar else None


@dataclass(frozen=True, slots=True)
class EmaSeries:
    period: int
    values: tuple[float, ...]
    ready_from_index: int

    @property
    def latest(self) -> float:
        return self.values[-1]

    @property
    def latest_ready(self) -> bool:
        return len(self.values) - 1 >= self.ready_from_index


@dataclass(frozen=True, slots=True)
class LogSlopeSeries:
    window: int
    values_per_bar: tuple[float | None, ...]
    calculation_version: str = LOG_SLOPE_VERSION

    @property
    def latest(self) -> float | None:
        return self.values_per_bar[-1] if self.values_per_bar else None


@dataclass(frozen=True, slots=True)
class SignedPathEfficiencySeries:
    window: int
    values: tuple[float | None, ...]
    calculation_version: str = PATH_EFFICIENCY_VERSION

    @property
    def latest(self) -> float | None:
        return self.values[-1] if self.values else None


@dataclass(frozen=True, slots=True)
class PrimitiveCalculationAudit:
    primitive_kernel_build_count: int = 1
    source_feature_kernel_reused: bool = True
    primitive_vector_pass_count: int = 1
    atr_series_count: int = 0
    realized_vol_series_count: int = 0
    ema_series_count: int = 0
    log_slope_series_count: int = 0
    path_efficiency_series_count: int = 0


@dataclass(frozen=True, slots=True)
class MarketPrimitiveKernelV2:
    kernel_version: str
    identity: PrimitiveIdentity
    closed_bar_count: int
    vectors: PrimitiveVectors
    atr_series: tuple[WilderAtrSeries, ...]
    realized_volatility_series: tuple[RealizedVolatilitySeries, ...]
    ema_series: tuple[EmaSeries, ...]
    log_slope_series: tuple[LogSlopeSeries, ...]
    path_efficiency_series: tuple[SignedPathEfficiencySeries, ...]
    source_snapshot_hash: str
    source_feature_kernel_hash: str
    primitive_hash: str
    missing_volume_count: int
    audit: PrimitiveCalculationAudit
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True

    def wilder_atr(self, period: int) -> WilderAtrSeries:
        for item in self.atr_series:
            if item.period == period:
                return item
        raise MarketPrimitiveKernelV2Error(f"Wilder ATR period {period} was not materialized")

    def realized_volatility(self, window: int) -> RealizedVolatilitySeries:
        for item in self.realized_volatility_series:
            if item.window == window:
                return item
        raise MarketPrimitiveKernelV2Error(f"realized-volatility window {window} was not materialized")

    def ema(self, period: int) -> EmaSeries:
        for item in self.ema_series:
            if item.period == period:
                return item
        raise MarketPrimitiveKernelV2Error(f"EMA period {period} was not materialized")

    def log_slope(self, window: int) -> LogSlopeSeries:
        for item in self.log_slope_series:
            if item.window == window:
                return item
        raise MarketPrimitiveKernelV2Error(f"log-slope window {window} was not materialized")

    def signed_path_efficiency(self, window: int) -> SignedPathEfficiencySeries:
        for item in self.path_efficiency_series:
            if item.window == window:
                return item
        raise MarketPrimitiveKernelV2Error(f"path-efficiency window {window} was not materialized")

    def receipt_summary(self) -> dict[str, object]:
        """Return a bounded, zero-authority summary for later shadow receipts."""

        latest = self.closed_bar_count - 1
        return {
            "kernel_version": self.kernel_version,
            "identity": {
                "symbol": self.identity.symbol,
                "timeframe": self.identity.timeframe,
                "decision_time_ns": self.identity.decision_time_ns,
                "snapshot_hash": self.identity.snapshot_hash,
                "source_feature_kernel_hash": self.identity.source_feature_kernel_hash,
            },
            "latest": {
                "true_range": self.vectors.true_ranges[latest],
                "log_return": self.vectors.log_returns[latest],
                "body_ratio": self.vectors.body_ratios[latest],
                "upper_wick_ratio": self.vectors.upper_wick_ratios[latest],
                "lower_wick_ratio": self.vectors.lower_wick_ratios[latest],
                "close_location": self.vectors.close_locations[latest],
                "overlap_to_smaller_range": self.vectors.overlap_to_smaller_range[latest],
                "signed_bar_efficiency": self.vectors.signed_bar_efficiency[latest],
                "volume_missing": self.vectors.missing_volume_mask[latest],
                "wilder_atr": {str(item.period): item.latest for item in self.atr_series},
                "realized_volatility_per_bar": {
                    str(item.window): item.latest for item in self.realized_volatility_series
                },
                "ema": {
                    str(item.period): {
                        "value": item.latest,
                        "warmup_complete": item.latest_ready,
                    }
                    for item in self.ema_series
                },
                "log_price_slope": {
                    str(item.window): item.latest for item in self.log_slope_series
                },
                "signed_path_efficiency": {
                    str(item.window): item.latest for item in self.path_efficiency_series
                },
            },
            "quality": {
                "closed_bar_count": self.closed_bar_count,
                "missing_volume_count": self.missing_volume_count,
                "legacy_average_range_preserved": True,
                "annualized_volatility_claimed": False,
                "undefined_ratios_are_null": True,
            },
            "provenance": {
                "source_snapshot_hash": self.source_snapshot_hash,
                "source_feature_kernel_hash": self.source_feature_kernel_hash,
                "primitive_hash": self.primitive_hash,
            },
            "authority": {
                "used_for_probability": False,
                "may_set_final_band": False,
                "may_execute": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
            },
        }


def build_market_primitive_kernel_v2(
    source: SnapshotFeatureKernel,
    *,
    atr_periods: Iterable[int] = DEFAULT_ATR_PERIODS,
    realized_vol_windows: Iterable[int] = DEFAULT_REALIZED_VOL_WINDOWS,
    ema_periods: Iterable[int] = DEFAULT_EMA_PERIODS,
    log_slope_windows: Iterable[int] = DEFAULT_LOG_SLOPE_WINDOWS,
    path_efficiency_windows: Iterable[int] = DEFAULT_PATH_EFFICIENCY_WINDOWS,
) -> MarketPrimitiveKernelV2:
    """Build deterministic market primitives from one locked M3.1 feature kernel."""

    _validate_source_kernel(source)
    atr_periods_n = _normalize_windows(atr_periods, "atr_periods")
    realized_vol_windows_n = _normalize_windows(realized_vol_windows, "realized_vol_windows")
    ema_periods_n = _normalize_windows(ema_periods, "ema_periods")
    log_slope_windows_n = _normalize_windows(log_slope_windows, "log_slope_windows")
    path_efficiency_windows_n = _normalize_windows(path_efficiency_windows, "path_efficiency_windows")

    vectors = _build_primitive_vectors(source)
    atr_series = tuple(
        _wilder_atr_series(source.vectors.ranges, vectors.true_ranges, period)
        for period in atr_periods_n
    )
    realized_volatility_series = tuple(
        RealizedVolatilitySeries(
            window=window,
            values_per_bar=_rolling_realized_volatility(vectors.log_returns, window),
        )
        for window in realized_vol_windows_n
    )
    ema_series = tuple(_ema_series(source.vectors.closes, period) for period in ema_periods_n)
    log_closes = tuple(math.log(float(value)) for value in source.vectors.closes)
    log_slope_series = tuple(
        LogSlopeSeries(window=window, values_per_bar=_rolling_linear_slope(log_closes, window))
        for window in log_slope_windows_n
    )
    path_efficiency_series = tuple(
        SignedPathEfficiencySeries(
            window=window,
            values=_rolling_signed_path_efficiency(source.vectors.closes, window),
        )
        for window in path_efficiency_windows_n
    )

    deterministic_payload = {
        "kernel_version": MARKET_PRIMITIVE_KERNEL_VERSION,
        "symbol": source.identity.symbol,
        "timeframe": source.identity.timeframe,
        "decision_time_ns": source.identity.decision_time_ns,
        "snapshot_hash": source.identity.snapshot_hash,
        "source_feature_kernel_hash": source.feature_hash,
        "source_feature_kernel_version": source.kernel_version,
        "vectors": {
            "true_ranges": vectors.true_ranges,
            "log_returns": vectors.log_returns,
            "body_ratios": vectors.body_ratios,
            "upper_wick_ratios": vectors.upper_wick_ratios,
            "lower_wick_ratios": vectors.lower_wick_ratios,
            "close_locations": vectors.close_locations,
            "overlap_to_smaller_range": vectors.overlap_to_smaller_range,
            "signed_bar_efficiency": vectors.signed_bar_efficiency,
            "missing_volume_mask": vectors.missing_volume_mask,
        },
        "atr": [
            {"period": item.period, "values": item.values, "range_ratios": item.range_ratios}
            for item in atr_series
        ],
        "realized_volatility": [
            {"window": item.window, "values": item.values_per_bar}
            for item in realized_volatility_series
        ],
        "ema": [
            {"period": item.period, "values": item.values, "ready_from_index": item.ready_from_index}
            for item in ema_series
        ],
        "log_slope": [
            {"window": item.window, "values": item.values_per_bar}
            for item in log_slope_series
        ],
        "path_efficiency": [
            {"window": item.window, "values": item.values}
            for item in path_efficiency_series
        ],
    }
    primitive_hash = _stable_hash(deterministic_payload)

    return MarketPrimitiveKernelV2(
        kernel_version=MARKET_PRIMITIVE_KERNEL_VERSION,
        identity=PrimitiveIdentity(
            symbol=source.identity.symbol,
            timeframe=source.identity.timeframe,
            decision_time_ns=source.identity.decision_time_ns,
            snapshot_hash=source.identity.snapshot_hash,
            snapshot_id=source.identity.snapshot_id,
            source_feature_kernel_hash=source.feature_hash,
            source_feature_kernel_version=source.kernel_version,
        ),
        closed_bar_count=source.closed_bar_count,
        vectors=vectors,
        atr_series=atr_series,
        realized_volatility_series=realized_volatility_series,
        ema_series=ema_series,
        log_slope_series=log_slope_series,
        path_efficiency_series=path_efficiency_series,
        source_snapshot_hash=source.source_snapshot_hash,
        source_feature_kernel_hash=source.feature_hash,
        primitive_hash=primitive_hash,
        missing_volume_count=sum(vectors.missing_volume_mask),
        audit=PrimitiveCalculationAudit(
            atr_series_count=len(atr_series),
            realized_vol_series_count=len(realized_volatility_series),
            ema_series_count=len(ema_series),
            log_slope_series_count=len(log_slope_series),
            path_efficiency_series_count=len(path_efficiency_series),
        ),
    )


def _validate_source_kernel(source: SnapshotFeatureKernel) -> None:
    if source.closed_bar_count <= 0:
        raise MarketPrimitiveKernelV2Error("source feature kernel must contain at least one closed bar")
    if len(source.identity.snapshot_hash) != 64 or len(source.feature_hash) != 64:
        raise MarketPrimitiveKernelV2Error("source snapshot/feature hash identity is malformed")
    if source.source_snapshot_hash != source.identity.snapshot_hash:
        raise MarketPrimitiveKernelV2Error("source snapshot hash identity drift")
    if len(source.vectors.closes) != source.closed_bar_count:
        raise MarketPrimitiveKernelV2Error("source vector length differs from closed_bar_count")
    for name, values in (
        ("open", source.vectors.opens),
        ("high", source.vectors.highs),
        ("low", source.vectors.lows),
        ("close", source.vectors.closes),
    ):
        if len(values) != source.closed_bar_count:
            raise MarketPrimitiveKernelV2Error(f"source {name} vector length differs from closed_bar_count")
        if any(not math.isfinite(float(value)) or float(value) <= 0.0 for value in values):
            raise MarketPrimitiveKernelV2Error(f"source {name} prices must be finite and strictly positive")


def _build_primitive_vectors(source: SnapshotFeatureKernel) -> PrimitiveVectors:
    true_ranges: list[float] = []
    log_returns: list[float | None] = []
    body_ratios: list[float | None] = []
    upper_wick_ratios: list[float | None] = []
    lower_wick_ratios: list[float | None] = []
    close_locations: list[float | None] = []
    overlaps: list[float | None] = []
    signed_efficiencies: list[float | None] = []
    missing_volume_mask: list[bool] = []

    previous_close: float | None = None
    previous_high: float | None = None
    previous_low: float | None = None

    for open_price, high, low, close, volume in zip(
        source.vectors.opens,
        source.vectors.highs,
        source.vectors.lows,
        source.vectors.closes,
        source.vectors.volumes,
        strict=True,
    ):
        candle_range = max(high - low, 0.0)
        true_range = candle_range
        if previous_close is not None:
            true_range = max(candle_range, abs(high - previous_close), abs(low - previous_close))
        true_ranges.append(true_range)
        log_returns.append(None if previous_close is None else math.log(close / previous_close))

        if candle_range <= 0.0:
            body_ratios.append(None)
            upper_wick_ratios.append(None)
            lower_wick_ratios.append(None)
            close_locations.append(None)
        else:
            body_ratios.append(abs(close - open_price) / candle_range)
            upper_wick_ratios.append(max(0.0, high - max(open_price, close)) / candle_range)
            lower_wick_ratios.append(max(0.0, min(open_price, close) - low) / candle_range)
            close_locations.append((close - low) / candle_range)

        if previous_high is None or previous_low is None:
            overlaps.append(None)
        else:
            previous_range = max(previous_high - previous_low, 0.0)
            smaller_range = min(previous_range, candle_range)
            if smaller_range <= 0.0:
                overlaps.append(None)
            else:
                overlap = max(0.0, min(high, previous_high) - max(low, previous_low))
                overlaps.append(min(1.0, overlap / smaller_range))

        signed_efficiencies.append(None if true_range <= 0.0 else (close - open_price) / true_range)
        missing_volume_mask.append(volume is None)
        previous_close = close
        previous_high = high
        previous_low = low

    return PrimitiveVectors(
        true_ranges=tuple(true_ranges),
        log_returns=tuple(log_returns),
        body_ratios=tuple(body_ratios),
        upper_wick_ratios=tuple(upper_wick_ratios),
        lower_wick_ratios=tuple(lower_wick_ratios),
        close_locations=tuple(close_locations),
        overlap_to_smaller_range=tuple(overlaps),
        signed_bar_efficiency=tuple(signed_efficiencies),
        missing_volume_mask=tuple(missing_volume_mask),
    )


def _wilder_atr_series(
    candle_ranges: tuple[float, ...],
    true_ranges: tuple[float, ...],
    period: int,
) -> WilderAtrSeries:
    values: list[float | None] = [None] * len(true_ranges)
    range_ratios: list[float | None] = [None] * len(true_ranges)
    if len(true_ranges) >= period:
        current = mean(true_ranges[:period])
        values[period - 1] = current
        range_ratios[period - 1] = candle_ranges[period - 1] / current if current > 0.0 else None
        for index in range(period, len(true_ranges)):
            current = ((current * (period - 1)) + true_ranges[index]) / period
            values[index] = current
            range_ratios[index] = candle_ranges[index] / current if current > 0.0 else None
    return WilderAtrSeries(period=period, values=tuple(values), range_ratios=tuple(range_ratios))


def _rolling_realized_volatility(
    log_returns: tuple[float | None, ...],
    window: int,
) -> tuple[float | None, ...]:
    output: list[float | None] = []
    for index in range(len(log_returns)):
        start = max(0, index - window + 1)
        sample = log_returns[start : index + 1]
        clean = [float(item) for item in sample if item is not None]
        if len(clean) < window:
            output.append(None)
        else:
            output.append(pstdev(clean))
    return tuple(output)


def _ema_series(closes: tuple[float, ...], period: int) -> EmaSeries:
    alpha = 2.0 / (period + 1.0)
    values: list[float] = []
    current = float(closes[0])
    values.append(current)
    for value in closes[1:]:
        current = float(value) * alpha + current * (1.0 - alpha)
        values.append(current)
    return EmaSeries(period=period, values=tuple(values), ready_from_index=period - 1)


def _rolling_linear_slope(values: tuple[float, ...], window: int) -> tuple[float | None, ...]:
    output: list[float | None] = []
    x_mean = (window - 1) / 2.0
    denominator = sum((index - x_mean) ** 2 for index in range(window))
    for index in range(len(values)):
        if index + 1 < window:
            output.append(None)
            continue
        sample = values[index - window + 1 : index + 1]
        y_mean = mean(sample)
        numerator = sum(
            (offset - x_mean) * (value - y_mean)
            for offset, value in enumerate(sample)
        )
        output.append(numerator / denominator if denominator > 0.0 else None)
    return tuple(output)


def _rolling_signed_path_efficiency(
    closes: tuple[float, ...],
    window: int,
) -> tuple[float | None, ...]:
    output: list[float | None] = []
    for index in range(len(closes)):
        if index + 1 < window:
            output.append(None)
            continue
        sample = closes[index - window + 1 : index + 1]
        net = sample[-1] - sample[0]
        path = sum(abs(sample[offset] - sample[offset - 1]) for offset in range(1, len(sample)))
        output.append(None if path <= 0.0 else max(-1.0, min(1.0, net / path)))
    return tuple(output)


def _normalize_windows(values: Iterable[int], name: str) -> tuple[int, ...]:
    normalized = tuple(sorted(set(int(value) for value in values)))
    if not normalized:
        raise MarketPrimitiveKernelV2Error(f"{name} cannot be empty")
    if any(value < 2 or value > MAX_WINDOW for value in normalized):
        raise MarketPrimitiveKernelV2Error(f"{name} values must be between 2 and {MAX_WINDOW}")
    return normalized


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
