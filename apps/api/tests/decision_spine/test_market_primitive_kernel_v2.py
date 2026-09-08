from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
from time import perf_counter

import pytest

from app.behavior.decision_spine.market_primitive_kernel_v2 import (
    MARKET_PRIMITIVE_KERNEL_VERSION,
    MarketPrimitiveKernelV2Error,
    build_market_primitive_kernel_v2,
)
from app.behavior.decision_spine.snapshot_feature_kernel import build_snapshot_feature_kernel
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import CandleBar, ClosedCandleSnapshot


BASE_NS = 1_725_858_900_000_000_000


def _snapshot(
    *,
    closes: list[float] | None = None,
    missing_volume_index: int | None = None,
    snapshot_hash: str = "a" * 64,
) -> ClosedCandleSnapshot:
    duration = timeframe_duration_ns("5m")
    closes = closes or [100.0 + index * 0.12 for index in range(40)]
    rows: list[CandleBar] = []
    previous = closes[0]
    for index, close in enumerate(closes):
        open_price = previous if index else close - 0.04
        high = max(open_price, close) + 0.10
        low = min(open_price, close) - 0.08
        rows.append(
            CandleBar(
                symbol="RELIANCE",
                timeframe="5m",
                timestamp_ns=BASE_NS + index * duration,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=None if index == missing_volume_index else 100_000.0 + index * 500.0,
                source="user_csv",
                sequence_number=index + 1,
            )
        )
        previous = close
    decision_time_ns = rows[-1].timestamp_ns + duration
    return ClosedCandleSnapshot(
        snapshot_version="closed-candle-snapshot.v1.87",
        snapshot_id="m3-1-1-primitive-test",
        snapshot_hash=snapshot_hash,
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision_time_ns,
        decision_time="2026-09-08T10:00:00+05:30",
        timezone_offset_minutes=330,
        bar_count=len(rows),
        first_bar_timestamp_ns=rows[0].timestamp_ns,
        last_bar_timestamp_ns=rows[-1].timestamp_ns,
        last_bar_close_time_ns=decision_time_ns,
        closed_ohlcv_bars=rows,
        source_schema_version="candles.v1",
        immutable=True,
        closed_candle_only=True,
        point_in_time_safe=True,
    )


def _build(**kwargs):
    return build_market_primitive_kernel_v2(build_snapshot_feature_kernel(_snapshot(**kwargs)))


def test_m311_primitive_001_is_immutable_zero_authority_shadow_substrate():
    kernel = _build()
    assert kernel.kernel_version == MARKET_PRIMITIVE_KERNEL_VERSION
    assert kernel.closed_bar_count == 40
    assert kernel.source_snapshot_hash == "a" * 64
    assert len(kernel.primitive_hash) == 64
    assert kernel.used_for_probability is False
    assert kernel.may_set_final_band is False
    assert kernel.may_execute is False
    assert kernel.trade_allowed is False
    assert kernel.order_routing_enabled is False
    assert kernel.live_trading_blocked is True
    with pytest.raises(FrozenInstanceError):
        kernel.closed_bar_count = 0  # type: ignore[misc]


def test_m311_primitive_002_same_source_replays_same_hash_and_vectors():
    first = _build()
    second = _build()
    assert first.primitive_hash == second.primitive_hash
    assert first.vectors == second.vectors
    assert first.atr_series == second.atr_series
    assert first.log_slope_series == second.log_slope_series


