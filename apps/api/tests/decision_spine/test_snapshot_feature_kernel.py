from __future__ import annotations

from dataclasses import FrozenInstanceError
from time import perf_counter

import pytest

from app.behavior.decision_spine.snapshot_feature_kernel import (
    SNAPSHOT_FEATURE_KERNEL_VERSION,
    SnapshotFeatureKernelError,
    build_snapshot_feature_kernel,
)
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import CandleBar, ClosedCandleSnapshot


BASE_NS = 1_725_858_900_000_000_000


def _snapshot(
    *,
    bars: int = 40,
    symbol: str = "RELIANCE",
    timeframe: str = "5m",
    price_scale: float = 1.0,
    volume_scale: float = 1.0,
    missing_volume_index: int | None = None,
    snapshot_hash: str = "a" * 64,
) -> ClosedCandleSnapshot:
    duration = timeframe_duration_ns(timeframe)
    rows: list[CandleBar] = []
    for index in range(bars):
        open_price = (100.0 + index * 0.08) * price_scale
        close = (100.0 + index * 0.08 + (0.06 if index % 4 else -0.02)) * price_scale
        high = max(open_price, close) + 0.10 * price_scale
        low = min(open_price, close) - 0.08 * price_scale
        volume = None if index == missing_volume_index else (100_000.0 + index * 700.0) * volume_scale
        rows.append(
            CandleBar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp_ns=BASE_NS + index * duration,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                source="user_csv",
                sequence_number=index + 1,
            )
        )

    decision_time_ns = rows[-1].timestamp_ns + duration
    return ClosedCandleSnapshot(
        snapshot_version="closed-candle-snapshot.v1.87",
        snapshot_id="m3-1-kernel-test",
        snapshot_hash=snapshot_hash,
        symbol=symbol,
        timeframe=timeframe,
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


def test_m31_kernel_001_builds_immutable_d2_causal_substrate():
    snapshot = _snapshot()
    kernel = build_snapshot_feature_kernel(snapshot)

    assert kernel.kernel_version == SNAPSHOT_FEATURE_KERNEL_VERSION
    assert kernel.identity.symbol == "RELIANCE"
    assert kernel.identity.timeframe == "5m"
    assert kernel.identity.snapshot_hash == snapshot.snapshot_hash
    assert kernel.source_snapshot_hash == snapshot.snapshot_hash
    assert kernel.closed_bar_count == snapshot.bar_count
    assert len(kernel.feature_hash) == 64
    assert len(kernel.bar_content_hash) == 64
    assert kernel.audit.feature_kernel_build_count == 1
    assert kernel.audit.bar_sort_pass_count == 1
    assert kernel.audit.derived_vector_pass_count == 1

    with pytest.raises(FrozenInstanceError):
        kernel.closed_bar_count = 999  # type: ignore[misc]


def test_m31_kernel_002_same_snapshot_and_parameters_replay_same_hashes():
    first = build_snapshot_feature_kernel(_snapshot())
    second = build_snapshot_feature_kernel(_snapshot())

    assert first.feature_hash == second.feature_hash
    assert first.bar_content_hash == second.bar_content_hash
    assert first.vectors == second.vectors
    assert first.average_range(14).values == second.average_range(14).values
    assert first.volume_stats(20).zscores == second.volume_stats(20).zscores


def test_m31_kernel_003_changed_closed_bar_changes_bar_and_feature_hashes():
    first_snapshot = _snapshot()
    second_snapshot = _snapshot(snapshot_hash="b" * 64)
    changed = second_snapshot.closed_ohlcv_bars[-1].model_copy(
        update={"close": second_snapshot.closed_ohlcv_bars[-1].close + 0.03,
                "high": second_snapshot.closed_ohlcv_bars[-1].high + 0.03}
    )
    second_snapshot = second_snapshot.model_copy(
        update={"closed_ohlcv_bars": [*second_snapshot.closed_ohlcv_bars[:-1], changed]}
    )

    first = build_snapshot_feature_kernel(first_snapshot)
    second = build_snapshot_feature_kernel(second_snapshot)

    assert first.bar_content_hash != second.bar_content_hash
    assert first.feature_hash != second.feature_hash


def test_m31_kernel_004_parameter_identity_changes_feature_hash_not_bar_hash():
    snapshot = _snapshot()
    first = build_snapshot_feature_kernel(snapshot, average_range_windows=(14,), volume_windows=(20,))
    second = build_snapshot_feature_kernel(snapshot, average_range_windows=(20,), volume_windows=(30,))

    assert first.bar_content_hash == second.bar_content_hash
    assert first.feature_hash != second.feature_hash


def test_m31_kernel_005_vectors_preserve_price_ratio_metamorphic_properties():
    base = build_snapshot_feature_kernel(_snapshot(price_scale=1.0))
    scaled = build_snapshot_feature_kernel(_snapshot(price_scale=10.0, snapshot_hash="b" * 64))

    for base_range, scaled_range in zip(base.vectors.ranges, scaled.vectors.ranges, strict=True):
        assert scaled_range == pytest.approx(base_range * 10.0)
    for base_body, scaled_body in zip(base.vectors.bodies, scaled.vectors.bodies, strict=True):
        assert scaled_body == pytest.approx(base_body * 10.0)
    for base_return, scaled_return in zip(base.vectors.returns, scaled.vectors.returns, strict=True):
        if base_return is None:
            assert scaled_return is None
        else:
            assert scaled_return == pytest.approx(base_return)


def test_m31_kernel_006_volume_scaling_preserves_relative_zscores():
    base = build_snapshot_feature_kernel(_snapshot(volume_scale=1.0))
    scaled = build_snapshot_feature_kernel(_snapshot(volume_scale=10.0, snapshot_hash="b" * 64))

    for base_z, scaled_z in zip(
        base.volume_stats(20).zscores,
        scaled.volume_stats(20).zscores,
        strict=True,
    ):
        if base_z is None:
            assert scaled_z is None
        else:
            assert scaled_z == pytest.approx(base_z)


def test_m31_kernel_007_average_range_preserves_existing_candle_anatomy_math():
    snapshot = _snapshot(bars=16)
    kernel = build_snapshot_feature_kernel(snapshot, average_range_windows=(14,))
    ranges = [bar.high - bar.low for bar in snapshot.closed_ohlcv_bars]
    expected_latest = sum(ranges[-14:]) / 14

    assert kernel.average_range(14).latest == pytest.approx(expected_latest)


def test_m31_kernel_008_anchored_vwap_is_explicit_slice_and_missing_volume_is_unknown():
    complete = build_snapshot_feature_kernel(_snapshot(bars=10))
    missing = build_snapshot_feature_kernel(_snapshot(bars=10, missing_volume_index=5))

    expected_num = sum(
        ((bar.high + bar.low + bar.close) / 3.0) * float(bar.volume or 0.0)
        for bar in _snapshot(bars=10).closed_ohlcv_bars[2:8]
    )
    expected_den = sum(float(bar.volume or 0.0) for bar in _snapshot(bars=10).closed_ohlcv_bars[2:8])

    assert complete.anchored_vwap(2, 8) == pytest.approx(expected_num / expected_den)
    assert missing.anchored_vwap(2, 8) is None
    with pytest.raises(SnapshotFeatureKernelError):
        complete.anchored_vwap(8, 2)


def test_m31_kernel_009_high_low_primitive_has_no_hidden_opening_range_semantics():
    snapshot = _snapshot(bars=10)
    kernel = build_snapshot_feature_kernel(snapshot)
    high, low = kernel.high_low(1, 6)

    assert high == max(bar.high for bar in snapshot.closed_ohlcv_bars[1:6])
    assert low == min(bar.low for bar in snapshot.closed_ohlcv_bars[1:6])


def test_m31_kernel_010_rejects_noncanonical_bar_order_instead_of_silently_repairing():
    snapshot = _snapshot(bars=8)
    shuffled = snapshot.model_copy(
        update={"closed_ohlcv_bars": list(reversed(snapshot.closed_ohlcv_bars))}
    )

    with pytest.raises(SnapshotFeatureKernelError, match="canonical timestamp/sequence order"):
        build_snapshot_feature_kernel(shuffled)


def test_m31_kernel_011_rejects_future_bar_close_relative_to_decision_time():
    snapshot = _snapshot(bars=8)
    unsafe = snapshot.model_copy(
        update={"decision_time_ns": snapshot.last_bar_close_time_ns - 1}
    )

    with pytest.raises(SnapshotFeatureKernelError, match="closing after decision_time_ns"):
        build_snapshot_feature_kernel(unsafe)


def test_m31_kernel_012_rejects_symbol_or_timeframe_drift_inside_d2_snapshot():
    snapshot = _snapshot(bars=8)
    wrong = snapshot.closed_ohlcv_bars[3].model_copy(update={"symbol": "TCS"})
    unsafe = snapshot.model_copy(
        update={"closed_ohlcv_bars": [*snapshot.closed_ohlcv_bars[:3], wrong, *snapshot.closed_ohlcv_bars[4:]]}
    )

    with pytest.raises(SnapshotFeatureKernelError, match="symbol differs"):
        build_snapshot_feature_kernel(unsafe)


def test_m31_kernel_013_rejects_invalid_snapshot_hash_and_window_identity():
    with pytest.raises(SnapshotFeatureKernelError, match="hexadecimal"):
        build_snapshot_feature_kernel(_snapshot(snapshot_hash="z" * 64))

    with pytest.raises(SnapshotFeatureKernelError, match="between 1"):
        build_snapshot_feature_kernel(_snapshot(), average_range_windows=(0,))


def test_m31_kernel_014_compact_audit_has_no_raw_bar_payload():
    kernel = build_snapshot_feature_kernel(_snapshot())
    audit = kernel.compact_audit()

    assert "vectors" not in audit
    assert "closed_ohlcv_bars" not in audit
    assert audit["closed_bar_count"] == 40
    assert audit["audit"]["feature_kernel_build_count"] == 1


def test_m31_kernel_015_400_bar_build_has_bounded_engineering_latency():
    snapshot = _snapshot(bars=400)
    start = perf_counter()
    kernel = build_snapshot_feature_kernel(snapshot)
    elapsed_ms = (perf_counter() - start) * 1000.0

    assert kernel.closed_bar_count == 400
    # This is an intentionally loose CI regression ceiling, not the <2 ms
    # optimization target and not a market-edge claim. We record/profile tighter
    # budgets separately once runner variance is known.
    assert elapsed_ms < 100.0
