from __future__ import annotations

from dataclasses import FrozenInstanceError
from time import perf_counter

import pytest

from app.behavior.decision_spine.canonical_candle_morphology_v2 import (
    CANONICAL_CANDLE_MORPHOLOGY_V2_VERSION,
    CanonicalCandleMorphologyV2Error,
    build_canonical_candle_morphology_v2,
)
from app.behavior.decision_spine.market_primitive_kernel_v2 import build_market_primitive_kernel_v2
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
        snapshot_id="m3-1-1-morphology-test",
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


def _build(snapshot: ClosedCandleSnapshot | None = None):
    observed = build_snapshot_feature_kernel(snapshot or _snapshot())
    primitive = build_market_primitive_kernel_v2(observed)
    return build_canonical_candle_morphology_v2(primitive, observed), primitive, observed


def test_m311_morphology_001_is_immutable_zero_authority_shadow_layer():
    morphology, _, _ = _build()
    assert morphology.calculation_version == CANONICAL_CANDLE_MORPHOLOGY_V2_VERSION
    assert morphology.epistemic_level == "DERIVED"
    assert morphology.research_only is True
    assert morphology.used_for_probability is False
    assert morphology.may_set_final_band is False
    assert morphology.may_execute is False
    assert morphology.trade_allowed is False
    assert morphology.order_routing_enabled is False
    assert morphology.live_trading_blocked is True
    assert morphology.human_approval_required is True
    with pytest.raises(FrozenInstanceError):
        morphology.atr_period = 20  # type: ignore[misc]


def test_m311_morphology_002_reuses_primitive_geometry_exactly():
    morphology, primitive, _ = _build()
    for index, bar in enumerate(morphology.bars):
        assert bar.true_range == primitive.vectors.true_ranges[index]
        assert bar.range_to_wilder_atr == primitive.wilder_atr(14).range_ratios[index]
        assert bar.body_ratio == primitive.vectors.body_ratios[index]
        assert bar.upper_wick_ratio == primitive.vectors.upper_wick_ratios[index]
        assert bar.lower_wick_ratio == primitive.vectors.lower_wick_ratios[index]
        assert bar.close_location == primitive.vectors.close_locations[index]
        assert bar.overlap_to_smaller_range == primitive.vectors.overlap_to_smaller_range[index]
        assert bar.signed_bar_efficiency == primitive.vectors.signed_bar_efficiency[index]
    assert morphology.audit.primitive_kernel_reused is True
    assert morphology.audit.primitive_geometry_recalculated is False


def test_m311_morphology_003_missing_volume_remains_unavailable_not_zero():
    snapshot = _snapshot(missing_volume_index=39)
    morphology, _, _ = _build(snapshot)
    latest = morphology.latest
    assert latest.volume is None
    assert latest.volume_available is False
    assert morphology.missing_volume_count == 1
    summary = morphology.receipt_summary()
    assert summary["quality"]["missing_volume_neutralized"] is False
    assert summary["latest"]["volume_available"] is False


def test_m311_morphology_004_zero_range_preserves_undefined_ratios_as_null():
    snapshot = _snapshot()
    rows = list(snapshot.closed_ohlcv_bars)
    rows[20] = rows[20].model_copy(update={"open": 102.0, "high": 102.0, "low": 102.0, "close": 102.0})
    snapshot = snapshot.model_copy(update={"closed_ohlcv_bars": rows})
    morphology, _, _ = _build(snapshot)
    bar = morphology.bars[20]
    assert bar.body_ratio is None
    assert bar.upper_wick_ratio is None
    assert bar.lower_wick_ratio is None
    assert bar.wick_asymmetry is None
    assert bar.close_location is None


