from __future__ import annotations

from time import perf_counter

import pytest

from app.behavior import paper_guidance_spine_m2_impl as m31_spine
from app.behavior.candle_anatomy import analyze_candles
from app.behavior.chart_reasoning_volatility import build_chart_reasoning_report
from app.behavior.condition_classifier import classify_conditions
from app.behavior.decision_spine.paper_guidance_decision_context_adapter import (
    build_paper_guidance_decision_context as real_build_context,
)
from app.behavior.decision_spine.snapshot_feature_kernel import build_snapshot_feature_kernel
from app.behavior.paper_guidance_config import PaperGuidanceConfig
from app.behavior.paper_guidance_spine import run_paper_guidance_p1
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import (
    CandleAnatomyRequest,
    CandleBar,
    CandleSeries,
    ChartReasoningRequest,
    ConditionClassifierRequest,
    KillSwitchState,
    PaperGuidanceRequest,
    SystemMode,
    SystemModeValue,
)


BASE_NS = 1_725_858_900_000_000_000


def _mode() -> SystemMode:
    return SystemMode(
        mode=SystemModeValue.MOCK,
        display_label="Mock research",
        immutable=True,
        allows_live_orders=False,
        allows_broker_credentials=False,
        watermark_text="MOCK - NO REAL MONEY",
    )


def _kill_switch() -> KillSwitchState:
    return KillSwitchState(
        state="armed",
        reason=None,
        source=None,
        actor_id=None,
        triggered_at=None,
        blocks_order_paths=False,
    )


def _series(*, bars: int = 40, missing_volume: int | None = None) -> CandleSeries:
    duration = timeframe_duration_ns("5m")
    rows: list[CandleBar] = []
    for index in range(bars):
        open_price = 100.0 + index * 0.08
        close = open_price + (0.06 if index % 4 else -0.02)
        rows.append(
            CandleBar(
                symbol="RELIANCE",
                timeframe="5m",
                timestamp_ns=BASE_NS + index * duration,
                open=open_price,
                high=max(open_price, close) + 0.10,
                low=min(open_price, close) - 0.08,
                close=close,
                volume=None if index == missing_volume else 100_000.0 + index * 700.0,
                source="user_csv",
                sequence_number=index + 1,
            )
        )
    return CandleSeries(
        symbol="RELIANCE",
        timeframe="5m",
        bars=rows,
        snapshot_id="m31-b-candle-test",
        schema_version="candles.v1",
    )


def _request(series: CandleSeries | None = None) -> PaperGuidanceRequest:
    series = series or _series()
    return PaperGuidanceRequest(
        symbol=series.symbol,
        timeframe=series.timeframe,
        series=series,
        decision_time_ns=series.bars[-1].timestamp_ns + timeframe_duration_ns(series.timeframe),
        higher_timeframe_series=[],
        required_higher_timeframes=[],
        indicator_ids=["si_vwap_conf"],
        historical_match_count=999,
    )


@pytest.fixture(autouse=True)
def _fast_dependencies(monkeypatch):
    def fake_runtime(candles, indicator_ids):
        return (
            {indicator_id: {"last": len(candles)} for indicator_id in indicator_ids},
            [
                {
                    "indicator_id": indicator_id,
                    "status": "computed",
                    "latency_ms": 0.1,
                    "source_latency_ms": 0.1,
                    "output_present": True,
                    "used_for_9c_vector": True,
                    "cache_hit": False,
                    "cache_version": "m31-b-test",
                    "error": None,
                }
                for indicator_id in indicator_ids
            ],
        )

    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.compute_real_indicator_outputs_with_telemetry",
        fake_runtime,
    )
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.list_indicator_signal_history_records",
        lambda **_: [],
    )


def _run(request: PaperGuidanceRequest | None = None):
    return run_paper_guidance_p1(
        request or _request(),
        mode=_mode(),
        kill_switch=_kill_switch(),
        config=PaperGuidanceConfig(),
    )


def _receipt(result, engine_id: str):
    return next(item for item in result.engine_receipts if item.engine_id == engine_id)


def test_m31b_001_canonical_route_builds_kernel_and_anatomy_exactly_once(monkeypatch):
    counts = {"kernel": 0, "anatomy": 0}
    original_kernel = m31_spine.build_snapshot_feature_kernel
    original_anatomy = m31_spine.analyze_candles

    def counted_kernel(snapshot):
        counts["kernel"] += 1
        return original_kernel(snapshot)

    def counted_anatomy(request, **kwargs):
        counts["anatomy"] += 1
        return original_anatomy(request, **kwargs)

    monkeypatch.setattr(m31_spine, "build_snapshot_feature_kernel", counted_kernel)
    monkeypatch.setattr(m31_spine, "analyze_candles", counted_anatomy)

    result = _run()
    audit = result.risk_summary["decision_context"]["calculation_audit"]

    assert counts == {"kernel": 1, "anatomy": 1}
    assert audit == {
        "feature_kernel_build_count": 1,
        "candle_anatomy_compute_count": 1,
        "decision_context_build_count": 1,
    }


