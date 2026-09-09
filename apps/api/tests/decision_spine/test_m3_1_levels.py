from __future__ import annotations

from datetime import date, datetime, time, timezone
import hashlib
import json
from time import perf_counter
from zoneinfo import ZoneInfo

import pytest

from app.behavior import paper_guidance_spine_m2_impl as m31_spine
from app.behavior import paper_guidance_spine as pg_spine
from app.behavior.context_engines import analyze_level_context
from app.behavior.decision_spine.canonical_level_intelligence import (
    LEVEL_INTELLIGENCE_VERSION,
    build_canonical_level_intelligence,
)
from app.behavior.decision_spine.paper_guidance_decision_context_adapter import (
    build_paper_guidance_decision_context as real_build_context,
)
from app.behavior.decision_spine.snapshot_feature_kernel import (
    SnapshotFeatureKernelError,
    build_snapshot_feature_kernel,
)
from app.behavior.paper_guidance_config import PaperGuidanceConfig
from app.behavior.paper_guidance_spine import run_paper_guidance_p1
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import (
    CandleBar,
    CandleSeries,
    ClosedCandleSnapshot,
    KillSwitchState,
    PaperGuidanceRequest,
    SystemMode,
    SystemModeValue,
    VwapOrbCprContextRequest,
)


IST = ZoneInfo("Asia/Kolkata")
PREVIOUS_DAY = date(2026, 9, 4)  # Friday
CURRENT_DAY = date(2026, 9, 7)   # Monday


def _ns(day: date, hour: int = 9, minute: int = 15) -> int:
    value = datetime.combine(day, time(hour, minute), tzinfo=IST)
    return int(value.timestamp() * 1_000_000_000)


def _session_rows(
    day: date,
    *,
    timeframe: str = "5m",
    count: int,
    sequence_start: int,
    price_base: float,
    volume_base: float = 100_000.0,
    missing_volume_offset: int | None = None,
    last_close_delta: float = 0.0,
) -> list[CandleBar]:
    duration = timeframe_duration_ns(timeframe)
    rows: list[CandleBar] = []
    for offset in range(count):
        open_price = price_base + offset * 0.08
        close = open_price + (0.05 if offset % 3 else -0.02)
        if offset == count - 1:
            close += last_close_delta
        rows.append(
            CandleBar(
                symbol="RELIANCE",
                timeframe=timeframe,
                timestamp_ns=_ns(day) + offset * duration,
                open=open_price,
                high=max(open_price, close) + 0.18,
                low=min(open_price, close) - 0.16,
                close=close,
                volume=None if offset == missing_volume_offset else volume_base + offset * 250.0,
                source="user_csv",
                sequence_number=sequence_start + offset,
            )
        )
    return rows