def test_m311_morphology_005_inside_outside_geometry_is_physical_and_causal():
    snapshot = _snapshot()
    rows = list(snapshot.closed_ohlcv_bars)
    prior = rows[10].model_copy(update={"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.2})
    inside = rows[11].model_copy(update={"open": 100.2, "high": 100.8, "low": 99.2, "close": 100.5})
    outside = rows[12].model_copy(update={"open": 100.5, "high": 101.2, "low": 98.8, "close": 100.1})
    rows[10:13] = [prior, inside, outside]
    snapshot = snapshot.model_copy(update={"closed_ohlcv_bars": rows})
    morphology, _, _ = _build(snapshot)
    assert morphology.bars[11].inside_bar_geometry is True
    assert morphology.bars[11].outside_bar_geometry is False
    assert morphology.bars[12].outside_bar_geometry is True


def test_m311_morphology_006_failed_extension_signatures_are_direction_symmetric():
    snapshot = _snapshot()
    rows = list(snapshot.closed_ohlcv_bars)
    rows[20] = rows[20].model_copy(update={"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0})
    rows[21] = rows[21].model_copy(update={"open": 100.0, "high": 101.5, "low": 99.2, "close": 100.8})
    rows[22] = rows[22].model_copy(update={"open": 100.8, "high": 101.0, "low": 98.5, "close": 99.5})
    snapshot = snapshot.model_copy(update={"closed_ohlcv_bars": rows})
    morphology, _, _ = _build(snapshot)
    assert morphology.bars[21].upward_extension == pytest.approx(0.5)
    assert morphology.bars[21].failed_upward_extension_signature is True
    assert morphology.bars[22].downward_extension == pytest.approx(0.7)
    assert morphology.bars[22].failed_downward_extension_signature is True


def test_m311_morphology_007_bar_open_discontinuity_is_signed_and_first_bar_unknown():
    snapshot = _snapshot()
    rows = list(snapshot.closed_ohlcv_bars)
    rows[15] = rows[15].model_copy(update={"open": rows[14].close * 1.01})
    snapshot = snapshot.model_copy(update={"closed_ohlcv_bars": rows})
    morphology, _, _ = _build(snapshot)
    assert morphology.bars[0].bar_open_discontinuity_bps is None
    assert morphology.bars[15].bar_open_discontinuity_bps == pytest.approx(100.0)


def test_m311_morphology_008_up_down_geometry_preserves_signed_symmetry():
    up_snapshot = _snapshot(closes=[100.0 + i * 0.2 for i in range(40)], snapshot_hash="a" * 64)
    down_snapshot = _snapshot(closes=[110.0 - i * 0.2 for i in range(40)], snapshot_hash="b" * 64)
    up, _, _ = _build(up_snapshot)
    down, _, _ = _build(down_snapshot)
    assert up.latest.signed_bar_efficiency is not None and up.latest.signed_bar_efficiency > 0.0
    assert down.latest.signed_bar_efficiency is not None and down.latest.signed_bar_efficiency < 0.0
    assert abs(up.latest.signed_bar_efficiency) == pytest.approx(abs(down.latest.signed_bar_efficiency))


def test_m311_morphology_009_replay_is_deterministic():
    first, _, _ = _build()
    second, _, _ = _build()
    assert first.morphology_hash == second.morphology_hash
    assert first.bars == second.bars


def test_m311_morphology_010_rejects_mismatched_causal_sources():
    observed_a = build_snapshot_feature_kernel(_snapshot(snapshot_hash="a" * 64))
    primitive_a = build_market_primitive_kernel_v2(observed_a)
    observed_b = build_snapshot_feature_kernel(_snapshot(snapshot_hash="b" * 64))
    with pytest.raises(CanonicalCandleMorphologyV2Error, match="snapshot hash mismatch|feature hash mismatch"):
        build_canonical_candle_morphology_v2(primitive_a, observed_b)


def test_m311_morphology_011_requires_materialized_true_atr_period():
    observed = build_snapshot_feature_kernel(_snapshot())
    primitive = build_market_primitive_kernel_v2(observed, atr_periods=(14,))
    with pytest.raises(CanonicalCandleMorphologyV2Error, match="20"):
        build_canonical_candle_morphology_v2(primitive, observed, atr_period=20)


def test_m311_morphology_012_receipt_contains_no_intent_probability_or_decision_claim():
    morphology, _, _ = _build()
    summary = morphology.receipt_summary()
    encoded = str(summary).lower()
    forbidden = (
        "manipulation",
        "stop hunt",
        "accumulation",
        "distribution",
        "institutional absorption",
        "order block",
        "smart money",
        "decision_band",
        "final_decision",
        "probability",
    )
    assert all(token not in encoded for token in forbidden)
    assert summary["quality"]["intent_claims_present"] is False
    assert summary["authority"]["may_set_final_band"] is False
    assert len(encoded) < 12_000


def test_m311_morphology_013_small_snapshot_runtime_is_bounded():
    observed = build_snapshot_feature_kernel(_snapshot())
    primitive = build_market_primitive_kernel_v2(observed)
    started = perf_counter()
    for _ in range(100):
        result = build_canonical_candle_morphology_v2(primitive, observed)
        assert result.latest.true_range >= 0.0
    assert perf_counter() - started < 2.0