def test_m311_primitive_003_true_range_includes_gap_from_previous_close():
    closes = [100.0, 100.1, 104.0, 104.1, 104.2, 104.3, 104.4, 104.5, 104.6, 104.7, 104.8, 104.9, 105.0, 105.1, 105.2]
    snapshot = _snapshot(closes=closes)
    # Force a true opening gap on bar 3 while preserving valid OHLC geometry.
    bar = snapshot.closed_ohlcv_bars[2].model_copy(update={"open": 103.8, "high": 104.1, "low": 103.7})
    snapshot = snapshot.model_copy(update={"closed_ohlcv_bars": [*snapshot.closed_ohlcv_bars[:2], bar, *snapshot.closed_ohlcv_bars[3:]]})
    source = build_snapshot_feature_kernel(snapshot)
    kernel = build_market_primitive_kernel_v2(source)
    expected = max(bar.high - bar.low, abs(bar.high - snapshot.closed_ohlcv_bars[1].close), abs(bar.low - snapshot.closed_ohlcv_bars[1].close))
    assert kernel.vectors.true_ranges[2] == pytest.approx(expected)
    assert kernel.vectors.true_ranges[2] > source.vectors.ranges[2]


def test_m311_primitive_004_wilder_atr_is_distinct_from_legacy_average_range():
    closes = [100.0 + index * 0.05 for index in range(30)]
    snapshot = _snapshot(closes=closes)
    # Introduce a gap so true range differs from candle range.
    changed = snapshot.closed_ohlcv_bars[14].model_copy(update={"open": 103.0, "high": 103.2, "low": 102.9, "close": 103.1})
    rows = list(snapshot.closed_ohlcv_bars)
    rows[14] = changed
    snapshot = snapshot.model_copy(update={"closed_ohlcv_bars": rows})
    source = build_snapshot_feature_kernel(snapshot)
    kernel = build_market_primitive_kernel_v2(source)
    assert kernel.wilder_atr(14).latest is not None
    assert kernel.wilder_atr(14).latest != pytest.approx(source.average_range(14).latest)


def test_m311_primitive_005_wilder_atr_has_explicit_warmup_not_fake_zero():
    source = build_snapshot_feature_kernel(_snapshot(closes=[100.0 + i * 0.1 for i in range(10)]))
    kernel = build_market_primitive_kernel_v2(source, atr_periods=(14,))
    assert kernel.wilder_atr(14).latest is None
    assert kernel.wilder_atr(14).warmup_complete is False
    assert all(item is None for item in kernel.wilder_atr(14).values)


def test_m311_primitive_006_zero_range_bar_keeps_undefined_morphology_null():
    snapshot = _snapshot()
    rows = list(snapshot.closed_ohlcv_bars)
    rows[5] = rows[5].model_copy(update={"open": 100.5, "high": 100.5, "low": 100.5, "close": 100.5})
    snapshot = snapshot.model_copy(update={"closed_ohlcv_bars": rows})
    kernel = build_market_primitive_kernel_v2(build_snapshot_feature_kernel(snapshot))
    assert kernel.vectors.body_ratios[5] is None
    assert kernel.vectors.upper_wick_ratios[5] is None
    assert kernel.vectors.lower_wick_ratios[5] is None
    assert kernel.vectors.close_locations[5] is None


def test_m311_primitive_007_missing_volume_is_masked_not_neutralized():
    kernel = _build(missing_volume_index=39)
    assert kernel.missing_volume_count == 1
    assert kernel.vectors.missing_volume_mask[-1] is True
    summary = kernel.receipt_summary()
    assert summary["latest"]["volume_missing"] is True
    assert summary["quality"]["missing_volume_count"] == 1


def test_m311_primitive_008_realized_volatility_is_per_bar_and_has_no_fake_history():
    kernel = _build()
    series = kernel.realized_volatility(20)
    assert all(item is None for item in series.values_per_bar[:20])
    assert series.latest is not None
    assert series.latest >= 0.0
    assert kernel.receipt_summary()["quality"]["annualized_volatility_claimed"] is False


def test_m311_primitive_009_signed_path_efficiency_separates_direction_from_strength():
    up = _build(closes=[100.0 + i * 0.2 for i in range(40)])
    down = _build(closes=[110.0 - i * 0.2 for i in range(40)], snapshot_hash="b" * 64)
    up_eff = up.signed_path_efficiency(20).latest
    down_eff = down.signed_path_efficiency(20).latest
    assert up_eff is not None and up_eff > 0.95
    assert down_eff is not None and down_eff < -0.95
    assert abs(up_eff) == pytest.approx(abs(down_eff))


