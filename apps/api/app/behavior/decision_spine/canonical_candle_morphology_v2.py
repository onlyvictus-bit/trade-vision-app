from __future__ import annotations

"""M3.1.1-B shadow Canonical Candle Morphology v2.

This module is a zero-authority sensory layer. It reads observed OHLCV identity
from the exact SnapshotFeatureKernel that produced a MarketPrimitiveKernelV2,
and reuses the primitive kernel for candle geometry/ATR facts rather than
recomputing them.

It intentionally describes physical price geometry only. It does not claim
market intent, institutional activity, manipulation, accumulation,
distribution, order blocks, stop hunts, or calibrated probabilities.
"""

from dataclasses import dataclass
import hashlib
import json
import math

from .market_primitive_kernel_v2 import MarketPrimitiveKernelV2
from .snapshot_feature_kernel import SnapshotFeatureKernel


CANONICAL_CANDLE_MORPHOLOGY_V2_VERSION = "canonical-candle-morphology.v2"
DEFAULT_ATR_PERIOD = 14


class CanonicalCandleMorphologyV2Error(ValueError):
    """Raised when morphology cannot be formed from one causally identical source."""


@dataclass(frozen=True, slots=True)
class MorphologyIdentity:
    symbol: str
    timeframe: str
    decision_time_ns: int
    snapshot_hash: str
    snapshot_id: str
    source_feature_kernel_hash: str
    source_primitive_hash: str


@dataclass(frozen=True, slots=True)
class CandleMorphologyBarV2:
    index: int
    timestamp_ns: int
    sequence_number: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    volume_available: bool
    true_range: float
    range_to_wilder_atr: float | None
    body_ratio: float | None
    upper_wick_ratio: float | None
    lower_wick_ratio: float | None
    wick_asymmetry: float | None
    close_location: float | None
    overlap_to_smaller_range: float | None
    signed_bar_efficiency: float | None
    bar_open_discontinuity_bps: float | None
    inside_bar_geometry: bool | None
    outside_bar_geometry: bool | None
    upward_extension: float | None
    downward_extension: float | None
    failed_upward_extension_signature: bool | None
    failed_downward_extension_signature: bool | None
    true_range_to_previous: float | None


@dataclass(frozen=True, slots=True)
class MorphologyCalculationAudit:
    morphology_build_count: int = 1
    primitive_kernel_reused: bool = True
    snapshot_feature_kernel_observed_only: bool = True
    primitive_geometry_recalculated: bool = False


