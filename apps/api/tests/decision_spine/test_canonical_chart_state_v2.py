from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
from time import perf_counter

import pytest

from app.behavior.decision_spine.canonical_chart_state_v2 import (
    CANONICAL_CHART_STATE_V2_VERSION,
    CanonicalChartStateV2Error,
    build_canonical_chart_state_v2,
)
from app.behavior.decision_spine.market_primitive_kernel_v2 import build_market_primitive_kernel_v2
from app.behavior.decision_spine.snapshot_feature_kernel import build_snapshot_feature_kernel
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import CandleBar, ClosedCandleSnapshot


BASE_NS = 1_725_858_900_000_000_000


def _snapshot(*, closes: list[float] | None = None, timeframe: str = "5m", snapshot_hash: str = "a" * 64, missing: set[int] | None = None) -> ClosedCandleSnapshot:
    closes = closes or [100.0 * math.exp(i * 0.0012) for i in range(60)]
    duration = timeframe_duration_ns(timeframe)
    missing = missing or set()
    rows: list[CandleBar] = []
    previous = closes[0] / math.exp(0.0012)
    for index, close in enumerate(closes):
        open_price = previous
        high = max(open_price, close) * 1.001
        low = min(open_price, close) * 0.999
        rows.append(CandleBar(
            symbol="RELIANCE", timeframe=timeframe, timestamp_ns=BASE_NS + index * duration,
            open=open_price, high=high, low=low, close=close,
            volume=None if index in missing else 100_000.0 + index * 250.0,
            source="user_csv", sequence_number=index + 1,
        ))
        previous = close
    decision_time_ns = rows[-1].timestamp_ns + duration
    return ClosedCandleSnapshot(
        snapshot_version="closed-candle-snapshot.v1.87", snapshot_id="m311-chart-state-test",
        snapshot_hash=snapshot_hash, symbol="RELIANCE", timeframe=timeframe,
        decision_time_ns=decision_time_ns, decision_time="2026-09-08T10:00:00+05:30",
        timezone_offset_minutes=330, bar_count=len(rows), first_bar_timestamp_ns=rows[0].timestamp_ns,
        last_bar_timestamp_ns=rows[-1].timestamp_ns, last_bar_close_time_ns=decision_time_ns,
        closed_ohlcv_bars=rows, source_schema_version="candles.v1", immutable=True,
        closed_candle_only=True, point_in_time_safe=True,
    )


def _build(snapshot: ClosedCandleSnapshot | None = None):
    observed = build_snapshot_feature_kernel(snapshot or _snapshot())
    primitive = build_market_primitive_kernel_v2(observed)
    return build_canonical_chart_state_v2(primitive, observed), primitive, observed


def test_m311_chart_001_zero_authority_immutable_shadow():
    state, _, _ = _build()
    assert state.calculation_version == CANONICAL_CHART_STATE_V2_VERSION
    assert state.research_only is True
    assert state.used_for_probability is False
    assert state.may_set_final_band is False
    assert state.may_execute is False
    assert state.trade_allowed is False
    assert state.order_routing_enabled is False
    assert state.live_trading_blocked is True
    with pytest.raises(FrozenInstanceError):
        state.trend_direction = "bearish"  # type: ignore[misc]


def test_m311_chart_002_bullish_direction_is_separate_from_high_persistence():
    state, _, _ = _build(_snapshot(closes=[100.0 * math.exp(i * 0.0015) for i in range(60)]))
    assert state.trend_direction == "bullish"
    assert state.trend_persistence is not None and state.trend_persistence > 0.8
    assert state.trend_strength is not None
    assert state.trend_efficiency is not None and state.trend_efficiency > 0.9
    assert state.signed_trend_evidence is not None and state.signed_trend_evidence > 0.0


def test_m311_chart_003_bearish_direction_is_separate_from_high_persistence():
    state, _, _ = _build(_snapshot(closes=[110.0 * math.exp(-i * 0.0015) for i in range(60)], snapshot_hash="b" * 64))
    assert state.trend_direction == "bearish"
    assert state.trend_persistence is not None and state.trend_persistence > 0.8
    assert state.trend_efficiency is not None and state.trend_efficiency > 0.9
    assert state.signed_trend_evidence is not None and state.signed_trend_evidence < 0.0


def test_m311_chart_004_mirrored_trends_preserve_magnitude_symmetry():
    up, _, _ = _build(_snapshot(closes=[100.0 * math.exp(i * 0.0015) for i in range(60)], snapshot_hash="a" * 64))
    down, _, _ = _build(_snapshot(closes=[100.0 * math.exp(-i * 0.0015) for i in range(60)], snapshot_hash="b" * 64))
    assert up.trend_direction == "bullish" and down.trend_direction == "bearish"
    assert up.trend_efficiency == pytest.approx(down.trend_efficiency)
    assert up.trend_persistence == pytest.approx(down.trend_persistence)
    assert abs(up.signed_trend_evidence) == pytest.approx(abs(down.signed_trend_evidence), rel=2e-2)