def test_m31b_002_same_anatomy_hash_is_dependency_for_condition_and_chart():
    result = _run()
    anatomy = _receipt(result, "CANDLE_ANATOMY")
    condition = _receipt(result, "CANDLE_CONDITION")
    chart = _receipt(result, "CHART_REASONING")

    assert anatomy.status == "completed"
    assert anatomy.engine_version == "candle-anatomy.v0.15"
    assert anatomy.source_snapshot_hash == result.snapshot_hash
    assert condition.output_summary["upstream_candle_anatomy_hash"] == anatomy.output_hash
    assert chart.output_summary["upstream_candle_anatomy_hash"] == anatomy.output_hash
    assert condition.source_snapshot_hash == result.snapshot_hash
    assert chart.source_snapshot_hash == result.snapshot_hash


def test_m31b_003_decision_context_activates_bounded_canonical_anatomy(monkeypatch):
    captured = {}

    def capture_context(**kwargs):
        context = real_build_context(**kwargs)
        captured["context"] = context
        return context

    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.build_paper_guidance_decision_context",
        capture_context,
    )
    result = _run()
    context = captured["context"]
    block = context.candle_anatomy
    anatomy_receipt = _receipt(result, "CANDLE_ANATOMY")

    assert block.source_engine == "CANDLE_ANATOMY"
    assert block.status.value == "AVAILABLE"
    assert block.source_snapshot_hash == result.snapshot_hash
    assert block.source_output_hash == anatomy_receipt.output_hash
    assert block.used_for_probability is False
    assert block.claims_trade_authority is False
    assert set(block.payload) >= {"latest", "recent_window", "quality", "provenance", "calculation_audit"}
    assert "features" not in block.payload
    assert "closed_ohlcv_bars" not in block.payload
    assert block.payload["quality"]["source_bar_count"] == 40
    assert block.payload["quality"]["calculation_version"] == "candle-anatomy.v0.15"


def test_m31b_004_anatomy_replay_hash_is_stable_and_changed_closed_bar_changes_hash():
    first = _run()
    replay = _run()
    changed_series = _series()
    changed_bar = changed_series.bars[-1].model_copy(
        update={
            "close": changed_series.bars[-1].close + 0.04,
            "high": changed_series.bars[-1].high + 0.04,
        }
    )
    changed_series = changed_series.model_copy(
        update={"bars": [*changed_series.bars[:-1], changed_bar]}
    )
    changed = _run(_request(changed_series))

    assert _receipt(first, "CANDLE_ANATOMY").output_hash == _receipt(replay, "CANDLE_ANATOMY").output_hash
    assert _receipt(first, "CANDLE_ANATOMY").output_hash != _receipt(changed, "CANDLE_ANATOMY").output_hash


def test_m31b_005_chart_and_condition_accept_precomputed_anatomy_without_recompute(monkeypatch):
    series = _series()
    request = _request(series)
    base = m31_spine._legacy.run_paper_guidance_p0(
        request,
        mode=_mode(),
        kill_switch=_kill_switch(),
        config=PaperGuidanceConfig(),
    )
    assert base.snapshot is not None
    canonical_series = m31_spine._legacy._series_from_snapshot(base.snapshot)
    kernel = build_snapshot_feature_kernel(base.snapshot)
    anatomy = analyze_candles(CandleAnatomyRequest(series=canonical_series), feature_kernel=kernel)

    monkeypatch.setattr(
        "app.behavior.chart_reasoning_volatility.analyze_candles",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("chart recomputed anatomy")),
    )
    monkeypatch.setattr(
        "app.behavior.condition_classifier.analyze_candles",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("condition recomputed anatomy")),
    )

    chart = build_chart_reasoning_report(ChartReasoningRequest(series=canonical_series), anatomy=anatomy)
    condition = classify_conditions(ConditionClassifierRequest(series=canonical_series, anatomy=anatomy))

    assert chart.source_bar_count == anatomy.total_candles
    assert len(condition.records) == anatomy.total_candles


def test_m31b_006_missing_volume_is_explicit_and_not_fabricated():
    series = _series(missing_volume=39)
    request = _request(series)
    base = m31_spine._legacy.run_paper_guidance_p0(
        request,
        mode=_mode(),
        kill_switch=_kill_switch(),
        config=PaperGuidanceConfig(),
    )
    assert base.snapshot is not None
    canonical_series = m31_spine._legacy._series_from_snapshot(base.snapshot)
    kernel = build_snapshot_feature_kernel(base.snapshot)
    anatomy = analyze_candles(CandleAnatomyRequest(series=canonical_series), feature_kernel=kernel)

    assert anatomy.latest is not None
    assert anatomy.latest.volume is None
    assert anatomy.latest.volume_z is None