@dataclass(frozen=True, slots=True)
class CanonicalCandleMorphologyV2:
    calculation_version: str
    identity: MorphologyIdentity
    atr_period: int
    bars: tuple[CandleMorphologyBarV2, ...]
    source_snapshot_hash: str
    source_feature_kernel_hash: str
    source_primitive_hash: str
    morphology_hash: str
    missing_volume_count: int
    audit: MorphologyCalculationAudit
    epistemic_level: str = "DERIVED"
    research_only: bool = True
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    human_approval_required: bool = True

    @property
    def latest(self) -> CandleMorphologyBarV2:
        return self.bars[-1]

    def receipt_summary(self) -> dict[str, object]:
        latest = self.latest
        return {
            "calculation_version": self.calculation_version,
            "epistemic_level": self.epistemic_level,
            "identity": {
                "symbol": self.identity.symbol,
                "timeframe": self.identity.timeframe,
                "decision_time_ns": self.identity.decision_time_ns,
                "snapshot_hash": self.identity.snapshot_hash,
                "source_feature_kernel_hash": self.identity.source_feature_kernel_hash,
                "source_primitive_hash": self.identity.source_primitive_hash,
            },
            "latest": {
                "timestamp_ns": latest.timestamp_ns,
                "sequence_number": latest.sequence_number,
                "true_range": latest.true_range,
                "range_to_wilder_atr": latest.range_to_wilder_atr,
                "body_ratio": latest.body_ratio,
                "upper_wick_ratio": latest.upper_wick_ratio,
                "lower_wick_ratio": latest.lower_wick_ratio,
                "wick_asymmetry": latest.wick_asymmetry,
                "close_location": latest.close_location,
                "overlap_to_smaller_range": latest.overlap_to_smaller_range,
                "signed_bar_efficiency": latest.signed_bar_efficiency,
                "bar_open_discontinuity_bps": latest.bar_open_discontinuity_bps,
                "inside_bar_geometry": latest.inside_bar_geometry,
                "outside_bar_geometry": latest.outside_bar_geometry,
                "upward_extension": latest.upward_extension,
                "downward_extension": latest.downward_extension,
                "failed_upward_extension_signature": latest.failed_upward_extension_signature,
                "failed_downward_extension_signature": latest.failed_downward_extension_signature,
                "true_range_to_previous": latest.true_range_to_previous,
                "volume_available": latest.volume_available,
            },
            "quality": {
                "bar_count": len(self.bars),
                "missing_volume_count": self.missing_volume_count,
                "missing_volume_neutralized": False,
                "undefined_values_are_null": True,
                "intent_claims_present": False,
            },
            "provenance": {
                "source_snapshot_hash": self.source_snapshot_hash,
                "source_feature_kernel_hash": self.source_feature_kernel_hash,
                "source_primitive_hash": self.source_primitive_hash,
                "morphology_hash": self.morphology_hash,
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


def build_canonical_candle_morphology_v2(
    primitive: MarketPrimitiveKernelV2,
    observed: SnapshotFeatureKernel,
    *,
    atr_period: int = DEFAULT_ATR_PERIOD,
) -> CanonicalCandleMorphologyV2:
    """Build deterministic physical candle morphology from one causal D2 root.

    ``observed`` is used only for raw OHLCV/timestamp/sequence observations that
    are deliberately not duplicated inside MarketPrimitiveKernelV2. Primitive
    geometry and true-ATR math are always reused from ``primitive``.
    """

    _validate_sources(primitive, observed, atr_period)
    atr = primitive.wilder_atr(atr_period)
    bars: list[CandleMorphologyBarV2] = []

    for index in range(primitive.closed_bar_count):
        open_price = float(observed.vectors.opens[index])
        high = float(observed.vectors.highs[index])
        low = float(observed.vectors.lows[index])
        close = float(observed.vectors.closes[index])
        volume = observed.vectors.volumes[index]
        previous_close = None if index == 0 else float(observed.vectors.closes[index - 1])
        previous_high = None if index == 0 else float(observed.vectors.highs[index - 1])
        previous_low = None if index == 0 else float(observed.vectors.lows[index - 1])

        upper_wick = primitive.vectors.upper_wick_ratios[index]
        lower_wick = primitive.vectors.lower_wick_ratios[index]
        true_range = float(primitive.vectors.true_ranges[index])
        previous_true_range = None if index == 0 else float(primitive.vectors.true_ranges[index - 1])

        inside, outside = _containment_geometry(
            high=high,
            low=low,
            previous_high=previous_high,
            previous_low=previous_low,
        )
        upward_extension, downward_extension = _extensions(
            high=high,
            low=low,
            previous_high=previous_high,
            previous_low=previous_low,
        )
        failed_up, failed_down = _failed_extension_signatures(
            close=close,
            previous_high=previous_high,
            previous_low=previous_low,
            upward_extension=upward_extension,
            downward_extension=downward_extension,
        )

        bars.append(
            CandleMorphologyBarV2(
                index=index,
                timestamp_ns=int(observed.vectors.timestamps_ns[index]),
                sequence_number=int(observed.vectors.sequence_numbers[index]),
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=None if volume is None else float(volume),
                volume_available=not primitive.vectors.missing_volume_mask[index],
                true_range=true_range,
                range_to_wilder_atr=atr.range_ratios[index],
                body_ratio=primitive.vectors.body_ratios[index],
                upper_wick_ratio=upper_wick,
                lower_wick_ratio=lower_wick,
                wick_asymmetry=_difference_or_none(lower_wick, upper_wick),
                close_location=primitive.vectors.close_locations[index],
                overlap_to_smaller_range=primitive.vectors.overlap_to_smaller_range[index],
                signed_bar_efficiency=primitive.vectors.signed_bar_efficiency[index],
                bar_open_discontinuity_bps=_bar_open_discontinuity_bps(open_price, previous_close),
                inside_bar_geometry=inside,
                outside_bar_geometry=outside,
                upward_extension=upward_extension,
                downward_extension=downward_extension,
                failed_upward_extension_signature=failed_up,
                failed_downward_extension_signature=failed_down,
                true_range_to_previous=_safe_ratio(true_range, previous_true_range),
            )
        )

    payload = {
        "calculation_version": CANONICAL_CANDLE_MORPHOLOGY_V2_VERSION,
        "atr_period": atr_period,
        "snapshot_hash": primitive.source_snapshot_hash,
        "source_feature_kernel_hash": primitive.source_feature_kernel_hash,
        "source_primitive_hash": primitive.primitive_hash,
        "bars": [
            {
                "index": item.index,
                "timestamp_ns": item.timestamp_ns,
                "sequence_number": item.sequence_number,
                "open": item.open,
                "high": item.high,
                "low": item.low,
                "close": item.close,
                "volume": item.volume,
                "volume_available": item.volume_available,
                "true_range": item.true_range,
                "range_to_wilder_atr": item.range_to_wilder_atr,
                "body_ratio": item.body_ratio,
                "upper_wick_ratio": item.upper_wick_ratio,
                "lower_wick_ratio": item.lower_wick_ratio,
                "wick_asymmetry": item.wick_asymmetry,
                "close_location": item.close_location,
                "overlap_to_smaller_range": item.overlap_to_smaller_range,
                "signed_bar_efficiency": item.signed_bar_efficiency,
                "bar_open_discontinuity_bps": item.bar_open_discontinuity_bps,
                "inside_bar_geometry": item.inside_bar_geometry,
                "outside_bar_geometry": item.outside_bar_geometry,
                "upward_extension": item.upward_extension,
                "downward_extension": item.downward_extension,
                "failed_upward_extension_signature": item.failed_upward_extension_signature,
                "failed_downward_extension_signature": item.failed_downward_extension_signature,
                "true_range_to_previous": item.true_range_to_previous,
            }
            for item in bars
        ],
    }
    morphology_hash = _stable_hash(payload)

    return CanonicalCandleMorphologyV2(
        calculation_version=CANONICAL_CANDLE_MORPHOLOGY_V2_VERSION,
        identity=MorphologyIdentity(
            symbol=primitive.identity.symbol,
            timeframe=primitive.identity.timeframe,
            decision_time_ns=primitive.identity.decision_time_ns,
            snapshot_hash=primitive.identity.snapshot_hash,
            snapshot_id=primitive.identity.snapshot_id,
            source_feature_kernel_hash=primitive.source_feature_kernel_hash,
            source_primitive_hash=primitive.primitive_hash,
        ),
        atr_period=atr_period,
        bars=tuple(bars),
        source_snapshot_hash=primitive.source_snapshot_hash,
        source_feature_kernel_hash=primitive.source_feature_kernel_hash,
        source_primitive_hash=primitive.primitive_hash,
        morphology_hash=morphology_hash,
        missing_volume_count=primitive.missing_volume_count,
        audit=MorphologyCalculationAudit(),
    )


def _validate_sources(
    primitive: MarketPrimitiveKernelV2,
    observed: SnapshotFeatureKernel,
    atr_period: int,
) -> None:
    if not isinstance(atr_period, int) or isinstance(atr_period, bool) or atr_period <= 0:
        raise CanonicalCandleMorphologyV2Error("atr_period must be a positive integer")
    if primitive.closed_bar_count <= 0:
        raise CanonicalCandleMorphologyV2Error("primitive kernel must contain at least one closed bar")
    if primitive.closed_bar_count != observed.closed_bar_count:
        raise CanonicalCandleMorphologyV2Error("primitive/observed bar-count mismatch")
    if primitive.identity.symbol != observed.identity.symbol:
        raise CanonicalCandleMorphologyV2Error("primitive/observed symbol mismatch")
    if primitive.identity.timeframe != observed.identity.timeframe:
        raise CanonicalCandleMorphologyV2Error("primitive/observed timeframe mismatch")
    if primitive.identity.decision_time_ns != observed.identity.decision_time_ns:
        raise CanonicalCandleMorphologyV2Error("primitive/observed decision-time mismatch")
    if primitive.source_snapshot_hash != observed.source_snapshot_hash:
        raise CanonicalCandleMorphologyV2Error("primitive/observed snapshot hash mismatch")
    if primitive.source_feature_kernel_hash != observed.feature_hash:
        raise CanonicalCandleMorphologyV2Error("primitive/observed feature hash mismatch")
    if primitive.identity.snapshot_id != observed.identity.snapshot_id:
        raise CanonicalCandleMorphologyV2Error("primitive/observed snapshot-id mismatch")
    try:
        primitive.wilder_atr(atr_period)
    except ValueError as exc:
        raise CanonicalCandleMorphologyV2Error(
            f"Wilder ATR period {atr_period} was not materialized in primitive kernel"
        ) from exc

    expected = primitive.closed_bar_count
    vector_lengths = {
        "timestamps": len(observed.vectors.timestamps_ns),
        "sequence_numbers": len(observed.vectors.sequence_numbers),
        "opens": len(observed.vectors.opens),
        "highs": len(observed.vectors.highs),
        "lows": len(observed.vectors.lows),
        "closes": len(observed.vectors.closes),
        "volumes": len(observed.vectors.volumes),
        "true_ranges": len(primitive.vectors.true_ranges),
        "body_ratios": len(primitive.vectors.body_ratios),
        "upper_wick_ratios": len(primitive.vectors.upper_wick_ratios),
        "lower_wick_ratios": len(primitive.vectors.lower_wick_ratios),
        "close_locations": len(primitive.vectors.close_locations),
        "overlaps": len(primitive.vectors.overlap_to_smaller_range),
        "signed_bar_efficiency": len(primitive.vectors.signed_bar_efficiency),
        "missing_volume_mask": len(primitive.vectors.missing_volume_mask),
    }
    for name, length in vector_lengths.items():
        if length != expected:
            raise CanonicalCandleMorphologyV2Error(
                f"{name} vector length {length} differs from closed_bar_count {expected}"
            )


def _containment_geometry(
    *, high: float, low: float, previous_high: float | None, previous_low: float | None
) -> tuple[bool | None, bool | None]:
    if previous_high is None or previous_low is None:
        return None, None
    return high <= previous_high and low >= previous_low, high >= previous_high and low <= previous_low


def _extensions(
    *, high: float, low: float, previous_high: float | None, previous_low: float | None
) -> tuple[float | None, float | None]:
    if previous_high is None or previous_low is None:
        return None, None
    return max(0.0, high - previous_high), max(0.0, previous_low - low)


def _failed_extension_signatures(
    *,
    close: float,
    previous_high: float | None,
    previous_low: float | None,
    upward_extension: float | None,
    downward_extension: float | None,
) -> tuple[bool | None, bool | None]:
    if previous_high is None or previous_low is None:
        return None, None
    return (
        bool(upward_extension is not None and upward_extension > 0.0 and close <= previous_high),
        bool(downward_extension is not None and downward_extension > 0.0 and close >= previous_low),
    )


def _bar_open_discontinuity_bps(open_price: float, previous_close: float | None) -> float | None:
    if previous_close is None:
        return None
    if previous_close <= 0.0 or not math.isfinite(previous_close):
        raise CanonicalCandleMorphologyV2Error("previous close must be finite and strictly positive")
    return ((open_price - previous_close) / previous_close) * 10_000.0


def _difference_or_none(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _safe_ratio(numerator: float, denominator: float | None) -> float | None:
    if denominator is None or denominator <= 0.0:
        return None
    return numerator / denominator


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