def test_m311_chart_005_explicitly_proves_legacy_d6_bearish_persistence_defect():
    state, _, _ = _build(_snapshot(closes=[120.0 * math.exp(-i * 0.0018) for i in range(60)], snapshot_hash="b" * 64))
    assert state.trend_direction == "bearish"
    assert state.trend_persistence is not None and state.trend_persistence > 0.5
    legacy_directionless_long_score = state.trend_persistence * 2.0 - 1.0
    assert legacy_directionless_long_score > 0.0
    assert state.signed_trend_evidence is not None and state.signed_trend_evidence < 0.0
    assert state.legacy_d6_compatibility_debt is True


def test_m311_chart_006_insufficient_history_is_not_fake_neutral_percentile_or_hurst():
    state, _, _ = _build(_snapshot(closes=[100.0 * math.exp(i * 0.001) for i in range(24)]))
    assert state.realized_vol_percentile is None
    assert state.realized_vol_percentile_availability == "INSUFFICIENT_HISTORY"
    assert state.hurst_diagnostic is None
    assert state.hurst_availability == "INSUFFICIENT_HISTORY"
    encoded = str(state.receipt_summary())
    assert "fake_neutral_percentiles_used': False" in encoded
    assert "fake_neutral_hurst_used': False" in encoded


def test_m311_chart_007_missing_volume_is_explicit_and_not_zero_derived():
    partial, _, _ = _build(_snapshot(missing={59}))
    unavailable, _, _ = _build(_snapshot(missing=set(range(60)), snapshot_hash="b" * 64))
    assert partial.volume_state == "PARTIAL"
    assert unavailable.volume_state == "UNAVAILABLE"
    assert partial.session_normalized_volume_confirmation == "UNAVAILABLE_REQUIRES_SESSION_HISTORY"
    assert unavailable.session_normalized_volume_confirmation == "UNAVAILABLE_REQUIRES_SESSION_HISTORY"
    assert unavailable.trend_direction in {"bullish", "bearish", "neutral"}


def test_m311_chart_008_intraday_realized_volatility_is_timeframe_correct_and_not_fake_annualized():
    state, _, _ = _build(_snapshot(timeframe="5m"))
    assert state.realized_vol_per_bar is not None
    assert state.realized_vol_per_session == pytest.approx(state.realized_vol_per_bar * math.sqrt(75.0))
    assert state.annualized_realized_vol is None
    assert state.receipt_summary()["quality"]["annualized_volatility_claimed"] is False


def test_m311_chart_009_replay_is_deterministic():
    first, _, _ = _build()
    second, _, _ = _build()
    assert first.chart_state_hash == second.chart_state_hash
    assert first == second


def test_m311_chart_010_rejects_mismatched_causal_sources():
    observed_a = build_snapshot_feature_kernel(_snapshot(snapshot_hash="a" * 64))
    primitive_a = build_market_primitive_kernel_v2(observed_a)
    observed_b = build_snapshot_feature_kernel(_snapshot(snapshot_hash="b" * 64))
    with pytest.raises(CanonicalChartStateV2Error, match="snapshot hash mismatch|feature hash mismatch"):
        build_canonical_chart_state_v2(primitive_a, observed_b)


def test_m311_chart_011_hurst_is_secondary_and_cannot_flip_signed_direction():
    state, _, _ = _build(_snapshot(closes=[100.0 * math.exp(i * 0.0015) for i in range(30)]))
    assert state.hurst_diagnostic is None
    assert state.hurst_is_secondary_only is True
    assert state.trend_direction == "bullish"
    assert state.signed_trend_evidence is not None and state.signed_trend_evidence > 0.0


def test_m311_chart_012_receipt_has_no_prediction_or_final_decision_authority():
    state, _, _ = _build()
    summary = state.receipt_summary()
    encoded = str(summary).lower()
    forbidden = ("continuation_probability", "reversal_probability", "decision_band", "final_decision")
    assert all(token not in encoded for token in forbidden)
    assert summary["authority"]["used_for_probability"] is False
    assert summary["authority"]["may_set_final_band"] is False
    assert summary["quality"]["scores_are_uncalibrated"] is True
    assert len(encoded) < 12_000


def test_m311_chart_013_runtime_is_bounded():
    observed = build_snapshot_feature_kernel(_snapshot())
    primitive = build_market_primitive_kernel_v2(observed)
    started = perf_counter()
    for _ in range(100):
        result = build_canonical_chart_state_v2(primitive, observed)
        assert len(result.chart_state_hash) == 64
    assert perf_counter() - started < 2.0