def test_m311_primitive_010_log_slope_preserves_signed_direction():
    up = _build(closes=[100.0 + i * 0.2 for i in range(40)])
    down = _build(closes=[110.0 - i * 0.2 for i in range(40)], snapshot_hash="b" * 64)
    assert up.log_slope(20).latest is not None and up.log_slope(20).latest > 0.0
    assert down.log_slope(20).latest is not None and down.log_slope(20).latest < 0.0


def test_m311_primitive_011_price_scale_preserves_dimensionless_morphology_and_log_returns():
    base_snapshot = _snapshot()
    scaled_rows = [
        bar.model_copy(update={"open": bar.open * 10, "high": bar.high * 10, "low": bar.low * 10, "close": bar.close * 10})
        for bar in base_snapshot.closed_ohlcv_bars
    ]
    scaled_snapshot = base_snapshot.model_copy(update={"snapshot_hash": "b" * 64, "closed_ohlcv_bars": scaled_rows})
    base = build_market_primitive_kernel_v2(build_snapshot_feature_kernel(base_snapshot))
    scaled = build_market_primitive_kernel_v2(build_snapshot_feature_kernel(scaled_snapshot))
    for left, right in zip(base.vectors.body_ratios, scaled.vectors.body_ratios, strict=True):
        assert left == pytest.approx(right) if left is not None else right is None
    for left, right in zip(base.vectors.log_returns, scaled.vectors.log_returns, strict=True):
        assert left == pytest.approx(right) if left is not None else right is None


def test_m311_primitive_012_rejects_corrupt_source_price_vector():
    source = build_snapshot_feature_kernel(_snapshot())
    broken_vectors = source.vectors.__class__(
        timestamps_ns=source.vectors.timestamps_ns,
        sequence_numbers=source.vectors.sequence_numbers,
        opens=source.vectors.opens,
        highs=source.vectors.highs,
        lows=source.vectors.lows,
        closes=tuple([*source.vectors.closes[:-1], 0.0]),
        volumes=source.vectors.volumes,
        ranges=source.vectors.ranges,
        bodies=source.vectors.bodies,
        typical_prices=source.vectors.typical_prices,
        returns=source.vectors.returns,
    )
    broken = source.__class__(
        kernel_version=source.kernel_version,
        identity=source.identity,
        closed_bar_count=source.closed_bar_count,
        first_timestamp_ns=source.first_timestamp_ns,
        last_timestamp_ns=source.last_timestamp_ns,
        latest_sequence=source.latest_sequence,
        vectors=broken_vectors,
        average_range_windows=source.average_range_windows,
        volume_windows=source.volume_windows,
        cumulative_volume=source.cumulative_volume,
        cumulative_typical_price_volume=source.cumulative_typical_price_volume,
        cumulative_missing_volume=source.cumulative_missing_volume,
        source_snapshot_hash=source.source_snapshot_hash,
        bar_content_hash=source.bar_content_hash,
        feature_hash=source.feature_hash,
        audit=source.audit,
    )
    with pytest.raises(MarketPrimitiveKernelV2Error, match="strictly positive"):
        build_market_primitive_kernel_v2(broken)


def test_m311_primitive_013_receipt_is_bounded_and_contains_no_decision_or_probability():
    kernel = _build()
    summary = kernel.receipt_summary()
    encoded = str(summary)
    assert "final_band" not in encoded
    assert "probability" in encoded  # only the explicit false authority field
    assert summary["authority"]["used_for_probability"] is False
    assert len(encoded) < 12_000


def test_m311_primitive_014_small_snapshot_runtime_is_bounded():
    source = build_snapshot_feature_kernel(_snapshot())
    started = perf_counter()
    for _ in range(100):
        result = build_market_primitive_kernel_v2(source)
        assert math.isfinite(result.vectors.true_ranges[-1])
    assert perf_counter() - started < 2.0