def _snapshot(
    *,
    previous_count: int = 75,
    current_count: int = 12,
    missing_current_volume: int | None = None,
    last_close_delta: float = 0.0,
    timeframe: str = "5m",
) -> ClosedCandleSnapshot:
    previous = _session_rows(
        PREVIOUS_DAY,
        timeframe=timeframe,
        count=previous_count,
        sequence_start=1,
        price_base=80.0,
        volume_base=900_000.0,
    )
    current = _session_rows(
        CURRENT_DAY,
        timeframe=timeframe,
        count=current_count,
        sequence_start=len(previous) + 1,
        price_base=100.0,
        volume_base=100_000.0,
        missing_volume_offset=missing_current_volume,
        last_close_delta=last_close_delta,
    )
    rows = [*previous, *current]
    duration = timeframe_duration_ns(timeframe)
    decision_time_ns = rows[-1].timestamp_ns + duration
    encoded = json.dumps(
        [row.model_dump(mode="json") for row in rows],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    snapshot_hash = hashlib.sha256(encoded).hexdigest()
    return ClosedCandleSnapshot(
        snapshot_version="closed-candle-snapshot.v1.87",
        snapshot_id=f"m31-c-{snapshot_hash[:16]}",
        snapshot_hash=snapshot_hash,
        symbol="RELIANCE",
        timeframe=timeframe,
        decision_time_ns=decision_time_ns,
        decision_time=datetime.fromtimestamp(
            decision_time_ns / 1_000_000_000,
            tz=timezone.utc,
        ).isoformat(),
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


def _canonical(snapshot: ClosedCandleSnapshot):
    kernel = build_snapshot_feature_kernel(snapshot)
    series = CandleSeries(
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        bars=snapshot.closed_ohlcv_bars,
        snapshot_id=snapshot.snapshot_id,
        schema_version=snapshot.source_schema_version,
    )
    request = VwapOrbCprContextRequest(
        series=series,
        decision_time_ns=snapshot.decision_time_ns,
    )
    return build_canonical_level_intelligence(request, feature_kernel=kernel), kernel, request


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


def _pg_series(*, bars: int = 40) -> CandleSeries:
    rows = _session_rows(
        CURRENT_DAY,
        count=bars,
        sequence_start=1,
        price_base=100.0,
    )
    return CandleSeries(
        symbol="RELIANCE",
        timeframe="5m",
        bars=rows,
        snapshot_id="m31-c-pg",
        schema_version="candles.v1",
    )


def _pg_request(series: CandleSeries | None = None) -> PaperGuidanceRequest:
    series = series or _pg_series()
    return PaperGuidanceRequest(
        symbol=series.symbol,
        timeframe=series.timeframe,
        series=series,
        decision_time_ns=series.bars[-1].timestamp_ns + timeframe_duration_ns(series.timeframe),
        timezone_offset_minutes=330,
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
                    "cache_version": "m31-c-test",
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


def _run_pg(request: PaperGuidanceRequest | None = None):
    return run_paper_guidance_p1(
        request or _pg_request(),
        mode=_mode(),
        kill_switch=_kill_switch(),
        config=PaperGuidanceConfig(),
    )


def _receipt(result, engine_id: str):
    return next(item for item in result.engine_receipts if item.engine_id == engine_id)


def test_m31c_001_session_vwap_resets_at_0915_and_uses_only_current_session():
    snapshot = _snapshot()
    result, kernel, _ = _canonical(snapshot)
    current_start = 75
    expected_num = sum(
        kernel.vectors.typical_prices[index] * float(kernel.vectors.volumes[index] or 0.0)
        for index in range(current_start, kernel.closed_bar_count)
    )
    expected_den = sum(
        float(kernel.vectors.volumes[index] or 0.0)
        for index in range(current_start, kernel.closed_bar_count)
    )

    assert result.session.session_id == CURRENT_DAY.isoformat()
    assert result.session.starts_at_session_open is True
    assert result.session.contiguous_from_session_open is True
    assert result.session_vwap.status == "AVAILABLE"
    assert result.session_vwap.value == pytest.approx(expected_num / expected_den, abs=1e-4)
    assert result.calculated_vwap is not None
    assert abs(result.calculated_vwap - result.session_vwap.value) > 5.0
    assert result.session_vwap.band_3_lower <= result.session_vwap.band_2_lower <= result.session_vwap.band_1_lower
    assert result.session_vwap.band_1_upper <= result.session_vwap.band_2_upper <= result.session_vwap.band_3_upper


def test_m31c_002_or5_or15_or30_are_time_windowed_not_global_first_three_bars():
    snapshot = _snapshot()
    result, _, _ = _canonical(snapshot)
    current = snapshot.closed_ohlcv_bars[75:]

    or5 = result.opening_range(5)
    or15 = result.opening_range(15)
    or30 = result.opening_range(30)
    assert (or5.status, or15.status, or30.status) == ("AVAILABLE", "AVAILABLE", "AVAILABLE")
    assert or5.source_bar_count == 1
    assert or15.source_bar_count == 3
    assert or30.source_bar_count == 6
    assert or5.high == pytest.approx(current[0].high)
    assert or5.low == pytest.approx(current[0].low)
    assert or15.high == pytest.approx(max(item.high for item in current[:3]))
    assert or15.low == pytest.approx(min(item.low for item in current[:3]))
    assert or30.high == pytest.approx(max(item.high for item in current[:6]))
    assert or30.low == pytest.approx(min(item.low for item in current[:6]))
    assert result.opening_range_high == pytest.approx(max(item.high for item in snapshot.closed_ohlcv_bars[:3]))
    assert result.opening_range_high != or15.high


def test_m31c_003_previous_session_pdh_pdl_close_and_cpr_are_pit_derived():
    snapshot = _snapshot()
    result, _, _ = _canonical(snapshot)
    previous = snapshot.closed_ohlcv_bars[:75]
    expected_high = max(item.high for item in previous)
    expected_low = min(item.low for item in previous)
    expected_close = previous[-1].close
    pivot = (expected_high + expected_low + expected_close) / 3.0
    bc_raw = (expected_high + expected_low) / 2.0
    tc_raw = pivot + (pivot - bc_raw)

    assert result.previous_session.status == "AVAILABLE"
    assert result.previous_session.session_id == PREVIOUS_DAY.isoformat()
    assert result.previous_session.source_bar_count == 75
    assert result.previous_session.high == pytest.approx(expected_high)
    assert result.previous_session.low == pytest.approx(expected_low)
    assert result.previous_session.close == pytest.approx(expected_close)
    assert result.previous_session.source_hash and len(result.previous_session.source_hash) == 64
    assert result.cpr.status == "AVAILABLE"
    assert result.cpr.pivot == pytest.approx(round(pivot, 4))
    assert result.cpr.bc == pytest.approx(round(min(bc_raw, tc_raw), 4))
    assert result.cpr.tc == pytest.approx(round(max(bc_raw, tc_raw), 4))
    assert result.cpr.source_hash == result.previous_session.source_hash


def test_m31c_004_missing_current_volume_is_unavailable_not_zero_or_partial_vwap():
    snapshot = _snapshot(missing_current_volume=5)
    result, _, _ = _canonical(snapshot)

    assert result.session_vwap.status == "UNAVAILABLE"
    assert result.session_vwap.value is None
    assert result.session_vwap.missing_volume_count == 1
    assert "missing volume" in (result.session_vwap.reason or "").lower()
    assert result.calculated_vwap is not None
    assert any("missing volume" in reason.lower() for reason in result.missing_reasons)


def test_m31c_005_incomplete_previous_session_withholds_pdh_pdl_and_cpr():
    snapshot = _snapshot(previous_count=74)
    result, _, _ = _canonical(snapshot)

    assert result.previous_session.status == "UNAVAILABLE"
    assert result.previous_session.high is None
    assert result.previous_session.low is None
    assert result.previous_session.close is None
    assert result.cpr.status == "UNAVAILABLE"
    assert result.cpr.pivot is None
    assert result.canonical_pdh_state == "unknown"
    assert result.canonical_pdl_state == "unknown"
    assert any("previous" in reason.lower() for reason in result.missing_reasons)


def test_m31c_006_opening_range_is_pending_until_complete_window_closes():
    snapshot = _snapshot(current_count=3)
    result, _, _ = _canonical(snapshot)

    assert result.opening_range(5).status == "AVAILABLE"
    assert result.opening_range(15).status == "AVAILABLE"
    assert result.opening_range(30).status == "PENDING"
    assert result.opening_range(30).high is None
    assert "not authoritative" in (result.opening_range(30).reason or "").lower()


def test_m31c_007_future_or_incomplete_bar_cannot_enter_kernel_or_levels():
    snapshot = _snapshot()
    unsafe = snapshot.model_copy(
        update={"decision_time_ns": snapshot.last_bar_close_time_ns - 1}
    )
    with pytest.raises(SnapshotFeatureKernelError, match="closing after decision_time_ns"):
        build_snapshot_feature_kernel(unsafe)


def test_m31c_008_same_d2_replays_same_level_hash_and_changed_closed_candle_changes_it():
    first, _, _ = _canonical(_snapshot())
    replay, _, _ = _canonical(_snapshot())
    changed, _, _ = _canonical(_snapshot(last_close_delta=0.25))

    assert first.provenance.canonical_level_hash == replay.provenance.canonical_level_hash
    assert first.provenance.canonical_level_hash != changed.provenance.canonical_level_hash
    assert first.provenance.source_snapshot_hash == replay.provenance.source_snapshot_hash


def test_m31c_009_legacy_compatibility_projection_is_exact_for_current_d6_contract():
    snapshot = _snapshot()
    result, _, request = _canonical(snapshot)
    legacy = analyze_level_context(request)

    for field in (
        "calculated_vwap",
        "price_vs_vwap_pct",
        "vwap_state",
        "opening_range_high",
        "opening_range_low",
        "opening_range_state",
        "cpr_pivot",
        "cpr_bc",
        "cpr_tc",
        "cpr_state",
        "pdh_state",
        "pdl_state",
        "vpd_state",
        "support_resistance_flags",
        "level_respect_score",
        "blocks_trade",
        "reasons",
    ):
        assert getattr(result, field) == getattr(legacy, field)


def test_m31c_010_canonical_route_reuses_kernel_and_computes_levels_exactly_once(monkeypatch):
    counts = {"kernel": 0, "levels": 0}
    real_kernel = m31_spine.build_snapshot_feature_kernel
    real_levels = pg_spine.build_canonical_level_intelligence

    def counted_kernel(snapshot):
        counts["kernel"] += 1
        return real_kernel(snapshot)

    def counted_levels(request, **kwargs):
        counts["levels"] += 1
        return real_levels(request, **kwargs)

    monkeypatch.setattr(m31_spine, "build_snapshot_feature_kernel", counted_kernel)
    monkeypatch.setattr(pg_spine, "build_canonical_level_intelligence", counted_levels)
    result = _run_pg()
    receipt = _receipt(result, "LEVEL_CONTEXT")

    assert counts == {"kernel": 1, "levels": 1}
    assert receipt.output_summary["calculation_audit"]["canonical_level_compute_count"] == 1
    assert receipt.output_summary["calculation_audit"]["feature_kernel_reused"] is True
    assert receipt.output_summary["provenance"]["source_snapshot_hash"] == result.snapshot_hash


def test_m31c_011_decision_context_levels_are_bounded_receipt_backed_evidence(monkeypatch):
    captured = {}

    def capture_context(**kwargs):
        context = real_build_context(**kwargs)
        captured["context"] = context
        return context

    monkeypatch.setattr(pg_spine, "build_paper_guidance_decision_context", capture_context)
    result = _run_pg()
    context = captured["context"]
    block = context.levels
    receipt = _receipt(result, "LEVEL_CONTEXT")

    assert block.source_engine == "LEVEL_CONTEXT"
    assert block.source_snapshot_hash == result.snapshot_hash
    assert block.source_output_hash == receipt.output_hash
    assert block.used_for_probability is False
    assert block.claims_trade_authority is False
    assert block.payload["canonical_level_intelligence"] is True
    assert "opening_ranges" in block.payload
    assert "closed_ohlcv_bars" not in block.payload
    assert "bars" not in block.payload
    assert "dataframe" not in str(block.payload).lower()


def test_m31c_012_level_engine_failure_blocks_before_d6_and_cannot_become_neutral(monkeypatch):
    monkeypatch.setattr(
        pg_spine,
        "build_canonical_level_intelligence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("forced-level-failure")),
    )
    result = _run_pg()

    assert result.final_band == "WAIT"
    assert result.next_action == "DO_NOTHING"
    assert "FINAL_CONFLUENCE_ARBITER" not in result.engines_run
    assert "D6_ARBITER:decision_context_block" in result.engines_skipped
    assert result.risk_summary["decision_context"] is None
    assert any("LEVEL_CONTEXT" in blocker for blocker in result.blockers)


def test_m31c_013_receipt_hash_and_provenance_are_deterministic_and_d2_bound():
    first = _run_pg()
    second = _run_pg()
    first_receipt = _receipt(first, "LEVEL_CONTEXT")
    second_receipt = _receipt(second, "LEVEL_CONTEXT")

    assert first_receipt.source_snapshot_hash == first.snapshot_hash
    assert first_receipt.output_hash == second_receipt.output_hash
    assert first_receipt.output_summary == second_receipt.output_summary
    assert first_receipt.output_summary["provenance"]["source_snapshot_hash"] == first.snapshot_hash
    assert len(first_receipt.output_summary["provenance"]["canonical_level_hash"]) == 64


def test_m31c_014_timeframe_aware_opening_ranges_do_not_assume_three_bars():
    snapshot = _snapshot(previous_count=25, current_count=4, timeframe="15m")
    result, _, _ = _canonical(snapshot)

    assert result.opening_range(5).status == "UNAVAILABLE"
    assert result.opening_range(5).required_bar_count is None
    assert result.opening_range(15).status == "AVAILABLE"
    assert result.opening_range(15).source_bar_count == 1
    assert result.opening_range(30).status == "AVAILABLE"
    assert result.opening_range(30).source_bar_count == 2


def test_m31c_015_level_intelligence_is_bounded_fast_and_has_zero_authority():
    snapshot = _snapshot()
    kernel = build_snapshot_feature_kernel(snapshot)
    series = CandleSeries(
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        bars=snapshot.closed_ohlcv_bars,
        snapshot_id=snapshot.snapshot_id,
        schema_version=snapshot.source_schema_version,
    )
    request = VwapOrbCprContextRequest(series=series, decision_time_ns=snapshot.decision_time_ns)

    started = perf_counter()
    results = [
        build_canonical_level_intelligence(request, feature_kernel=kernel)
        for _ in range(50)
    ]
    elapsed = perf_counter() - started
    summary = results[-1].receipt_summary()

    assert elapsed < 2.0
    assert all(item.calculation_version == LEVEL_INTELLIGENCE_VERSION for item in results)
    assert summary["used_for_probability"] is False
    assert summary["trade_allowed"] is False
    assert summary["order_routing_enabled"] is False
    assert summary["live_trading_blocked"] is True
    assert len(json.dumps(summary)) < 20_000