def test_m31b_007_zero_range_doji_is_safe_and_deterministic():
    duration = timeframe_duration_ns("5m")
    bars = [
        CandleBar(
            symbol="RELIANCE",
            timeframe="5m",
            timestamp_ns=BASE_NS + index * duration,
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            volume=1000.0,
            source="user_csv",
            sequence_number=index + 1,
        )
        for index in range(3)
    ]
    series = CandleSeries(symbol="RELIANCE", timeframe="5m", bars=bars, schema_version="candles.v1")
    result = analyze_candles(CandleAnatomyRequest(series=series))

    assert result.latest is not None
    assert result.latest.direction == "doji"
    assert result.latest.candle_range == 0.0
    assert result.latest.body_pct == 0.0
    assert result.latest.range_atr == 0.0


def test_m31b_008_rejection_inside_outside_and_failed_followthrough_are_preserved():
    duration = timeframe_duration_ns("5m")
    rows = [
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS, open=100, high=101, low=99, close=100.8, volume=1000, source="user_csv", sequence_number=1),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + duration, open=100.7, high=100.9, low=99.3, close=99.5, volume=1100, source="user_csv", sequence_number=2),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 2 * duration, open=99.7, high=100.5, low=99.5, close=100.2, volume=1200, source="user_csv", sequence_number=3),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 3 * duration, open=100.1, high=100.4, low=99.7, close=100.2, volume=900, source="user_csv", sequence_number=4),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 4 * duration, open=100.0, high=101.3, low=99.0, close=101.1, volume=1500, source="user_csv", sequence_number=5),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 5 * duration, open=101.0, high=101.4, low=99.9, close=100.1, volume=1600, source="user_csv", sequence_number=6),
    ]
    series = CandleSeries(symbol="RELIANCE", timeframe="5m", bars=rows, schema_version="candles.v1")
    result = analyze_candles(
        CandleAnatomyRequest(
            series=series,
            breakout_reference_high=100.5,
            breakout_reference_low=99.2,
        )
    )
    all_types = {kind for feature in result.features for kind in feature.candle_structure_types}

    assert "rejection_candle" in all_types
    assert "inside_bar" in all_types
    assert "outside_bar" in all_types
    assert any(feature.failed_follow_through for feature in result.features)


def test_m31b_009_trend_expansion_and_compression_classification_are_deterministic():
    duration = timeframe_duration_ns("5m")
    rows = [
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 0 * duration, open=100.00, high=100.12, low=99.92, close=100.08, volume=1000, source="user_csv", sequence_number=1),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 1 * duration, open=100.08, high=100.18, low=100.00, close=100.12, volume=1000, source="user_csv", sequence_number=2),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 2 * duration, open=100.12, high=100.24, low=100.04, close=100.20, volume=1000, source="user_csv", sequence_number=3),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 3 * duration, open=100.20, high=102.20, low=100.10, close=102.00, volume=2500, source="user_csv", sequence_number=4),
        CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=BASE_NS + 4 * duration, open=102.00, high=102.05, low=101.95, close=102.00, volume=900, source="user_csv", sequence_number=5),
    ]
    series = CandleSeries(symbol="RELIANCE", timeframe="5m", bars=rows, schema_version="candles.v1")
    result = analyze_candles(CandleAnatomyRequest(series=series))

    assert "trend_candle" in result.features[3].candle_structure_types
    assert "expansion_candle" in result.features[3].candle_structure_types
    assert "compression_candle" in result.features[4].candle_structure_types


def test_m31b_010_anatomy_failure_does_not_reach_d6_as_neutral(monkeypatch):
    monkeypatch.setattr(
        m31_spine,
        "analyze_candles",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("forced-anatomy-failure")),
    )
    result = _run()

    assert result.final_band == "WAIT"
    assert result.next_action == "DO_NOTHING"
    assert "FINAL_CONFLUENCE_ARBITER" not in result.engines_run
    assert result.arbiter_summary.get("arbiter_run") is False
    assert any("CANDLE_ANATOMY" in warning for warning in result.warnings)


def test_m31b_011_condition_failure_does_not_reach_d6_as_neutral(monkeypatch):
    monkeypatch.setattr(
        m31_spine._legacy,
        "classify_conditions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("forced-condition-failure")),
    )
    result = _run()

    assert result.final_band == "WAIT"
    assert "FINAL_CONFLUENCE_ARBITER" not in result.engines_run
    assert any("CANDLE_CONDITION" in warning for warning in result.warnings)


def test_m31b_012_chart_failure_does_not_reach_d6_as_neutral(monkeypatch):
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.build_chart_reasoning_report",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("forced-chart-failure")),
    )
    result = _run()

    assert result.final_band == "WAIT"
    assert "FINAL_CONFLUENCE_ARBITER" not in result.engines_run
    assert any("CHART_REASONING" in warning for warning in result.warnings)


def test_m31b_013_canonical_candle_migration_has_bounded_fixture_latency():
    start = perf_counter()
    result = _run()
    elapsed_ms = (perf_counter() - start) * 1000.0

    assert result.snapshot_hash
    # Loose CI ceiling only. This proves absence of pathological regression; it
    # is not an edge claim and not the final production latency budget.
    assert elapsed_ms < 500.0
